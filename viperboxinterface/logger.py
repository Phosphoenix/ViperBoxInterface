from __future__ import annotations

import logging
import logging.handlers
import pickle
import socketserver
import struct
import time
from pathlib import Path

# https://docs.python.org/3/howto/logging-cookbook.html#sending-and-receiving-logging-events-across-a-network


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """

    def handle(self):
        """Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self.unPickle(chunk)
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def unPickle(self, data):
        return pickle.loads(data)

    def handleLogRecord(self, record):
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """Simple TCP socket-based logging receiver suitable for testing."""

    allow_reuse_address = True

    def __init__(
        self,
        host="localhost",
        port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        handler=LogRecordStreamHandler,
    ):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        import select

        abort = 0
        while not abort:
            rd, wr, ex = select.select([self.socket.fileno()], [], [], self.timeout)
            if rd:
                self.handle_request()
            abort = self.abort


def start_log_server(session_datetime):
    log_folder = Path.cwd() / "logs"
    log_file = f"log_{session_datetime}.log"
    log_folder.mkdir(parents=True, exist_ok=True)
    log_file_path = log_folder.joinpath(log_file)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s - %(asctime)s - %(name)s - %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file_path),
            # logging.StreamHandler(sys.stdout),
        ],
    )
    tcpserver = LogRecordSocketReceiver()
    print("About to start TCP server...")
    tcpserver.serve_until_stopped()


if __name__ == "__main__":
    start_log_server(time.strftime("%Y%m%d_%H%M%S"))
