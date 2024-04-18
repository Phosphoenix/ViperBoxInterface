"""******************  (C) IMEC vzw 2023  *************************************
* NeuraViPeR ASIC V1 Test                                                     *
*******************************************************************************
* Source filename :     NeuraviperPy_imec.py
*
*
* History :
* ~~~~~~~
* Version   Date        Authors   Comments
* v0.1      19/09/2022  NVG       Preliminary version (nvrAPIv0.2-MSVC-x64.zip)
*                       PHE       Added comments... #[PHE]...
* v0.2      24/10/2022  PHE       Add functionality to read packets
*                                 Distinction "IMEC"-internal functions
* v0.3      25/10/2022  PHE       API update: nvrAPIv0.3-MSVC-x64.zip
* v0.4      17/01/2023  PHE       API update: nvrAPIv0.5-MSVC-x64.zip
*                                 Update readElectrodeData()
* v0.5      09/02/2023  PHE       API update: nvrAPIv0.7-MSVC-x64.zip
*                                 readElectrodeData(): remove 12bit data mask
*                                 Add free_library()
* v0.99     17/02/2023  PHE       Pre-release IMTEK:
*                                 API update: nvrAPIv0.8-MSVC-x64.zip
*                                 Original readElectrodeData()
*                                 Update setFileStream()
* v1.0      23/02/2023  PHE       Release:
*                                 API update: nvrAPIv1.0-MSVC-x64.zip
*                                 Added comments with DLL loading
* v1.3      05/07/2023  PHE       API update: nvrAPIv1.3-MSVC-x64.zip
* v1.5      20/10/2023  PHE       API update: nvrAPIv1.6-MSVC-x64.zip
*                                 Add setGain()
*                                 Add writeChannelConfiguration()
*                                 Add setOsImage()
*                                 Add writeOsConfiguration()
*******************************************************************************
* IMPORTANT reminder:
*
* All function parameters: zero-indexed !!!
*
****************************************************************************
"""

from __future__ import annotations

import ctypes
import logging
import logging.handlers
import os
import re
import sys
from ctypes import (
    POINTER,
    c_bool,
    c_char,
    c_char_p,
    c_double,
    c_int,
    c_int16,
    c_size_t,
    c_uint,
    c_uint8,
    c_void_p,
    sizeof,
)
from enum import IntEnum
from inspect import signature
from sys import platform as _platform
from types import FunctionType

# logger = logging.getLogger(__name__)
logger = logging.getLogger("NVP")
logger.setLevel(logging.DEBUG)
socketHandler = logging.handlers.SocketHandler(
    "localhost",
    logging.handlers.DEFAULT_TCP_LOGGING_PORT,
)
logger.addHandler(socketHandler)

if not (_platform.startswith("win32") or _platform.startswith("cygwin")):
    raise RuntimeError("Not supported on this platform")

_bundled_lib_path = None
_lib_path = None
_arch = "x86" if sizeof(c_void_p) == 4 else "x64"
_pattern = f"NeuraviperAPI_[0-9]+_[0-9]+(_[0-9]+)?_{_arch}.dll"

for path in sys.path:
    _this_dir = os.path.abspath(path)

    try:
        _files = [f for f in os.listdir(_this_dir) if re.search(_pattern, f)]
    except FileNotFoundError:
        continue

    if _files:
        _bundled_lib_path = os.path.join(_this_dir, sorted(_files, reverse=True)[0])
        _lib_path = os.getenv("NEUROPIXPY_LIB", _bundled_lib_path)
        break

# If we are running Cygwin/MSYS python, ensure that we use a valid Windows path
if _platform.startswith("cygwin"):
    import subprocess

    _lib_path = (
        subprocess.check_output(["cygpath", "-w", _lib_path]).decode("utf-8").strip()
    )

try:
    print(f"Found NeuraViPeR API DLL: {_lib_path}")
    _nvplib = ctypes.CDLL(_lib_path)
    print("Successfully loaded", _nvplib)
except Exception as e:
    raise RuntimeError(f"Could not load NeuraViPeR API DLL: {_lib_path}") from e


def free_library() -> None:
    # Frees the loaded library
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.FreeLibrary.argtypes = [ctypes.wintypes.HMODULE]
    kernel32.FreeLibrary(_nvplib._handle)


#
# C Wrapper Plumbing
#


def _c_fn(*args):
    """Dummy wrapped function"""
    None


