import json
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List

import numpy as np
from lxml import etree

# box contains 4 probes
# each probe contains 64 channels, 8 SU's and 128 electrodes
# recording goes through the 64 channels
# stimulation goes through the 8 SU's

# Stack overflow nested data classes https://stackoverflow.com/questions/51564841/creating-nested-dataclass-objects-in-python


@dataclass
class StatusTracking:
    recording: bool = False
    recording_settings_uploaded: bool = False
    stimulation_settings_uploaded: bool = False
    test_mode: bool = False
    BIST_number: int | None = None
    box_connected: bool = False
    probe_connected: bool = False
    active_TTLs: List[bool] = field(default_factory=list)
    _SU_busy = "0" * 16


@dataclass
class ChanSettings:
    references: str = "100000000"
    gain: int = 0
    input: int = 0

    @property
    def get_refs(self):
        return int(int(self.references, 2))

    @classmethod
    def from_dict(cls, env):
        tmp_dct = {}
        for k, v in cls.__annotations__.items():
            if k == "references":
                tmp_dct[k] = parse_references(env[k])
            elif not isinstance(env[k], v):
                tmp_dct[k] = int(env[k])
            else:
                tmp_dct[k] = str(env[k])
        return cls(**tmp_dct)

    @property
    def hash(self):
        return hash(f"{self.references}{self.gain}{self.input}")


@dataclass
class SUSettings:
    # stim_unit: int = 0
    polarity: bool = False
    pulses: int = 20
    prephase: int = 0
    amplitude1: int = 1
    width1: int = 170
    interphase: int = 60
    amplitude2: int = 1
    width2: int = 170
    discharge: int = 200
    duration: int = 600
    aftertrain: int = 0

    @classmethod
    def from_dict(cls, env):
        tmp_dct = {}
        for k, v in cls.__annotations__.items():
            if not isinstance(env[k], v):
                tmp_dct[k] = int(env[k])
            # if not isinstance(env[k], v):
            else:
                tmp_dct[k] = str(env[k])
            # else:
            #     tmp_dct[k] = bool(env[k])
        return cls(**tmp_dct)

    def SUConfig(self):
        return (
            # self.stim_unit,
            bool(self.polarity),
            self.pulses,
            self.amplitude1,
            self.amplitude2,
            self.duration,
            self.prephase,
            self.width1,
            self.interphase,
            self.width2,
            self.discharge,
            self.aftertrain,
        )


@dataclass
class ProbeSettings:
    channel: Dict[int, ChanSettings] = field(default_factory=dict)
    stim_unit_sett: Dict[int, SUSettings] = field(default_factory=dict)
    stim_unit_elec: Dict[int, List[int]] = field(default_factory=dict)
    _sus: int = 8
    _elecs: int = 128

    def SUs_connected(self, stim_unit: int):
        # return binary string of SU's for a particular SU that have uploaded settings
        pass

    @property
    def os_data(self):
        os_data_array = np.zeros((self._sus, self._elecs))
        if self.stim_unit_elec:
            for su, elec_list in self.stim_unit_elec.items():
                for elec in elec_list:
                    os_data_array[su, elec] = 1
            return os_data_array
        # get sum over second axis of os_data_array

    # def get_gains(self):
    #     np.zeros(64)
    #     return self.gain_vec


class IDInformation:
    serial_number: int = 0
    version_major: int = 0
    version_minor: int = 0
    headstage_id: str = ""


@dataclass
class TTLSettings:
    trigger_function: str = ""
    target_box: str = ""
    target_probe: str = ""
    target_SU: str = ""


@dataclass
class TTL_probes:
    TTL_probes: Dict[int, TTLSettings] = field(default_factory=dict)


@dataclass
class TTL_boxes:
    TTL_boxes: Dict[int, TTLSettings] = field(default_factory=dict)


@dataclass
class BoxSettings:
    hardware_id_base_station: IDInformation | None = None
    hardware_id_head_stage: IDInformation | None = None
    probes: Dict[int, ProbeSettings] = field(default_factory=dict)


