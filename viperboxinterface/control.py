from __future__ import annotations

import copy
import logging
import logging.handlers
import os
import threading
import time
import traceback
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import numpy as np
import requests
from lxml import etree
from XML_handler import (
    add_to_stimrec,
    check_script_validity,
    check_xml_boxprobes_exist_and_verify_data_with_settings,
    create_empty_xml,
    update_settings_with_XML,
    verify_params,
    verify_step_min_max,
)

import viperboxinterface.NeuraviperPy as NVP
from viperboxinterface.data_classes import (
    BoxSettings,
    ConnectedBoxes,
    ConnectedProbes,
    GeneralSettings,
    ProbeSettings,
    StatusTracking,
    parse_numbers,
)
from viperboxinterface.data_thread import _DataSenderThread
from viperboxinterface.mappings import Mappings

# TODO: implement rotation of logs to not hog up memory


class ViperBox:
    """Class for interacting with the IMEC Neuraviper API."""

    NUM_SAMPLES = 500
    NUM_CHANNELS = 60
    SKIP_SIZE = 20
    FREQ = 20000
    OS_WRITE_TIME = 1

    def __init__(self, _session_datetime: str, start_oe=True, use_mapping=True) -> None:
        """Initialize the ViperBox class."""
        self._working_directory = os.getcwd()

        self.local_settings = GeneralSettings()
        self.connected = ConnectedBoxes()
        self.uploaded_settings = GeneralSettings()
        self.tracking = StatusTracking()
        self._box_ptrs: Any = {}
        self.mapping = Mappings("defaults/electrode_mapping_short_cables.xlsx")

        self._session_datetime = _session_datetime
        self._rec_start_time: float | None = None

        log_folder = Path.cwd() / "logs"
        log_file = f"log_{self._session_datetime}.log"
        log_folder.mkdir(parents=True, exist_ok=True)
        self._log = log_folder.joinpath(log_file)
        self.stim_file_path: Path | None = None
        self._rec_path: Path | None = None

        self.start_oe = start_oe
        self.boxless = False
        self.emulation = False
        self.use_mapping = use_mapping

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        socketHandler = logging.handlers.SocketHandler(
            "localhost",
            logging.handlers.DEFAULT_TCP_LOGGING_PORT,
        )
        self.logger.addHandler(socketHandler)
        self.mtx = self._os2chip_mat()

        if not self.use_mapping:
            self.logger.info("Bypassing mapping")
            self.NUM_CHANNELS = 64

        # Debugging functionality to switch permanent discharge on on these channels
        self.permanent_discharge_list: list = []

        return None

    def connect_oe(self, reset=False) -> tuple[bool, str]:
        """
        Check if Open Ephys is running and start it if not.

        Connect once TCP to Open Ephys once it started, send some data and maybe wait
        for a connections response.

        Treats following variables:
        - OE running
        - Data thread existing
        - Connected
        """
        # Start OE
        self.logger.info("Checking if Open Ephys is running")
        try:
            r = requests.get("http://localhost:37497/api/status", timeout=0.1)
            self.logger.info("Open Ephys is running")
        except Exception:
            threading.Thread(target=self._start_oe, daemon=True).start()
            self.logger.info("Open Ephys not running, starting it")
            time.sleep(2)
            # Wait for OE finish starting
            r = requests.get("http://localhost:37497/api/status", timeout=5)

        # Check if data thread exists
        if hasattr(self, "data_thread"):
            self.logger.info("Data thread exists")
        else:
            self.data_thread = _DataSenderThread(
                self.NUM_SAMPLES,
                self.FREQ,
                self.NUM_CHANNELS,
                self.mtx,
                self.use_mapping,
            )
            self.data_thread.start("", 0, empty=True)
            r = requests.put(
                "http://localhost:37497/api/status",
                json={"mode": "ACQUIRE"},
                timeout=1,
            )
            return True, "Open Ephys was already running. Data thread created."

        # check if data thread is connected
        if reset:
            self.data_thread.shutdown()
            self.data_thread = _DataSenderThread(
                self.NUM_SAMPLES,
                self.FREQ,
                self.NUM_CHANNELS,
                self.mtx,
                self.use_mapping,
            )
            self.data_thread.start("", 0, empty=True)
            r = requests.put(
                "http://localhost:37497/api/status",
                json={"mode": "ACQUIRE"},
                timeout=1,
            )
            return (
                True,
                "Both Open Ephys and data thread were running, data thread recreated",
            )
        else:
            r = requests.get("http://localhost:37497/api/status", timeout=0.1)
            if r.json()["mode"] != "ACQUIRE":
                self.data_thread.start("", 0, empty=True)
                r = requests.put(
                    "http://localhost:37497/api/status",
                    json={"mode": "ACQUIRE"},
                    timeout=1,
                )
            return True, "Open Ephys running and connected"

    def connect(
        self,
        probe_list: str = "1",
        emulation: bool = False,
        boxless: bool = False,
    ) -> tuple[bool, str]:
        """Initiates ViperBox and connects to probes. Box is created and emulation\
        type is set.

        TODO: !!!!! all existing data is removed because the local settings are reset.
        The solution is to mention this in the docs and GUI.
        """
        # self._time()
        self.boxless = boxless
        self.emulation = emulation
        self.logger.info(
            f"ViperBox connect: probe list: {probe_list}, emulation: {self.emulation}, \
boxless: {boxless}.",
        )

        # Checks if the ViperBox is connected and connects if not.
        if self.tracking.box_connected is True:
            self.logger.info("Already connected to ViperBox, disconnecting first.")
            self.disconnect()

        if self.boxless is False:
            self.logger.info("Connecting to ViperBox...")

        # check if boxless mode is enabled
        if self.boxless is True:
            # Boxless mode connects 1 box and 1 probe
            self.connected.boxes[0] = ConnectedProbes()
            self.connected.boxes[0].probes[0] = True
            self.recording_settings(default_values=True)
            self.stimulation_settings(default_values=True)
            self.logger.info(f"local settings: {self.local_settings}")
            self.logger.info(f"connected probes: {self.local_settings.connected}")
            return True, "Boxless mode, no connection to ViperBox"

        # check if probes is a list of 4 elements and only containing ints 1 or 0
        try:
            probe_list_int = parse_numbers(probe_list, [0, 1, 2, 3])
        except ValueError as e:
            return (
                False,
                f"Invalid probe list: {self._er(e)}",
            )

        if self.start_oe:
            threading.Thread(target=self._start_oe, daemon=True).start()

        # Scan for devices
        NVP.scanBS()
        devices = NVP.getDeviceList(16)
        number_of_devices = len(devices)
        if number_of_devices == 0:
            err_msg = "No device found, please check if the ViperBox is connected"
            self.logger.error(err_msg)
            return False, err_msg
        elif number_of_devices > 1:
            err_msg = """More than one device found, currently this software can only \
                box one device"""
            self.logger.error(err_msg)
            return False, err_msg
        elif number_of_devices == 1:
            self.logger.info(f"Device found: {devices[0]}")
            # TODO add box settings and info and stuffff
            self.local_settings.boxes[0] = BoxSettings()
            self.connected.boxes[0] = ConnectedProbes()
        else:
            self.logger.info(
                "Unknown error, please restart the ViperBox or check the \
                logs for more information",
            )
            return False, "Unknown error, please check the logs for more information"
        self.tracking.box_connected = True

        # Connect and set up viperbox
        # TODO boxfix: also loop over boxes
        box = 0
        tmp_handel = NVP.createHandle(devices[0].ID)
        self._box_ptrs[box] = tmp_handel
        # self._box_ptrs[box] = NVP.createHandle(devices[0].ID)
        self.logger.info(f"Box handle created: {self._box_ptrs[box]}")
        NVP.openBS(self._box_ptrs[box])
        self.logger.info(f"BS opened: {self._box_ptrs[box]}")
        if (
            self.emulation is True
        ):  # Choose linear ramp emulation (1 sample shift between channels)
            NVP.setDeviceEmulatorMode(
                self._box_ptrs[box],
                NVP.DeviceEmulatorMode.STATIC,
            )
            NVP.setDeviceEmulatorType(
                self._box_ptrs[box],
                NVP.DeviceEmulatorType.EMULATED_PROBE,
            )
            self.logger.info("Emulation mode: linear ramp")
        else:
            NVP.setDeviceEmulatorMode(self._box_ptrs[box], NVP.DeviceEmulatorMode.OFF)
            NVP.setDeviceEmulatorType(self._box_ptrs[box], NVP.DeviceEmulatorType.OFF)
            self.logger.info("Emulation mode: off")
        # print(
        #     f"""{self._time()-start_time} finished setting emulation, starting \
        #     opening probes"""
        # )
        try:
            NVP.openProbes(self._box_ptrs[box])
        except Exception as e:
            self.logger.warning(f"!! NVP.openProbes() exception error: {self._er(e)}")
            self.disconnect()
            return False, "Please connect asic to ViperBox and try again."
        self.logger.info(f"Probes opened: {self._box_ptrs[box]}")

        # print(f"{self._time()-start_time} opened probes, starting initialization")
        # Connect and set up probes
        # TODO boxfix: also loop over boxes
        for probe in probe_list_int:
            try:
                NVP.init(self._box_ptrs[box], int(probe))  # Initialize all probes
                self.logger.info(f"Probe {probe} initialized: {self._box_ptrs[box]}")
                self.local_settings.boxes[0].probes[probe] = ProbeSettings()
                self.connected.boxes[0].probes[probe] = True
            except Exception as error:
                self.logger.warning(
                    f"!! NVP.init() exception error, probe {probe}: {self._er(error)}",
                )
        self.logger.info(f"API channel opened: {devices[0]}")
        self._deviceId = devices[0].ID

        self.uploaded_settings = copy.deepcopy(self.local_settings)

        # TODO boxfix: also loop over boxes
        return (
            True,
            f"""ViperBox initialized successfully with probes \
{self.local_settings.connected}""",
        )

    def disconnect(self) -> tuple[bool, str]:
        """Disconnects from the ViperBox and closes the API channel."""
        try:
            self.data_thread.shutdown()
        except Exception:
            pass

        if self.boxless is True:
            return True, "Boxless mode, no connection to ViperBox"
        elif self.tracking.box_connected is False:
            return True, "Not connected to ViperBox"

        # TODO boxfix: also loop over boxes
        try:
            box = 0
            NVP.closeProbes(self._box_ptrs[box])
            NVP.closeBS(self._box_ptrs[box])
            NVP.destroyHandle(self._box_ptrs[box])
            self._deviceId = 0
            self.tracking.box_connected = False
            self.uploaded_settings = GeneralSettings()
            self.logger.info("ViperBox disconnected")
        except KeyError as e:
            self.logger.debug(
                f"Can't disconnect from ViperBox, no ViperBox connection. \
Error: {self._er(e)}",
            )
            return (
                False,
                "Can't disconnect from ViperBox, no ViperBox connection. \
Please restart the ViperBox and the software and try again.",
            )

        return True, "ViperBox disconnected"

    def shutdown(self) -> tuple[bool, str]:
        self.disconnect()
        return True, "ViperBox shutdown"

    def _upload_recording_settings(
        self,
        updated_tmp_settings,
        mapping_file="defaults/electrode_mapping_short_cables.xlsx",
    ):
        if self.boxless is True:
            self.logger.info(
                "No box connected, skipping uploading recording settings \
to ViperBox",
            )
            return

        # TODO multibox this should be added to general settings and loaded if the
        # instructions do not come from XML but from probably the GUI.
        self.mapping = Mappings(mapping_file)

        for box in updated_tmp_settings.boxes.keys():
            for probe in updated_tmp_settings.boxes[box].probes.keys():
                for channel in (
                    updated_tmp_settings.boxes[box].probes[probe].channel.keys()
                ):
                    try:
                        input_selection = self.mapping.channel_input[channel]
                        if not self.use_mapping:
                            input_selection = 0
                        NVP.selectElectrode(
                            self._box_ptrs[box],
                            probe,
                            channel,
                            input_selection,
                        )
                    except KeyError:
                        self.logger.debug(
                            f"Input for channel {channel} not found, defaulting to 0"
                        )
                        NVP.selectElectrode(self._box_ptrs[box], probe, channel, 0)
                    NVP.setReference(
                        self._box_ptrs[box],
                        probe,
                        channel,
                        updated_tmp_settings.boxes[box]
                        .probes[probe]
                        .channel[channel]
                        .get_refs,
                    )
                    # self.logger.debug(
                    #     f"reference set: {updated_tmp_settings.boxes[box].probes[probe].channel[channel].get_refs}"
                    # )
                    NVP.setGain(
                        self._box_ptrs[box],
                        probe,
                        channel,
                        updated_tmp_settings.boxes[box]
                        .probes[probe]
                        .channel[channel]
                        .gain,
                    )
                    NVP.setAZ(
                        self._box_ptrs[box],
                        probe,
                        channel,
                        False,
                    )  # see email Patrick 08/01/2024

                self.logger.debug(
                    f"Writing Channel config to box: \
{updated_tmp_settings.boxes[box].probes[probe]}",
                )
                if not self.emulation:
                    NVP.writeChannelConfiguration(self._box_ptrs[box], probe, False)

    def set_permanent_discharge(self, oss) -> tuple[bool, str]:
        """Set the check OS for the stimulation settings."""
        if self.use_mapping:
            probe_mapping = Mappings("defaults/electrode_mapping_short_cables.xlsx")
            oss = [probe_mapping.probe_to_os_map[channel] for channel in oss]
        self.permanent_discharge_list = oss
        return True, f"Check OS set to {oss}"

    # def check_SR(self, lst):

    #     #Send/receive a single "SPI" command
    #     #lst    : 1-dimensional list "TX"
    #     #Return : 1-dimensional list "RX", or [] in case of error
    #     box=0
    #     probe= 0
    #     reply = []
    #     if lst == []:
    #         print("!! Empty command")
    #     else:                               #list  format e.g. [2,3,252,...]
    #         tx = bytes(lst)                 #bytes
    # format e.g. b'\x02\x03\xFC...' (immutable)
    #         try:
    #             rx = NVP.transferSPI(self._box_ptrs[box], probe, tx)
    #             print('.')
    #             reply = list(rx)
    #         except Exception as err:
    #             print("!! API SPI error:", err)
    #     return reply

    def _upload_stimulation_settings(self, updated_tmp_settings: GeneralSettings):
        """Uploads the stimulation settings to the ViperBox."""
        self.logger.info(
            f"Writing stimulation settings to ViperBox: {updated_tmp_settings}",
        )

        if self.boxless is True:
            self.logger.info(
                "No box connected, skipping uploading stimulation \
settings to ViperBox",
            )
            return
        for box in updated_tmp_settings.boxes.keys():
            for probe in updated_tmp_settings.boxes[box].probes.keys():
                # Always set settings for entire probe at once.
                NVP.setOSimage(
                    self._box_ptrs[box],
                    probe,
                    updated_tmp_settings.boxes[box].probes[probe].os_data,
                )
                self.logger.debug("printing osdata")
                self.logger.debug(updated_tmp_settings.boxes[box].probes[probe].os_data)
                for OStage in range(128):
                    NVP.setOSStimblank(self._box_ptrs[box], probe, OStage, True)
                    NVP.setOSDischargeperm(self._box_ptrs[box], probe, OStage, False)
                    if OStage in self.permanent_discharge_list:
                        NVP.setOSDischargeperm(self._box_ptrs[box], probe, OStage, True)
                NVP.writeOsConfiguration(self._box_ptrs[box], probe, False, False)

                for SU in (
                    updated_tmp_settings.boxes[box].probes[probe].stim_unit_sett.keys()
                ):
                    self.logger.debug(f"Writing SU configuration to {SU}")
                    NVP.writeSUConfiguration(
                        self._box_ptrs[box],
                        probe,
                        SU,
                        *updated_tmp_settings.boxes[box]
                        .probes[probe]
                        .stim_unit_sett[SU]
                        .SUConfig(),
                    )

    def recording_settings(
        self,
        xml_string: str | None = None,
        reset: bool = False,
        default_values: bool = False,
        read_mapping_xlsx: bool = False,
    ) -> tuple[bool, str]:
        """Loads the recording settings from an XML string or default file."""
        if self.boxless is True:
            pass
        elif self.tracking.box_connected is False:
            return False, "Not connected to ViperBox"

        if self.tracking.recording is True:
            return (
                False,
                "Recording in progress, cannot change settings. To verify \
custom XML settings, use the verify_xml API call.",
            )

        if default_values is True:
            XML_data = etree.parse("defaults/default_recording_settings.xml")
        else:
            try:
                XML_data = etree.fromstring(xml_string)
            except TypeError as e:
                return (
                    False,
                    f"Invalid xml string. Error: {self._er(e)}",
                )

        # make temporary copy of settings
        tmp_local_settings = copy.deepcopy(self.local_settings)

        self.logger.debug(f"Checking XML with settings: {tmp_local_settings}")
        result, feedback = check_xml_boxprobes_exist_and_verify_data_with_settings(
            XML_data,
            tmp_local_settings,
            self.connected,
            "recording",
        )
        # result, feedback = check_xml_with_settings(
        #     XML_data, tmp_local_settings, "recording"
        # )
        if result is False:
            return result, feedback

        if reset:
            self.logger.info("Resetting recording settings")
            tmp_local_settings.reset_recording_settings()
        self.logger.info("Updating supplied settings to local settings")
        # add connected boxes and probes to tmp_local_settings

        updated_tmp_settings = update_settings_with_XML(
            XML_data,
            tmp_local_settings,
            "recording",
        )

        try:
            # Always set settings for entire probe at once.
            # TODO boxfix: also loop over boxes
            self._upload_recording_settings(updated_tmp_settings)
        except Exception as e:
            return (
                False,
                f"Error in uploading recording settings, settings not applied and \
reverted to previous settings. Error: {self._er(e)}",
            )

        self.local_settings = updated_tmp_settings  # Why not deepcopy??
        self.logger.info("uploaded_settings = local_settings")
        self.uploaded_settings = copy.deepcopy(self.local_settings)
        return True, "Recording settings loaded"

    # def _stimrec_write_recording_settings(self, settings_to_write, start_time, dt_time):
    #     self.logger.info(
    #         f"Writing recording settings to stimrec file: {settings_to_write}",
    #     )
    #     for box in updated_tmp_settings.boxes.keys():
    #         for probe in updated_tmp_settings.boxes[box].probes.keys():
    #             if self.stim_file_path is not None:
    #                 for channel in (
    #                     self.uploaded_settings.boxes[box].probes[probe].channel.keys()
    #                 ):
    #                     add_to_stimrec(
    #                         self.stim_file_path,
    #                         "Settings",
    #                         "Channel",
    #                         {
    #                             "box": box,
    #                             "probe": probe,
    #                             "channel": channel,
    #                             **self.uploaded_settings.boxes[box]
    #                             .probes[probe]
    #                             .channel[channel]
    #                             .__dict__,
    #                         },
    #                         start_time,
    #                         dt_time,
    #                     )

    def _stimrec_write_stimulation_settings(
        self,
        updated_tmp_settings,
        start_time,
        dt_time,
    ):
        self.logger.info(
            f"Writing stimulation settings to stimrec file: {updated_tmp_settings}",
        )
        if self.stim_file_path:
            for box in updated_tmp_settings.boxes.keys():
                for probe in updated_tmp_settings.boxes[box].probes.keys():
                    for configuration in (
                        updated_tmp_settings.boxes[box]
                        .probes[probe]
                        .stim_unit_sett.keys()
                    ):
                        add_to_stimrec(
                            self.stim_file_path,
                            "Settings",
                            "Configuration",
                            {
                                "box": box,
                                "probe": probe,
                                "stimunit": configuration,
                                **updated_tmp_settings.boxes[box]
                                .probes[probe]
                                .stim_unit_sett[configuration]
                                .__dict__,
                            },
                            start_time,
                            dt_time,
                        )
                    for mapping in (
                        updated_tmp_settings.boxes[box]
                        .probes[probe]
                        .stim_unit_os.keys()
                    ):
                        add_to_stimrec(
                            self.stim_file_path,
                            "Settings",
                            "Mapping",
                            {
                                "box": box,
                                "probe": probe,
                                "stimunit": mapping,
                                "electrodes": updated_tmp_settings.boxes[box]
                                .probes[probe]
                                .stim_unit_os[mapping],
                            },
                            start_time,
                            dt_time,
                        )
        return True, "Stimulation settings wrote to stimrec file"

    def stimulation_settings(
        self,
        xml_string: str | None = None,
        reset: bool = False,
        default_values: bool = True,
    ) -> tuple[bool, str]:
        """Loads the stimulation settings from an XML file."""
        if self.boxless is True:
            pass
        elif self.tracking.box_connected is False:
            return False, "Not connected to ViperBox"
        # elif self.tracking.recording is True:
        #     return (
        #         False,
        #         "Recording in progress, cannot change settings. First stop recording.",
        #     )

        if default_values is True:
            XML_data = etree.parse("defaults/default_stimulation_settings.xml")
        else:
            try:
                XML_data = etree.fromstring(xml_string)
            except TypeError as e:
                return (
                    False,
                    f"Invalid xml string. Error: {self._er(e)}",
                )

        tmp_local_settings = copy.deepcopy(self.local_settings)

        result, feedback = check_xml_boxprobes_exist_and_verify_data_with_settings(
            XML_data,
            tmp_local_settings,
            self.connected,
            "stimulation",
        )

        if result is False:
            return result, feedback

        if reset:
            tmp_local_settings.reset_stimulation_settings()

        updated_tmp_settings = update_settings_with_XML(
            XML_data,
            tmp_local_settings,
            "stimulation",
        )

        # TODO boxfix: also loop over boxes
        start_time = self._time()
        try:
            self._upload_stimulation_settings(updated_tmp_settings)
            self.uploaded_settings = copy.deepcopy(updated_tmp_settings)
            self.tracking.stimulation_settings_uploaded = True
            self.tracking.stimulation_settings_written_to_stimrec = False
        except Exception as e:
            return (
                False,
                f"Error in uploading stimulation settings, settings not applied and \
reverted to previous settings. Error: {self._er(e)}",
            )
        dt_time = self._time() - start_time

        self.tracking.stimset_upload_times = (start_time, dt_time)
        self.local_settings = copy.deepcopy(updated_tmp_settings)

        # # if stim_file_path doesn't exist, the recording hasn't started yet
        # # settings will be written to stimrec at recording start
        # if self.stim_file_path:
        #     result, feedback = self._stimrec_write_stimulation_settings(
        #         updated_tmp_settings, start_time, dt_time
        #     )
        #     if result is False:
        #         return result, feedback

        return True, "Stimulation settings loaded"

    def verify_xml_with_local_settings(
        self,
        XML_dictionary: dict,
        XML_data: Any,
        check_topic: str = "all",
    ) -> tuple[bool, str]:
        """API Verifies the XML string or dictionary."""
        tmp_data = copy.deepcopy(self.local_settings)

        if XML_dictionary != {}:
            params = [
                tuple
                for tuple in verify_params
                if list(XML_dictionary.keys())[0] in tuple
            ]
            try:
                int(list(XML_dictionary.values())[0])
            except ValueError:
                return (
                    False,
                    "Input value should be an integer",
                )
            verify_step_min_max(*params[0], int(list(XML_dictionary.values())[0]))
            return True, f"Verify xml call with dictionary: {XML_dictionary}"
        elif XML_data != "":
            result, feedback = check_xml_boxprobes_exist_and_verify_data_with_settings(
                XML_data,
                tmp_data,
                self.connected,
                "all",
            )
        else:
            return False, "No XML data found"

        # TODO:
        return result, feedback

    def default_settings(self) -> tuple[bool, str]:
        """Loads the default settings from an XML file."""
        if self.boxless is True:
            pass
        elif self.tracking.box_connected is False:
            return False, "Not connected to ViperBox"

        if self.tracking.recording is True:
            return (
                False,
                """Recording in progress, cannot change settings. First stop recording \
to load default settings""",
            )

        XML_data = etree.parse("defaults/default_settings.xml")

        tmp_local_settings = copy.deepcopy(self.local_settings)

        result, feedback = check_xml_boxprobes_exist_and_verify_data_with_settings(
            XML_data,
            tmp_local_settings,
            self.connected,
            "all",
        )
        # result, feedback =
        # check_xml_with_settings(XML_data, tmp_local_settings, "all")

        if result is False:
            return result, feedback

        tmp_local_settings.reset_probe_settings()

        updated_tmp_settings = update_settings_with_XML(
            XML_data,
            tmp_local_settings,
            "recording",
        )
        updated_tmp_settings = update_settings_with_XML(
            XML_data,
            updated_tmp_settings,
            "stimulation",
        )

        # TODO boxfix: also loop over boxes
        try:
            self._upload_recording_settings(updated_tmp_settings)
        except Exception as e:
            if e == KeyError and self.boxless is True:
                self.logger.info("No box connected, skipping recording settings")
            else:
                return (
                    False,
                    f"Error in uploading recording settings, settings not applied and \
reverted to previous settings. Error: {self._er(e)}",
                )

        start_time = self._time()
        try:
            self._upload_stimulation_settings(updated_tmp_settings)
            self.tracking.stimulation_settings_uploaded = True
            self.tracking.stimulation_settings_written_to_stimrec = False
        except Exception as e:
            return (
                False,
                f"Error in uploading stimulation settings, settings not applied and \
reverted to previous settings. Error: {self._er(e)}",
            )

        dt_time = self._time() - start_time
        self.tracking.stimset_upload_times = (start_time, dt_time)

        self.local_settings = updated_tmp_settings
        self.uploaded_settings = copy.deepcopy(self.local_settings)

        return True, "Default recording and stimulation settings loaded"

    def start_recording(self, recording_name: str = "") -> tuple[bool, str]:
        """Start recording.

        Arguments:
        ---------
        - recording_name: str | None - the name of the recording, it will be
        saved in the Recordings folder. This can also be a folder path or a
        file path. If it is a folder path, the recording will be saved as
        unnamed_recording in that folder. In case of a file path, the recording will be
        named as the filepath. If no name is given, the recording will be saved as
        unnamed_recording in the Recordings folder.

        Tests:
        - start recording with incomplete settings uploaded
        """
        if self.boxless is True or self.emulation is True:
            pass
        elif self.tracking.box_connected is False:
            return False, "Not connected to ViperBox"

        if self.tracking.recording is True:
            return (
                False,
                """Already recording, first stop recording to start a new \
                    recording""",
            )

        # TODO this should check if recording settings are available for all
        # connected boxes
        if not self.emulation:
            self.logger.debug("Check if uploaded settings has all recording settings")
            for box in self.uploaded_settings.boxes.keys():
                for probe in self.uploaded_settings.boxes[box].probes.keys():
                    if (
                        len(self.uploaded_settings.boxes[box].probes[probe].channel)
                        != 64
                    ):
                        return (
                            False,
                            f"""No recording settings available for all channels on box {box}, probe {probe}. First upload default settings for all channels, then upload your custom settings and then try again.""",
                        )

        self._recording_datetime = time.strftime("%Y%m%d_%H%M%S")

        rec_folder = Path.cwd() / "Recordings"
        rec_folder.mkdir(parents=True, exist_ok=True)
        self.recording_name = recording_name

        # The options are: no input, input fname, input bs, input full path
        if not ("\\" in self.recording_name or "/" in self.recording_name):
            # this is a filename
            self._rec_path = rec_folder.joinpath(
                f"{self.recording_name}_{self._recording_datetime}.bin",
            )
        elif "\\" in self.recording_name or "/" in self.recording_name:
            tmp_rec_path = Path(self.recording_name)
            # this is a path
            # the last folder is used with unnamed recording
            # the file is used as is
            if tmp_rec_path.exists():
                if tmp_rec_path.is_dir():
                    self._rec_path = tmp_rec_path.joinpath(
                        f"unnamed_recording_{self._recording_datetime}.bin",
                    )
                elif tmp_rec_path.is_file():
                    self._rec_path = tmp_rec_path.with_suffix(".bin")
        else:
            self._rec_path = rec_folder.joinpath(
                f"unnamed_recording_{self._recording_datetime}.bin",
            )

        self.logger.debug(self._box_ptrs)
        self.logger.debug("NVP.setFileStream")
        box = 0
        NVP.setFileStream(self._box_ptrs[box], str(self._rec_path))
        self.logger.debug("NVP.enableFileStream")
        NVP.enableFileStream(self._box_ptrs[box], str(self._rec_path))
        self.logger.debug("NVP.arm")
        NVP.arm(self._box_ptrs[box])

        self.logger.debug("NVP.setSWTrigger")
        self._rec_start_time = self._time()
        NVP.setSWTrigger(self._box_ptrs[box])
        dt_rec_start = self._time()

        if self.recording_name:
            stimrec_name = self.recording_name
        else:
            stimrec_name = "unnamed_stimulation_record"
        self.stim_file_path = self._create_file_folder(
            "Stimulations",
            stimrec_name,
            "xml",
            f"{time.strftime('%Y%m%d_%H%M%S')}",
        )

        # Create stimulation record
        create_empty_xml(self.stim_file_path, stimrec_name)

        self.logger.debug("Write recording settings to stimrec")
        # Write recording settings to stimrec
        for box in self.uploaded_settings.boxes.keys():
            for probe in self.uploaded_settings.boxes[box].probes.keys():
                for channel in (
                    self.uploaded_settings.boxes[box].probes[probe].channel.keys()
                ):
                    add_to_stimrec(
                        self.stim_file_path,
                        "Settings",
                        "Channel",
                        {
                            "box": box,
                            "probe": probe,
                            "channel": channel,
                            **self.uploaded_settings.boxes[box]
                            .probes[probe]
                            .channel[channel]
                            .__dict__,
                        },
                        0.01,
                        0.01,
                    )

        # Not necessary because will be written at stimulation start
        # # Try to write stimulation settings to stimrec if they are available.
        # self._stimrec_write_stimulation_settings(self.local_settings, 0.01, 0.01)
        self.logger.debug("Write recording start to stimrec")
        add_to_stimrec(
            self.stim_file_path,
            "Instructions",
            "Instruction",
            {"filename": self.recording_name, "instruction_type": "recording_start"},
            0.0,
            dt_rec_start,
        )

        self.tracking.recording = True

        # TODO fix probe number
        # probably add a que for all data streams and be able to let open ephys
        # switch between them
        self.oe_socket = True
        probe = 0
        self.logger.debug("Start sending data")
        self.data_thread.start(self._rec_path, probe, empty=False)

        self.logger.info(f"Recording started: {recording_name}")

        r = requests.put(
            "http://localhost:37497/api/recording",
            json={
                "parent_directory": str(self._rec_path.parent),
                "append_text": "",
                "base_text": str(self._rec_path.stem),
                "prepend_text": "",
                "default_record_engine": "OPENEPHYS",
            },
            timeout=0.1,
        )
        self.logger.info(
            f"Renaming of recording file name and directory: {r.status_code}"
        )

        return True, f"Recording started: {recording_name}"

    def _time(self) -> float:
        """Returns the current time in seconds.
        If _rec_start_time exists, it will be subtracted from the current time.

        Year 2262 this will wrap.
        """
        if self._rec_start_time:
            effective_time = time.time_ns() / 1e9 - self._rec_start_time
            if effective_time < 1e8:
                return effective_time
            else:
                return -0.01
        else:
            return time.time_ns() / 1e9

    def _create_file_folder(
        self,
        folder_name: str,
        file_name: str,
        extension: str,
        custom_datetime: None | str = None,
        create_empty_file: bool = False,
    ) -> Path:
        folder = Path.cwd() / folder_name
        if custom_datetime:
            file = f"{file_name}_{custom_datetime}.{extension}"
        else:
            file = f"{file_name}_{time.strftime('%Y%m%d_%H%M%S')}.{extension}"
        folder.mkdir(parents=True, exist_ok=True)
        if create_empty_file:
            open(folder.joinpath(file), "w").close()
        self.logger.info(f"Created file: {folder.joinpath(file)}")
        return folder.joinpath(file)

    def _start_oe(self):
        try:
            requests.get("http://localhost:37497/api/status", timeout=0.1)
        except Exception:
            # TODO: change to shortcut in
            # C:\ProgramData\Microsoft\Windows\Start Menu\Programs
            os.startfile(r"C:\Program Files\Open Ephys\open-ephys.exe")

    def _os2chip_mat(self):
        mtx = np.zeros((64, self.NUM_CHANNELS), dtype="uint16")
        for k, v in self.mapping.electrode_mapping.items():
            mtx[k][v] = 1
        return mtx

    def stop_recording(self) -> tuple[bool, str]:
        if self.tracking.box_connected is False:
            return False, "Not connected to ViperBox"

        if self.tracking.recording is False:
            return False, "Recording not started"

        self.logger.info("Stopping recording")
        start_time = self._time()
        box = 0
        self.logger.debug("Run NVP.arm to stop recording")
        NVP.arm(self._box_ptrs[box])
        # Close file
        self.logger.debug("Run NVP.setFileStream to no name")
        NVP.setFileStream(self._box_ptrs[box], "")
        dt_time = self._time() - start_time
        self.oe_socket = False

        self.logger.debug("Write to stimrec")
        add_to_stimrec(
            self.stim_file_path,
            "Instructions",
            "Instruction",
            {"filename": self.recording_name, "instruction_type": "recording_stop"},
            start_time,
            dt_time,
        )

        self.tracking.recording = False
        self._rec_start_time = None

        # TODO: combine stim history and recording into some file format
        # self._convert_recording()

        return True, "Recording stopped"

    def _SU_list_to_bitmask(self, SU_list: list[int]) -> int:
        # convert SUs to NVP format
        SU_string = "".join(["1" if i in SU_list else "0" for i in range(8)])
        SU_string = SU_string[::-1]
        self.logger.debug(f"SU_string bitmask (SU8, SU7, .., SU1): {SU_string}")
        return int(SU_string, 2)

    def start_stimulation(
        self,
        boxes: str,
        probes: str,
        SU_input: str,
    ) -> tuple[bool, str]:
        """Starts stimulation on the specified box(s), probe(s) and SU(s).
        First checks if the SUs are configured for their respective boxes and probes.

        Arguments:
        ---------
        - boxes: str - all boxes to start stimulation in
        - probes: str - all probes to start stimulation in
        - SU_input: str - the SUs to start stimulation in

        Test:
        - Check if this also works if sus are half configured
        """
        if self.tracking.box_connected is False:
            return False, "Not connected to ViperBox"

        if self.tracking.recording is False:
            return (
                False,
                """No recording in progress, cannot start stimulation, please \
                    start recording first""",
            )

        if self.tracking.stimulation_settings_uploaded is False:
            return (
                False,
                """Stimulation settings not uploaded, please upload stimulation \
settings first""",
            )

        # Create a trigger dict
        # fill the trigger dict with values that are configured
        # trigger SUs and store time and dt
        # write stim settings to stimrec if not changed since last time
        # write triggers to stimrec

        # SU_dict = {0: {0: [0,1,2], 1: [3,4,6]}}
        # SU_dict = {box: {probe: [SU_list in binary format]}}
        SU_dict: Any = {}
        # Check if boxes, probes and SUs are in right format and properly configured
        # i.e, have waveform configured
        # Using try/except to catch ValueError from parse_numbers
        for box in parse_numbers(boxes, list(self.uploaded_settings.boxes.keys())):
            SU_dict[box] = {}
            for probe in parse_numbers(
                probes,
                list(self.uploaded_settings.boxes[box].probes.keys()),
            ):
                SU_dict[box][probe] = self._SU_list_to_bitmask(
                    parse_numbers(
                        SU_input,
                        list(
                            self.uploaded_settings.boxes[box]
                            .probes[probe]
                            .stim_unit_sett.keys(),
                        ),
                    ),
                )
                # SU bitmask order is reversed, see _SU_list_to_bitmask
                SUs = [
                    index + 1
                    for index, char in enumerate(bin(SU_dict[box][probe])[2:])
                    if char == "1"
                ]
                self.logger.info(
                    f"Starting stimulation on box {box}, probe {probe}, SU's {SUs}"
                )
                for SU in SUs:
                    probe_info = self.uploaded_settings.boxes[box].probes[probe]
                    self.logger.debug(
                        f"On electrodes: {probe_info.stim_unit_os[int(SU)-1]}"
                    )

        start_dt_times: Any = {}

        # Trigger SUs
        self.logger.info(f"Triggering SUs: {SU_dict}")
        for box in SU_dict.keys():
            start_dt_times[box] = {}
            for probe in SU_dict[box].keys():
                tmp_counter = self._time()
                # TODO could be faster by not having to do this converstion here
                NVP.SUtrig1(
                    self._box_ptrs[box],
                    probe,
                    SU_dict[box][probe],
                )
                tmp_delta = self._time() - tmp_counter
                start_dt_times[box][probe] = (tmp_counter, tmp_delta)

        # Write stimulation settings to stimrec if not changed since last upload
        if self.tracking.stimulation_settings_written_to_stimrec is False:
            self._stimrec_write_stimulation_settings(
                self.uploaded_settings,
                self.tracking.stimset_upload_times[0],
                self.tracking.stimset_upload_times[1],
            )
            self.tracking.stimulation_settings_written_to_stimrec = True

        for box in start_dt_times.keys():
            for probe in start_dt_times[box].keys():
                add_to_stimrec(
                    self.stim_file_path,
                    "Instructions",
                    "Instruction",
                    {
                        "filename": self.recording_name,
                        "instruction_type": "stimulation_start",
                        "box": box,
                        "probe": probe,
                        "stimunit": SU_input,
                    },
                    start_dt_times[box][probe][0],
                    start_dt_times[box][probe][1],
                )

        return_statement = f"Stimulation started on box {boxes}, probe {probes} \
for SU's {SU_dict}"
        return True, return_statement

    def _er(self, error):
        return "".join(traceback.TracebackException.from_exception(error).format())

    def run_script(self, script_path: str) -> tuple[bool, str]:
        "Run script from XML file"

        self.logger.info("########## Initiating script")

        # check if already recording
        if self.tracking.recording is True:
            return (
                False,
                "Recording in progress, cannot run script. First stop recording to run a script",
            )

        # re-init settings
        self.logger.info("Re-initializing settings")
        self.local_settings = GeneralSettings()
        self.local_settings.boxes[0] = BoxSettings()
        self.connected = ConnectedBoxes()
        self.connected.boxes[0] = ConnectedProbes()
        self.uploaded_settings = GeneralSettings()
        self.tracking = StatusTracking()
        self.tracking.box_connected = True
        self.mapping = Mappings("defaults/electrode_mapping_short_cables.xlsx")

        # re-init probes
        self.logger.info("Re-initializing probes")
        probe_list_int = [0]
        box = 0
        for probe in probe_list_int:
            try:
                NVP.init(self._box_ptrs[box], int(probe))  # Initialize all probes
                self.logger.info(f"Probe {probe} initialized: {self._box_ptrs[box]}")
                self.local_settings.boxes[0].probes[probe] = ProbeSettings()
                self.connected.boxes[0].probes[probe] = True
            except Exception as error:
                self.logger.warning(
                    f"!! NVP.init() exception error, probe {probe}: {self._er(error)}",
                )

        self.uploaded_settings = copy.deepcopy(self.local_settings)

        # Check script validity
        self.logger.info("Checking script validity")
        return_value, return_message = check_script_validity(script_path)
        if not return_value:
            return return_value, return_message

        # Run script
        self.logger.info("Parse XML file")
        try:
            script = etree.parse(script_path)
        except etree.XMLSyntaxError as e:
            return (
                False,
                f"Error in XML file, sometimes before the line mentioned in the error message: {e}.",
            )
        root = script.getroot()
        file_name = root.attrib["file_name"]

        initial_time = -2.0
        # print(f"time: {time.time()}")
        self.logger.info("Start script")
        for element in root:
            # print("1 level:", element.tag)
            if element.tag == "Settings":
                for child in element:
                    # print("2 level: ", child.tag)
                    # if child.tag == "RecordingSettings": TODO this might need to be added
                    #     mapping_file = child.attrib["mapping_file"]
                    for grandchild in child:
                        start_time = grandchild.attrib["start_time"]
                        begin = f"<Program><Settings><{child.tag}>"
                        end = f"</{child.tag}></Settings></Program>"
                        middle = ET.tostring(grandchild).decode("utf-8")
                        middle = middle[:-3]
                        xml_string = begin + middle + end
                        while time.time() < initial_time + float(start_time):
                            time.sleep(0.01)
                        if grandchild.tag == "Channel":
                            # print(f"3 level: {grandchild.tag}: Channel")
                            self.logger.info(
                                f"Uploading recording settings with XML string: {xml_string}"
                            )
                            return_value, return_message = self.recording_settings(
                                xml_string
                            )
                            if not return_value:
                                self.logger.warning(return_message)
                        elif grandchild.tag in ["Configuration", "Mapping"]:
                            # print(f"3 level: {grandchild.tag}: Configuration or Mapping")
                            self.logger.info(
                                f"Uploading stimulation settings with XML string: {xml_string}"
                            )
                            return_value, return_message = self.stimulation_settings(
                                xml_string
                            )
                            if not return_value:
                                self.logger.warning(return_message)
            elif element.tag == "Instructions":
                for child in element:
                    # print("2 level: ", child.tag)
                    if (
                        child.tag == "Instruction"
                        and child.attrib["instruction_type"] == "recording_start"
                    ):
                        start_time = child.attrib["start_time"]
                        initial_time = time.time()
                        while time.time() < initial_time + float(start_time):
                            time.sleep(0.01)
                        # print(f"3 level: {child.attrib}: Start recording")
                        self.logger.warning(
                            f"Start recording with file name: {file_name}"
                        )
                        return_value, return_message = self.start_recording(file_name)
                        if not return_value:
                            self.logger.warning(return_message)
                    elif (
                        child.tag == "Instruction"
                        and child.attrib["instruction_type"] == "stimulation_start"
                    ):
                        start_time = child.attrib["start_time"]
                        while time.time() < initial_time + float(start_time):
                            time.sleep(0.01)
                        # print(f"3 level: {child.tag}: Stimulate")
                        self.logger.info(
                            f"Start stimulation on stimunit: {child.attrib['stimunit']}"
                        )
                        return_value, return_message = self.start_stimulation(
                            boxes=child.attrib["box"],
                            probes=child.attrib["probe"],
                            SU_input=child.attrib["stimunit"],
                        )
                        if not return_value:
                            self.logger.warning(return_message)
                    elif (
                        child.tag == "Instruction"
                        and child.attrib["instruction_type"] == "recording_stop"
                    ):
                        start_time = child.attrib["start_time"]
                        while time.time() < initial_time + float(start_time):
                            time.sleep(0.01)
                        # print(f"3 level: {child.tag}: Stop recording")
                        self.logger.info("Stop recording, end of script.")
                        return_value, return_message = self.stop_recording()
                        if not return_value:
                            self.logger.warning(return_message)

        return True, "Script ran successfully"


