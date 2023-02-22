""" Interface to the Rinnai Touch Controller
    The primary purpose of this is to be integrated into Home Assistant.
"""

from .system import RinnaiSystemStatus, RinnaiSystem
from .unit_status import RinnaiUnitStatus
from .const import (
    RinnaiSchedulePeriod,
    RinnaiCapabilities,
    RinnaiOperatingMode,
    RinnaiSystemMode,
    TEMP_FAHRENHEIT,
    TEMP_CELSIUS
)

__ALL__ = [
    RinnaiSystemStatus,
    RinnaiUnitStatus,
    RinnaiSystem,
    RinnaiSchedulePeriod,
    RinnaiCapabilities,
    RinnaiOperatingMode,
    RinnaiSystemMode,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT
    ]
