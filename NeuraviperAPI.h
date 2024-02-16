/*
    NeuraViPeR C API

    (c) Imec 2022

*/

#pragma once

#include <cstddef>
#include <cstdint>

#define NVP_EXPORT extern "C" __declspec(dllexport)
#define NVP_CALLBACK __stdcall

typedef enum NVPPlatformID {
    NVPPlatform_None = 0, /*!< unknown platform */
    NVPPlatform_USB = 1, /*!< USB platform (ViPeRBox) */
    NVPPlatform_ALL = NVPPlatform_USB, /*!< default platform ID (i.e. use all platforms) */
} NVPPlatformID;

typedef struct BasestationID
{
    NVPPlatformID platformid; /*!< platform of basestation */
    int id; /*!< serial number of basestation */
} BasestationID;

typedef struct PacketInfo {
    uint32_t Timestamp; /*!< Timestamp reported by the basestation */
    uint16_t Status; /*!< Status byte */
    uint16_t payloadlength; /*!< Number of samples (= channels) in packet */
    uint8_t session_id; /*!< Session ID of the stream */
} PacketInfo;

typedef enum NVP_ErrorCode {
    SUCCESS = 0, /*!< The function returned sucessfully */
    FAILED = 1, /*!< Unspecified failure */
    ALREADY_OPEN = 2, /*!< A board was already open */
    NOT_OPEN = 3, /*!< The function cannot execute, because the board or port is not open */
    IIC_ERROR = 4, /*!< An error occurred while accessing devices on the BS i2c bus */
    VERSION_MISMATCH = 5, /*!< FPGA firmware version mismatch */
    PARAMETER_INVALID = 6, /*!< A parameter had an illegal value or out of range */
    UART_ACK_ERROR = 7, /*!< uart communication on the serdes link failed to receive an acknowledgement */
    TIMEOUT = 8, /*!< the function did not complete within a restricted period of time */
    WRONG_CHANNEL = 9, /*!< illegal channel or channel group number */
    WRONG_BANK = 10, /*!< illegal electrode bank number */
    WRONG_REF = 11, /*!< a reference number outside the valid range was specified */
    WRONG_INTREF = 12, /*!< an internal reference number outside the valid range was specified */
    CSV_READ_ERROR = 13, /*!< an parsing error occurred while reading a malformed CSV file. */
    BIST_ERROR = 14, /*!< a BIST operation has failed */
    FILE_OPEN_ERROR = 15, /*!< The file could not be opened */
    TIMESTAMPNOTFOUND = 16, /*!< the specified timestamp could not be found in the stream */
    FILE_IO_ERR = 17, /*!< a file IO operation failed */
    OUTOFMEMORY = 18, /*!< the operation could not complete due to insufficient process memory */
    NO_LOCK = 19, /*!< missing serializer clock. Probably bad cable or connection */
    WRONG_AP = 20, /*!< AP gain number out of range */
    WRONG_LFP = 21, /*!< LFP gain number out of range */
    IO_ERROR = 22, /*!< a data stream IO error occurred. */
    NO_SLOT = 23, /*!< no NeuraViPeR board found at the specified slot number */
    WRONG_SLOT = 24, /*!<  the specified slot is out of bound */
    WRONG_PORT = 25, /*!<  the specified port is out of bound */
    STREAM_EOF = 26, /*!<  The stream is at the end of the file, but more data was expected*/
    HDRERR_MAGIC = 27, /*!< The packet header is corrupt and cannot be decoded */
    HDRERR_CRC = 28, /*!< The packet header's crc is invalid */
    WRONG_PROBESN = 29, /*!< The probe serial number does not match the calibration data */
    PROGRAMMINGABORTED = 30, /*!<  the flash programming was aborted */
    WRONG_DOCK_ID = 31, /*!<  the specified probe id is out of bound */
    NO_LINK = 32, /*!< no head stage was detected */
    NO_MEZZANINE = 33, /*!< no mezzanine board was detected */
    NO_PROBE = 34, /*!< no probe was detected */
    WRONG_OUTPUT_STAGE = 35, /*!< Output stage number is out of bounds */
    WRONG_STIM_UNIT = 36, /*!< Stimulation unit number is out of bounds */
    ERROR_SR_CHAIN_CH = 37, /*!< Validation of channel configuration SR chain data upload failed */
    ERROR_SR_CHAIN_OS = 38, /*!< Validation of output stage SR chain data upload failed */
    ERROR_SR_CHAIN_SU = 39, /*!< Validation of stimulation unit SR chain data upload failed */
    ERROR_SR_CHAIN_GEN = 40, /*!< Validation of general configuration SR chain data upload failed */
    DEVICE_NOT_FOUND = 41, /*!< Basestation with given serial number not found */
    INVALID_DEVICE_HANDLE = 42, /*!< Invalid device handle */
    ILLEGAL_HANDLE = 43, /*!< the value of the 'handle' parameter is not valid. */
    OBJECT_MISMATCH = 44, /*!< the object type is not of the expected class */
    READBACK_ERROR = 45,/**< a BIST readback verification failed */
    NOTSUPPORTED = 0xFE, /*!<  the function is not supported */
    NOTIMPLEMENTED = 0xFF, /*!<  the function is not implemented */
} NVP_ErrorCode;

