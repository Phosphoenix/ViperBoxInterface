from dataclasses import dataclass, asdict
from typing import Any, List

"""
This module contains classes and functions for defining and verifying parameters
for stimulation and recording.
"""

# TODO:
# - run verify_values whenever any setting is changed (lazy) OR only run
#   relevant checks if specific values are changed
# - adapt and include discharge times if necessary, if so, add logic
#   to make interpulse_interval the same as the sum of both discharge times
# - implement onset_jitter in trigger probably


def verify_step_min_max(name: str, value: int, step: int, min_val: int, max_val: int):
    """
    Verifies that a given value is within a specified range and is a multiple of a step
    value.

    :param str name: Name of the parameter to verify
    :param int value: The value of the parameter to verify
    :param int step: The step size for the parameter
    :param int min_val: The minimum allowed value for the parameter
    :param int max_val: The maximum allowed value for the parameter
    :raises ValueError: If the value is out of the specified range or not a multiple of
    step
    """
    if not min_val <= value <= max_val:
        raise ValueError(f"{name} must be between {min_val} and {max_val}.")
    if (value - min_val) % step != 0:
        raise ValueError(f"{name} must be a multiple of {step}.")


@dataclass
class PulseShapeParameters:
    """
    Class for holding pulse shape parameters.

    :param bool biphasic: Whether the pulse is biphasic or monophasic (default: True)
    :param int first_pulse_phase_width: Width of the first phase of the pulse (default:
    170 us)
    :param int pulse_interphase_interval: Interval between the two phases of the pulse
    (default: 60 us)
    :param int second_pulse_phase_width: Width of the second phase of the pulse
    (default: 170 us)
    :param int discharge_time: Time for discharge (default: 200 us)
    :param int discharge_time_extra: Additional time for discharge (default: 0 us)
    :param int interpulse_interval: Interval between pulses (default: 200 us)
    :param int pulse_amplitude_anode: Amplitude of the anode pulse (default: 1)
    :param int pulse_amplitude_cathode: Amplitude of the cathode pulse (default: 1)
    :param bool pulse_amplitude_equal: Whether the amplitude of anode and cathode pulses
    should be equal (default: False)
    """

    biphasic: bool = True
    first_pulse_phase_width: int = 170
    pulse_interphase_interval: int = 60
    second_pulse_phase_width: int = 170
    discharge_time: int = 200
    discharge_time_extra: int = 0
    interpulse_interval: int = 200  # = discharge time
    pulse_amplitude_anode: int = 1
    pulse_amplitude_cathode: int = 1
    pulse_amplitude_equal: bool = False

    def __post_init__(self) -> None:
        """Initialize values and verify them."""
        self.correct_values()
        self.verify_values()

    def __setattr__(self, __name: str, __value: Any) -> None:
        """Make sure that every time a attribute is changed, some checks will be
        done."""
        super().__setattr__(__name, __value)
        self.verify_values()

    def correct_values(self) -> None:
        """Set and correct values based on other attributes."""
        self.discharge_time = self.interpulse_interval
        self.discharge_time_extra = 0
        if self.pulse_amplitude_equal:
            self.pulse_amplitude_cathode = self.pulse_amplitude_anode
            self.biphasic = True
        if self.biphasic is False:
            self.pulse_amplitude_cathode = 0

    def verify_values(self) -> None:
        """Verify the values against minimum, maximum and step size."""
        # List of parameters to verify
        verify_params = [
            ("first_pulse_phase_width", self.first_pulse_phase_width, 10, 10, 2550),
            ("pulse_interphase_interval", self.pulse_interphase_interval, 10, 10, 2550),
            ("second_pulse_phase_width", self.second_pulse_phase_width, 10, 10, 2550),
            ("interpulse_interval", self.interpulse_interval, 100, 100, 51000),
            ("pulse_amplitude_anode", self.pulse_amplitude_anode, 1, 0, 255),
            ("pulse_amplitude_cathode", self.pulse_amplitude_cathode, 1, 0, 255),
        ]

        # Loop through parameters to verify and call verify_step_min_max
        for param in verify_params:
            verify_step_min_max(*param)

        # Additional validation checks
        self._additional_checks()

    def _additional_checks(self) -> None:
        """Run additional checks to verify the values."""
        # some checks to see wheter values weren't changed manually
        expected_discharge_time = self.interpulse_interval
        if self.discharge_time != expected_discharge_time:
            raise ValueError(
                f"Expected discharge_time to be {expected_discharge_time}, but got "
                + f"{self.discharge_time}"
            )

        if self.discharge_time_extra != 0:
            raise ValueError("Expected discharge_time_extra to be 0")

        if self.pulse_amplitude_equal:
            if self.pulse_amplitude_cathode != self.pulse_amplitude_anode:
                raise ValueError(
                    "Expected pulse_amplitude_cathode to be equal to "
                    + "pulse_amplitude_anode when pulse_amplitude_equal is True"
                )

            if self.biphasic is False:
                raise ValueError(
                    "Expected biphasic to be True when pulse_amplitude_equal is True"
                )

        if self.biphasic is False:
            if self.pulse_amplitude_cathode != 0:
                raise ValueError(
                    "Expected pulse_amplitude_cathode to be 0 when biphasic is False "
                    + "(i.e. monophasic)"
                )


