"""Constants and enumerations"""
from enum import Enum, Flag

class RinnaiSystemMode(Enum):
    """Define system modes."""
    HEATING = 1
    EVAP = 2
    COOLING = 3
    RC = 4
    NONE = 5

class RinnaiOperatingMode(Enum):
    """Define unit operating modes."""
    NONE = 0
    MANUAL = 1
    AUTO = 2

class RinnaiCapabilities(Flag):
    """Define system capabilities."""
    NONE = 0
    HEATER = 1
    COOLER = 2
    EVAP = 4

class RinnaiSchedulePeriod(Enum):
    """Define system schedule time periods."""
    def __str__(self):
        return str(self.value)

    NONE = None
    WAKE = "W"
    LEAVE = "L"
    RETURN = "R"
    PRE_SLEEP = "P"
    SLEEP = "S"

class RinnaiUnitId(Enum):
    """Define unit ids."""
    def __str__(self):
        return str(self.value)

    HEATER = "HGOM"
    COOLER = "CGOM"
    EVAP = "ECOM"

ZONE_A = "A"
ZONE_B = "B"
ZONE_C = "C"
ZONE_D = "D"
COMMON_ZONE = "U"

MAIN_ZONES = [ ZONE_A, ZONE_B, ZONE_C, ZONE_D ]
ALL_ZONES = [ ZONE_A, ZONE_B, ZONE_C, ZONE_D, COMMON_ZONE ]

TEMP_CELSIUS = "°C"
TEMP_FAHRENHEIT = "°F"

SYSTEM = "SYST"

GENERAL_SYSTEM_OPERATION = "GSO"
GENERAL_SYSTEM_STATUS = "GSS"
OVERALL_OPERATION = "OOP"
CONFIGURATION = "CFG"
CAPABILITIES = "AVM"
FAULT_INFO = "FLT"
FAULT_DETECTED = "AV"

GAS_HEATING = "HG"
COOLING_ADDON = "CG"
COOLING_EVAPORATIVE = "EC"
MODULE_ENABLED = "Y"

MULTI_SET_POINT = "MTSP"

FIRMWARE_VERSION = "VR"
WIFI_MODULE_VERSION = "CV"

SWITCH_STATE = "SW"
OPERATING_STATE = "ST"
FAN_STATE = "FS"
PUMP_STATE = "PS"
STATE_ON = "N"
STATE_OFF = "F"
STATE_FAN_ONLY = "Z"

PREWETTING = "PW"
COOLER_BUSY = "BY"
PUMP_OPERATING = "PO"
FAN_OPERATING = "FO"
PREHEATING = "PH"
MEASURED_TEMPERATURE = "MT"

FAN_SPEED_LEVEL = "FL"
SET_POINT = "SP" # either comfort level or set temp
TEMPERATURE_UNIT = "TU"
UNIT_FAHRENHEIT = "F"

SCHEDULE_PERIOD = "AT"
ADVANCE_PERIOD = "AZ"
SCHEDULE_OVERRIDE = "AO"
ADVANCED = "A"

USER_ENABLED = "UE"
AUTO_ENABLED = "AE"

OPERATING_PROGRAM = "OP"
MODE_MANUAL = "M"
MODE_AUTO = "A"
