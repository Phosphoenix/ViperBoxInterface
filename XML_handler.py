import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any, Tuple

import numpy as np
from lxml import etree

from VB_classes import (
    BoxSettings,
    ChanSettings,
    GeneralSettings,
    ProbeSettings,
    SUSettings,
    parse_numbers,
    printable_dtd,
)

# logger = logging.getLogger(__name__)
logger = logging.getLogger("XML_handler")
logger.setLevel(logging.DEBUG)
socketHandler = logging.handlers.SocketHandler(
    "localhost", logging.handlers.DEFAULT_TCP_LOGGING_PORT
)
logger.addHandler(socketHandler)


def check_boxes_exist(data, existing_boxes):
    """Check if xml boxes are in existing boxes. If not, throw ValueError, else pass

    Arguments:
    - data: xml data of type lxml.etree._ElementTree
    - existing_boxes: list of existing boxes
    TODO: existing boxes should be changed to something that comes from the local
    settings.

    test cases:
    - xml box is not in existing boxes

    """
    for element in data.xpath(".//*[@box]"):
        setting_boxes = element.attrib["box"]
        _ = parse_numbers(setting_boxes, existing_boxes)
    return True


# def check_references_format(references: str) -> bool:
#     """Check if references are in the correct format

#     Arguments:
#     - references: string of 9 digits, only 1s and 0s

#     test cases:
#     - references are 10 digits
#     - references contains a 2
#     - references contains a letter
#     """
#     if len(references) != 9:
#         print("References should be a 9 digit string")
#         raise ValueError("References should be a 9 digit string")
#     if not all([i in ["0", "1", "b"] for i in references]):
#         print("References should only contain 0s and 1s")
#         raise ValueError("References should only contain 0s and 1s")
#     return True


def check_gain_input_format(gain: int) -> bool:
    """Check if gain or input is in the correct format

    Arguments:
    - gain or nput: integer between 1 and 4

    test cases:
    - gain is 5
    """
    gain = int(gain)
    gain += 1
    if gain not in [1, 2, 3, 4]:
        raise ValueError(
            f"Gain/input is {gain} or input should be an integer between 1 and 4"
        )
    return True


verify_params = [
    # name, step, min, max
    ("polarity", 1, 0, 1),
    # TODO deal with infinite pulses
    ("pulses", 1, 0, 255),
    ("amplitude1", 1, 0, 255),
    ("amplitude2", 1, 0, 255),
    ("duration", 100, 100, 25500),
    ("prephase", 100, 0, 25500),
    ("width1", 10, 0, 2550),
    ("interphase", 10, 10, 2550),
    ("width2", 10, 0, 2550),
    ("discharge", 100, 0, 25500),
    ("aftertrain", 100, 0, 25500),
]

screen_name = {
    "pulses": "Number of pulses",
    "prephase": "Prephase",
    "amplitude1": "Pulse amplitude anode",
    "width1": "1st pulse phase width",
    "interphase": "Pulse interphase interval",
    "amplitude2": "Pulse amplitude cathode",
    "width2": "2nd pulse phase width",
    "discharge": "Interpulse interval (discharge)",
    "duration": "Pulse duration",
    "aftertrain": "Train interval (discharge)",
}


def verify_step_min_max(name: str, step: int, min_val: int, max_val: int, value: int):
    """
    The variable name must be the first thing that is mentioned in the error message.
    It is used in the front end to correct a value to it's default.
    """
    if not min_val <= value <= max_val:
        raise ValueError(
            f"{screen_name[name]} must be between {min_val} and {max_val} and a \
multiple of {step}. It is now {value}."
        )
    if (value - min_val) % step != 0:
        raise ValueError(
            f"{screen_name[name]} must be between {min_val} and {max_val} and a \
multiple of {step}. It is now {value}."
        )
    return True