@dataclass
class GeneralSettings:
    viperbox_software_id: str = ""
    session_starting_datetime: str = ""
    api_version_minor: str = ""
    api_version_major: str = ""
    boxes: Dict[int, BoxSettings] = field(default_factory=dict)

    @property
    def connected(self):
        connected_boxprobes = {}
        if self.boxes:
            box_list = list(self.boxes.keys())
            for box in box_list:
                if self.boxes[box].probes:
                    connected_boxprobes[box] = list(self.boxes[box].probes.keys())
            return connected_boxprobes
        else:
            return connected_boxprobes

    def reset_recording_settings(self):
        connected_hp = self.connected
        for box, probes in connected_hp.items():
            for probe in probes:
                self.boxes[box].probes[probe].channel = {}

    def reset_stimulation_settings(self):
        connected_hp = self.connected
        for box, probes in connected_hp.items():
            for probe in probes:
                self.boxes[box].probes[probe].stim_unit_sett = {}
                self.boxes[box].probes[probe].stim_unit_elec = {}

    def reset_probe_settings(self):
        connected_hp = self.connected
        for box, probes in connected_hp.items():
            for probe in probes:
                self.boxes[box].probes[probe].channel = {}
                self.boxes[box].probes[probe].stim_unit_sett = {}
                self.boxes[box].probes[probe].stim_unit_elec = {}


def printable_dtd(obj: Any) -> None:
    """
    Recursively convert dataclass instances to dictionaries.
    """

    print(json.dumps(dataclass_to_dict(obj), indent=4, sort_keys=True))


def readable_dtd(obj: Any) -> json:
    """
    Recursively convert dataclass instances to dictionaries.
    """

    return json.dumps(dataclass_to_dict(obj), indent=4, sort_keys=True)


def printet(obj: Any) -> None:
    """
    Readable print of an ET object.
    """
    # print(etree.tostring(obj, pretty_print=True, indent=4).decode())
    print(etree.tostring(obj, pretty_print=True).decode())


