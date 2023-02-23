"""Class to define the properties of a climate zone"""

from .const import ADVANCED, MODE_AUTO, MODE_MANUAL


class Zone():
    """Class to define the properties of a climate zone"""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name: str) -> None:
        self.name = name
        self.temperature = 999
        self.set_temp = 0 # < 8 means off
        self.schedule_period = None
        self.advance_period = None
        self.advanced = False
        self.user_enabled = False # applies only to fan_only
        self.auto_mode = False
        self.preheating: bool = False #mtsp it's per zone
        self.gas_valve_active: bool = False #mtsp it's per zone
        self.compressor_active: bool = False #mtsp it's per zone
        self.calling_for_work: bool = False #mtsp it's per zone
        self.fan_operating: bool = False #mtsp for heating and cooling it's per zone (AE)

    def set_mode(self, mode: str) -> None:
        """Set auto/manual mode."""
        # A = Auto Mode and M = Manual Mode
        if mode == MODE_AUTO:
            self.auto_mode = True
        elif mode == MODE_MANUAL:
            self.auto_mode = False

    def set_advanced(self, status_str: str) -> None:
        """Set advanced state."""
        # A = Advance, N = None, O = Operation (what is that?)
        if status_str == ADVANCED:
            self.advanced = True
        else:
            self.advanced = False
