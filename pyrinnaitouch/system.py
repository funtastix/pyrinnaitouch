﻿"""Main system control"""

import logging
import queue
from datetime import datetime
from typing import Any

from .const import RinnaiSystemMode, RinnaiUnitId

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from .pollconnection import RinnaiPollConnection
from .event import Event
from .system_status import RinnaiSystemStatus
from .commands import (
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
    EVAP_ZONE_SET_AUTO,
    MODE_COOL_CMD,
    MODE_EVAP_CMD,
    MODE_HEAT_CMD,
    EVAP_COMMANDS,
    MODE_COMMANDS,
    SYSTEM_ENTER_TIME_SETTING,
    SYSTEM_SAVE_TIME,
    SYSTEM_SET_TIME,
    UNIT_ADVANCE,
    UNIT_ADVANCE_CANCEL,
    UNIT_CIRC_FAN_ON,
    UNIT_CIRC_FAN_SPEED,
    UNIT_COMMANDS,
    UNIT_OFF_CMD,
    UNIT_ON_CMD,
    UNIT_SET_AUTO,
    UNIT_SET_MANUAL,
    UNIT_SET_TEMP,
    UNIT_ZONE_ADVANCE,
    UNIT_ZONE_ADVANCE_CANCEL,
    UNIT_ZONE_OFF,
    UNIT_ZONE_ON,
    UNIT_ZONE_SET_AUTO,
    UNIT_ZONE_SET_MANUAL,
    UNIT_ZONE_SET_TEMP,
)

from .util import daemonthreaded

_LOGGER = logging.getLogger(__name__)