def dataclass_to_dict(obj: Any) -> Any:
    """
    Recursively convert dataclass instances to dictionaries.
    """
    if is_dataclass(obj):
        return {k: dataclass_to_dict(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [dataclass_to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: dataclass_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, tuple):
        return tuple(dataclass_to_dict(item) for item in obj)
    else:
        return obj


def dict_to_dataclass(cls: Any, dict_obj: Any) -> Any:
    """
    Recursively convert dictionaries to dataclass instances.

    Arguments:
    - cls: The given dataclass type to convert to.
    - dict_obj: The dictionary to convert.
    """
    if hasattr(cls, "__annotations__"):
        field_types = cls.__annotations__
        return cls(
            **{
                k: dict_to_dataclass(field_types[k], v)
                for k, v in dict_obj.items()
                if k in field_types
            }
        )
    else:
        return dict_obj


def parse_numbers(numstr: str, all_values: list[int]) -> list[int]:
    """Parse a string of numbers, converts to 0 indexed and compare to an
    available list.

    If the format is wrong or if the numbers are not in the list, raise an error.
    These are inputs like: '1,2,3,4-6,8' or '-' for all possible values.

    Arguments:
    - numstr {str} -- string of numbers to parse
    - all_values {list[int]} -- list of all possible values for the numbers

    Returns:
    - result {numpy.ndarray} -- numpy array of parsed integers in sequential order

    Test cases:
    - wrong ranges: '1-2-3', '1-', '1,,2', '1--2', '-1'
    might be more.
    """

    if ",," in numstr:
        raise ValueError("Invalid input, can't have double commas")
    if "--" in numstr:
        raise ValueError("Invalid input, can't have double dashes")
    result = np.array([], dtype=int)
    if numstr == "-":
        if all_values is None:
            raise ValueError("all_values not known")
        result = np.asarray(all_values)
    elif len(numstr) == 1:
        # - 1 because xml is 1 indexed and code is 0 indexed
        result = np.array([int(numstr) - 1])
    else:
        split_numstr = numstr.split(",")
        for item in split_numstr:
            if item[0] == "-":
                raise ValueError("Invalid input, can't start with a dash")
            if item[-1] == "-":
                raise ValueError("Invalid input, can't end with a dash")
            if "-" in item:
                split_item = item.split("-")
                # check if the range is valid
                if len(split_item) != 2:
                    raise ValueError("Invalid range")
                elif int(split_item[0]) > int(split_item[1]):
                    np_item = np.asarray(
                        range(int(split_item[1]), int(split_item[0]) + 1)
                    )
                else:
                    np_item = np.asarray(
                        range(int(split_item[0]), int(split_item[1]) + 1)
                    )
            else:
                np_item = np.asarray(int(item))
            result = np.append(result, np_item)
        result = np.unique(result)
        # - 1 because xml is 1 indexed and code is 0 indexed
        result = result - 1
    if not set(result).issubset(set(all_values)):
        raise ValueError(
            "Invalid values; following instances are not connected"
            f":{set(result) - set(all_values)}."
        )
    return result.tolist()


def parse_references(refstr: str) -> str:
    """Parse a string of references, replaces b with 0'th reference.

    If the format is wrong or if the numbers are not in the list, raise an error.
    These are inputs like: '1,2,3,4-6,8' or '-' for all possible values.

    Arguments:
    - refstr {str} -- string of numbers to parse
    - all_values {list[int]} -- list of all possible values for the numbers

    Returns:
    - result {numpy.ndarray} -- numpy array of parsed integers in sequential order

    Test cases:
    - wrong ranges: '1-2-3', '1-', '1,,2', '1--2', '-1'
    might be more.
    """

    all_values = list(range(9))
    if ",," in refstr:
        raise ValueError("Invalid input, can't have double commas")
    if "--" in refstr:
        raise ValueError("Invalid input, can't have double dashes")
    refstr = refstr.replace("b", "0")
    result = np.array([], dtype=int)
    if refstr == "-":
        if all_values is None:
            raise ValueError("all_values not known")
        result = np.asarray(all_values)
    elif len(refstr) == 1:
        result = np.array([int(refstr)])
    else:
        split_refstr = refstr.split(",")
        for item in split_refstr:
            if item[0] == "-":
                raise ValueError("Invalid input, can't start with a dash")
            if item[-1] == "-":
                raise ValueError("Invalid input, can't end with a dash")
            if "-" in item:
                split_item = item.split("-")
                # check if the range is valid
                if len(split_item) != 2:
                    raise ValueError("Invalid range")
                elif int(split_item[0]) > int(split_item[1]):
                    np_item = np.asarray(
                        range(int(split_item[1]), int(split_item[0]) + 1)
                    )
                else:
                    np_item = np.asarray(
                        range(int(split_item[0]), int(split_item[1]) + 1)
                    )
            else:
                np_item = np.asarray(int(item))
            result = np.append(result, np_item)
        result = np.unique(result)
    if not set(result).issubset(set(all_values)):
        raise ValueError(
            "Invalid values; following instances are not connected"
            f":{set(result) - set(all_values)}."
        )
    result = ["1" if i in result else "0" for i in all_values]
    return result


def get_boxes(settings):
    """Get the boxes of all settings in the settings dictionary

    Arguments:
    - settings {dict} -- dictionary of settings

    Returns:
    - boxes {list} -- list of boxes
    """
    boxes = [int(i) for i in settings["boxes"].keys()]
    if not boxes:
        raise ValueError("No boxes found in settings")
    return boxes


def get_probes(box: int, settings):
    """Get the probes of a box

    Arguments:
    - box {int} -- box of the setting
    - settings {dict} -- dictionary of settings

    Returns:
    - probes {list} -- list of probes
    """
    probes = [int(i) for i in settings["boxes"][str(box)]["probes"].keys()]
    if not probes:
        raise ValueError(f"No probes found in box {box}")
    return probes


def __check_boxes_exist(data, existing_boxes):
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