#     def _convert_recording(
#         self,
#     ) -> None:
#         """Converts the raw recording into a numpy format."""
#         # TODO: not implemented

#     def _add_to_zarr(self, databuffer: np.ndarray) -> None:
#         """Adds the data to the zarr file."""
#         # TODO: not implemented


# def TTL_start(
#     self, probe: str, TTL_channel: str, SU_input: str
# ) -> Tuple[bool, str]:
#     """Starts TTL on the specified channel."""
#     if TTL_channel not in [1, 2]:
#         return False, "TTL channel should be 1 or 2"

#     # Check SU_input format
#     SU_list = parse_numbers(SU_input, [1, 2, 3, 4, 5, 6, 7, 8])

#     # convert SUs to NVP format
#     SU_string = "".join(["1" if i in SU_list else "0" for i in range(1, 9)])
#     SU_bit_mask = int(SU_string, 2)

#     if self.tracking.box_connected is False:
#         return False, "Not connected to ViperBox"

#     if self.tracking.recording is True:
#         return False, "Recording in progress, cannot start stimulation"

#     all_configured, not_configured = self._check_SUs_configured(SU_bit_mask)
#     if not all_configured:
#         return False, f"Can't trigger SUs {not_configured}"

#     threading.Thread(
#         target=self._start_TTL_tracker_thread,
#         args=(probe, TTL_channel, SU_bit_mask),
#     ).start()
#     # self._start_TTL_tracker_thread(probe, TTL_channel, SU_bit_mask)

