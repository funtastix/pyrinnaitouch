"""Utility functions"""
import logging

_LOGGER = logging.getLogger(__name__)

def get_attribute(data, attribute, default_value):
    """get json attriubte from data."""
    return data.get(attribute) or default_value

def y_n_to_bool(str_arg):
    """Convert Rinnai YN to Bool"""
    if str_arg == "Y":
        return True
    return False
