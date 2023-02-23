"""Rinnai Touch Wifi command strings"""
# Top level mode
# Operating mode
MODE_COOL_CMD = '{"SYST": {"OSS": {"MD": "C" } } }'
MODE_EVAP_CMD = '{"SYST": {"OSS": {"MD": "E" } } }'
MODE_HEAT_CMD = '{"SYST": {"OSS": {"MD": "H" } } }'

UNIT_ON_CMD = '{{"{unit_id}": {{"OOP": {{"ST": "N" }} }} }}'
UNIT_OFF_CMD = '{{"{unit_id}": {{"OOP": {{"ST": "F" }} }} }}'
UNIT_CIRC_FAN_ON = '{{"{unit_id}": {{"OOP": {{"ST": "Z" }} }} }}'
UNIT_CIRC_FAN_SPEED = '{{"{unit_id}": {{"OOP": {{"FL": "{speed}" }} }} }}' # 1 - 16

UNIT_SET_TEMP = '{{"{unit_id}": {{"GSO": {{"SP": "{temp}" }} }} }}'
UNIT_SET_MANUAL = '{{"{unit_id}": {{"GSO": {{"OP": "M" }} }} }}'
UNIT_SET_AUTO = '{{"{unit_id}": {{"GSO": {{"OP": "A" }} }} }}'
UNIT_ADVANCE = '{{"{unit_id}": {{"GSO": {{"AO": "A" }} }} }}'
UNIT_ADVANCE_CANCEL = '{{"{unit_id}": {{"GSO": {{"AO": "N" }} }} }}'

UNIT_ZONE_ON = '{{"{unit_id}": {{"Z{zone}O": {{"UE": "Y" }} }} }}'
UNIT_ZONE_OFF = '{{"{unit_id}": {{"Z{zone}O": {{"UE": "N" }} }} }}'
UNIT_ZONE_SET_TEMP = '{{"{unit_id}": {{"Z{zone}O": {{"SP": "{temp}" }} }} }}'
UNIT_ZONE_SET_MANUAL = '{{"{unit_id}": {{"Z{zone}O": {{"OP": "M" }} }} }}'
UNIT_ZONE_SET_AUTO = '{{"{unit_id}": {{"Z{zone}O": {{"OP": "A" }} }} }}'
UNIT_ZONE_ADVANCE = '{{"{unit_id}": {{"Z{zone}O": {{"AO": "A" }} }} }}'
UNIT_ZONE_ADVANCE_CANCEL = '{{"{unit_id}": {{"Z{zone}O": {{"AO": "A" }} }} }}'

UNIT_COMMANDS = [
    UNIT_ON_CMD,
    UNIT_OFF_CMD,
    UNIT_SET_TEMP,
    UNIT_CIRC_FAN_ON,
    UNIT_ZONE_ON,
    UNIT_ZONE_OFF,
    UNIT_SET_MANUAL,
    UNIT_SET_AUTO,
    UNIT_ADVANCE,
    UNIT_ADVANCE_CANCEL,
    UNIT_ZONE_SET_TEMP,
    UNIT_ZONE_SET_MANUAL,
    UNIT_ZONE_SET_AUTO,
    UNIT_ZONE_ADVANCE,
    UNIT_ZONE_ADVANCE_CANCEL,
    UNIT_CIRC_FAN_SPEED
]

# Evap Cooling commands
EVAP_ON_CMD =  '{"ECOM": {"GSO": {"SW": "N" } } }'
EVAP_OFF_CMD =  '{"ECOM": {"GSO": {"SW": "F" } } }'

EVAP_PUMP_ON = '{"ECOM": {"GSO": {"PS": "N" } } }'
EVAP_PUMP_OFF = '{"ECOM": {"GSO": {"PS": "F" } } }'

EVAP_FAN_ON = '{"ECOM": {"GSO": {"FS": "N" } } }'
EVAP_FAN_OFF = '{"ECOM": {"GSO": {"FS": "F" } } }'
EVAP_FAN_SPEED = '{{"ECOM": {{"GSO": {{"FL": "{speed}" }} }} }}' # 1 - 16

EVAP_SET_COMFORT = '{{"ECOM": {{"GSO": {{"SP": "{comfort}" }} }} }}'

EVAP_ZONE_ON = '{{"ECOM": {{"GSO": {{"Z{zone}UE": "Y" }} }} }}'
EVAP_ZONE_OFF = '{{"ECOM": {{"GSO": {{"Z{zone}UE": "N" }} }} }}'
EVAP_ZONE_SET_MANUAL = '{{"ECOM": {{"GSS": {{"Z{zone}AE": "N" }} }} }}'
EVAP_ZONE_SET_AUTO = '{{"ECOM": {{"GSS": {{"Z{zone}AE": "Y" }} }} }}'

EVAP_COMMANDS = [
    UNIT_ON_CMD,
    UNIT_OFF_CMD,
    EVAP_ON_CMD,
    EVAP_OFF_CMD,
    EVAP_PUMP_ON,
    EVAP_PUMP_OFF,
    EVAP_FAN_ON,
    EVAP_FAN_OFF,
    EVAP_FAN_SPEED,
    EVAP_SET_COMFORT,
    EVAP_ZONE_ON,
    EVAP_ZONE_OFF,
    EVAP_ZONE_SET_MANUAL,
    EVAP_ZONE_SET_AUTO
]

MODE_COMMANDS = [
    MODE_COOL_CMD,
    MODE_EVAP_CMD,
    MODE_HEAT_CMD,
    UNIT_ON_CMD,
    EVAP_ON_CMD,
    UNIT_SET_AUTO,
    UNIT_SET_MANUAL
]
