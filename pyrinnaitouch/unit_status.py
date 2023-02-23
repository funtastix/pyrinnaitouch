"""Unit status handling"""
import logging
from typing import Any, Callable, Dict, Optional

from .const import (
    ADVANCE_PERIOD,
    ADVANCED,
    ALL_ZONES,
    AUTO_ENABLED,
    CONFIGURATION,
    COOLER_BUSY,
    FAN_OPERATING,
    FAN_SPEED_LEVEL,
    FAN_STATE,
    GENERAL_SYSTEM_OPERATION,
    GENERAL_SYSTEM_STATUS,
    MEASURED_TEMPERATURE,
    MODE_AUTO,
    MODE_MANUAL,
    OPERATING_PROGRAM,
    OPERATING_STATE,
    OVERALL_OPERATION,
    PREHEATING,
    PREWETTING,
    PUMP_OPERATING,
    PUMP_STATE,
    SCHEDULE_OVERRIDE,
    SCHEDULE_PERIOD,
    SET_POINT,
    STATE_FAN_ONLY,
    STATE_OFF,
    STATE_ON,
    SWITCH_STATE,
    USER_ENABLED,
    RinnaiCapabilities,
    RinnaiOperatingMode,
    RinnaiSchedulePeriod,
    RinnaiUnitId
    )

from .util import get_attribute, symbol_to_schedule_period, y_n_to_bool
from .zone import Zone

_LOGGER = logging.getLogger(__name__)