/**
* Operating mode of the probe
*/
typedef enum ProbeOpMode {
    RECORDING = 1 << 0, /*!< Recording mode: (default) pixels connected to channels */
    CALIBRATION = 1 << 1, /*!< Calibration mode: test signal input connected to pixel, channel or ADC input */
    DIGITAL_TEST = 1 << 2, /*!< Digital test mode: data transmitted over the PSB bus is a fixed data pattern */
    STIMULATION = 1 << 3, /*!< Stimulation mode: enable stimulation units */
    IMPEDANCE_MEASUREMENT = 1 << 4 /*!< Impedance-measurement mode */
} ProbeOpMode;

/**
* test input mode
*/
typedef enum TestInputMode {
    NO_TEST_MODE = 0, /*!< No test mode */
    OS_CALIBRATION = 1, /*!< OS calibration */
    CHANNEL_CALIBRATION = 2, /*!< Digital test */
    ADC_CALIBRATION = 3 /*!< Stimulation */
} TestInputMode;

typedef enum ChannelReference {
    EXT_REF = 0,  /*!< External electrode */
    TIP_REF = 1,  /*!< Tip electrode */
    INT_REF = 2,   /*!< Internal electrode */
    GND_REF = 3,   /*!< Ground reference */
    NONE_REF = 0xFF /*!< disconnect reference */
} ChannelReference;

typedef enum ElectrodeInput {
    INPUT_0 = 0x00, /*!< In 0 */
    INPUT_1 = 0x01, /*!< In 1 */
    INPUT_2 = 0x02, /*!< In 2 */
    INPUT_3 = 0x03  /*!< In 3 */
} ElectrodeInput;

typedef void* StreamHandle;

const int HARDWAREID_PN_LEN = 40;
#pragma pack(push, 1)
typedef struct HardwareID {
    uint8_t version_major;
    uint8_t version_minor;
    uint64_t serial_number;
    char product_number[HARDWAREID_PN_LEN];
} HardwareID;
#pragma pack(pop)

typedef struct DiagStats {
    uint64_t total_bytes;      /*!< total amount of bytes received */
    uint32_t packet_count;     /*!< Amount of packets received */
    uint32_t triggers;         /*!< Amount of triggers received */
    uint32_t session_mismatch; /*!< Number of packets with session ID not matching the current in use (i.e. packets stuck in USB FIFO from previous recording) */
    uint32_t err_bad_magic;    /*!< amount of packet header bad magic markers */
    uint32_t err_bad_crc;      /*!< amount of packet header CRC errors */
    uint32_t err_count;        /*!< Every psb frame has an incrementing count index. If the received frame count value is not as expected possible data loss has occured and this flag is raised. */
    uint32_t err_serdes;       /*!< Incremented if a deserializer error (hardware pin) occurred during reception of this frame this flag is raised */
    uint32_t err_lock;         /*!< Incremented if a deserializer loss of lock (hardware pin) occurred during reception of this frame this flag is raised */
    uint32_t err_pop;          /*!< Incremented whenever the next blocknummer round-robin FiFo is flagged empty during request of the next value (for debug purpose only, irrelevant for end-user software) */
    uint32_t err_sync;         /*!< Front-end receivers are out of sync. => frame is invalid. */
} DiagStats;

typedef enum DeviceEmulatorMode {
    DeviceEmulatorMode_OFF = 0,    /*!< No emulation data is generated */
    DeviceEmulatorMode_STATIC = 1, /*!< static data per channel: value = channel number */
    DeviceEmulatorMode_LINEAR = 2, /*!< a linear ramp is generated per channel (1 sample shift between channels) */
} DeviceEmulatorMode;

