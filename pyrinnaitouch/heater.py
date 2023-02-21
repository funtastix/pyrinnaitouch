"""Heater unit handling"""
import logging
from tempfile import tempdir

from .util import get_attribute, y_n_to_bool, symbol_to_schedule_period

_LOGGER = logging.getLogger(__name__)

def handle_heating_mode(j,brivis_status):
    """Parse heater part of JSON."""
    # pylint: disable=too-many-branches,too-many-statements,too-many-locals

    cfg = get_attribute(j[1].get("HGOM"),"CFG",None)
    if not cfg:
        # Probably an error
        _LOGGER.error("No CFG - Not happy, Jan")

    else:
        if y_n_to_bool(get_attribute(cfg, "ZAIS", None)):
            _LOGGER.debug("Appending Zone A")
            brivis_status.heater_status.zones.append("A")
        if y_n_to_bool(get_attribute(cfg, "ZBIS", None)):
            brivis_status.heater_status.zones.append("B")
        if y_n_to_bool(get_attribute(cfg, "ZCIS", None)):
            brivis_status.heater_status.zones.append("C")
        if y_n_to_bool(get_attribute(cfg, "ZDIS", None)):
            brivis_status.heater_status.zones.append("D")

    oop = get_attribute(j[1].get("HGOM"),"OOP",None)
    if not oop:
        # Probably an error
        _LOGGER.error("No OOP - Not happy, Jan")

    else:
        brivis_status.heater_status.schedule_period = None
        brivis_status.heater_status.advance_period = None
        brivis_status.heater_status.advanced = False

        switch = get_attribute(oop,"ST",None)
        if switch == "N":
            _LOGGER.debug("Heater is ON")
            brivis_status.system_on = True
            brivis_status.heater_status.heater_on = True
            brivis_status.heater_status.set_circulation_fan_on(switch)

            # Heater is on - get attributes
            fan_speed = get_attribute(oop,"FL",None)
            _LOGGER.debug("Fan Speed is: %s", fan_speed)
            brivis_status.heater_status.fan_speed = int(fan_speed) # Should catch errors!

            if brivis_status.is_multi_set_point:
                pass
            else:
                # GSO should be there for single set point
                gso = get_attribute(j[1].get("HGOM"),"GSO",None)
                if not gso:
                    # Probably an error
                    _LOGGER.error("No GSO when heater on. Not happy, Jan")
                else:
                    # Heater is on - get attributes
                    op_mode = get_attribute(gso,"OP",None)
                    _LOGGER.debug("Heat OpMode is: %s", op_mode) # A = Auto, M = Manual
                    brivis_status.heater_status.set_mode(op_mode)

                    # Set temp?
                    set_temp = get_attribute(gso,"SP",None)
                    _LOGGER.debug("Heat set temp is: %s", set_temp)
                    brivis_status.heater_status.set_temp = int(set_temp)

                    brivis_status.heater_status.set_advanced(get_attribute(gso,"AO",None))

                    gss = get_attribute(j[1].get("HGOM"),"GSS",None)
                    if not gss:
                        _LOGGER.error("No GSS here")
                    else:
                        preheat = y_n_to_bool(get_attribute(gss,"PH",False))
                        brivis_status.heater_status.preheating = preheat
                        period = symbol_to_schedule_period(get_attribute(gss,"AT",None))
                        brivis_status.heater_status.schedule_period = period
                        period = symbol_to_schedule_period(get_attribute(gss,"AZ",None))
                        brivis_status.heater_status.advance_period = period

        elif switch == "F":
            # Heater is off
            _LOGGER.debug("Heater is OFF")
            brivis_status.system_on = False
            brivis_status.heater_status.heater_on = False
            brivis_status.heater_status.set_circulation_fan_on(switch)

        elif switch == "Z":
            _LOGGER.debug("Circulation Fan is: %s", switch)
            brivis_status.system_on = True
            brivis_status.heater_status.heater_on = False
            brivis_status.heater_status.set_circulation_fan_on(switch)

            fan_speed = get_attribute(oop,"FL",None)
            _LOGGER.debug("Fan Speed is: %s", fan_speed)
            brivis_status.heater_status.fan_speed = int(fan_speed) # Should catch errors!

        for zoneid in ["a","b","c","d"]:
            zone = get_attribute(j[1].get("HGOM"),"Z"+zoneid.upper()+"O",None)
            if zone:
                setattr(brivis_status.cooling_status, "zone_" + zoneid, y_n_to_bool(get_attribute(zone,"UE",None)))
                setattr(brivis_status.cooling_status, "zone_" + zoneid + "_set_temp", get_attribute(zone,"SP", 999))
            zone = get_attribute(j[1].get("HGOM"),"Z"+zoneid.upper()+"S",None)
            if zone:
                setattr(brivis_status.cooling_status, "zone_" + "_auto", y_n_to_bool(get_attribute(zone,"AE",None)))
                setattr(brivis_status.cooling_status, "zone_" + "_temp", get_attribute(zone,"MT", 999))

        zone = get_attribute(j[1].get("HGOM"),"ZUO",None)
        if zone:
            brivis_status.cooling_status.common_zone = y_n_to_bool(get_attribute(zone,"UE",None))
            brivis_status.cooling_status._set_temp = get_attribute(zone,"SP", 999)
        zone = get_attribute(j[1].get("HGOM"),"ZUS",None)
        if zone:
            brivis_status.cooling_status.common_auto = y_n_to_bool(get_attribute(zone,"AE",None))
            brivis_status.cooling_status.temperature = get_attribute(zone,"MT", 999)


class HeaterZone():

    temperature = 999
    set_temp = 0 # < 8 means off
    schedule_period = None
    advance_period = None
    advanced = False
    user_enabled = False # applies only to fan_only

class HeaterStatus():
    """Heater function status"""
    # pylint: disable=too-many-instance-attributes

    heater_on = False
    fan_speed = 0
    circulation_fan_on = False
    manual_mode = False
    auto_mode = False
    set_temp = 0
    temperature = 999
    preheating = False
    schedule_period = None
    advance_period = None
    advanced = False

    #zones
    zones = []

    def set_mode(self,mode):
        """Set auto/manual mode."""
        # A = Auto Mode and M = Manual Mode
        if mode == "A":
            self.auto_mode = True
            self.manual_mode = False
        elif mode == "M":
            self.auto_mode = False
            self.manual_mode = True

    def set_circulation_fan_on(self,status_str):
        """Set circ fan state."""
        # Z = On, N = Off
        if status_str == "Z":
            self.circulation_fan_on = True
        else:
            self.circulation_fan_on = False

    def set_advanced(self,status_str):
        """Set advanced state."""
        # A = Advance, N = None, O = Operation (what is that?)
        if status_str == "A":
            self.advanced = True
        else:
            self.advanced = False