def _c_function(function_name, res_type, arg_types):
    """Create wrapped C API function.

    Parameters
    ----------
        function_name (string): Name of the function to be wrapped
        res_type (type): Type of return value
        arg_types (List[type]): List of argument types
    """
    c_fn = getattr(_nvplib, function_name)
    c_fn.restype = res_type
    c_fn.argtypes = arg_types
    logging.debug(
        f"NVP API function {function_name} called with argument types {arg_types}",
    )
    return c_fn


def _wrap_function(function_name, res_type, arg_types):
    """Implicit wrapping of imported C function.
    Injects `_c_fn' into the environment of wrapped function.
    """
    # Make a copy of the global environment and inject C function
    env = globals().copy()
    env["_c_fn"] = _c_function(function_name, res_type, arg_types)

    def decorator(func):
        new_fn = FunctionType(func.__code__, env, name=func.__name__)
        new_fn.__signature__ = signature(func)
        return new_fn

    return decorator


class Struct(ctypes.Structure):
    ":meta private:"

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        d = {field[0]: getattr(self, field[0]) for field in self._fields_}
        return f"<({self.__class__.__name__}){d}>"


#
# Constants and Enums
#

# TODO: Error codes


class LogLevel(IntEnum):
    "Enumeration for logging level"

    VERBOSE = 5
    DEBUG = 4
    INFO = 3
    WARNING = 2
    ERROR = 1
    NONE = 0


class NPPlatform(IntEnum):
    "Enumeration for Neuropixels Platform types."

    NONE = 0
    USB = 1

    def __str__(self) -> str:
        return self.name


class DeviceEmulatorMode(IntEnum):
    OFF = 0
    STATIC = 1
    LINEAR = 2


class DeviceEmulatorType(IntEnum):
    OFF = 0
    EMULATED_PROBE = 1


class SyncMode(IntEnum):
    MASTER = 0
    SLAVE = 1


class TriggerMode(IntEnum):
    MASTER = 0
    SLAVE = 1


#
# Datatypes
#

NVP_ErrorCode = c_int

DeviceHandle = c_void_p

StreamHandle = c_void_p

ElectrodeInput = c_int


class BasestationID(Struct):
    "BasestationID"

    _fields_ = [("platformid", c_int), ("ID", c_int)]


_HARDWAREID_PN_LEN = 40


class HardwareID(Struct):
    "HardwareID"

    _pack_ = 1
    _fields_ = [
        ("version_major", ctypes.c_uint8),
        ("version_minor", ctypes.c_uint8),
        ("serial_number", ctypes.c_uint64),
        ("_product_number", c_char * _HARDWAREID_PN_LEN),
    ]

    @property
    def product_number(self) -> str:
        try:
            pn = self._product_number.decode("ASCII")
            return pn
        except UnicodeDecodeError:
            return ""

    @product_number.setter
    def product_number(self, value: str):
        self._product_number = value.encode("ASCII")

    @property
    def version(self) -> tuple[c_uint8, c_uint8]:
        return (self.version_major, self.version_minor)

    @version.setter
    def version(self, v):
        (maj, min) = v
        self.version_major = ctypes.c_uint8(maj)
        self.version_minor = ctypes.c_uint8(min)


class PacketInfo(Struct):
    "PacketInfo"

    _fields_ = [
        ("Timestamp", ctypes.c_uint32),
        ("Status", ctypes.c_uint16),
        ("payloadlength", ctypes.c_uint16),
        ("session_id", ctypes.c_uint8),
    ]


class Packet:
    def __init__(self, timestamp, status, payloadlength, sessionID, data):
        self.timestamp = timestamp
        self.status = status
        self.payloadlength = payloadlength
        self.sessionID = sessionID
        self.data = data


class DiagStats(Struct):
    "DiagStats"

    _fields_ = [
        ("total_bytes", ctypes.c_uint64),
        ("packet_count", ctypes.c_uint32),
        ("triggers", ctypes.c_uint32),
        ("session_mismatch", ctypes.c_uint32),
        ("err_bad_magic", ctypes.c_uint32),
        ("err_bad_crc", ctypes.c_uint32),
        ("err_count", ctypes.c_uint32),
        ("err_serdes", ctypes.c_uint32),
        ("err_lock", ctypes.c_uint32),
        ("err_pop", ctypes.c_uint32),
        ("err_sync", ctypes.c_uint32),
    ]