typedef enum DeviceEmulatorType {
    DeviceEmulatorType_Off = 0,
    DeviceEmulatorType_EmulatedProbe = 1
} DeviceEmulatorType;

typedef enum LogLevel
{
    logOFF = -1,
    logFATAL = 0,
    logERROR = 1,
    logWARNING = 2,
    logINFO = 3,
    logDEBUG = 4,
    logVERBOSE = 5,
} LogLevel;

/* System Functions *******************************************************************/

/**
 * Get the version number of the API.
 *
 * @param version_major Pointer to variable holding the major version
 * @param version_minor Pointer to variable holding the minor version
 * @param version_patch Pointer to variable holding the patch version
 */
NVP_EXPORT void getAPIVersion(int* version_major, int* version_minor, int* version_patch);

/**
 * Set logging level.
 *
 * All messages sent to the log are directed to the standard output.
 *
 * @param level Desired logging level
 */
NVP_EXPORT void setLogLevel(LogLevel level);

/**
 * Get current log level
 *
 * @returns Current logging level
 */
NVP_EXPORT LogLevel getLogLevel(void);

/**
 * Read the last error message
 *
 * @param buffer Destination buffer
 * @param size   Size of the destination buffer
 *
 * @returns      Amount of characters written to the destination buffer
 */
NVP_EXPORT size_t getLastErrorMessage(char* buffer, size_t size);

/**
 * Get error message for a given error code.
 *
 * Only a pointer to the corresponding error string is returned.
 *
 * @param error_code Error code to get the error message for
 * @param message Pointer to set to the error message
 *
 * @retval SUCCESS Always returns SUCCESS
 */
NVP_EXPORT NVP_ErrorCode getErrorMessage(NVP_ErrorCode error_code, char** message);

/**
 * Scan the system for available devices.
 *
 * This function updates the cached device list.
 *
 * @retval SUCCESS If no errors occurred during enumeration.
 */
NVP_EXPORT NVP_ErrorCode scanBS(void);

/**
 * Get a cached list of available devices. Use 'scanBS' to update this list.
 *
 * @param list  Output list of available devices
 * @param count Entry count of list buffer
 * @returns     Amount of devices found
 */
NVP_EXPORT int getDeviceList(struct BasestationID* list, int count);

typedef void* DeviceHandle;

/**
 * Create handle for device.
 *
 * If a serial number is provided, and a handle has already been created for the device, the existing handle will be returned.
 * If no serial number is provided (i.e. serial number is 0 or -1), a handle will be created for the first unmapped device.
 *
 * @param handle Pointer to the variable holding the handle
 * @param serial_number Serial number of device to be mapped
 *
 * @returns Status code
 * @retval SUCCESS If handle was created
 * @retval DEVICE_NOT_FOUND If serial number not found, no unmapped devices found, or other issue was present
 */
NVP_EXPORT NVP_ErrorCode createHandle(DeviceHandle* handle, int serial_number);

/**
 * Destroy device handle. Closes device and platform link as well.
 *
 * @param handle Device handle of basestation
 */
NVP_EXPORT NVP_ErrorCode destroyHandle(DeviceHandle handle);

/**
 * Get the basestation info descriptor for a mapped device.
 *
 * @param handle Device handle of the basestation
 * @param info Pointer to BasestationID
 */
NVP_EXPORT NVP_ErrorCode getDeviceInfo(DeviceHandle handle, struct BasestationID* info);

/* Basestation functions */

/**
 * Test if basestation with serial number is connected
 *
 * @param serial_number Serial number of device
 * @param detected Pointer to bool holding result
 */
NVP_EXPORT NVP_ErrorCode detectBS(int serial_number, bool* detected);

/**
 * Open and initialise a basestation.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode openBS(DeviceHandle handle);

/**
 * Close a basestation.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode closeBS(DeviceHandle handle);

/**
 * Returns the BS temperature (measured on FPGA)
 *
 * @param handle Device handle of the basestation
 * @param temperature Pointer to temperature destination
 */
NVP_EXPORT NVP_ErrorCode getTemperature(DeviceHandle handle, double* temperature);

