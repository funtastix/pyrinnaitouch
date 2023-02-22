"""Main system control"""
import logging
import queue
from typing import Any

from pyrinnaitouch.const import RinnaiSystemMode
try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

from .connection import RinnaiConnection
from .receiver import RinnaiReceiver
from .event import Event
from .system_status import RinnaiSystemStatus
from .commands import (
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
    HEAT_CIRC_FAN_SPEED,
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
    COOL_CIRC_FAN_SPEED,
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
    EVAP_ZONE_SET_AUTO,
    MODE_COOL_CMD,
    MODE_EVAP_CMD,
    MODE_HEAT_CMD,
    HEAT_COMMANDS,
    COOL_COMMANDS,
    EVAP_COMMANDS,
    MODE_COMMANDS
)

from .util import daemonthreaded

_LOGGER = logging.getLogger(__name__)

class RinnaiSystem:
    """Main controller class to interact with the Rinnai Touch Wifi unit."""
    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    instances = {}

    def __init__(self, ip_address: str) -> None:
        self._connection = RinnaiConnection(ip_address)
        self._lastupdated = 0
        self._status = RinnaiSystemStatus()
        self._nosendupdates = 0
        self._receiverqueue = queue.Queue()
        RinnaiSystem.instances[ip_address] = self
        self._on_updated = Event()

    @staticmethod
    def get_instance(ip_address: str) -> Self:
        """Get a single instance of the system defined by its IP address."""
        if ip_address in RinnaiSystem.instances:
            return RinnaiSystem.instances[ip_address]
        return RinnaiSystem(ip_address)

    def subscribe_updates(self,obj_method: Any) -> None:
        """Subscribe to updates when the system status refreshes."""
        self._on_updated += obj_method

    def unsubscribe_updates(self,obj_method: Any) -> None:
        """Unsubscribe from updates received when the system status refreshes."""
        self._on_updated -= obj_method

    @daemonthreaded
    def poll_loop(self) -> None:
        """Main poll thread to receive updated messages from the unit."""
        #create the first connection
        self._connection.renew_connection()
        #start the receiver thread
        receiver = RinnaiReceiver(self._connection, self._receiverqueue)
        receiver.receiver()

        #enter loop, wait for received (new) messages and push them to hass
        while True:
            new_status_json = self._receiverqueue.get()
            if new_status_json:
                status = RinnaiSystemStatus()
                res = status.handle_status(new_status_json)
                if res:
                    self._status = status
                    self._on_updated()
                else:
                    self._connection.log_json_error()


    async def set_cooling_mode(self) -> bool:
        """Set system to cooling mode."""
        return self.validate_and_send(MODE_COOL_CMD)

    async def set_evap_mode(self) -> bool:
        """Set system to evap mode."""
        return self.validate_and_send(MODE_EVAP_CMD)

    async def set_heater_mode(self) -> bool:
        """Set system to heater mode."""
        return self.validate_and_send(MODE_HEAT_CMD)

    async def turn_heater_on(self) -> bool:
        """Turn heater on (and system)."""
        return self.validate_and_send(HEAT_ON_CMD)

    async def turn_heater_off(self) -> bool:
        """Turn heater off (and system)."""
        return self.validate_and_send(HEAT_OFF_CMD)

    async def turn_heater_fan_only(self) -> bool:
        """Turn circ fan on in heating mode while system is off."""
        return self.validate_and_send(HEAT_CIRC_FAN_ON)

    async def set_heater_temp(self, temp: int) -> bool:
        """Set target temperature in heating mode."""
        cmd=HEAT_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(temp=temp))
            return True
        return False

    async def set_heater_auto(self) -> bool:
        """Set to auto mode in heater."""
        return self.validate_and_send(HEAT_SET_AUTO)

    async def set_heater_manual(self) -> bool:
        """Set to manual mode in heater."""
        return self.validate_and_send(HEAT_SET_MANUAL)

    async def heater_advance(self) -> bool:
        """Press advance button in heater mode."""
        return self.validate_and_send(HEAT_ADVANCE)

    async def heater_advance_cancel(self) -> bool:
        """Press advance cancel button in heater mode."""
        return self.validate_and_send(HEAT_ADVANCE_CANCEL)

    async def turn_heater_zone_on(self, zone: str) -> bool:
        """Turn a zone on in heating mode."""
        cmd=HEAT_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_heater_zone_off(self, zone: str) -> bool:
        """Turn a zone off in heating mode."""
        cmd=HEAT_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_temp(self, zone: str, temp: int) -> bool:
        """Set target temperature for a zone in heating mode."""
        cmd=HEAT_ZONE_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone, temp=temp))
            return True
        return False

    async def set_heater_zone_auto(self, zone: str) -> bool:
        """Set zone to auto mode in heating."""
        cmd=HEAT_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_manual(self, zone: str) -> bool:
        """Set zone to manual mode in heating."""
        cmd=HEAT_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_advance(self, zone: str) -> bool:
        """Press zone advance button in heater mode."""
        cmd=HEAT_ZONE_ADVANCE
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_advance_cancel(self, zone: str) -> bool:
        """Press zone advance cacnel button in heater mode."""
        cmd=HEAT_ZONE_ADVANCE_CANCEL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_cooling_on(self) -> bool:
        """Turn cooling on (and system)."""
        return self.validate_and_send(COOL_ON_CMD)

    async def turn_cooling_off(self) -> bool:
        """Turn cooling off (and system)."""
        return self.validate_and_send(COOL_OFF_CMD)

    async def turn_cooling_fan_only(self) -> bool:
        """Turn circ fan on (fan only) in cooling mode while system off."""
        return self.validate_and_send(COOL_CIRC_FAN_ON)

    async def set_cooling_temp(self, temp: int) -> bool:
        """Set main target temperature in cooling mode."""
        cmd=COOL_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(temp=temp))
            return True
        return False

    async def set_cooling_auto(self) -> bool:
        """Set auto mode in cooling."""
        return self.validate_and_send(COOL_SET_AUTO)

    async def set_cooling_manual(self) -> bool:
        """Set manual mode in cooling."""
        return self.validate_and_send(COOL_SET_MANUAL)

    async def cooling_advance(self) -> bool:
        """Press advance button in cooling mode."""
        return self.validate_and_send(COOL_ADVANCE)

    async def cooling_advance_cancel(self) -> bool:
        """Press advance cancel button in cooling mode."""
        return self.validate_and_send(COOL_ADVANCE_CANCEL)

    async def turn_cooling_zone_on(self, zone: str) -> bool:
        """Turn zone on in cooling mode."""
        cmd=COOL_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_cooling_zone_off(self, zone: str) -> bool:
        """Turn zone off in cooling mode."""
        cmd=COOL_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_temp(self, zone: str, temp: int) -> bool:
        """Set zone target temperature in cooling."""
        cmd=COOL_ZONE_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone, temp=temp))
            return True
        return False

    async def set_cooling_zone_auto(self, zone: str) -> bool:
        """Set zone to auto mode in cooling."""
        cmd=COOL_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_manual(self, zone: str) -> bool:
        """Set zone to manual mode in cooling."""
        cmd=COOL_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_advance(self, zone: str) -> bool:
        """Press advance button in a zone in cooling mode."""
        cmd=COOL_ZONE_ADVANCE
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_advance_cancel(self, zone: str) -> bool:
        """Press advance cancel button in a zone in cooling mode."""
        cmd=COOL_ZONE_ADVANCE_CANCEL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
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

    async def set_evap_auto(self) -> bool:
        """Set to auto mode in evap."""
        return self.validate_and_send(EVAP_SET_AUTO)

    async def set_evap_manual(self) -> bool:
        """Set to manual mode in evap."""
        return self.validate_and_send(EVAP_SET_MANUAL)

    async def set_evap_fanspeed(self, speed: int) -> bool:
        """Set fan speed in evap mode."""
        cmd=EVAP_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f'{speed:02d}'))
            return True
        return False

    async def set_heater_fanspeed(self, speed: int) -> bool:
        """Set fan speed in heater mode."""
        cmd=HEAT_CIRC_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f'{speed:02d}'))
            return True
        return False

    async def set_cooling_fanspeed(self, speed: int) -> bool:
        """Set fan speed in cooling mode."""
        cmd=COOL_CIRC_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f'{speed:02d}'))
            return True
        return False

    async def set_evap_comfort(self, comfort: int) -> bool:
        """Set comfort level in Evap auto mode."""
        cmd=EVAP_SET_COMFORT
        if self.validate_command(cmd):
            self.send_command(cmd.format(comfort=comfort))
            return True
        return False

    async def turn_evap_zone_on(self, zone: str) -> bool:
        """Turn zone off in Evap mode."""
        cmd=EVAP_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_evap_zone_off(self, zone: str) -> bool:
        """Turn zone off in Evap mode."""
        cmd=EVAP_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_evap_zone_auto(self, zone: str) -> bool:
        """Set zone to Auto mode on Evap."""
        cmd=EVAP_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_evap_zone_manual(self, zone: str) -> bool:
        """Set zone to manual mode on Evap."""
        cmd=EVAP_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    def get_stored_status(self) -> RinnaiSystemStatus:
        """Get the current status without a refresh."""
        return self._status

    def validate_command(self, cmd: str) -> bool:
        """Validate a command is appropriat to the current operating mode."""
        if cmd in MODE_COMMANDS:
            return True
        if cmd in HEAT_COMMANDS and self._status.mode == RinnaiSystemMode.HEATING:
            return True
        if cmd in COOL_COMMANDS and self._status.mode == RinnaiSystemMode.COOLING:
            return True
        if cmd in EVAP_COMMANDS and self._status.mode == RinnaiSystemMode.EVAP:
            return True
        return False

    def send_command(self, cmd: str) -> None:
        """Send the command to the unit."""
        self._connection.dispatch_command(cmd)

    def validate_and_send(self, cmd: str) -> bool:
        """Validate and send a command."""
        if self.validate_command(cmd):
            self.send_command(cmd)
            return True
        _LOGGER.error("Validation of command failed. Not sending")
        return False

    def get_status(self) -> RinnaiSystemStatus:
        """Retrieve initial empty status from the unit."""
        if self._connection.renew_connection():
            _LOGGER.debug("Client Connection: %s", self._connection) # pylint: disable=protected-access
            self.poll_loop()
        else:
            _LOGGER.debug("renewing connection failed, ooops")

        return self._status

    async def async_will_remove_from_hass(self) -> None:
        """Call this when removing the integration from home assistant."""
        try:
            self._connection.shutdown()
        except: # pylint: disable=bare-except
            _LOGGER.debug("Nothing to close")