error_dct = {
    0: "SUCCESS, The function returned sucessfully",
    1: "FAILED, Unspecified failure",
    2: "ALREADY_OPEN, A board was already open",
    3: "NOT_OPEN, The function cannot execute, because the board or port is not open",
    4: "IIC_ERROR, An error occurred while accessing devices on the BS i2c bus",
    5: "VERSION_MISMATCH, FPGA firmware version mismatch",
    6: "PARAMETER_INVALID, A parameter had an illegal value or out of range",
    7: "UART_ACK_ERROR, uart communication on the serdes link failed to receive an "
    "acknowledgement",
    8: "TIMEOUT, the function did not complete within a restricted period of time",
    9: "WRONG_CHANNEL, illegal channel or channel group number",
    10: "WRONG_BANK, illegal electrode bank number",
    11: "WRONG_REF, a reference number outside the valid range was specified",
    12: "WRONG_INTREF, an internal reference number outside the valid range was "
    "specified",
    13: "CSV_READ_ERROR, an parsing error occurred while reading a malformed CSV file.",
    14: "BIST_ERROR, a BIST operation has failed",
    15: "FILE_OPEN_ERROR, The file could not be opened",
    16: "TIMESTAMPNOTFOUND, the specified timestamp could not be found in the stream",
    17: "FILE_IO_ERR, a file IO operation failed",
    18: "OUTOFMEMORY, the operation could not complete due to insufficient process "
    "memory",
    19: "NO_LOCK, missing serializer clock. Probably bad cable or connection",
    20: "WRONG_AP, AP gain number out of range",
    21: "WRONG_LFP, LFP gain number out of range",
    22: "IO_ERROR, a data stream IO error occurred.",
    23: "NO_SLOT, no NeuraViPeR board found at the specified slot number",
    24: "WRONG_SLOT, the specified slot is out of bound",
    25: "WRONG_PORT, the specified port is out of bound",
    26: "STREAM_EOF, The stream is at the end of the file, but more data was expected",
    27: "HDRERR_MAGIC, The packet header is corrupt and cannot be decoded",
    28: "HDRERR_CRC, The packet header’s crc is invalid",
    29: "WRONG_PROBESN, The probe serial number does not match the calibration data",
    30: "PROGRAMMINGABORTED, the flash programming was aborted",
    31: "WRONG_DOCK_ID, the specified probe id is out of bound",
    32: "NO_LINK, no head stage was detected",
    33: "NO_MEZZANINE, no mezzanine board was detected",
    34: "NO_PROBE, no probe was detected",
    35: "WRONG_OUTPUT_STAGE, Output stage number is out of bounds",
    36: "WRONG_STIM_UNIT, Stimulation unit number is out of bounds",
    37: "ERROR_SR_CHAIN_CH, Validation of channel configuration SR chain data upload "
    "failed",
    38: "ERROR_SR_CHAIN_OS, Validation of output stage SR chain data upload failed",
    39: "ERROR_SR_CHAIN_SU, Validation of stimulation unit SR chain data upload failed",
    40: "ERROR_SR_CHAIN_GEN, Validation of general configuration SR chain data upload "
    "failed",
    41: "DEVICE_NOT_FOUND, Basestation with given serial number not found",
    42: "INVALID_DEVICE_HANDLE, Invalid device handle",
    43: "ILLEGAL_HANDLE, the value of the ‘handle’ parameter is not valid.",
    44: "OBJECT_MISMATCH, the object type is not of the expected class",
    45: "READBACK_ERROR, a BIST readback verification failed",
    46: "NOTSUPPORTED, the function is not supported",
    47: "NOTIMPLEMENTED, the function is not implemented",
}

#
# Helpers
#


@_wrap_function("getLastErrorMessage", c_size_t, [c_char_p, c_size_t])
def getLastError() -> str:
    """Returns last error message reported by API.

    :rtype: String
    """
    buf = ctypes.create_string_buffer(256)
    _c_fn(buf, 256)
    return buf.value.decode("utf-8")


class NeuraviperAPIError(Exception):
    def __init__(self, errorcode, message=False):
        if not message:
            super().__init__(getLastError())
        else:
            super().__init__(message)
        self.errorcode = errorcode


def __assertnvperror(nvperror):
    if nvperror != 0:
        logger.warning(error_dct[nvperror])
        print(f"custom print by me: {error_dct[nvperror]}")
        raise NeuraviperAPIError(nvperror)
    else:
        logging.debug("Previous NVP API call successful")


