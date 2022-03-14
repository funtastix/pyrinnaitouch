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
