import logging
import logging.handlers
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger("defaults")
logger.setLevel(logging.DEBUG)
socketHandler = logging.handlers.SocketHandler(
    "localhost", logging.handlers.DEFAULT_TCP_LOGGING_PORT
)
logger.addHandler(socketHandler)


class Mappings:
    """
    Read mappings from Excel file and provide them as properties.
    Excel file is 1-indexed, but the properties are 0-indexed, except probe electrode
    and EL_PAD# numbering. Probe electrode is 1-indexed. EL_PAD# is used to provide
    values for the XML which is also 1-indexed.
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.get_mappings()

    def get_mappings(self):
        hardcoded_mapping = pd.DataFrame(
            {
                "Probe electrode": np.arange(60),
                "EL_PAD#": np.arange(60),
                "Resulting channel": np.arange(60),
                "Resulting input selection": np.zeros(60),
                "Resulting electrode": np.arange(60),
            },
            dtype=int,
        )
        try:
            self.mapping = pd.read_excel(self.file_path, sheet_name=1)
            self.stim_mapping = self.mapping[
                [
                    "Probe electrode",
                    "EL_PAD#",
                ]
            ].copy()
            self.rec_mapping = self.mapping[
                [
                    "Resulting channel",
                    "Resulting input selection",
                    "Resulting electrode",
                ]
            ].copy()
            self.rec_mapping.dropna(inplace=True)
            self.rec_mapping = self.rec_mapping.map(int)
            self.rec_mapping["Resulting channel"] = (
                self.rec_mapping["Resulting channel"] - 1
            )
            self.rec_mapping["Resulting electrode"] = (
                self.rec_mapping["Resulting electrode"] - 1
            )

            logger.info("Mappings read from excel file")
        except Exception as e:
            self.rec_mapping = hardcoded_mapping.copy()
            logger.warning(
                f"Couldn't read mappings from excel file, using defaults. Error: {e}"
            )

    @property
    def channel_input(self):
        return self.rec_mapping.set_index("Resulting channel")[
            "Resulting input selection"
        ].to_dict()

    @property
    def electrode_mapping(self):
        return self.rec_mapping.set_index("Resulting channel")[
            "Resulting electrode"
        ].to_dict()

    @property
    def probe_to_os_map(self):
        # logger.info(
        #     f"probe to os map: "
        #     f"{self.stim_mapping.set_index('Probe electrode')['EL_PAD#'].to_dict()}"
        # )
        return self.stim_mapping.set_index("Probe electrode")["EL_PAD#"].to_dict()


@dataclass
class Snappings:
    # at initialization, get values from the excel file

    def __init__(self):
        try:
            self.mapping = pd.read_excel(
                "defaults/electrode_mapping_short_cables.xlsx", sheet_name=1
            )
            self.mapping = self.mapping[
                [
                    "Resulting channel",
                    "Resulting input selection",
                    "Resulting electrode",
                ]
            ].copy()
            self.mapping.dropna(inplace=True)
            self.mapping["Resulting channel"] = self.mapping["Resulting channel"] - 1
            self.mapping["Resulting electrode"] = (
                self.mapping["Resulting electrode"] - 1
            )

            self.channel_input = self.mapping.set_index("Resulting channel")[
                "Resulting input selection"
            ].to_dict()

            self.electrode_mapping = self.mapping.set_index("Resulting channel")[
                "Resulting electrode"
            ].to_dict()
            self.defaults = False
            logger.info("Mappings read from excel file")
            print("Mappings read from excel file")
        except FileNotFoundError:
            logger.warning("Couldn't read mappings from excel file, using defaults")
            print("Couldn't read mappings from excel file, using defaults")
            self.channel_input = {k: 0 for k in range(64)}
            self.electrode_mapping = {k: v for k, v in range(64)}
            # self.electrode_mapping = {
            #     54: 1,
            #     50: 2,
            #     47: 3,
            #     45: 4,
            #     46: 5,
            #     21: 6,
            #     53: 7,
            #     52: 8,
            #     40: 9,
            #     62: 10,
            #     56: 11,
            #     39: 12,
            #     38: 13,
            #     55: 14,
            #     48: 15,
            #     51: 16,
            #     49: 17,
            #     19: 18,
            #     64: 19,
            #     60: 20,
            #     24: 21,
            #     44: 22,
            #     63: 24,
            #     61: 25,
            #     18: 26,
            #     37: 27,
            #     7: 28,
            #     9: 29,
            #     36: 30,
            #     43: 31,
            #     42: 33,
            #     33: 34,
            #     5: 37,
            #     35: 38,
            #     28: 40,
            #     15: 41,
            #     29: 42,
            #     23: 44,
            #     41: 46,
            #     58: 47,
            #     57: 48,
            #     4: 52,
            #     34: 54,
            #     59: 56,
            # }
            self.defaults = True


# OS2chip = {
#     1: 55,
#     2: 36,
#     3: 59,
#     4: 51,
#     5: 43,
#     6: 35,
#     7: 58,
#     8: 50,
#     9: 42,
#     10: 52,
#     11: 40,
#     12: 37,
#     13: 45,
#     14: 53,
#     15: 57,
#     16: 38,
#     17: 3,
#     18: 29,
#     19: 18,
#     20: 26,
#     21: 4,
#     22: 12,
#     23: 19,
#     24: 15,
#     25: 17,
#     # 26
#     27: 2,
#     28: 10,
#     29: 16,
#     30: 24,
#     31: 11,
#     32: 9,
#     33: 7,
#     34: 20,
#     35: 14,
#     36: 5,
#     37: 28,
#     38: 1,
#     # 39
#     40: 25,
#     41: 41,
#     42: 13,
#     43: 30,
#     44: 22,
#     45: 27,
#     46: 8,
#     # 47
#     48: 23,
#     49: 21,
#     50: 44,
#     51: 6,
#     52: 56,
#     53: 48,
#     54: 60,
#     55: 33,
#     # 56
#     57: 32,
#     58: 39,
#     59: 47,
#     60: 54,
#     61: 31,
#     62: 34,
#     63: 46,
#     64: 49,
# }