/**
 * Enable power to headstage and initialise SerDes link.
 *
 * Enables communication with probes.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode openProbes(DeviceHandle handle);

/**
 * Disable power supply to headstage.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode closeProbes(DeviceHandle handle);

/**
 * The function resets the connected probes to the default settings:
 * load the default settings for configuration registers and memory map;
 * and subsequently initialize the probe in recording mode.
 *
 * @param handle Device handle of the basestation
 * @param probe_number Number of the probe to initialise
 */
NVP_EXPORT NVP_ErrorCode init(DeviceHandle handle, int probe_number);

/**
 * Write and/or read one or more bytes to/from a probe ASIC using SPI.
 *
 * The output buffer and input buffer should be the same size.
 * The function will write a single byte out of \p output_buffer to the device, and read back a single byte into \p input_buffer, until all bytes have been transmitted.
 * It is up to the user of the function to extract the relevant data out of the read-back buffer.
 *
 * Note that this function will not work properly if probes haven't been opened using openProbes.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe (valid range 0 to 3)
 * @param output_buffer Pointer to buffer containing data to write to SPI device
 * @param input_buffer Pointer to buffer for read-back
 * @param len Size of output and input buffer
 */
NVP_EXPORT NVP_ErrorCode transferSPI(DeviceHandle handle, uint8_t probe, uint8_t* output_buffer, uint8_t* input_buffer, size_t len);

/**
 * Write one or more bytes to a probe ASIC using SPI.
 *
 * Note that this function will not work properly if probes haven't been opened using openProbes.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe (valid range 0 to 3)
 * @param output_buffer Pointer to buffer containing data to write to SPI device
 * @param len Size of output and input buffer
 */
NVP_EXPORT NVP_ErrorCode writeSPI(DeviceHandle handle, uint8_t probe, uint8_t* output_buffer, size_t len);

/**
 * Read basestation boot version
 *
 * @param handle Device handle of the basestation
 * @param version_major Pointer to major version variable
 * @param version_minor Pointer to minor version variable
 */
NVP_EXPORT NVP_ErrorCode getBSBootVersion(DeviceHandle handle, uint8_t* version_major, uint8_t* version_minor);

/**
 * Read HardwareID from basestation.
 *
 * version_minor is board ID read from IO extender on basestation PCB.
 *
 * @param handle Device handle of the basestation
 * @param hwid HardwareID to read to.
 */
NVP_EXPORT NVP_ErrorCode readBSHardwareID(DeviceHandle handle, HardwareID* hwid);

/**
 * Read HardwareID from headstage.
 *
 * @param handle Device handle of the basestation
 * @param hwid HardwareID to read to.
 */
NVP_EXPORT NVP_ErrorCode readHSHardwareID(DeviceHandle handle, HardwareID* hwid);

/**
 * Read HardwareID from mezzanine.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe (valid range 0 to 3)
 * @param hwid HardwareID to read to.
 */
NVP_EXPORT NVP_ErrorCode readMezzanineHardwareID(DeviceHandle handle, uint8_t probe, HardwareID* hwid);

/**
 * Read HardwareID from probe.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe (valid range 0 to 3)
 * @param hwid HardwareID to read to.
 */
NVP_EXPORT NVP_ErrorCode readProbeHardwareID(DeviceHandle handle, uint8_t probe, HardwareID* hwid);

/**
 * Set OPMODE of NeuraViPeR ASIC
 *
 * @param handle Handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param mode_mask Value to write to the OPMODE register, multiple values can be combined to create a mask
 */
NVP_EXPORT NVP_ErrorCode setOPMODE(DeviceHandle handle, uint8_t probe, ProbeOpMode mode_mask);

/**
 * Set CALMODE of NeuraViPeR ASIC
 *
 * @param handle Handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param mode Value to write to the CALMODE register
 */
NVP_EXPORT NVP_ErrorCode setCALMODE(DeviceHandle handle, uint8_t probe, TestInputMode mode);

/**
 * The following function resets and then sets the CH_NRESET signal to the probe ASIC.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 */
NVP_EXPORT NVP_ErrorCode setREC_NRESET(DeviceHandle handle, uint8_t probe);

/**
 * This function sets which electrode is connected to a channel. By using this function, the user can only connect one electrode at a time to a channel.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param channel Recording channel number (valid range 0 to 63)
 * @param electrode Electrode number
 */
NVP_EXPORT NVP_ErrorCode selectElectrode(DeviceHandle handle, uint8_t probe, int channel, ElectrodeInput electrode);

