"""Rinnai Touch Wifi command strings"""
# Top level mode
# Operating mode
MODE_COOL_CMD = '{"SYST": {"OSS": {"MD": "C" } } }'
MODE_EVAP_CMD = '{"SYST": {"OSS": {"MD": "E" } } }'
MODE_HEAT_CMD = '{"SYST": {"OSS": {"MD": "H" } } }'

# Heating Commands
HEAT_ON_CMD = '{"HGOM": {"OOP": {"ST": "N" } } }'
HEAT_OFF_CMD = '{"HGOM": {"OOP": {"ST": "F" } } }'
HEAT_CIRC_FAN_ON = '{"HGOM": {"OOP": {"ST": "Z" } } }'
HEAT_CIRC_FAN_SPEED = '{{"HGOM": {{"OOP": {{"FL": "{speed}" }} }} }}' # 1 - 16

HEAT_SET_TEMP = '{{"HGOM": {{"GSO": {{"SP": "{temp}" }} }} }}'
HEAT_SET_MANUAL = '{{"HGOM": {{"GSO": {{"OP": "M" }} }} }}'
HEAT_SET_AUTO = '{{"HGOM": {{"GSO": {{"OP": "A" }} }} }}'
HEAT_ADVANCE = '{{"HGOM": {{"GSO": {{"AO": "A" }} }} }}'
HEAT_ADVANCE_CANCEL = '{{"HGOM": {{"GSO": {{"AO": "N" }} }} }}'

HEAT_ZONE_ON = '{{"HGOM": {{"Z{zone}O": {{"UE": "Y" }} }} }}'
HEAT_ZONE_OFF = '{{"HGOM": {{"Z{zone}O": {{"UE": "N" }} }} }}'
HEAT_ZONE_SET_TEMP = '{{"HGOM": {{"Z{zone}O": {{"SP": "{temp}" }} }} }}'
HEAT_ZONE_SET_MANUAL = '{{"HGOM": {{"Z{zone}O": {{"OP": "M" }} }} }}'
HEAT_ZONE_SET_AUTO = '{{"HGOM": {{"Z{zone}O": {{"OP": "A" }} }} }}'
HEAT_ZONE_ADVANCE = '{{"HGOM": {{"Z{zone}O": {{"AO": "A" }} }} }}'
HEAT_ZONE_ADVANCE_CANCEL = '{{"HGOM": {{"Z{zone}O": {{"AO": "A" }} }} }}'

HEAT_COMMANDS = [
    HEAT_ON_CMD,
    HEAT_OFF_CMD,
    HEAT_SET_TEMP,
    HEAT_CIRC_FAN_ON,
    HEAT_ZONE_ON,
    HEAT_ZONE_OFF,
    HEAT_SET_MANUAL,
    HEAT_SET_AUTO,
    HEAT_ADVANCE,
    HEAT_ADVANCE_CANCEL,
    HEAT_ZONE_SET_TEMP,
    HEAT_ZONE_SET_MANUAL,
    HEAT_ZONE_SET_AUTO,
    HEAT_ZONE_ADVANCE,
    HEAT_ZONE_ADVANCE_CANCEL,
    HEAT_CIRC_FAN_SPEED
]

# Cooling Commands
COOL_ON_CMD = '{"CGOM": {"OOP": {"ST": "N" } } }'
COOL_OFF_CMD = '{"CGOM": {"OOP": {"ST": "F" } } }'
COOL_CIRC_FAN_ON = '{"CGOM": {"OOP": {"ST": "Z" } } }'
COOL_CIRC_FAN_SPEED = '{{"CGOM": {{"OOP": {{"FL": "{speed}" }} }} }}' # 1 - 16

COOL_SET_TEMP = '{{"CGOM": {{"GSO": {{"SP": "{temp}" }} }} }}'
COOL_SET_MANUAL = '{{"CGOM": {{"GSO": {{"OP": "M" }} }} }}'
COOL_SET_AUTO = '{{"CGOM": {{"GSO": {{"OP": "A" }} }} }}'
COOL_ADVANCE = '{{"CGOM": {{"GSO": {{"AO": "A" }} }} }}'
COOL_ADVANCE_CANCEL = '{{"CGOM": {{"GSO": {{"AO": "N" }} }} }}'

