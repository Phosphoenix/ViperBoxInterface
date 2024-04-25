import logging
import logging.handlers

import numpy as np
import pandas as pd

logger = logging.getLogger("defaults")
logger.setLevel(logging.DEBUG)
socketHandler = logging.handlers.SocketHandler(
    "localhost",
    logging.handlers.DEFAULT_TCP_LOGGING_PORT,
)
logger.addHandler(socketHandler)


class Mappings:
    """Read mappings from Excel file and provide them as properties.
    Excel file is 1-indexed, but the properties are 0-indexed, except probe electrode
    and EL_PAD# numbering. Probe electrode is 1-indexed. EL_PAD# is used to provide
    values for the XML which is also 1-indexed.
    """

    def __init__(self, file_path):
        self.file_path = file_path
        # TMPFIX should be removed
        self.file_path = "defaults/electrode_mapping_long_cables.xlsx"
        # TMPFIX should be 60
        self.output_size = 64
        self.get_mappings()

    def get_mappings(self):
        hardcoded_mapping = pd.DataFrame(
            {
                "Probe electrode": np.arange(self.output_size),
                "EL_PAD#": np.arange(self.output_size),
                "Resulting channel": np.arange(self.output_size),
                "Resulting input selection": np.zeros(self.output_size),
                "Resulting electrode": np.arange(self.output_size),
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
                f"Couldn't read mappings from excel file, using defaults. Error: {e}",
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