@_wrap_function("getLogLevel", c_int, [])
def getLogLevel() -> LogLevel:
    lvl = _c_fn()
    return LogLevel(lvl)


def setLogLevel(level: LogLevel) -> None:
    """Set the logging level of the API.

    :param level: Required logging level
    :type level: DebugLevel
    """
    if not isinstance(level, LogLevel):
        raise NeuraviperAPIError(
            42,
            "Debug level must be set using DebugLevel enumeration!",
        )
    _nvplib.setLogLevel(level.value)


#
# API
#


@_wrap_function("getAPIVersion", None, [POINTER(c_int), POINTER(c_int), POINTER(c_int)])
def getAPIVersion() -> tuple[int, int, int]:
    """Get the API version.

    :return: A tuple with the major, minor, and patch version numbers
    :rtype: Tuple[int, int, int]
    """
    v_maj = c_int(0)
    v_min = c_int(0)
    v_patch = c_int(0)
    _c_fn(v_maj, v_min, v_patch)
    return (v_maj.value, v_min.value, v_patch.value)


@_wrap_function("scanBS", NVP_ErrorCode, [])
def scanBS() -> None:
    __assertnvperror(_c_fn())


@_wrap_function("getDeviceList", c_int, [POINTER(BasestationID), c_int])
def getDeviceList(count: int) -> list[BasestationID]:
    """Returns a list of connected devices.

    :param count: Maximum number of devices to be reported
    :type count: int
    :rtype: List[BasestationID]
    """
    arr = (BasestationID * count)()
    ret = _c_fn(arr, count)
    return list(arr)[0:ret]


@_wrap_function("createHandle", NVP_ErrorCode, [POINTER(DeviceHandle), c_int])
def createHandle(serial_number: int) -> DeviceHandle:
    ptr = c_void_p()
    __assertnvperror(_c_fn(ctypes.byref(ptr), serial_number))
    return ptr


@_wrap_function("destroyHandle", NVP_ErrorCode, [DeviceHandle])
def destroyHandle(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("openBS", NVP_ErrorCode, [DeviceHandle])
def openBS(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("closeBS", NVP_ErrorCode, [DeviceHandle])
def closeBS(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("openProbes", NVP_ErrorCode, [DeviceHandle])
def openProbes(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("closeProbes", NVP_ErrorCode, [DeviceHandle])
def closeProbes(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("init", NVP_ErrorCode, [DeviceHandle, c_uint8])
def init(handle: DeviceHandle, probe: int):
    __assertnvperror(_c_fn(handle, probe))


@_wrap_function(
    "transferSPI",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, POINTER(c_uint8), POINTER(c_uint8), c_size_t],
)
def transferSPI(handle: DeviceHandle, probe: int, buffer: bytes) -> bytes:
    size = len(buffer)
    output = (c_uint8 * size).from_buffer_copy(buffer)
    input = (c_uint8 * size)()
    __assertnvperror(_c_fn(handle, probe, output, input, size))
    return bytes(input)


@_wrap_function(
    "writeSPI",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, POINTER(c_uint8), c_size_t],
)
def writeSPI(handle: DeviceHandle, probe: int, buffer: bytes):
    size = len(buffer)
    output = (c_uint8 * size).from_buffer_copy(buffer)
    __assertnvperror(_c_fn(handle, probe, output, size))


@_wrap_function(
    "writeI2C",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_uint8, POINTER(c_uint8), c_size_t],
)
def writeI2C(
    handle: DeviceHandle,
    device: int,
    address: int,
    bytearr: bytearray,
) -> None:
    data = (c_char * len(bytearr)).from_buffer(bytearr)
    __assertnvperror(_c_fn(handle, device, address, data, len(bytearr)))


@_wrap_function(
    "readI2C",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_uint8, POINTER(c_uint8), c_size_t],
)
def readI2C(handle: DeviceHandle, device: int, address: int, length: int) -> bytearray:
    b = bytearray(length)
    ptr = (c_char * length).from_buffer(b)
    __assertnvperror(_c_fn(handle, device, address, ptr, length))
    return b


@_wrap_function(
    "writeI2Cctrl",
    NVP_ErrorCode,
    [DeviceHandle, c_int, c_uint8, c_uint8, POINTER(c_uint8), c_size_t],
)
def writeI2Cctrl(
    handle: DeviceHandle,
    device: int,
    address: int,
    bytearr: bytearray,
) -> None:
    data = (c_char * len(bytearr)).from_buffer(bytearr)
    __assertnvperror(_c_fn(handle, device, address, data, len(bytearr)))


@_wrap_function(
    "readI2Cctrl",
    NVP_ErrorCode,
    [DeviceHandle, c_int, c_uint8, c_uint8, POINTER(c_uint8), c_size_t],
)
def readI2Cctrl(
    handle: DeviceHandle,
    device: int,
    address: int,
    length: int,
) -> bytearray:
    b = bytearray(length)
    ptr = (c_char * length).from_buffer(b)
    __assertnvperror(_c_fn(handle, device, address, ptr, length))
    return b


@_wrap_function("setGain", NVP_ErrorCode, [DeviceHandle, c_uint8, c_int, c_int])
def setGain(handle: DeviceHandle, probe: int, channel: int, gain: int):
    __assertnvperror(_c_fn(handle, probe, channel, gain))


@_wrap_function(
    "writeChannelConfiguration",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_bool],
)
def writeChannelConfiguration(handle: DeviceHandle, probe: int, readCheck: bool):
    __assertnvperror(_c_fn(handle, probe, readCheck))


