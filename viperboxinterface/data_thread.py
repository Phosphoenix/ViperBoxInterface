import logging
import multiprocessing
import socket
import threading
import time

import numpy as np
from scipy import signal

import viperboxinterface.NeuraviperPy as NVP


class _DataSenderThread(multiprocessing.Process):
    def __init__(
        self,
        NUM_SAMPLES: int,
        FREQ: int,
        NUM_CHANNELS: int,
        mtx: np.ndarray,
        use_mapping: bool = True,
        port=9001,
    ):
        super().__init__()
        self.thread = None
        self.stop_stream = None
        self.use_mapping = use_mapping

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        socketHandler = logging.handlers.SocketHandler(
            "localhost",
            logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        )
        self.logger.addHandler(socketHandler)

        self.NUM_SAMPLES = NUM_SAMPLES
        self.FREQ = FREQ
        self.NUM_CHANNELS = NUM_CHANNELS
        self.bufferInterval = self.NUM_SAMPLES / self.FREQ
        self._prep_lfilter(f0=50.0, Q=30.0, FREQ=self.FREQ)
        self._create_header(
            NUM_CHANNELS=self.NUM_CHANNELS,
            NUM_SAMPLES=self.NUM_SAMPLES,
        )

        self.mtx = mtx
        self.tcpServer = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.tcpServer.bind(("localhost", port))
        self.tcpServer.listen(1)
        self.tcpServer.settimeout(None)
        self.tcpServer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.logger.info("Waiting for external connection to start...")
        (tcpClient, socket_address) = self.tcpServer.accept()
        self.logger.info("Connected.")
        self.tcpClient = tcpClient
        self.socket_address = socket_address

    def _prep_lfilter(self, f0: float = 50.0, Q: float = 30.0, FREQ: int = 20000):
        b, a = signal.iirnotch(f0, Q, FREQ)
        z = np.zeros((self.NUM_CHANNELS, 2))
        self.b, self.a, self.z = b, a, z

    def _create_header(self, NUM_CHANNELS: int = 60, NUM_SAMPLES: int = 500):
        # ---- DEFINE HEADER VALUES ---- #
        offset = 0  # Offset of bytes in this packet; only used for buffers > ~64 kB
        dataType = 2  # Enumeration value based on OpenCV.Mat data types
        elementSize = 2  # Number of bytes per element. elementSize = 2 for U16
        # Data types:   [ U8, S8, U16, S16, S32, F32, F64 ]
        # Enum value:   [  0,  1,   2,   3,   4,   5,   6 ]
        # Element Size: [  1,  1,   2,   2,   4,   4,   8 ]
        # Add two extra channels to NUM_CHANNELS for 2 TTL bits
        bytesPerBuffer = (NUM_CHANNELS + 2) * NUM_SAMPLES * elementSize
        # Add two extra channels to NUM_CHANNELS for 2 TTL bits
        self.header = (
            np.array([offset, bytesPerBuffer], dtype="i4").tobytes()
            + np.array([dataType], dtype="i2").tobytes()
            + np.array(
                [elementSize, NUM_CHANNELS + 2, NUM_SAMPLES], dtype="i4"
            ).tobytes()
        )

    def _time(self):
        return time.time_ns() / (10**9)

    def _extract_bits(self, value):
        # value AND 0b00000010, then shift right by 1
        bit_1 = ((value & (1 << 1)) >> 1) * 65535
        # value AND 0b00000100, then shift right by 2
        bit_2 = ((value & (1 << 2)) >> 2) * 65536
        return bit_1, bit_2

    def _prepare_databuffer(self, databuffer: np.ndarray, z, bits) -> tuple:
        if self.use_mapping:
            databuffer = (databuffer @ self.mtx).T
        else:
            databuffer = databuffer.T
        databuffer, z = signal.lfilter(self.b, self.a, databuffer, axis=1, zi=z)
        databuffer = np.concatenate((databuffer, bits.T), axis=0)
        databuffer = databuffer.astype("uint16")
        databuffer = databuffer.copy(order="C")
        return databuffer.tobytes(), z

    def send_data(self, rec_path, probe):
        self.logger.info("Started sending data to Open Ephys")
        # TODO: How to handle data streams from multiple probes? align on timestamp?
        self.logger.debug(f"Recording path: {rec_path}")
        send_data_read_handle = NVP.streamOpenFile(str(rec_path), probe)
        counter = 0
        # create a bit of a buffer such that you won't run out of packets
        # when updating stimulation settings.
        # time.sleep(1.5)
        databuffer = np.zeros((self.NUM_CHANNELS + 2, 500), dtype="uint16")
        t0 = self._time()
        while not self.stop_stream.is_set():
            counter += 1
            packets = NVP.streamReadData(send_data_read_handle, self.NUM_SAMPLES)
            count = len(packets)
            if count == 0:
                self.logger.info("No packets read.")
                break
            if count < self.NUM_SAMPLES:
                asdf = [packets[i].timestamp for i in range(500)]
                subtracted = np.asarray([asdf[i + 1] - asdf[i] - 5 for i in range(499)])
                self.logger.debug(
                    f" max, min value in time difference{subtracted.max(), subtracted.min()}"
                )
                self.logger.debug(f"Time difference between packets: {subtracted}")
                self.logger.info(
                    f"Out of packets; {count} packets read. Sending empty data."
                )
                databuffer = np.tile(databuffer[-1, :], (500, 1)).T
                self.tcpClient.sendto(self.header + databuffer, self.socket_address)
                t2 = self._time()
                while (t2 - t0) < counter * self.bufferInterval:
                    t2 = self._time()
                time.sleep(1)
                counter += 40
                continue
            databuffer = np.asarray(
                [packets[i].data for i in range(self.NUM_SAMPLES)],
                dtype="uint16",
            )
            TTL_bits = np.asarray(
                [
                    self._extract_bits(packets[i].status)
                    for i in range(self.NUM_SAMPLES)
                ],
                dtype="uint16",
            )
            if counter % 40 == 0:
                TTL_bits = np.zeros((self.NUM_SAMPLES, 2), dtype="uint16")
            databuffer, self.z = self._prepare_databuffer(databuffer, self.z, TTL_bits)
            print(databuffer.shape)
            self.tcpClient.sendto(self.header + databuffer, self.socket_address)
            t2 = self._time()
            while (t2 - t0) < counter * self.bufferInterval:
                t2 = self._time()
        NVP.streamClose(send_data_read_handle)

    def _send_empty(self):
        self.logger.info("Started sending empty data to Open Ephys")
        counter = 0
        t0 = self._time()
        for _ in range(10):
            counter += 1
            # Add two extra channels to NUM_CHANNELS for 2 TTL bits
            databuffer = np.zeros(
                (self.NUM_CHANNELS + 2, 500), dtype="uint16"
            ).tobytes()
            self.tcpClient.sendto(self.header + databuffer, self.socket_address)
            t2 = self._time()
            while (t2 - t0) < counter * self.bufferInterval:
                t2 = self._time()

    def start(self, recording_path, probe, empty=False):
        if self.thread is not None and self.thread.is_alive():
            self.logger.info("Thread already running")
            return
        if empty:
            self.stop_stream = threading.Event()
            self.thread = threading.Thread(target=self._send_empty, daemon=True)
            self.thread.start()
        else:
            self.stop_stream = threading.Event()
            self.thread = threading.Thread(
                target=self.send_data,
                args=(recording_path, probe),
                daemon=True,
            )
            self.thread.start()

    def stop(self):
        self.stop_stream.set()
        self.thread.join()

    def pause(self):
        self.stop_stream.set()

    def shutdown(self):
        self.stop()
        self.tcpServer.close()
        self.tcpClient.close()

    def is_connected(self):
        try:
            self.tcpClient.getpeername()
            return True
        except OSError:
            return False
