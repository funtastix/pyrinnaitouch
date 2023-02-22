"""Evap unit handling"""
import logging

from .util import get_attribute, y_n_to_bool
from .zone import Zone

_LOGGER = logging.getLogger(__name__)

def handle_evap_mode(j,brivis_status):
    """Parse evap part of JSON."""
    # pylint: disable=too-many-branches,too-many-statements

    cfg = get_attribute(j[1].get("ECOM"),"CFG",None)
    if not cfg:
        # Probably an error
        _LOGGER.error("No CFG - Not happy, Jan")

    else:
        for zoneid in ["A","B","C","D", "U"]:
            if y_n_to_bool(get_attribute(cfg, "Z"+zoneid+"IS", None)):
                brivis_status.evap_status.zones[zoneid] = Zone(zoneid)

    # no multi, there's always a GSO
    gso = get_attribute(j[1].get("ECOM"),"GSO",None)
    if not gso:
        _LOGGER.error("No GSO here")
    else:
        #_LOGGER.debug("Looking at: {}".format(gso))
        switch = get_attribute(gso,"SW", None)
        if switch == "N":
            opmode = get_attribute(gso, "OP", None)
            #_LOGGER.debug("setting opmode: {}".format(opmode))
            brivis_status.evap_status.set_mode(opmode)

            _LOGGER.debug("EVAP is ON")
            brivis_status.system_on = True
            brivis_status.evap_status.evap_on = True

            if opmode == "M":
                # Evap is on and manual - what is the fan speed
                evap_fan = get_attribute(gso,"FS",None)
                _LOGGER.debug("Fan is: %s", evap_fan)
                brivis_status.evap_status.set_fan(evap_fan)

                fan_speed = get_attribute(gso,"FL",None)
                _LOGGER.debug("Fan Speed is: %s", fan_speed)
                brivis_status.evap_status.set_fan_speed(int(fan_speed))

                water_pump = get_attribute(gso,"PS",None)
                _LOGGER.debug("Water Pump is: %s", water_pump)
                brivis_status.evap_status.set_water_pump(water_pump)

            else:
                # Evap is on and auto - look for comfort level
                comfort = get_attribute(gso, "SP", 0)
                _LOGGER.debug("Comfort Level is: %s", comfort)
                brivis_status.evap_status.set_comfort(comfort)

            for zoneid in ["A","B","C","D","U"]:
                if zoneid in brivis_status.evap_status.zones.keys():
                    brivis_status.evap_status.zones[zoneid].user_enabled = \
                        y_n_to_bool(get_attribute(gso,"Z"+zoneid+"UE",False))


            gss = get_attribute(j[1].get("ECOM"),"GSS",None)
            if not gss:
                _LOGGER.error("No GSS here")
            else:
                for zoneid in ["A","B","C","D","U"]:
                    if zoneid in brivis_status.evap_status.zones.keys():
                        brivis_status.evap_status.zones[zoneid].auto_mode = \
                            y_n_to_bool(get_attribute(gss,"Z"+zoneid+"AE",False))

                brivis_status.evap_status.prewetting = y_n_to_bool(get_attribute(gss,"PW",False))
                brivis_status.evap_status.cooler_busy = y_n_to_bool(get_attribute(gss,"BY",False))


        elif switch == "F":
            # Evap is off
            _LOGGER.debug("EVAP is OFF")
            brivis_status.system_on = False
            brivis_status.evap_status.evap_on = False

class EvapStatus():
    """Evap function status"""
    evap_on = False
    manual_mode = False
    auto_mode = False
    fan_on = False
    fan_speed = 0
    water_pump_on = False
    comfort = 0
    temperature = 999
    prewetting = False
    cooler_busy = False

    #zones
    zones = {}

    def set_fan(self,status_str):
        """Set fan state."""
        # N = On, F = Off
        if status_str == "N":
            self.fan_on = True
        else:
            self.fan_on = False

    def set_fan_speed(self,speed_int):
        """Set fan speed."""
        self.fan_speed = speed_int

    def set_water_pump(self,status_str):
        """Set water pump state."""
        # N = On, F = Off
        if status_str == "N":
            self.water_pump_on = True
        else:
            self.water_pump_on = False

    def set_mode(self,mode):
        """Set auto/manual mode."""
        # A = Auto Mode and M = Manual Mode
        if mode == "A":
            self.auto_mode = True
            self.manual_mode = False
        elif mode == "M":
            self.auto_mode = False
            self.manual_mode = True

    def set_comfort(self, comfort):
        """Set target comfort level."""
        self.comfort = comfort