@_wrap_function("setOSimage", NVP_ErrorCode, [DeviceHandle, c_uint8, POINTER(c_uint8)])
def setOSimage(handle: DeviceHandle, probe: int, buffer: bytes):
    size = len(buffer)
    output = (c_uint8 * size).from_buffer_copy(buffer)
    __assertnvperror(_c_fn(handle, probe, output))


@_wrap_function(
    "writeOSConfiguration",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_bool, c_bool],
)
def writeOsConfiguration(
    handle: DeviceHandle,
    probe: int,
    readCheck: bool,
    skip_sync_check: bool,
):
    __assertnvperror(_c_fn(handle, probe, readCheck, skip_sync_check))


@_wrap_function("arm", NVP_ErrorCode, [DeviceHandle])
def arm(handle: DeviceHandle) -> None:
    __assertnvperror(_c_fn(handle))


@_wrap_function("setSWTrigger", NVP_ErrorCode, [DeviceHandle])
def setSWTrigger(handle: DeviceHandle) -> None:
    __assertnvperror(_c_fn(handle))


@_wrap_function("setSyncClockFrequency", NVP_ErrorCode, [DeviceHandle, c_double])
def setSyncClockFrequency(handle: DeviceHandle, frequency: float) -> None:
    __assertnvperror(_c_fn(handle, frequency))


@_wrap_function(
    "getSyncClockFrequency",
    NVP_ErrorCode,
    [DeviceHandle, POINTER(c_double)],
)
def getSyncClockFrequency(handle: DeviceHandle) -> float:
    freq = c_double(0)
    __assertnvperror(_c_fn(handle, freq))
    return freq.value


@_wrap_function("setSyncClockPeriod", NVP_ErrorCode, [DeviceHandle, c_uint])
def setSyncClockPeriod(handle: DeviceHandle, period: int) -> None:
    __assertnvperror(_c_fn(handle, period))


@_wrap_function("getSyncClockPeriod", NVP_ErrorCode, [DeviceHandle, POINTER(c_uint)])
def getSyncClockPeriod(handle: DeviceHandle) -> int:
    period = c_uint(0)
    __assertnvperror(_c_fn(handle, period))
    return period.value


@_wrap_function("setSyncMode", NVP_ErrorCode, [DeviceHandle, c_int])
def setSyncMode(handle: DeviceHandle, mode: SyncMode) -> None:
    __assertnvperror(_c_fn(handle, mode.value))


@_wrap_function("getSyncMode", NVP_ErrorCode, [DeviceHandle, POINTER(c_int)])
def getSyncMode(handle: DeviceHandle) -> SyncMode:
    mode = c_int(0)
    __assertnvperror(_c_fn(handle, mode))
    return SyncMode(mode.value)


@_wrap_function("setTriggerMode", NVP_ErrorCode, [DeviceHandle, c_int])
def setTriggerMode(handle: DeviceHandle, mode: TriggerMode) -> None:
    __assertnvperror(_c_fn(handle, mode.value))


@_wrap_function("getTriggerMode", NVP_ErrorCode, [DeviceHandle, POINTER(c_int)])
def getTriggerMode(handle: DeviceHandle) -> TriggerMode:
    mode = c_int(0)
    __assertnvperror(_c_fn(handle, mode))
    return TriggerMode(mode.value)