def overwrite_settings(
    data_xml: Any, local_settings: GeneralSettings, check_topic: str = "all"
):
    """Write xml data_xml to local settings, only if the respective boxes and probes
    are connected. Else they are skipped.
    Also checks if the values are allowed.

    Goes through all boxes and probes in data_xml xml

    Arguments:
    - data_xml: xml of type lxml.etree._ElementTree
    - local_settings: local settings of type GeneralSettings
    - check_topic: string, either "all", "recording" or "stimulation"

    """

    # TODO deal with overwriting all settings.
    logger.info(
        "THIS IS A TEST FROM XML_HANDLER, also deal with overwriting all \
                settings"
    )
    if check_topic == "all":
        tags = [
            "RecordingSettings",
            "StimulationWaveformSettings",
            "StimulationMappingSettings",
        ]
    elif check_topic == "recording":
        tags = ["RecordingSettings"]
    else:
        tags = ["StimulationWaveformSettings", "StimulationMappingSettings"]

    for XML_element in data_xml.iter():
        # goes through all XML_elements
        if XML_element.tag in tags:
            # if XML_element contains recording settings, add these settings
            for XML_settings in XML_element:
                boxes = parse_numbers(
                    XML_settings.attrib["box"], list(local_settings.connected.keys())
                )
                for box in boxes:
                    probes = parse_numbers(
                        XML_settings.attrib["probe"], local_settings.connected[box]
                    )
                    for probe in probes:
                        if XML_settings.tag == "Channel":
                            all_channels = parse_numbers(
                                XML_settings.attrib["channel"], list(range(64))
                            )
                            for channel in all_channels:
                                # check_references_format(
                                #     XML_settings.attrib["references"]
                                # )
                                check_gain_input_format(XML_settings.attrib["gain"])
                                check_gain_input_format(XML_settings.attrib["input"])
                                local_settings.boxes[box].probes[probe].channel[
                                    channel
                                ] = ChanSettings.from_dict(XML_settings.attrib)
                        if XML_settings.tag == "Configuration":
                            all_waveforms = parse_numbers(
                                XML_settings.attrib["stimunit"], list(range(8))
                            )
                            for waveform in all_waveforms:
                                for parameter_set in verify_params:
                                    verify_step_min_max(
                                        *parameter_set,
                                        int(XML_settings.attrib[parameter_set[0]]),
                                    )
                                local_settings.boxes[box].probes[probe].stim_unit_sett[
                                    waveform
                                ] = SUSettings.from_dict(XML_settings.attrib)
                        if XML_settings.tag == "Mapping":
                            all_mappings = parse_numbers(
                                XML_settings.attrib["stimunit"], list(range(8))
                            )
                            for mapping in all_mappings:
                                local_settings.boxes[box].probes[probe].stim_unit_elec[
                                    mapping
                                ] = parse_numbers(
                                    XML_settings.attrib["electrodes"],
                                    list(range(128)),
                                )
    return local_settings


def update_checked_settings(
    data: Any, settings: GeneralSettings, check_topic: str
) -> GeneralSettings:
    """
    Adds the xml to the settings dictionary.
    """

    settings = overwrite_settings(data, settings, check_topic)
    return settings


def check_xml_with_settings(
    data: Any, settings: GeneralSettings, check_topic: str, boxless: bool = False
) -> Tuple[bool, str]:
    """
    Checks if settings are valid with existing local_settings.
    """
    if isinstance(data, str):
        logger.debug("XML is supplied as string")
        data = etree.fromstring(data)
    else:
        logger.debug(f"XML is supplied as {type(data)}")
    if not boxless:
        logger.debug("Checking XML with boxless = False, so box should be attached.")
        try:
            check_boxes_exist(data, list(settings.connected.keys()))
        except ValueError as e:
            return False, f"Requested box is not connected. Error: {e}"
    else:
        logger.debug("Check XML with boxless = True.")
    try:
        _ = overwrite_settings(data, settings, check_topic)
    except ValueError as e:
        return False, f"Settings aren't valid. Error: {e}"
    return True, "XML is valid."