#     self._add_stimulation_record(
#         "TTL_start",
#         self._time() - self._rec_start_time,
#         0,
#         f"TTL channel: {TTL_channel}",
#     )

#     return (
#         True,
#         f"""TTL tracking started on channel {TTL_channel} with SU's
#         {SU_bit_mask} on probe {probe}""",
#     )

# def _start_TTL_tracker_thread(
#     self, probe: int, TTL_channel: int, SU_bit_mask: str
# ) -> None:
#     """Converts the raw recording into a numpy format."""
#     # TODO: this can be reduced to one function that listens to both TTL channels

#     # note this should be probe specific, not self._probe, that needs to
#     # be checked anyway
#     TTL_read_handle = NVP.streamOpenFile(self._rec_path, probe)

#     self._active_TTLs[TTL_channel] = True

#     # mtx = self._os2chip_mat()
#     while self._active_TTLs[TTL_channel] is True:
#         # TODO: implement skipping of packages by checking:
#         # time = 0
#         # NAND
#         # session id is wrong

#         packets = NVP.streamReadData(TTL_read_handle, self.BUFFER_SIZE)
#         count = len(packets)

#         if count < self.BUFFER_SIZE:
#             self.logger.warning("Out of packets")
#             break

#         # TODO: Rearrange data depending on selected gain
#         databuffer = np.asarray(
#             [
#                 [
#                     int(str(bin(packets[0].status))[3:-1][0]),
#                     int(str(bin(packets[0].status))[3:-1][1]),
#                 ]
#                 for i in range(self.BUFFER_SIZE)
#             ],
#             dtype="uint16",
#         )
#         if databuffer[:, TTL_channel].any():
#             ret_val, text = self.start_stimulation(probe, SU_bit_mask)

#         if ret_val is False:
#             # tell the user that the stimulation was not started
#             raise ThreadingError(ret_val, text)

# def TTL_stop(self, TTL_channel: int) -> Tuple[bool, str]:
#     """Stops the TTL tracker thread."""
#     if self._active_TTLs[TTL_channel] is False:
#         return False, f"TTL {TTL_channel} not running."

#     self._active_TTLs[TTL_channel] = False

#     return True, f"Tracking of TTL {TTL_channel} stopped."

# TODO: get session id from somewhere and store it as recording self parameter
# TODO: handle stimulation mappings (SU->input->mzipa->probe) and
# recording (probe->MZIPA->OS->chan)
# TODO: implement gain_vec in vb classes for usage in recording settings