@_wrap_function(
    "readElectrodeData",
    NVP_ErrorCode,
    [
        DeviceHandle,
        c_uint8,
        POINTER(PacketInfo),
        POINTER(c_int16),
        c_int,
        c_int,
        POINTER(c_int),
    ],
)
def readElectrodeData(
    handle: DeviceHandle,
    probe: int,
    packet_count: int,
) -> list[Packet]:
    # Read electrode data
    # handle: device handle got by createHandle()
    # probe: number of focussed probe: 0...3
    # packet_count: number of packets to read (the number actually read can be lower)
    # Return: list of "Packet"

    channel_count = 64  # Channel count must be 64
    packets_read = c_int(0)  # Class constructor; packets_read.value = 0
    info_arr = (
        PacketInfo * packet_count
    )()  # Ctypes way of defining an array of packet_count times a PacketInfo element;
    # (): empty
    data_arr = (c_int16 * (packet_count * channel_count))()

    __assertnvperror(
        _c_fn(
            handle,
            probe,
            info_arr,
            data_arr,
            channel_count,
            packet_count,
            packets_read,
        ),
    )

    packets = [None] * packets_read.value
    for i in range(packets_read.value):
        info = info_arr[i]
        offset = i * channel_count
        data = data_arr[offset : offset + channel_count]
        packets[i] = Packet(
            info.Timestamp,
            info.Status,
            info.payloadlength,
            info.session_id,
            data,
        )
    return packets


@_wrap_function("readDiagStats", NVP_ErrorCode, [DeviceHandle, POINTER(DiagStats)])
def readDiagStats(handle: DeviceHandle) -> DiagStats:
    stats = DiagStats()
    __assertnvperror(_c_fn(handle, stats))
    return stats


@_wrap_function("readBSHardwareID", NVP_ErrorCode, [DeviceHandle, POINTER(HardwareID)])
def readBSHardwareID(handle: DeviceHandle) -> HardwareID:
    hwid = HardwareID()
    __assertnvperror(_c_fn(handle, hwid))
    return hwid


@_wrap_function("readHSHardwareID", NVP_ErrorCode, [DeviceHandle, POINTER(HardwareID)])
def readHSHardwareID(handle: DeviceHandle) -> HardwareID:
    hwid = HardwareID()
    __assertnvperror(_c_fn(handle, hwid))
    return hwid


@_wrap_function(
    "readMezzanineHardwareID",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, POINTER(HardwareID)],
)
def readMezzanineHardwareID(handle: DeviceHandle, probe: int) -> HardwareID:
    hwid = HardwareID()
    __assertnvperror(_c_fn(handle, probe, hwid))
    return hwid


@_wrap_function(
    "readProbeHardwareID",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, POINTER(HardwareID)],
)
def readProbeHardwareID(handle: DeviceHandle, probe: int) -> HardwareID:
    hwid = HardwareID()
    __assertnvperror(_c_fn(handle, probe, hwid))
    return hwid


@_wrap_function("setFileStream", NVP_ErrorCode, [DeviceHandle, c_char_p])
def setFileStream(handle: DeviceHandle, filename: str) -> None:
    if filename != "":
        __assertnvperror(_c_fn(handle, filename.encode("ASCII")))
    else:
        __assertnvperror(_c_fn(handle, None))  # to unlock a file


@_wrap_function("enableFileStream", NVP_ErrorCode, [DeviceHandle, c_bool])
def enableFileStream(handle: DeviceHandle, enable: bool) -> None:
    __assertnvperror(_c_fn(handle, enable))


@_wrap_function(
    "streamOpenFile",
    NVP_ErrorCode,
    [c_char_p, POINTER(StreamHandle), c_uint8],
)
def streamOpenFile(filename: str, probe: int) -> StreamHandle:
    ptr = c_void_p()
    __assertnvperror(_c_fn(filename.encode("ASCII"), ctypes.byref(ptr), probe))
    return ptr


@_wrap_function("streamClose", NVP_ErrorCode, [StreamHandle])
def streamClose(handle: StreamHandle) -> None:
    __assertnvperror(_c_fn(handle))


