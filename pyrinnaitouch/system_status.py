"""Main system status"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .unit_status import RinnaiUnitStatus
from .const import (
    CAPABILITIES,
    CONFIGURATION,
    COOLING_ADDON,
    COOLING_EVAPORATIVE,
    FAULT_DETECTED,
    FAULT_INFO,
    FIRMWARE_VERSION,
    GAS_HEATING,
    MAIN_ZONES,
    MODULE_ENABLED,
    MULTI_SET_POINT,
    SYSTEM,
    TEMPERATURE_UNIT,
    UNIT_FAHRENHEIT,
    WIFI_MODULE_VERSION,
    RinnaiCapabilities,
    RinnaiSystemMode,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    RinnaiUnitId
    )
from .util import UnknownModeException, get_attribute, y_n_to_bool

_LOGGER = logging.getLogger(__name__)

@dataclass
class RinnaiSystemStatus():
    """Overall Class for describing status"""
    # pylint: disable=too-many-instance-attributes

    def __init__(self) -> None:
        self.mode: RinnaiSystemMode = RinnaiSystemMode.NONE
        self.system_on: bool = False
        self.temp_unit: str = TEMP_CELSIUS
        self.capabilities: RinnaiCapabilities = RinnaiCapabilities.NONE
        self.unit_status: RinnaiUnitStatus = RinnaiUnitStatus()

        #system info
        self.firmware_version: Optional[str] = None
        self.wifi_module_version: Optional[str] = None

        #zones
        self.zone_descriptions: Dict[str, Optional[str]] = {}

        self.is_multi_set_point: bool = False

        #faults
        self.has_fault: bool = False

    def handle_status(self, status_json: Any) -> bool:
        """Handle the JSON response from the system."""
        try:
            #_LOGGER.debug(json.dumps(j[0], indent = 4))
            self.set_config(get_attribute(status_json[0].get(SYSTEM), CONFIGURATION,None))
            self.set_capabilities(get_attribute(status_json[0].get(SYSTEM), CAPABILITIES,None))
            self.set_fault(get_attribute(status_json[0].get(SYSTEM), FAULT_INFO, None))

            parts = []
            for part in status_json:
                parts.extend(part.keys())

            if str(RinnaiUnitId.HEATER) in parts:
                capability = RinnaiCapabilities.HEATER
                self.mode = RinnaiSystemMode.HEATING
                _LOGGER.debug("We are in HEAT mode")

            elif str(RinnaiUnitId.COOLER) in parts:
                capability = RinnaiCapabilities.COOLER
                self.mode = RinnaiSystemMode.COOLING
                _LOGGER.debug("We are in COOL mode")

            elif str(RinnaiUnitId.EVAP) in parts:
                capability = RinnaiCapabilities.EVAP
                self.mode = RinnaiSystemMode.EVAP
                _LOGGER.debug("We are in EVAP mode")

            else:
                _LOGGER.debug("Unknown mode")
                raise UnknownModeException("Unknown mode, this is not going well.")

            self.unit_status = RinnaiUnitStatus()
            self.unit_status.handle_status(
                capability,
                self.is_multi_set_point,
                self.set_system_status,
                status_json
                )
            return True

        except Exception as err: # pylint: disable=broad-except
            _LOGGER.error("Couldn't decode JSON (exception), skipping (%s)", repr(err))
            return False

    def set_system_status(self, is_on: bool) -> None:
        """Set on/off status for the entire system"""
        self.system_on = is_on

    def set_config(self, cfg):
        """Parse and set system configuration."""
        if not cfg:
            # Probably an error
            _LOGGER.error("No CFG - Not happy, Jan")
        else:
            if get_attribute(cfg, TEMPERATURE_UNIT, None) == UNIT_FAHRENHEIT:
                self.temp_unit = TEMP_FAHRENHEIT
            else:
                self.temp_unit = TEMP_CELSIUS

            self.is_multi_set_point = y_n_to_bool(get_attribute(cfg, MULTI_SET_POINT, None))
            for zone in MAIN_ZONES:
                self.zone_descriptions[zone] = get_attribute(cfg, "Z" + zone, None).strip()

            self.firmware_version = get_attribute(cfg, FIRMWARE_VERSION, None).strip()
            self.wifi_module_version = get_attribute(cfg, WIFI_MODULE_VERSION, None).strip()

    def set_fault(self, flt) -> None:
        """Parse and set fault state."""
        if not flt:
            # Probably an error
            _LOGGER.error("No FLT - Not happy, Jan")
        else:
            self.has_fault = y_n_to_bool(get_attribute(flt, FAULT_DETECTED, None))

    def set_capabilities(self, avm: Any) -> None:
        """Parse and set system capabilities, e.g. heater, cooler, evap."""
        if not avm:
                # Probably an error
            _LOGGER.error("No AVM - Not happy, Jan")
        else:
            self.capabilities = RinnaiCapabilities.NONE
            if get_attribute(avm, GAS_HEATING, None) == MODULE_ENABLED:
                self.capabilities |= RinnaiCapabilities.HEATER
            if get_attribute(avm, COOLING_ADDON, None) == MODULE_ENABLED:
                self.capabilities |= RinnaiCapabilities.COOLER
            if get_attribute(avm, COOLING_EVAPORATIVE, None) == MODULE_ENABLED:
                self.capabilities |= RinnaiCapabilities.EVAP
