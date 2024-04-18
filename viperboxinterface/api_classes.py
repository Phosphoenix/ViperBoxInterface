from __future__ import annotations

import xml.etree.ElementTree as ET

from pydantic import BaseModel, field_validator
from pydantic.dataclasses import dataclass

from viperboxinterface.VB_classes import parse_numbers

"""
The following classes are used to validate the input from the API.
"""


@dataclass
class Connect(BaseModel):
    probes: str = "1"
    emulation: bool = False
    boxless: bool = False

    @field_validator("probes")
    @classmethod
    def check_probes(cls, probes: str) -> str:
        try:
            parse_numbers(probes, [0, 1, 2, 3])
        except ValueError as e:
            raise ValueError(
                f"probes must be a list of integers, separated by \
                            commas and in the range 1-4. Error: {e}",
            )
        return probes


@dataclass
class apiRecSettings(BaseModel):
    recording_XML: str = ""
    reset: bool = False
    default_values: bool = True

    @field_validator("recording_XML")
    @classmethod
    def check_xml(cls, recording_XML: str) -> str:
        if recording_XML != "":
            try:
                ET.fromstring(recording_XML)
            except ET.ParseError as e:
                raise ValueError(f"recording_XML is not valid XML. Error: {e}") from e
        return recording_XML


@dataclass
class apiStimSettings(BaseModel):
    stimulation_XML: str = ""
    reset: bool = False
    default_values: bool = True

    @field_validator("stimulation_XML")
    @classmethod
    def check_xml(cls, stimulation_XML: str, values) -> str:
        if stimulation_XML != "":
            try:
                ET.fromstring(stimulation_XML)
            except ET.ParseError as e:
                raise ValueError(f"stimulation_XML is not valid XML. Error: {e}")
        # elif values["default_values"] is False:
        #     raise ValueError(
        #         "recording_XML is empty and default_values is False. \
        #                     Please provide a recording_XML or set default_values to \
        #                     True."
        #     )
        return stimulation_XML


@dataclass
class apiStartRec(BaseModel):
    recording_name: str = ""

    @field_validator("recording_name")
    @classmethod
    def check_unicode(cls, recording_name: str) -> str:
        try:
            recording_name.encode("ascii")
        except UnicodeEncodeError as e:
            raise ValueError(f"recording_name must be utf-8. Error: {e}") from e
        return recording_name


@dataclass
class apiStartStim(BaseModel):
    boxes: str = "1"
    probes: str = "1"
    SU_input: str = "1,2,3,4,5,6,7,8"

    @field_validator("boxes")
    @classmethod
    def check_boxes(cls, boxes: str) -> str:
        if boxes not in "1":
            raise ValueError("boxes must be 1, multiple boxes not implemented yet.")
        # try:
        #     parse_numbers(boxes, [1])
        # except ValueError as e:
        #     raise ValueError(
        #         f"boxes must be a list of integers, separated by \
        #                     commas and in the range 1-3. Error: {e}"
        #     )
        return boxes

    @field_validator("probes")
    @classmethod
    def check_probes(cls, probes: str) -> str:
        try:
            parse_numbers(probes, [0, 1, 2, 3])
        except ValueError as e:
            raise ValueError(
                f"probes must be a list of integers, separated by \
                            commas and in the range 1-4. Error: {e}",
            )
        return probes

    @field_validator("SU_input")
    @classmethod
    def check_SU_input(cls, SU_input: str) -> str:
        try:
            parse_numbers(SU_input, [0, 1, 2, 3, 4, 5, 6, 7])
        except ValueError as e:
            raise ValueError(
                f"SU_input must be a list of integers, separated by \
                            commas and in the range 1-8. Error: {e}",
            )
        return SU_input


@dataclass
class apiTTLStart(BaseModel):
    TTL_channel: int = 0
    TTL_XML: str = ""
    SU_bit_mask: list = []

    @field_validator("TTL_channel")
    @classmethod
    def check_TTL_channel(cls, TTL_channel: int) -> int:
        if TTL_channel not in [0, 1]:
            raise ValueError("TTL_channel must be 1 or 2")
        return TTL_channel

    @field_validator("TTL_XML")
    @classmethod
    def check_xml(cls, TTL_XML: str) -> str:
        try:
            ET.fromstring(TTL_XML)
        except ET.ParseError as e:
            raise ValueError(f"TTL_XML is not valid XML. Error: {e}") from e
        return TTL_XML

    @field_validator("SU_bit_mask")
    @classmethod
    def check_SU_bit_mask(cls, SU_bit_mask: list[int]) -> list[int]:
        if len(SU_bit_mask) != 8:
            raise ValueError("SU_bit_mask must contain exactly 8 integers")
        for i in SU_bit_mask:
            if i not in [0, 1]:
                raise ValueError("SU_bit_mask can only contain 0 or 1")
        return SU_bit_mask


@dataclass
class apiTTLStop(BaseModel):
    TTL_channel: int = 0

    @field_validator("TTL_channel")
    @classmethod
    def check_TTL_channel(cls, TTL_channel: int) -> int:
        if TTL_channel not in [0, 1]:
            raise ValueError("TTL_channel must be 1 or 2")
        return TTL_channel


@dataclass
class apiVerifyXML(BaseModel):
    dictionary: dict = {}
    XML: str = ""
    check_topic: str = "all"

    @field_validator("dictionary")
    @classmethod
    def check_dictionary(cls, dictionary: dict) -> dict:
        if not isinstance(dictionary, dict):
            raise ValueError("dictionary must be a dictionary")
        if len(dictionary) != 1:
            raise ValueError("dictionary must contain exactly one key-value pair")
        return dictionary

    @field_validator("XML")
    @classmethod
    def check_xml(cls, verify_XML: str) -> str:
        if verify_XML != "":
            try:
                ET.fromstring(verify_XML)
            except ET.ParseError as e:
                raise ValueError(f"Input is not valid XML. Error: {e}") from e
        return verify_XML

    @field_validator("check_topic")
    @classmethod
    def check_topic_value(cls, check_topic: str) -> str:
        if check_topic not in ["all", "recording", "stimulation"]:
            raise ValueError("check_topic must be 'all', 'recording' or 'stimulation'")
        return check_topic