@_wrap_function(
    "streamReadData",
    NVP_ErrorCode,
    [DeviceHandle, POINTER(PacketInfo), POINTER(c_int16), c_int, c_int, POINTER(c_int)],
)
def streamReadData(handle: StreamHandle, packet_count: int) -> list[Packet]:
    # Read stream data
    # StreamHandle: handle of the stream buffer
    # packet_count: number of packets to read
    # Return: list of "Packet"

    channel_count = 64  # Channel count must be 64
    packets_read = c_int(0)  # Class constructor; packets_read.value = 0
    info_arr = (
        PacketInfo * packet_count
    )()  # Ctypes way of defining an array of packet_count times a PacketInfo element;
    # (): empty
    data_arr = (c_int16 * (packet_count * channel_count))()

    error_code = _c_fn(
        handle,
        info_arr,
        data_arr,
        channel_count,
        packet_count,
        packets_read,
    )
    # STREAM_EOF = 26
    if error_code != 26 and error_code != 0:
        raise NeuraviperAPIError(error_code)

    packets = [None] * packets_read.value
    for i in range(packets_read.value):
        info = info_arr[i]
        offset = i * channel_count
        data = data_arr[offset : offset + channel_count]
        packets[i] = Packet(
            info.Timestamp,
            info.Status,
            info.payloadlength,
            info.session_id,
            data,
        )
    return packets


@_wrap_function("setDeviceEmulatorMode", NVP_ErrorCode, [DeviceHandle, c_int])
def setDeviceEmulatorMode(handle: DeviceHandle, mode: DeviceEmulatorMode) -> None:
    __assertnvperror(_c_fn(handle, mode.value))


@_wrap_function("setDeviceEmulatorType", NVP_ErrorCode, [DeviceHandle, c_int])
def setDeviceEmulatorType(handle: DeviceHandle, type: DeviceEmulatorType) -> None:
    __assertnvperror(_c_fn(handle, type.value))


@_wrap_function("bistBS", NVP_ErrorCode, [DeviceHandle])
def bistBS(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("bistStartPRBS", NVP_ErrorCode, [DeviceHandle])
def bistStartPRBS(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function(
    "bistStopPRBS",
    NVP_ErrorCode,
    [DeviceHandle, POINTER(c_int), POINTER(c_int)],
)
def bistStopPRBS(handle: DeviceHandle) -> tuple[int, int]:
    prbs_err_data = c_int(0)
    prbs_err_ctrl = c_int(0)
    __assertnvperror(_c_fn(handle, prbs_err_data, prbs_err_ctrl))
    return (prbs_err_data.value, prbs_err_ctrl.value)


@_wrap_function(
    "bistReadPRBS",
    NVP_ErrorCode,
    [DeviceHandle, POINTER(c_int), POINTER(c_int)],
)
def bistReadPRBS(handle: DeviceHandle) -> tuple[int, int]:
    prbs_err_data = c_int(0)
    prbs_err_ctrl = c_int(0)
    __assertnvperror(_c_fn(handle, prbs_err_data, prbs_err_ctrl))
    return (prbs_err_data.value, prbs_err_ctrl.value)


@_wrap_function("bistEEPROM", NVP_ErrorCode, [DeviceHandle])
def bistEEPROM(handle: DeviceHandle):
    __assertnvperror(_c_fn(handle))


@_wrap_function("bistSPIMM", NVP_ErrorCode, [DeviceHandle, c_uint8])
def bistSPIMM(handle: DeviceHandle, probe: int):
    __assertnvperror(_c_fn(handle, probe))


@_wrap_function("bistSR", NVP_ErrorCode, [DeviceHandle, c_uint8])
def bistSR(handle: DeviceHandle, probe: int):
    __assertnvperror(_c_fn(handle, probe))


#######################################################################################
#######################################################################################
#######################################################################################
@_wrap_function(
    "selectElectrode",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_int, ElectrodeInput],
)
def selectElectrode(
    handle: DeviceHandle,
    probe: int,
    channel: int,
    electrode: ElectrodeInput,
) -> None:
    __assertnvperror(_c_fn(handle, probe, channel, electrode))


@_wrap_function("setReference", NVP_ErrorCode, [DeviceHandle, c_uint8, c_int, c_int])
def setReference(
    handle: DeviceHandle,
    probe: int,
    channel: int,
    reference: int,
) -> None:
    __assertnvperror(_c_fn(handle, probe, channel, reference))


@_wrap_function("setOSEnable", NVP_ErrorCode, [DeviceHandle, c_uint8, c_int, c_bool])
def setOSEnable(
    handle: DeviceHandle,
    probe: int,
    output_stage: int,
    enable: bool,
) -> None:
    __assertnvperror(_c_fn(handle, probe, output_stage, enable))


@_wrap_function(
    "writeSUConfiguration",
    NVP_ErrorCode,
    [
        DeviceHandle,
        c_uint8,
        c_uint8,
        c_bool,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
        c_uint8,
    ],
)
def writeSUConfiguration(
    handle: DeviceHandle,
    probe: int,
    stimunit: int,
    polarity: bool,
    npulse: int,
    DAC_AN: int,
    DAC_CAT: int,
    TPULSE: int,
    TDLY: int,
    TON1: int,
    TOFF: int,
    TON2: int,
    TDIS: int,
    TDISEND: int,
) -> None:
    __assertnvperror(
        _c_fn(
            handle,
            probe,
            stimunit,
            polarity,
            npulse,
            DAC_AN,
            DAC_CAT,
            TPULSE,
            TDLY,
            TON1,
            TOFF,
            TON2,
            TDIS,
            TDISEND,
        ),
    )


@_wrap_function("SUtrig1", NVP_ErrorCode, [DeviceHandle, c_uint8, c_uint8])
def SUtrig1(handle: DeviceHandle, probe: int, trigger: int) -> None:
    __assertnvperror(_c_fn(handle, probe, trigger))


@_wrap_function(
    "setOSInputSU",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_uint8, c_uint8],
)
def setOSInputSU(
    handle: DeviceHandle,
    probe: int,
    output_stage: int,
    stim_unit: int,
) -> None:
    __assertnvperror(_c_fn(handle, probe, output_stage, stim_unit))