/**
 * Select reference electrode(s) for recording channel.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param channel Recording channel number (valid range 0 to 63)
 * @param reference_mask Reference electrode mask
 */
NVP_EXPORT NVP_ErrorCode setReference(DeviceHandle handle, uint8_t probe, int channel, int reference_mask);

/**
 * Set channel gain
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param channel Recording channel number (valid range 0 to 63)
 * @param gain Gain (valid range 0 to 3)
 */
NVP_EXPORT NVP_ErrorCode setGain(DeviceHandle handle, uint8_t probe, int channel, int gain);

/**
 * Enables or disables impedance measurement bit (Zmeas_ON) for a channel.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param channel Recording channel number
 * @param Zmeas Impedance measurement bit to write
 */
NVP_EXPORT NVP_ErrorCode setZmeas(DeviceHandle handle, uint8_t probe, int channel, bool Zmeas);

/**
 * Set a channel in stand-by mode.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param channel Recording channel number
 * @param standby The standby value to write
 */
NVP_EXPORT NVP_ErrorCode setStdb(DeviceHandle handle, uint8_t probe, int channel, bool standby);

/**
 * Enable the Auto Reset function for a channel.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param channel Recording channel number (valid range 0 to 63)
 * @param autoreset The auto reset value to write
 */
NVP_EXPORT NVP_ErrorCode setAZ(DeviceHandle handle, uint8_t probe, int channel, bool autoreset);

/**
 * Write shank and base configuration to probe ASIC.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param readCheck If enabled, read the configuration shift registers back to check
 */
NVP_EXPORT NVP_ErrorCode writeChannelConfiguration(DeviceHandle handle, uint8_t probe, bool readCheck);

/**
 * Select stimulation unit for output stage
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param output_stage Output stage number (valid range: 0 to 127)
 * @param stim_unit Stimulation unit number (valid range: 0 to 7)
 */
NVP_EXPORT NVP_ErrorCode setOSInputSU(DeviceHandle handle, uint8_t probe, int output_stage, int stim_unit);

/**
 * Enable output stage.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param output_stage Output stage number (valid range: 0 to 127)
 * @param enable Enable output stage
 */
NVP_EXPORT NVP_ErrorCode setOSEnable(DeviceHandle handle, uint8_t probe, int output_stage, bool enable);

/**
 * Connect output stage to the calibration signal line.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param output_stage Output stage number (valid range: 0 to 127)
 * @param calibrate Connect output stage to calibration signal line
 */
NVP_EXPORT NVP_ErrorCode setOSCalibrate(DeviceHandle handle, uint8_t probe, int output_stage, bool calibrate);

/**
 * Each OS has a switch to discharge the electrode automatically after a stimulation event.
 * However, this switch may be forced permanently closed for certain applications by setting this flag.
 * The user can set each OS individually.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param output_stage Output stage number (valid range: 0 to 127)
 * @param dischperm The dischperm value to write
 */
NVP_EXPORT NVP_ErrorCode setOSDischargeperm(DeviceHandle handle, uint8_t probe, int output_stage, bool dischperm);

/**
 * Each channel has a switch to disconnect the electrode from the channel input automatically during a stimulation event
 * to avoid large input voltages. This switch is controlled by the output stage whos signal is connected to the channel
 * input. The stimulation blanking can be set using this flag and should be enabled by default. The user can set each
 * OS individually.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param output_stage Output stage number (valid range: 0 to 127)
 * @param stimblank The stimblank value to write, default enabled
 */
NVP_EXPORT NVP_ErrorCode setOSStimblank(DeviceHandle handle, uint8_t probe, int output_stage, bool stimblank);

/**
 * Sets the value of the output stage pixels.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param osdata Array of 128*4 bits (= 64 bytes) which contain the core configuration of the 128 output stages.
 */
NVP_EXPORT NVP_ErrorCode setOSimage(DeviceHandle handle, uint8_t probe, uint8_t* osdata);

/**
 * Write output stage configuration to ASIC registers.
 *
 * A bug in the ASIC can cause a write to SR chains to fail, or even overwrite the probe's sync word.
 * To prevent this from happening, a safeguard has been built-in, at the cost of increased latency.
 * This workaround can be bypassed by setting skip_sync_check to true.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param read_check If enabled, read the configuration shift registers back to check
 * @param skip_sync_check Set to true to bypass SR chain write bug work-around
 */
