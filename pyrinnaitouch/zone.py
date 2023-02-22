"""Class to define the properties of a climate zone"""

from .const import ADVANCED, MODE_AUTO, MODE_MANUAL


class Zone():
    """Class to define the properties of a climate zone"""

    def __init__(self, name: str) -> None:
        self.name = name

    name = ""
    temperature = 999
    set_temp = 0 # < 8 means off
    schedule_period = None
    advance_period = None
    advanced = False
    user_enabled = False # applies only to fan_only
    auto_mode = False

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