COOL_ZONE_ON = '{{"CGOM": {{"Z{zone}O": {{"UE": "Y" }} }} }}'
COOL_ZONE_OFF = '{{"CGOM": {{"Z{zone}O": {{"UE": "N" }} }} }}'
COOL_ZONE_SET_TEMP = '{{"CGOM": {{"Z{zone}O": {{"SP": "{temp}" }} }} }}'
COOL_ZONE_SET_MANUAL = '{{"CGOM": {{"Z{zone}O": {{"OP": "M" }} }} }}'
COOL_ZONE_SET_AUTO = '{{"CGOM": {{"Z{zone}O": {{"OP": "A" }} }} }}'
COOL_ZONE_ADVANCE = '{{"CGOM": {{"Z{zone}O": {{"AO": "A" }} }} }}'
COOL_ZONE_ADVANCE_CANCEL = '{{"CGOM": {{"Z{zone}O": {{"AO": "N" }} }} }}'

COOL_COMMANDS = [
    COOL_ON_CMD,
    COOL_OFF_CMD,
    COOL_SET_TEMP,
    COOL_CIRC_FAN_ON,
    COOL_ZONE_ON,
    COOL_ZONE_OFF,
    COOL_SET_MANUAL,
    COOL_SET_AUTO,
    COOL_ADVANCE,
    COOL_ADVANCE_CANCEL,
    COOL_ZONE_SET_TEMP,
    COOL_ZONE_SET_MANUAL,
    COOL_ZONE_SET_AUTO,
    COOL_ZONE_ADVANCE,
    COOL_ZONE_ADVANCE_CANCEL,
    COOL_CIRC_FAN_SPEED
]

# Evap Cooling commands
EVAP_ON_CMD =  '{"ECOM": {"GSO": {"SW": "N" } } }'
EVAP_OFF_CMD =  '{"ECOM": {"GSO": {"SW": "F" } } }'

EVAP_PUMP_ON = '{"ECOM": {"GSO": {"PS": "N" } } }'
EVAP_PUMP_OFF = '{"ECOM": {"GSO": {"PS": "F" } } }'

EVAP_FAN_ON = '{"ECOM": {"GSO": {"FS": "N" } } }'
EVAP_FAN_OFF = '{"ECOM": {"GSO": {"FS": "F" } } }'
EVAP_FAN_SPEED = '{{"ECOM": {{"GSO": {{"FL": "{speed}" }} }} }}' # 1 - 16

EVAP_SET_MANUAL = '{{"ECOM": {{"GSO": {{"OP": "M" }} }} }}'
EVAP_SET_AUTO = '{{"ECOM": {{"GSO": {{"OP": "A" }} }} }}'
EVAP_SET_COMFORT = '{{"ECOM": {{"GSO": {{"SP": "{comfort}" }} }} }}'

EVAP_ZONE_ON = '{{"ECOM": {{"GSO": {{"Z{zone}UE": "Y" }} }} }}'
EVAP_ZONE_OFF = '{{"ECOM": {{"GSO": {{"Z{zone}UE": "N" }} }} }}'
EVAP_ZONE_SET_MANUAL = '{{"ECOM": {{"GSS": {{"Z{zone}AE": "N" }} }} }}'
EVAP_ZONE_SET_AUTO = '{{"ECOM": {{"GSS": {{"Z{zone}AE": "Y" }} }} }}'

EVAP_COMMANDS = [
    EVAP_ON_CMD,
    EVAP_OFF_CMD,
    EVAP_PUMP_ON,
    EVAP_PUMP_OFF,
    EVAP_FAN_ON,
    EVAP_FAN_OFF,
    EVAP_FAN_SPEED,
    EVAP_SET_MANUAL,
    EVAP_SET_AUTO,
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
    HEAT_ON_CMD,
    COOL_ON_CMD,
    EVAP_ON_CMD,
    HEAT_SET_AUTO,
    HEAT_SET_MANUAL,
    COOL_SET_AUTO,
    COOL_SET_MANUAL,
    EVAP_SET_AUTO,
    EVAP_SET_MANUAL
]