NVP_EXPORT NVP_ErrorCode writeOSConfiguration(DeviceHandle handle,
                                              uint8_t probe,
                                              bool read_check,
                                              bool skip_sync_check = false);

/**
 * Configure stimulation unit registers.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param stimunit Stimulation unit number (valid range 0 to 8)
 * @param polarity Polarity bit POL in SUx_CONFIG register
 * @param npulse Number of stimulation pulses, register SUx_NPULSE
 * @param DAC_AN Current level for the anodic pulse, register SUx_DAC_AN
 * @param DAC_CAT Current level for the cathodic pulse, register SUx_DAC_CAT
 * @param TPULSE Pulse period, register SUx_TPULSE
 * @param TDLY Delay at the start of a stimulation, register SUx_TDLY
 * @param TON1 Duration of the first stimulation pulse, register SUx_TON1
 * @param TOFF Duration of the off period between pulses, register SUx_TOFF
 * @param TON2 Duration of the second stimulation pulse, register SUx_TON2
 * @param TDIS Duration of the discharge phase, register SUx_TDIS
 * @param TDISEND Duration of the last discharge pulse, register SUx_TDIS_END
 */
NVP_EXPORT NVP_ErrorCode writeSUConfiguration(
    DeviceHandle handle,
    uint8_t probe,
    uint8_t stimunit,
    bool polarity,
    uint8_t npulse,
    uint8_t DAC_AN,
    uint8_t DAC_CAT,
    uint8_t TPULSE,
    uint8_t TDLY,
    uint8_t TON1,
    uint8_t TOFF,
    uint8_t TON2,
    uint8_t TDIS,
    uint8_t TDISEND
);

/**
 * Set bit mask of SU_TRIG1 register.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param trigger To be written to SU_TRIG1 register, contains the bit mask to which SU will trigger
 */
NVP_EXPORT NVP_ErrorCode SUtrig1(DeviceHandle handle, uint8_t probe, uint8_t trigger);

/**
 * Configure the electrode impedance frequency and amplitude.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param frequency Set the frequency of the impedance measurement (valid range 0-7)
 * @param amplitude Set the amplitude of the impedance measurement (valid range 0-1)
 */
NVP_EXPORT NVP_ErrorCode setElimp(DeviceHandle handle, uint8_t probe, uint8_t frequency, uint8_t amplitude);

/**
 * Enable the reset of the impedance generator.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param reset Enable the reset of the impedance generator, bit ELIMP_NRESET in EL_IMP_MOD register
 */
NVP_EXPORT NVP_ErrorCode resetElimp(DeviceHandle handle, uint8_t probe, bool reset);

/**
 * Arms the basestation for recording.
 *
 * In anticipation of receiving a start trigger, the system is set in ‘arm’ mode.
 * In ‘arm’ mode, neural data packets from the probe are not buffered in the
 * DRAM FIFO on the basestation, and the time stamp is fixed at 0. Upon receiving
 * the start trigger, the system starts to buffer the incoming neural data in the
 * basestation DRAM FIFO buffer and start the timestamp generator.
 *
 * After the system has received a start trigger and is buffering incoming neural
 * data, calling the API ‘arm’ function again stops the buffering of neural data
 * packets, clears the basestation DRAM FIFO, stops the time stamp generator and
 * resets the timestamp to 0.
 * 
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode arm(DeviceHandle handle);

/**
 * Generate a software start trigger.
 * 
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode setSWTrigger(DeviceHandle handle);

/**
 * Set the (approximate) frequency of the internal sync clock.
 *
 * This function will attempt to set the frequency of the internal sync clock to
 * the target frequency. Because of rounding and conversion of the frequency to
 * a half period in milliseconds, the actual frequency may differ slightly from
 * the target frequency. The actual frequency can always be checked by using
 * `getSyncClockFrequency`.
 *
 * @param handle Device handle of the basestation
 * @param frequency Target frequency in Hz
 * @returns PARAMETER_INVALID if the target frequency is out-of-bounds or otherwise illegal
 */
NVP_EXPORT NVP_ErrorCode setSyncClockFrequency(DeviceHandle handle, double frequency);

/**
 * Get the frequency of the internal sync clock.
 *
 * @param handle Device handle of the basestation
 * @param frequency Pointer to result (in Hz)
 */
