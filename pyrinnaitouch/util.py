"""Utility functions"""
import logging
from enum import Enum

_LOGGER = logging.getLogger(__name__)

def get_attribute(data, attribute, default_value):
    """get json attriubte from data."""
    return data.get(attribute) or default_value

def y_n_to_bool(str_arg):
    """Convert Rinnai YN to Bool"""
    if str_arg == "Y":
        return True
    return False

class SchedulePeriod(Enum):
    """Define system schedule time periods."""
    WAKE = "W"
    LEAVE = "L"
    RETURN = "R"
    PRE_SLEEP = "P"
    SLEEP = "S"

def symbol_to_schedule_period(symbol):
    """Convert JSON symbol to schedule time periods."""
    if symbol == "W":
        return SchedulePeriod.WAKE
    if symbol == "L":
        return SchedulePeriod.LEAVE
    if symbol == "R":
        return SchedulePeriod.RETURN
    if symbol == "P":
        return SchedulePeriod.PRE_SLEEP
    if symbol == "S":
        return SchedulePeriod.SLEEP
    return None

class Zone():

    def __init__(self, name) -> None:
        self.name = name

    name = ""
    temperature = 999
    set_temp = 0 # < 8 means off
    schedule_period = None
    advance_period = None
    advanced = False
    user_enabled = False # applies only to fan_only
    auto_mode = False

    def set_mode(self,mode):
        """Set auto/manual mode."""
        # A = Auto Mode and M = Manual Mode
        if mode == "A":
            self.auto_mode = True
        elif mode == "M":
            self.auto_mode = False

    def set_advanced(self,status_str):
        """Set advanced state."""
        # A = Advance, N = None, O = Operation (what is that?)
        if status_str == "A":
            self.advanced = True
        else:
            self.advanced = False
            