class RinnaiUnitStatus():
    """Handle and represent the status of the unit, e.g. heater, cooler, evap"""
    # pylint: disable=too-many-instance-attributes

    def __init__(self) -> None:
        self.capability: RinnaiCapabilities = RinnaiCapabilities.NONE
        self.unit_id: Optional[str] = None
        self.is_on: bool = False
        self.fan_speed: int = 0
        self.circulation_fan_on: bool = False
        self.operating_mode: RinnaiOperatingMode = RinnaiOperatingMode.NONE
        self.set_temp: int = 0
        self.comfort: int = 0
        self.temperature: int = 999
        self.preheating: bool = False #mtsp it's per zone
        self.gas_valve_active: bool = False #mtsp it's per zone
        self.compressor_active: bool = False #mtsp it's per zone
        self.calling_for_heat: bool = False #mtsp it's per zone
        self.calling_for_cool: bool = False #mtsp it's per zone
        self.schedule_period: RinnaiSchedulePeriod = RinnaiSchedulePeriod.NONE
        self.advance_period: RinnaiSchedulePeriod = RinnaiSchedulePeriod.NONE
        self.advanced: bool = False
        self.fan_on: bool = False
        self.water_pump_on: bool = False
        self.prewetting: bool = False
        self.cooler_busy: bool = False
        self.pump_operating: bool = False
        self.fan_operating: bool = False #mtsp for heating and cooling it's per zone (AE)
        self.zones: Dict[object] = {}

    def set_mode(self,mode: str) -> None:
        """Set auto/manual mode."""
        # A = Auto Mode and M = Manual Mode
        if mode == MODE_AUTO:
            self.operating_mode = RinnaiOperatingMode.AUTO
        else:
            self.operating_mode = RinnaiOperatingMode.MANUAL

    def set_circulation_fan_on(self,status_str: str) -> None:
        """Set circ fan state."""
        # Z = On, N = Off
        if status_str == STATE_FAN_ONLY:
            self.circulation_fan_on = True
        else:
            self.circulation_fan_on = False

    def set_advanced(self,status_str: str) -> None:
        """Set advanced state."""
        # A = Advance, N = None, O = Operation (what is that?)
        if status_str == ADVANCED:
            self.advanced = True
        else:
            self.advanced = False

    def set_fan(self,status_str: str) -> None:
        """Set fan state."""
        # N = On, F = Off
        if status_str == STATE_ON:
            self.fan_on = True
        else:
            self.fan_on = False

    def set_fan_speed(self,speed_int: int) -> None:
        """Set fan speed."""
        self.fan_speed = speed_int

    def set_water_pump(self,status_str: str) -> None:
        """Set water pump state."""
        # N = On, F = Off
        if status_str == STATE_ON:
            self.water_pump_on = True
        else:
            self.water_pump_on = False

    def set_comfort(self, comfort: int) -> None:
        """Set target comfort level."""
        self.comfort = comfort

    def handle_status(
            self,
            capability: RinnaiCapabilities,
            is_multi_set_point: bool,
            set_parent_status: Callable,
            status_json: Any
        ) -> None:
        """Parse operational part of JSON."""
        self.set_capability(capability)
        self.set_config(get_attribute(status_json[1].get(self.unit_id),CONFIGURATION,None))

        if capability == RinnaiCapabilities.EVAP:
            self.parse_evap_gso(set_parent_status, status_json)
        else:
            oop = get_attribute(status_json[1].get(self.unit_id),OVERALL_OPERATION,None)
            if not oop:
                # Probably an error
                _LOGGER.error("No OOP - Not happy, Jan")

            else:
                self.schedule_period = RinnaiSchedulePeriod.NONE
                self.advance_period = RinnaiSchedulePeriod.NONE
                self.advanced = False

                switch = get_attribute(oop,OPERATING_STATE,None)
                if switch == STATE_ON:
                    _LOGGER.debug("Unit is ON")
                    set_parent_status(True)
                    self.is_on = True
                    self.set_circulation_fan_on(switch)

                    # Heater is on - get attributes
                    fan_speed = get_attribute(oop,FAN_SPEED_LEVEL,None)
                    _LOGGER.debug("Fan Speed is: %s", fan_speed)
                    self.fan_speed = int(fan_speed) # Should catch errors!

                    if is_multi_set_point:
                        pass
                    else:
                        # GSO should be there for single set point
                        self.parse_standard_gso(status_json)

                elif switch == STATE_OFF:
                    # Unit is off
                    _LOGGER.debug("Unit is OFF")
                    set_parent_status(False)
                    self.is_on = False
                    self.set_circulation_fan_on(switch)

                elif switch == STATE_FAN_ONLY:
                    _LOGGER.debug("Circulation Fan is: %s", switch)
                    set_parent_status(True)
                    self.is_on = False
                    self.set_circulation_fan_on(switch)

                    fan_speed = get_attribute(oop,FAN_SPEED_LEVEL,None)
                    _LOGGER.debug("Fan Speed is: %s", fan_speed)
                    self.fan_speed = int(fan_speed) # Should catch errors!

                # Single Point
                # ZXO => user enabled
                # ZXS => *MT (temp) and *AE (Auto enabled (calling for heat))
                # Multi Point
                # ZXO => user enabled for Fan_Only, OP (auto/manual),
                #        SP (set_temp), AO (schedule override)
                # ZXS => *AE (calling for heat), FS (fan active), PH (preheat), *MT (temp),
                #         AT (schedule_period), AZ (advance_period)
                for zoneid in ALL_ZONES:
                    zone = get_attribute(status_json[1].get(self.unit_id),"Z"+zoneid+"O",None)
                    self.parse_zone_operation(is_multi_set_point, zoneid, zone)

                    zone = get_attribute(status_json[1].get(self.unit_id),"Z"+zoneid+"S",None)
                    self.parse_zone_state(is_multi_set_point, zoneid, zone)

    def parse_zone_state(self, is_multi_set_point: bool, zoneid: str, zone: Any) -> None:
        """Parse Zone Status"""
        if zone and zoneid in self.zones.keys(): # pylint: disable=consider-iterating-dictionary
                        # these ones are common
            self.zones[zoneid].calling_for_work = y_n_to_bool(get_attribute(zone,AUTO_ENABLED,None))
            self.zones[zoneid].temperature = get_attribute(zone,MEASURED_TEMPERATURE, 999)
                        # these ones are multi only
            if is_multi_set_point:
                self.zones[zoneid].advance_period = \
                                symbol_to_schedule_period(get_attribute(zone,ADVANCE_PERIOD,None))
                self.zones[zoneid].schedule_period = \
                                symbol_to_schedule_period(get_attribute(zone,SCHEDULE_PERIOD,None))

    def parse_zone_operation(self, is_multi_set_point: bool, zoneid: str, zone: Any) -> None:
        """Parse Zone Settings"""
        if zone and zoneid in self.zones.keys(): # pylint: disable=consider-iterating-dictionary
                        # this one is single set point and multi set point with fan only
            if is_multi_set_point or self.circulation_fan_on:
                self.zones[zoneid].user_enabled = y_n_to_bool(get_attribute(zone,USER_ENABLED,None))
                        # these ones are multi only
            if is_multi_set_point:
                self.zones[zoneid].set_temp = get_attribute(zone,SET_POINT, 999)
                self.zones[zoneid].set_advanced(get_attribute(zone,SCHEDULE_OVERRIDE, None))
                self.zones[zoneid].set_mode(get_attribute(zone,OPERATING_PROGRAM,None))

    def parse_standard_gso(self, status_json: Any) -> None:
        """Parse the GSO part of the JSON for heaters and coolers"""
        gso = get_attribute(status_json[1].get(self.unit_id),GENERAL_SYSTEM_OPERATION,None)
        if not gso:
            # Probably an error
            _LOGGER.error("No GSO when heater on. Not happy, Jan")
        else:
            # Unit is on - get attributes
            op_mode = get_attribute(gso,OPERATING_PROGRAM,None)
            _LOGGER.debug("Unit OpMode is: %s", op_mode) # A = Auto, M = Manual
            self.set_mode(op_mode)

            set_temp = get_attribute(gso,SET_POINT,None)
            _LOGGER.debug("Unit set temp is: %s", set_temp)
            self.set_temp = int(set_temp)

            self.set_advanced(get_attribute(gso,SCHEDULE_OVERRIDE,None))

            gss = get_attribute(status_json[1].get(self.unit_id),GENERAL_SYSTEM_STATUS,None)
            if not gss:
                _LOGGER.error("No GSS here")
            else:
                if self.capability == RinnaiCapabilities.HEATER:
                    preheat = y_n_to_bool(get_attribute(gss,PREHEATING,False))
                    self.preheating = preheat
                period = symbol_to_schedule_period(get_attribute(gss,SCHEDULE_PERIOD,None))
                self.schedule_period = period
                period = symbol_to_schedule_period(get_attribute(gss,ADVANCE_PERIOD,None))
                self.advance_period = period

    def parse_evap_gso(
            self,
            set_parent_status: Callable,
            status_json: Any
            ) -> None:
        """Parse the GSO part of the JSON for evaps"""
        # no multi, there's always a GSO
        gso = get_attribute(status_json[1].get(self.unit_id),GENERAL_SYSTEM_OPERATION,None)
        if not gso:
            _LOGGER.error("No GSO here")
        else:
            switch = get_attribute(gso,SWITCH_STATE, None)
            if switch == STATE_ON:
                opmode = get_attribute(gso, OPERATING_PROGRAM, None)
                self.set_mode(opmode)

                _LOGGER.debug("Unit is ON")
                set_parent_status(True)
                self.is_on = True

                if opmode == MODE_MANUAL:
                    # Evap is on and manual - what is the fan speed
                    evap_fan = get_attribute(gso,FAN_STATE,None)
                    _LOGGER.debug("Fan is: %s", evap_fan)
                    self.set_fan(evap_fan)

                    fan_speed = get_attribute(gso,FAN_SPEED_LEVEL,None)
                    _LOGGER.debug("Fan Speed is: %s", fan_speed)
                    self.set_fan_speed(int(fan_speed))

                    water_pump = get_attribute(gso,PUMP_STATE,None)
                    _LOGGER.debug("Water Pump is: %s", water_pump)
                    self.set_water_pump(water_pump)

                else:
                    # Evap is on and auto - look for comfort level
                    comfort = get_attribute(gso, SET_POINT, 0)
                    _LOGGER.debug("Comfort Level is: %s", comfort)
                    self.set_comfort(comfort)

                for zoneid in ALL_ZONES:
                    if zoneid in self.zones.keys(): # pylint: disable=consider-iterating-dictionary
                        self.zones[zoneid].user_enabled = \
                            y_n_to_bool(get_attribute(gso,"Z"+zoneid+USER_ENABLED,False))


                gss = get_attribute(status_json[1].get(self.unit_id),GENERAL_SYSTEM_STATUS,None)
                if not gss:
                    _LOGGER.error("No GSS here")
                else:
                    for zoneid in ALL_ZONES:
                        if zoneid in self.zones.keys(): # pylint: disable=consider-iterating-dictionary
                            self.zones[zoneid].auto_mode = \
                                y_n_to_bool(get_attribute(gss,"Z"+zoneid+AUTO_ENABLED,False))

                    self.prewetting = y_n_to_bool(get_attribute(gss,PREWETTING,False))
                    self.cooler_busy = y_n_to_bool(get_attribute(gss,COOLER_BUSY,False))
                    self.pump_operating = y_n_to_bool(get_attribute(gss,PUMP_OPERATING,False))
                    self.fan_operating = y_n_to_bool(get_attribute(gss,FAN_OPERATING,False))


            elif switch == STATE_OFF:
                # Evap is off
                _LOGGER.debug("Unit is OFF")
                set_parent_status(False)
                self.is_on = False

    def set_config(self, cfg: Any) -> None:
        """Set the zone configuration"""
        if not cfg:
            # Probably an error
            _LOGGER.error("No CFG - Not happy, Jan")

        else:
            for zoneid in ALL_ZONES:
                if y_n_to_bool(get_attribute(cfg, "Z"+zoneid+"IS", None)):
                    self.zones[zoneid] = Zone(zoneid)

    def set_capability(self, capability: RinnaiCapabilities) -> None:
        """Set the unit type"""
        self.capability = capability
        if self.capability == RinnaiCapabilities.COOLER:
            self.unit_id = str(RinnaiUnitId.COOLER)
        elif self.capability == RinnaiCapabilities.HEATER:
            self.unit_id = str(RinnaiUnitId.HEATER)
        elif self.capability == RinnaiCapabilities.EVAP:
            self.unit_id = str(RinnaiUnitId.EVAP)
        else:
            self.unit_id = None