@_wrap_function("setAZ", NVP_ErrorCode, [DeviceHandle, c_uint8, c_uint8, c_bool])
def setAZ(handle: DeviceHandle, probe: int, channel: int, autoreset: bool) -> None:
    __assertnvperror(_c_fn(handle, probe, channel, autoreset))


@_wrap_function(
    "setOSDischargeperm",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_uint8, c_bool],
)
def setOSDischargeperm(
    handle: DeviceHandle,
    probe: int,
    OS: int,
    discharge_perm: bool,
) -> None:
    __assertnvperror(_c_fn(handle, probe, OS, discharge_perm))


@_wrap_function(
    "setOSStimblank",
    NVP_ErrorCode,
    [DeviceHandle, c_uint8, c_uint8, c_bool],
)
def setOSStimblank(handle: DeviceHandle, probe: int, OS: int, stimblank: bool) -> None:
    __assertnvperror(_c_fn(handle, probe, OS, stimblank))


###############################################################################

if __name__ == "__main__":
    setLogLevel(LogLevel.VERBOSE)

    import sys

    print("API Version: {}.{}.{}".format(*getAPIVersion()))

    # scanBS() happens automatically, but we can use it to force re-discovery of devices
    scanBS()
    devices = getDeviceList(16)

    if len(devices) == 0:
        print("No devices connected...")
        sys.exit()

    print("Connected devices: ")
    for device in devices:
        print(f"\t{device}")

    # Creating a handle, opening basestation and probes
    handle = createHandle(devices[0].ID)
    openBS(handle)
    openProbes(handle)

    # SPI example
    writeSPI(handle, 0, b"Hello, world!")
    out = transferSPI(handle, 0, b"Hello, world!")
    print(out)

    # PRBS test
    import time

    print("Starting PRBS test (10 seconds)")
    bistStartPRBS(handle)
    time.sleep(10)
    (prbs_err_data, prbs_err_ctrl) = bistStopPRBS(handle)
    print(f"PRBS Error counts: {prbs_err_data} (data), {prbs_err_ctrl} (control)")

    # BIST tests
    try:
        bistBS(handle)
    except NeuraviperAPIError as e:
        print("bistBS failed with exception:")
        print(e)

    try:
        bistEEPROM(handle)
    except NeuraviperAPIError as e:
        print("bistEEPROM failed with exception:")
        print(e)

    try:
        bistSPIMM(handle, 0)
    except NeuraviperAPIError as e:
        print("bistSPIMM failed with exception:")
        print(e)

    try:
        bistSR(handle, 0)
    except NeuraviperAPIError as e:
        print("bistSR failed with exception:")
        print(e)

    closeBS(handle)
    destroyHandle(handle)

    free_library()