class RinnaiSystem:
    """Main controller class to interact with the Rinnai Touch Wifi unit."""

    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    instances = {}

    def __init__(self, ip_address: str) -> None:
        self._receiverqueue = queue.SimpleQueue()
        self._connection = RinnaiPollConnection(ip_address, self._receiverqueue)
        self._lastupdated = 0
        self._status = RinnaiSystemStatus()
        self._nosendupdates = 0
        RinnaiSystem.instances[ip_address] = self
        self._on_updated = Event()

        # Start the thread
        self.poll_loop()

    @staticmethod
    def get_instance(ip_address: str) -> Self:
        """Get a single instance of the system defined by its IP address."""
        if ip_address in RinnaiSystem.instances:
            return RinnaiSystem.instances[ip_address]
        return RinnaiSystem(ip_address)

    @staticmethod
    def remove_instance(ip_address: str) -> None:
        """Remove an instance of the system defined by its IP address."""
        if ip_address in RinnaiSystem.instances:
            RinnaiSystem.instances[ip_address].shutdown()
            del RinnaiSystem.instances[ip_address]
            _LOGGER.debug("Removed instance for IP: %s", ip_address)
        else:
            _LOGGER.warning("No instance found for IP: %s", ip_address)

    def subscribe_updates(self, obj_method: Any) -> None:
        """Subscribe to updates when the system status refreshes."""
        self._on_updated += obj_method

    def unsubscribe_updates(self, obj_method: Any) -> None:
        """Unsubscribe from updates received when the system status refreshes."""
        self._on_updated -= obj_method

    @daemonthreaded
    def poll_loop(self) -> None:
        """Main poll thread to receive updated messages from the unit."""

        # enter loop, wait for received (new) messages and push them to hass
        while True:
            new_status_json = self._receiverqueue.get()
            if new_status_json:
                if "sys.exit" in new_status_json:
                    break
                if (
                    isinstance(new_status_json, list)
                    and "SYST" in new_status_json[0]
                    and "STM" in new_status_json[0]["SYST"]
                ):
                    self._status.set_timesetting(True)
                    self._on_updated()
                else:
                    status = RinnaiSystemStatus()
                    res = status.handle_status(new_status_json)
                    if res:
                        self._status = status
                        self._on_updated()
                    else:
                        _LOGGER.error("JSON Error: %s", new_status_json)
        _LOGGER.debug("Shutting down the polling thread")

    async def set_cooling_mode(self) -> bool:
        """Set system to cooling mode."""
        return self.validate_and_send(MODE_COOL_CMD)

    async def set_evap_mode(self) -> bool:
        """Set system to evap mode."""
        return self.validate_and_send(MODE_EVAP_CMD)

    async def set_heater_mode(self) -> bool:
        """Set system to heater mode."""
        return self.validate_and_send(MODE_HEAT_CMD)

    async def turn_unit_on(self) -> bool:
        """Turn unit on (and system)."""
        cmd = UNIT_ON_CMD
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def turn_heater_on(self) -> bool:
        """Turn unit on (and system)."""
        cmd = UNIT_ON_CMD
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=str(RinnaiUnitId.HEATER)))
            return True
        return False

    async def turn_cooler_on(self) -> bool:
        """Turn unit on (and system)."""
        cmd = UNIT_ON_CMD
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=str(RinnaiUnitId.COOLER)))
            return True
        return False

    async def turn_unit_off(self) -> bool:
        """Turn unit off (and system)."""
        cmd = UNIT_OFF_CMD
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def turn_unit_fan_only(self) -> bool:
        """Turn circ fan on in while system is off."""
        cmd = UNIT_CIRC_FAN_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def set_unit_temp(self, temp: int) -> bool:
        """Set target temperature."""
        cmd = UNIT_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(
                cmd.format(unit_id=self._status.unit_status.unit_id, temp=f"{temp:02d}")
            )
            return True
        return False

    async def set_unit_auto(self) -> bool:
        """Set to auto mode."""
        cmd = UNIT_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def set_unit_manual(self) -> bool:
        """Set to manual mode."""
        cmd = UNIT_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def unit_advance(self) -> bool:
        """Press advance button."""
        cmd = UNIT_ADVANCE
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def unit_advance_cancel(self) -> bool:
        """Press advance cancel button."""
        cmd = UNIT_ADVANCE_CANCEL
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id))
            return True
        return False

    async def turn_unit_zone_on(self, zone: str) -> bool:
        """Turn a zone on."""
        cmd = UNIT_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id, zone=zone))
            return True
        return False

    async def turn_unit_zone_off(self, zone: str) -> bool:
        """Turn a zone off."""
        cmd = UNIT_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id, zone=zone))
            return True
        return False

    async def set_unit_zone_temp(self, zone: str, temp: int) -> bool:
        """Set target temperature for a zone."""
        cmd = UNIT_ZONE_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(
                cmd.format(
                    unit_id=self._status.unit_status.unit_id,
                    zone=zone,
                    temp=f"{temp:02d}",
                )
            )
            return True
        return False

    async def set_unit_zone_auto(self, zone: str) -> bool:
        """Set zone to auto mode."""
        cmd = UNIT_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id, zone=zone))
            return True
        return False

    async def set_unit_zone_manual(self, zone: str) -> bool:
        """Set zone to manual mode."""
        cmd = UNIT_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id, zone=zone))
            return True
        return False

    async def set_unit_zone_advance(self, zone: str) -> bool:
        """Press zone advance button."""
        cmd = UNIT_ZONE_ADVANCE
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id, zone=zone))
            return True
        return False

    async def set_unit_zone_advance_cancel(self, zone: str) -> bool:
        """Press zone advance cacnel button."""
        cmd = UNIT_ZONE_ADVANCE_CANCEL
        if self.validate_command(cmd):
            self.send_command(cmd.format(unit_id=self._status.unit_status.unit_id, zone=zone))
            return True
        return False

    async def turn_evap_on(self) -> bool:
        """Turn on evap (and system)."""
        return self.validate_and_send(EVAP_ON_CMD)

    async def turn_evap_off(self) -> bool:
        """Turn off evap (and system)."""
        return self.validate_and_send(EVAP_OFF_CMD)

    async def turn_evap_pump_on(self) -> bool:
        """Turn water pump on in evap mode."""
        return self.validate_and_send(EVAP_PUMP_ON)

    async def turn_evap_pump_off(self) -> bool:
        """Turn water pump off in evap mode."""
        return self.validate_and_send(EVAP_PUMP_OFF)

    async def turn_evap_fan_on(self) -> bool:
        """Turn fan on in evap mode."""
        return self.validate_and_send(EVAP_FAN_ON)

    async def turn_evap_fan_off(self) -> bool:
        """Turn fan off in evap mode."""
        return self.validate_and_send(EVAP_FAN_OFF)

    async def set_evap_fanspeed(self, speed: int) -> bool:
        """Set fan speed in evap mode."""
        cmd = EVAP_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f"{speed:02d}"))
            return True
        return False

    async def set_unit_fanspeed(self, speed: int) -> bool:
        """Set fan speed."""
        cmd = UNIT_CIRC_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(
                cmd.format(unit_id=self._status.unit_status.unit_id, speed=f"{speed:02d}")
            )
            return True
        return False

    async def set_evap_comfort(self, comfort: int) -> bool:
        """Set comfort level in Evap auto mode."""
        cmd = EVAP_SET_COMFORT
        if self.validate_command(cmd):
            self.send_command(cmd.format(comfort=comfort))
            return True
        return False

    async def turn_evap_zone_on(self, zone: str) -> bool:
        """Turn zone off in Evap mode."""
        cmd = EVAP_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_evap_zone_off(self, zone: str) -> bool:
        """Turn zone off in Evap mode."""
        cmd = EVAP_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_evap_zone_auto(self, zone: str) -> bool:
        """Set zone to Auto mode on Evap."""
        cmd = EVAP_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_evap_zone_manual(self, zone: str) -> bool:
        """Set zone to manual mode on Evap."""
        cmd = EVAP_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_system_time(self, set_datetime: datetime = None) -> bool:
        """Set system time."""
        now = datetime.now()
        if set_datetime is not None and isinstance(set_datetime, datetime):
            now = set_datetime
        set_time = now.strftime("%H:%M")
        set_day = now.strftime("%a").upper()
        result = self.validate_and_send(SYSTEM_ENTER_TIME_SETTING)
        cmd = SYSTEM_SET_TIME
        if self.validate_command(cmd):
            result = self.send_command(cmd.format(day=set_day, time=set_time)) and result
        result = self.validate_and_send(SYSTEM_SAVE_TIME) and result
        return result

    def get_stored_status(self) -> RinnaiSystemStatus:
        """Get the current status without a refresh."""
        return self._status

    def validate_command(self, cmd: str) -> bool:
        """Validate a command is appropriat to the current operating mode."""
        if cmd in MODE_COMMANDS:
            return True
        if cmd in UNIT_COMMANDS and self._status.mode in (
            RinnaiSystemMode.HEATING,
            RinnaiSystemMode.COOLING,
        ):
            return True
        if cmd in EVAP_COMMANDS and self._status.mode == RinnaiSystemMode.EVAP:
            return True
        return False

    def send_command(self, cmd: str) -> None:
        """Send the command to the unit."""
        self._connection.send_command(cmd)

    def validate_and_send(self, cmd: str) -> bool:
        """Validate and send a command."""
        if self.validate_command(cmd):
            self.send_command(cmd)
            return True
        _LOGGER.error(
            "Validation of command failed. Not sending. CMD: %s, Mode: %s",
            cmd,
            self._status.mode,
        )
        return False

    def register_socket_state_handler(self, socket_handler: Any) -> None:
        """Register a socket state handler to receive updates."""
        self._connection.register_socket_state_handler(socket_handler)

    def unregister_socket_state_handler(self, socket_handler: Any) -> None:
        """Unregister a socket state handler."""
        self._connection.unregister_socket_state_handler(socket_handler)

    def get_status(self) -> RinnaiSystemStatus:
        """Retrieve (initially empty) status from the unit."""
        self._connection.start_thread()
        return self._status

    def shutdown(self) -> None:
        """Call this when removing the integration from home assistant."""
        try:
            self._connection.stop_thread()
            _LOGGER.debug("Connection thread stopped")
        except:  # pylint: disable=bare-except  # noqa: E722
            _LOGGER.debug("Error stopping the connection thread")
