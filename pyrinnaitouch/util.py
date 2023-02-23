"""Utility functions"""
import threading
from typing import Any, Callable
from .const import RinnaiSchedulePeriod

def get_attribute(data: Any, attribute: str, default_value: Any) -> Any:
    """get json attriubte from data."""
    return data.get(attribute) or default_value

def y_n_to_bool(str_arg: str) -> bool:
    """Convert Rinnai YN to Bool"""
    if str_arg == "Y":
        return True
    return False

def symbol_to_schedule_period(symbol: str) -> RinnaiSchedulePeriod:
    """Convert JSON symbol to schedule time periods."""
    if symbol == "W":
        return RinnaiSchedulePeriod.WAKE
    if symbol == "L":
        return RinnaiSchedulePeriod.LEAVE
    if symbol == "R":
        return RinnaiSchedulePeriod.RETURN
    if symbol == "P":
        return RinnaiSchedulePeriod.PRE_SLEEP
    if symbol == "S":
        return RinnaiSchedulePeriod.SLEEP
    return RinnaiSchedulePeriod.NONE

def daemonthreaded(function_arg: Callable) -> Callable:
    """Decoration to start object function as thread"""
    def wrapper(*args, **kwargs) -> threading.Thread:
        thread = threading.Thread(target=function_arg, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

class UnknownModeException(Exception):
    """Exception to catch system being in an unknown mode"""

    # Constructor or Initializer
    def __init__(self, value):
        self.value = value

    # __str__ is to print() the value
    def __str__(self):
        return repr(self.value)