NVP_EXPORT NVP_ErrorCode getSyncClockFrequency(DeviceHandle handle, double* frequency);

/**
 * Set the period of the internal sync clock.
 *
 * Due to technical reasons, the period must be an even number between 2 and 32766.
 *
 * @param handle Device handle of the basestation
 * @param period_ms Target period in milliseconds
 * @returns PARAMETER_INVALID if period is out-of-bounds or otherwise illegal
 */
NVP_EXPORT NVP_ErrorCode setSyncClockPeriod(DeviceHandle handle, unsigned int period_ms);

/**
 * Get the period of the internal sync clock.
 *
 * @param handle Device handle of the basestation
 * @param period_ms Pointer to result (in milliseconds)
 */
NVP_EXPORT NVP_ErrorCode getSyncClockPeriod(DeviceHandle handle, unsigned int* period_ms);

typedef enum SyncMode {
    SyncMode_MASTER = 0, /*!< Device uses and exports internally generated sync clock */
    SyncMode_SLAVE  = 1  /*!< Device uses and imports externally generated sync clock */
} SyncMode;

/**
 * Configure the basestation's synchronization mode
 *
 * @param handle Device handle of the basestation
 * @param mode Mode
 */
NVP_EXPORT NVP_ErrorCode setSyncMode(DeviceHandle handle, SyncMode mode);

/**
 * Get the current synchronization mode of a basestation
 *
 * @param handle Device handle of the basestation
 * @param mode Pointer to result
 */
NVP_EXPORT NVP_ErrorCode getSyncMode(DeviceHandle handle, SyncMode* mode);

typedef enum TriggerMode {
    TriggerMode_MASTER = 0, /*!< Device uses and exports internally generated trigger */
    TriggerMode_SLAVE  = 1  /*!< Device uses and imports externally generated trigger */
} TriggerMode;

/**
 * Configure the basestation's trigger mode
 *
 * @param handle Device handle of the basestation
 * @param mode Mode
 */
NVP_EXPORT NVP_ErrorCode setTriggerMode(DeviceHandle handle, TriggerMode mode);

/**
 * Get the current trigger mode of a basestation
 *
 * @param handle Device handle of the basestation
 * @param mode Pointer to result
 */
NVP_EXPORT NVP_ErrorCode getTriggerMode(DeviceHandle handle, TriggerMode* mode);

/**
 * Fetch data packets from the BS FIFO buffer.
 * 
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 * @param info Output data containing additional packet data: timestamp, stream status, payload length, and session ID (size of buffer should be at least channel_count)
 * @param data Unpacked 16 bit right aligned data (size of buffer should be at least channel_count * packet_count * sizeof(int16_t))
 * @param channel_count Number of channels to read per packet (this value should be 64)
 * @param packet_count Maximum number of packets to read
 * @param packets_read Actual number of packets read
 */
NVP_EXPORT NVP_ErrorCode readElectrodeData(DeviceHandle handle, uint8_t probe, PacketInfo* info, int16_t* data,
                                           int channel_count, int packet_count, int* packets_read);

/**
 * Read diagnostic statistics from the basestation's stream processor.
 * See \ref DiagStats for more info on the statistics.
 * Note that the stream processor's statistics are reset on every call of \ref arm
 *
 * @param handle Device handle of the basestation
 * @param stats Pointer to result
 */
NVP_EXPORT NVP_ErrorCode readDiagStats(DeviceHandle handle, DiagStats* stats);

/**
 * Set file to write datastream received from basestation to.
 *
 * Use enableFileStream to enable or disable the actual writing of data.
 *
 * @param handle Device handle of the basestation
 * @param filename Filename of target file (use nullptr to select no file)
 */
NVP_EXPORT NVP_ErrorCode setFileStream(DeviceHandle handle, const char* filename);

/**
 * Enable or disable writing of datastream received from basestation to file.
 *
 * If enabled and path is correctly configured, all data received from the
 * basestation will be written to the file without any processing.
 *
 * If the filename provided using setFileStream already exists, data will
 * be appended to the file.
 *
 * @param handle Device handle of the basestation
 * @param enable Enable or disable writing of data
 */
NVP_EXPORT NVP_ErrorCode enableFileStream(DeviceHandle handle, bool enable);

/**
 * Open file containing basestation datastream in order to process probe data.
 *
 * @param filename Filename of target file
 * @param handle Handle to open file containing datastream
 * @param probe Index of the probe whose data should be processed (valid range 0 to 3)
 */