@dataclass
class PulseTrainParameters:
    """
    Data class to store parameters of a pulse train.

    :param number_of_pulses: Number of pulses in the train.
    :param frequency_of_pulses: Frequency of pulses.
    :param number_of_trains: Number of pulse trains.
    :param train_interval: Interval between trains.
    :param onset_jitter: Jitter in onset timing.
    """

    number_of_pulses: int = 50
    frequency_of_pulses: int = 2500
    number_of_trains: int = 1
    train_interval: int = 1000
    onset_jitter: int = 1000

    def __post_init__(self) -> None:
        """Verifies the values after initialization."""
        self.verify_values()

    def verify_values(self) -> None:
        """Verifies the constraints for all parameters."""
        verify_step_min_max("number_of_pulses", self.number_of_pulses, 1, 1, 255)
        verify_step_min_max("number_of_trains", self.number_of_trains, 1, 1, 20)
        verify_step_min_max("train_interval", self.train_interval, 1000, 1000, 3000000)
        verify_step_min_max("onset_jitter", self.onset_jitter, 1000, 0, 2000000)
        # TODO: check if 1/frequency_of_pulses is the same as pulse_duration, this
        #       should probably be done on the level of ConfigurationParameters

    def __setattr__(self, __name: str, __value: Any) -> None:
        super().__setattr__(__name, __value)
        self.verify_values()


@dataclass
class ViperBoxConfiguration:
    """
    Data class to store the configuration parameters for a ViperBox.

    :param probe: Probe index to be used (should be between 0 and 3).
    """

    probe: int

    def __post_init__(self) -> None:
        """Verifies the probe number is within bounds."""
        self.verify_values()

    def __setattr__(self, __name: str, __value: Any) -> None:
        super().__setattr__(__name, __value)
        self.verify_values()

    def verify_values(self) -> None:
        if not 0 <= self.probe <= 3:
            raise ValueError("Probe value should be between 0 and 3.")


@dataclass
class ConfigurationParameters:
    """
    Data class to store all the configuration parameters:
    - pulse shape
    - pulse train
    - stimulation electrodes
    - ViperBox

    :param pulse_shape_parameters: Object of PulseShapeParameters class.
    :param pulse_train_parameters: Object of PulseTrainParameters class.
    :param list_of_stimulation_electrodes: List of electrodes to be stimulated.
    :param viperbox_configuration: Object of ViperBoxConfiguration class.
    """

    pulse_shape_parameters: PulseShapeParameters
    pulse_train_parameters: PulseTrainParameters
    list_of_stimulation_electrodes: List[int]
    viperbox_configuration: ViperBoxConfiguration

    def __post_init__(self) -> None:
        """Verifies the electrodes after initialization."""
        self.verify_electrodes()

    def verify_electrodes(self) -> None:
        """Verifies the constraints for the list of electrodes."""
        electrodes_set = set(self.list_of_stimulation_electrodes)
        if len(electrodes_set) != len(self.list_of_stimulation_electrodes):
            # log "You've supplied duplicate electrodes."
            # raise ValueError("Duplicate electrodes are not allowed.")
            pass

        for elec in electrodes_set:
            if not 1 <= elec <= 128:
                raise ValueError("Electrodes should have values between 1 and 128.")

    def get_SUConfig_pars(
        self, handle=None, probe=0, stimunit=0, polarity=0
    ) -> List[Any]:
        """
        Generate and return stimulation unit parameters from all the configured
        parameters.

        :param handle: Hardware handle (default is None).
        :param probe: Probe index (default is 0).
        :param stimunit: Stimulation unit index (default is 0).
        :param polarity: Polarity of the pulse (default is 0).
        :return: A list containing the SUConfig parameters that can be fed directly into
        NVP.writeSUConfiguration.
        """
        all_parameters = {
            **asdict(self.pulse_shape_parameters),
            **asdict(self.pulse_train_parameters),
        }

        if not handle:
            raise ValueError("No handle was passed")
        return (
            handle,
            probe,
            stimunit,
            polarity,
            all_parameters.get("number_of_pulses", None),
            all_parameters.get("pulse_amplitude_anode", None),
            all_parameters.get("pulse_amplitude_cathode", None),
            all_parameters.get("pulse_duration", None),
            0,  # pulse_delay
            # all_parameters.get("pulse_delay", None),
            all_parameters.get("first_pulse_phase_width", None),
            all_parameters.get("pulse_interphase_interval", None),
            all_parameters.get("second_pulse_phase_width", None),
            all_parameters.get("discharge_time", None),
            all_parameters.get("discharge_time_extra", None),
        )


if __name__ == "__main__":
    # Example usage:
    pulse_shape = PulseShapeParameters()
    pulse_train = PulseTrainParameters()
    electrodes = [1, 2, 3]
    viperbox = ViperBoxConfiguration(0)
    config = ConfigurationParameters(pulse_shape, pulse_train, electrodes, viperbox)
    test = config.get_SUConfig_pars()
    print("SUConfig pars: ", test)