def create_empty_xml(path: Path):
    """Create an empty xml file with the root element Recording and a child element
        Settings

    It is assumed that the first line that is written to the stim record is always a
        settings line.

    Arguments:
    - path: path to the xml file

    Test cases:
    - path is not a string
    - first line is not a settings line
    """
    program = etree.Element("Recording")
    _ = etree.SubElement(program, "Settings")
    xml_bytes = etree.tostring(
        program, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
    with open(path, "wb") as xml_file:
        xml_file.write(xml_bytes)
    return program


def add_to_stimrec(
    path: Path | None,
    main_type: str,
    sub_type: str,
    settings_dict: dict,
    start_time: float,
    delta_time: float,
):
    """
    Add setting or instruction to the stimrec xml file.
    Converst from 0-indexing to 1-indexing.

    Arguments:
    - path: path to the xml file
    - main_type: type of the setting, should be 'Settings' or 'Instructions'
    - sub_type: sub_type of the setting, should be 'Channel', 'Configuration' or
        'Mapping' only in case of settings
    - settings_dict: dictionary with the settings to be added. This is currently not
        checked
    - start_time: start time of the setting
    - delta_time: delta time of the setting

    Test cases:
    - path is not a string
    - main_type is not 'Settings' or 'Instructions'
    - sub_type is not 'Channel', 'Configuration' or 'Mapping'
    - settings_dict is not a dictionary
    - keys/values in settings_dict are not strings
    - keys/values in settings_dict are not valid


    """
    if path is None:
        logger.error("Path to stimrec file is not defined.")
        raise ValueError("Path to stimrec file is not defined.")

    plus_one_list = ["box", "probe", "channel", "stimunit"]
    for key in plus_one_list:
        if key in settings_dict.keys():
            settings_dict[key] = settings_dict[key] + 1
    if "electrodes" in settings_dict.keys():
        settings_dict["electrodes"] = ", ".join(
            map(str, np.asarray(settings_dict["electrodes"]) + 1)
        )

    settings_dict = {str(key): str(value) for key, value in settings_dict.items()}
    settings_dict = {
        "start_time": str(start_time),
        "delta_time": str(delta_time),
        **settings_dict,
    }
    sub_type_map = {
        "Channel": "RecordingSettings",
        "Configuration": "StimulationWaveformSettings",
        "Mapping": "StimulationMappingSettings",
        "Instruction": "Instructions",
    }
    if main_type not in ["Settings", "Instructions"]:
        raise ValueError(
            f"""{main_type} is not a valid type, should be 'Settings' or 
                        'Instructions'"""
        )
    if sub_type not in sub_type_map.keys():
        raise ValueError(
            f"""{sub_type} is not a valid sub_type, should be 'Channel', 
                        'Configuration' or 'Mapping'"""
        )

    program = etree.parse(path)
    recording = program.getroot()
    recording_list = list(recording)
    if main_type == "Settings":
        # recording list == [settings]
        if len(recording_list) == 1:
            settings = recording.find(".//Settings")
        # recording list == [settings, ..., instructions]
        elif recording_list[-1].tag == "Instructions":
            settings = etree.SubElement(recording, "Settings")
        # recording list == [settings, ..., settings]
        else:
            settings = recording[-1]

        # Create sub_type parent ["RecordingSettings",
        # "StimulationWaveformSettings". "StimulationMappingSettings"] if it does
        # not exist
        if settings.find(f".//{sub_type_map[sub_type]}") is None:
            parent_settings = etree.SubElement(settings, f"{sub_type_map[sub_type]}")
        else:
            parent_settings = settings.find(f".//{sub_type_map[sub_type]}")

        # create subelement for sub_type if it didn't exist
        if parent_settings.find(f".//{sub_type}") is None:
            etree.SubElement(parent_settings, f"{sub_type}", attrib=settings_dict)
        # create sibling for previous sub_type
        else:
            sub_settings = parent_settings.find(f".//{sub_type}")
            sub_settings.addnext(etree.Element(f"{sub_type}", attrib=settings_dict))
    else:
        # if [..., instructions]
        if recording_list[-1].tag == "Instructions":
            print(recording_list[-1])
            instructions = recording[-1]
        # if [..., settings]
        else:
            instructions = etree.SubElement(recording, "Instructions")

        # create subelement for sub_type if it didn't exist
        if instructions.find(".//instruction") is None:
            etree.SubElement(instructions, f"{sub_type}", attrib=settings_dict)
        # create sibling for previous sub_type
        else:
            instruction = instructions.find(".//instruction")
            instruction.addnext(etree.Element(f"{sub_type}", attrib=settings_dict))

    etree.indent(program, space="    ", level=0)
    xml_bytes = etree.tostring(
        program, pretty_print=True, xml_declaration=True, encoding="UTF-8"
    )
    with open(path, "wb") as xml_file:
        xml_file.write(xml_bytes)
    return program


# Testing code:
if __name__ == "__main__":
    strixml = """<Program>
        <Settings>
            <MetaData>
                <RecordingName>Mouse22</RecordingName>
            </MetaData>
            <TTLSettings>
                <Setting box="1" probe="1" TTL="1" trigger_function="start_recording"
                    target_box="1" target_probe="1" target_SU="-" />
            </TTLSettings>
            <RecordingSettings>
                <Channel box="-" probe="-" channel="1-3" references="100101000" 
                gain="1" input="0" />
                <Channel box="1" probe="3" channel="63" references="100000000" 
                gain="1" input="0" />
            </RecordingSettings>
            <StimulationWaveformSettings>
                <Configuration box="1" probe="1,2,3,4" stimunit="5-8,2,1" 
                polarity="0" pulses="20"
                    prephase="0" amplitude1="5" width1="170" interphase="60" 
                    amplitude2="5" width2="170"
                    discharge="200" duration="600" aftertrain="1000" />
                <Configuration box="2" probe="1" stimunit="1" polarity="0" 
                pulses="20" prephase="0"
                    amplitude1="5" width1="170" interphase="60" amplitude2="5" 
                    width2="170"
                    discharge="200" duration="600" aftertrain="1000" />
            </StimulationWaveformSettings>
            <StimulationMappingSettings>
                <Mapping box="1,2" probe="1" stimunit="1" electrodes="1,2,5,21" />
                <Mapping box="1" probe="1" stimunit="1" electrodes="1,5,22" />
                <Mapping box="1" probe="2" stimunit="1" electrodes="25" />
                <Mapping box="1" probe="3" stimunit="1" electrodes="11,12,13" />
            </StimulationMappingSettings>
        </Settings>
        <StimulationSequence>
            <Instruction type="trigger_recording" data_address="1.0.0.127" />
            <StimulationSequence>
                <Instruction type="stimulus" box="1" probe="1,2,3,4" stimunit="1" />
                <Instruction type="wait" time="20" />
                <Instruction type="stimulus" box="1" probe="1" stimunit="1" />
                <Instruction type="wait" time="5" />
            </StimulationSequence>
        </StimulationSequence>
    </Program>"""

    data = etree.parse("defaults/instructions.xml")
    with open("defaults/settings_classes.json") as f:
        classes = json.load(f)

    connected_boxes_probes = {}
    existing_boxes = [int(key) for key in classes["boxes"].keys()]
    for box in existing_boxes:
        try:
            connected_boxes_probes[box] = [
                int(key) for key in classes["boxes"][str(box)]["probes"].keys()
            ]
        except KeyError:
            connected_boxes_probes[box] = []
    print(
        f"""boxes: {list(connected_boxes_probes.keys())} and \nbox probe 
        dict: {connected_boxes_probes}"""
    )

    local_settings = GeneralSettings()
    for key in connected_boxes_probes.keys():
        local_settings.boxes[key] = BoxSettings()
        for probe in connected_boxes_probes[key]:
            local_settings.boxes[key].probes[probe] = ProbeSettings()

    check_xml_with_settings(data, local_settings, "all")
    local_settings = update_checked_settings(data, local_settings, "all")
    printable_dtd(local_settings)