NVP_EXPORT NVP_ErrorCode streamOpenFile(const char* filename, StreamHandle* handle, uint8_t probe);

/**
 * Close open file containing datastream
 *
 * @param handle Handle to open file containing datastream
 */
NVP_EXPORT NVP_ErrorCode streamClose(StreamHandle handle);

/**
 * Read data packets from datastream file.
 *
 * This function works similar to readElectrodeData, except that it reads from
 * a data stream file. Note that a datastream file can contain data from more
 * than one recording session, hence it is important to look at the session_id
 * field in PacketInfo structs when processing the data.
 *
 * @param handle Handle to open file containing datastream
 * @param info Output data containing additional packet data: timestamp, stream status, payload length, and session ID (size of buffer should be at least channel_count)
 * @param data Unpacked 16 bit right aligned data (size of buffer should be at least channel_count * packet_count * sizeof(int16_t))
 * @param channel_count Number of channels to read per packet
 * @param packet_count Maximum number of packets to read
 * @param packets_read Actual number of packets read
 *
 * @retval STREAM_EOF If all packets have been read from the file
 * @retval SUCCESS If packets have been successfully read from the file
 */
NVP_EXPORT NVP_ErrorCode streamReadData(StreamHandle handle, PacketInfo* info, int16_t* data, int channel_count, int packet_count, int* packets_read);

/**
 * Configure the basestation emulation mode.
 *
 * @param handle Device handle of basestation
 * @param mode Emulator mode
 */
NVP_EXPORT NVP_ErrorCode setDeviceEmulatorMode(DeviceHandle handle, DeviceEmulatorMode mode);

/**
 * Get basestation emulation mode.
 *
 * @param handle Device handle of basestation
 * @param mode Emulator mode
 */
NVP_EXPORT NVP_ErrorCode getDeviceEmulatorMode(DeviceHandle handle, DeviceEmulatorMode* mode);

/**
 * Configure the basestation emulator type.
 *
 * @param handle Device handle of basestation
 * @param type Emulator type
 */
NVP_EXPORT NVP_ErrorCode setDeviceEmulatorType(DeviceHandle handle, DeviceEmulatorType type);

/**
 * Get basestation emulator type.
 *
 * This function can only be called if no emulated probes are open.
 * Call this function before calling openProbes.
 *
 * @param handle Device handle of basestation
 * @param type Emulator type
 */
NVP_EXPORT NVP_ErrorCode getDeviceEmulatorType(DeviceHandle handle, DeviceEmulatorType* type);

/**
 * Run built-in/automated self test on basestation.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode bistBS(DeviceHandle handle);

/**
 * Start PRBS test for data and control SerDes links.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode bistStartPRBS(DeviceHandle handle);

/**
 * Stop PRBS test for data and control SerDes links.
 *
 * @param handle Device handle of the basestation
 * @param prbs_err_data Error count for data SerDes link (can be NULL)
 * @param prbs_err_ctrl Error count for control (SPI) SerDes link (can be NULL)
 */
NVP_EXPORT NVP_ErrorCode bistStopPRBS(DeviceHandle handle, int* prbs_err_data, int* prbs_err_ctrl);

/**
 * Read PRBS test error count for data and control SerDes links.
 *
 * @param handle Device handle of the basestation
 * @param prbs_err_data Error count for data SerDes link (can be NULL)
 * @param prbs_err_ctrl Error count for control (SPI) SerDes link (can be NULL)
 */
NVP_EXPORT NVP_ErrorCode bistReadPRBS(DeviceHandle handle, int* prbs_err_data, int* prbs_err_ctrl);

/**
 * BIST to read/write from/to ASIC memory map.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 */
NVP_EXPORT NVP_ErrorCode bistSPIMM(DeviceHandle handle, uint8_t probe);

/**
 * BIST to read/write from/to EEPROM on headstage and connected mezzanine boards.
 *
 * @param handle Device handle of the basestation
 */
NVP_EXPORT NVP_ErrorCode bistEEPROM(DeviceHandle handle);

/**
 * BIST to test write to ASIC SR chains.
 *
 * @param handle Device handle of the basestation
 * @param probe Index of the probe/mezzanine board (valid range 0 to 3)
 */
NVP_EXPORT NVP_ErrorCode bistSR(DeviceHandle handle, uint8_t probe);