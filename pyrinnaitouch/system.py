"""Main system control"""
import logging
import socket
import time
import json
import re
import threading
import queue
from enum import Enum
from dataclasses import dataclass
from .heater import handle_heating_mode, HeaterStatus
from .cooler import handle_cooling_mode, CoolingStatus
from .evap import handle_evap_mode, EvapStatus
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

from .util import get_attribute, y_n_to_bool

_LOGGER = logging.getLogger(__name__)

def daemonthreaded(function_arg):
    """Decoration to start object function as thread"""
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=function_arg, args=args, kwargs=kwargs)
        thread.setDaemon(True)
        thread.start()
        return thread
    return wrapper

class Event():
    """Simple event class."""

    def __init__(self):
        self.__eventhandlers = []

    def __iadd__(self, handler):
        """Add event handler."""
        self.__eventhandlers.append(handler)
        return self

    def __isub__(self, handler):
        """Remove event handler."""
        self.__eventhandlers.remove(handler)
        return self

    def __call__(self, *args, **keywargs):
        """Call event handler."""
        for eventhandler in self.__eventhandlers:
            if eventhandler is not None:
                eventhandler(*args, **keywargs)

@dataclass
class BrivisStatus():
    """Overall Class for describing status"""
    # pylint: disable=too-many-instance-attributes
    #modes
    #TODO: turn into mode
    evap_mode: bool = False
    cooling_mode: bool = False
    heater_mode: bool = False
    system_on: bool = False
    temp_unit: str = None
    #turn into capabilities
    has_heater: bool = True
    has_cooling: bool = True
    has_evap: bool = True

    #system info
    firmware_version: str = None
    wifi_module_version: str = None

    #zones
    zone_a_desc: str = None
    zone_b_desc: str = None
    zone_c_desc: str = None
    zone_d_desc: str = None
    is_multi_set_point: bool = False

    #faults
    has_fault: bool = False

    heater_status: HeaterStatus = HeaterStatus()
    cooling_status: CoolingStatus = CoolingStatus()
    evap_status: EvapStatus = EvapStatus()

    def set_mode(self,mode):
        """Set the mode."""
        if mode == Mode.HEATING:
            self.heater_mode = True
            self.cooling_mode = False
            self.evap_mode = False
        elif mode == Mode.COOLING:
            self.heater_mode = False
            self.cooling_mode = True
            self.evap_mode = False
        elif mode == Mode.EVAP:
            self.heater_mode = False
            self.cooling_mode = False
            self.evap_mode = True

class Mode(Enum):
    """Define system modes."""
    HEATING = 1
    EVAP = 2
    COOLING = 3
    RC = 4
    NONE = 5

class RinnaiSystem:
    """Main controller class to interact with the Rinnai Touch Wifi unit."""
    # pylint: disable=too-many-instance-attributes,too-many-public-methods

    clients = {}
    instances = {}

    TEMP_CELSIUS = "°C"
    TEMP_FAHRENHEIT = "°F"

    def __init__(self, ip_address):
        self._touch_ip = ip_address
        self._touch_port = 27847
        self._send_sequence = 1
        self._lastupdated = 0
        self._status = BrivisStatus()
        self._lastclosed = 0
        self._client = None
        self._zones = []
        self._jsonerrors = 0
        self._nosendupdates = 0
        self._senderqueue = queue.Queue()
        self._receiverqueue = queue.Queue()
        if ip_address not in RinnaiSystem.clients:
            RinnaiSystem.clients[ip_address] = self._client
        else:
            self._client = RinnaiSystem.clients[ip_address]
        RinnaiSystem.instances[ip_address] = self
        self._on_updated = Event()

    def set_zones(self, zones):
        """Set the active zones in the system."""
        self._zones = zones

    @staticmethod
    def get_instance(ip_address):
        """Get a single instance of the system defined by its IP address."""
        if ip_address in RinnaiSystem.instances:
            return RinnaiSystem.instances[ip_address]
        return RinnaiSystem(ip_address)

    def subscribe_updates(self,obj_method):
        """Subscribe to updates when the system status refreshes."""
        self._on_updated += obj_method

    def unsubscribe_updates(self,obj_method):
        """Unsubscribe from updates received when the system status refreshes."""
        self._on_updated -= obj_method

    @daemonthreaded
    def receiver(self):
        """Main send and receive thread to process and send messages."""
        lastdata = ''
        counter = 0

        while True:
            counter+=1
            # send next message if any
            try:
                message = self._senderqueue.get(False)
                self._client.sendall(message)
                _LOGGER.error("Fired off command: (%s)", message.decode())
                counter = 0
            except ConnectionError as connerr:
                _LOGGER.error("Couldn't send command (connection): (%s)", repr(connerr))
                self.renew_connection()
            except queue.Empty:
                None # pylint: disable=pointless-statement

            #send empty command ever so often
            if counter > 10:
                try:
                    cmd = "NA"
                    self._client.sendall(cmd.encode())
                    counter = 0
                except ConnectionError as connerr:
                    _LOGGER.error("Couldn't send command (connection): (%s)", repr(connerr))
                    self.renew_connection()

            #receive status
            try:
                temp = self._client.recv(8096)
                if temp:
                    #_LOGGER.debug("Received data: (%s)", temp.decode())
                    data = temp
                    exp = re.search('^.*([0-9]{6}).*(\[[^\[]*\])[^]]*$', str(data)) # pylint: disable=anomalous-backslash-in-string
                    seq = int(exp.group(1))
                    if seq >= 255:
                        seq = 0
                    else:
                        seq = seq + 1
                    self._send_sequence = seq
                    json_str = exp.group(2)
                    if json_str != lastdata:
                        _LOGGER.debug("Sequence: %s Json: %s", seq, json_str)
                        status_json = json.loads(json_str)
                        self._receiverqueue.put(status_json)
                        lastdata = json_str
            except ConnectionError as connerr:
                _LOGGER.error("Couldn't decode JSON (connection), skipping (%s)", repr(connerr))
                _LOGGER.debug("Client shutting down")
                self._client.shutdown(socket.SHUT_RDWR)
                self._client.close()
                self._lastclosed = time.time()
                self.renew_connection()
            except AttributeError as atterr:
                _LOGGER.error("Couldn't decode JSON (probably HELLO), skipping (%s)", repr(atterr))

    @daemonthreaded
    def poll_loop(self):
        """Main poll thread to receive updated messages from the unit."""
        #create the first connection
        self.renew_connection()
        #start the receiver thread
        self.receiver()

        #enter loop, wait for received (new) messages and push them to hass
        while True:
            new_status = self._receiverqueue.get()
            if new_status:
                status = BrivisStatus()
                res = self.handle_status(status, new_status)
                if res:
                    self._status = status
                    self._on_updated()

    def renew_connection(self):
        """Safely renew the connection if it is disconnected."""
        connection_error = False
        try:
            if self._client is not None:
                if (
                    self._client.getpeername
                    and self._client.getpeername() is not None
                    and self._jsonerrors < 4
                ):
                    return True
        except (OSError, ConnectionError) as ocerr:
            _LOGGER.debug("Error 1st phase during renewConnection %s", ocerr)
            connection_error = True

        if (
            self._client is None
            or self._client._closed # pylint: disable=protected-access
            or connection_error
            or (self._jsonerrors > 2)
        ):
            try:
                if connection_error or (self._jsonerrors > 2):
                    self._client.close()
                self._jsonerrors = 0
                self.connect_to_touch(self._touch_ip,self._touch_port)
                RinnaiSystem.clients[self._touch_ip] = self._client
                _LOGGER.debug("Connected to %s", self._client.getpeername())
                return True
            except ConnectionRefusedError as crerr:
                _LOGGER.debug("Error during renewConnection %s", crerr)
            except ConnectionError as cerr:
                _LOGGER.debug("Error during renewConnection %s", cerr)
            except Exception as eerr: # pylint: disable=broad-except
                _LOGGER.debug("Error during renewConnection %s", eerr)
        return False

    def connect_to_touch(self, touch_ip, port):
        """Connect the client."""
        # create an ipv4 (AF_INET) socket object using the tcp protocol (SOCK_STREAM)
        _LOGGER.debug("Creating new client...")
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10)
            client.connect((touch_ip, port))
            self._client = client
            _LOGGER.debug("Client connection created: %s", self._client.getpeername())
        except ConnectionRefusedError as crerr:
            _LOGGER.debug("Client refused connection: %s", crerr)
            raise crerr
            #should really take a few hours break to recover!

    def handle_status(self, brivis_status, status_json):
        """Handle the JSON response from the system."""
        # pylint: disable=too-many-branches,too-many-statements

        try:
            #jStr = status[14:]
            #_LOGGER.debug(json.dumps(j[0], indent = 4))
            cfg = get_attribute(status_json[0].get("SYST"),"CFG",None)
            if not cfg:
                # Probably an error
                _LOGGER.error("No CFG - Not happy, Jan")

            else:
                if get_attribute(cfg, "TU", None) == "F":
                    brivis_status.temp_unit = RinnaiSystem.TEMP_FAHRENHEIT
                else:
                    brivis_status.temp_unit = RinnaiSystem.TEMP_CELSIUS

                brivis_status.is_multi_set_point = y_n_to_bool(get_attribute(cfg, "MTSP", None))
                brivis_status.zone_a_desc = get_attribute(cfg, "ZA", None).strip()
                brivis_status.zone_b_desc = get_attribute(cfg, "ZB", None).strip()
                brivis_status.zone_c_desc = get_attribute(cfg, "ZC", None).strip()
                brivis_status.zone_d_desc = get_attribute(cfg, "ZD", None).strip()
                brivis_status.firmware_version = get_attribute(cfg, "VR", None).strip()
                brivis_status.wifi_module_version = get_attribute(cfg, "CV", None).strip()

            avm = get_attribute(status_json[0].get("SYST"),"AVM",None)
            if not avm:
                # Probably an error
                _LOGGER.error("No AVM - Not happy, Jan")

            else:
                if get_attribute(avm, "HG", None) == "Y":
                    brivis_status.has_heater = True
                else:
                    brivis_status.has_heater = False
                if get_attribute(avm, "CG", None) == "Y":
                    brivis_status.has_cooling = True
                else:
                    brivis_status.has_cooling = False
                if get_attribute(avm, "EC", None) == "Y":
                    brivis_status.has_evap = True
                else:
                    brivis_status.has_evap = False

            flt = get_attribute(status_json[0].get("SYST"), "FLT", None)
            if not avm:
                # Probably an error
                _LOGGER.error("No FLT - Not happy, Jan")

            else:
                brivis_status.has_fault = y_n_to_bool(get_attribute(flt, "AV", None))

            if 'HGOM' in status_json[1]:
                handle_heating_mode(status_json,brivis_status)
                brivis_status.set_mode(Mode.HEATING)
                _LOGGER.debug("We are in HEAT mode")

            elif 'CGOM' in status_json[1]:
                handle_cooling_mode(status_json,brivis_status)
                brivis_status.set_mode(Mode.COOLING)
                _LOGGER.debug("We are in COOL mode")

            elif 'ECOM' in status_json[1]:
                handle_evap_mode(status_json,brivis_status)
                brivis_status.set_mode(Mode.EVAP)
                _LOGGER.debug("We are in EVAP mode")

            else:
                _LOGGER.debug("Unknown mode")
            return True
        except Exception as err: # pylint: disable=broad-except
            _LOGGER.error("Couldn't decode JSON (exception), skipping (%s)", repr(err))
            self._jsonerrors = self._jsonerrors + 1
            return False

    async def set_cooling_mode(self):
        """Set system to cooling mode."""
        return self.validate_and_send(MODE_COOL_CMD)

    async def set_evap_mode(self):
        """Set system to evap mode."""
        return self.validate_and_send(MODE_EVAP_CMD)

    async def set_heater_mode(self):
        """Set system to heater mode."""
        return self.validate_and_send(MODE_HEAT_CMD)

    async def turn_heater_on(self):
        """Turn heater on (and system)."""
        return self.validate_and_send(HEAT_ON_CMD)

    async def turn_heater_off(self):
        """Turn heater off (and system)."""
        return self.validate_and_send(HEAT_OFF_CMD)

    async def turn_heater_fan_only(self):
        """Turn circ fan on in heating mode while system is off."""
        return self.validate_and_send(HEAT_CIRC_FAN_ON)

    async def set_heater_temp(self, temp):
        """Set target temperature in heating mode."""
        cmd=HEAT_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(temp=temp))
            return True
        return False

    async def set_heater_auto(self):
        """Set to auto mode in heater."""
        return self.validate_and_send(HEAT_SET_AUTO)

    async def set_heater_manual(self):
        """Set to manual mode in heater."""
        return self.validate_and_send(HEAT_SET_MANUAL)

    async def heater_advance(self):
        """Press advance button in heater mode."""
        return self.validate_and_send(HEAT_ADVANCE)

    async def heater_advance_cancel(self):
        """Press advance cancel button in heater mode."""
        return self.validate_and_send(HEAT_ADVANCE_CANCEL)

    async def turn_heater_zone_on(self, zone):
        """Turn a zone on in heating mode."""
        cmd=HEAT_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_heater_zone_off(self, zone):
        """Turn a zone off in heating mode."""
        cmd=HEAT_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_temp(self, zone, temp):
        """Set target temperature for a zone in heating mode."""
        cmd=HEAT_ZONE_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone, temp=temp))
            return True
        return False

    async def set_heater_zone_auto(self, zone):
        """Set zone to auto mode in heating."""
        cmd=HEAT_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_manual(self, zone):
        """Set zone to manual mode in heating."""
        cmd=HEAT_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_advance(self, zone):
        """Press zone advance button in heater mode."""
        cmd=HEAT_ZONE_ADVANCE
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_heater_zone_advance_cancel(self, zone):
        """Press zone advance cacnel button in heater mode."""
        cmd=HEAT_ZONE_ADVANCE_CANCEL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_cooling_on(self):
        """Turn cooling on (and system)."""
        return self.validate_and_send(COOL_ON_CMD)

    async def turn_cooling_off(self):
        """Turn cooling off (and system)."""
        return self.validate_and_send(COOL_OFF_CMD)

    async def turn_cooling_fan_only(self):
        """Turn circ fan on (fan only) in cooling mode while system off."""
        return self.validate_and_send(COOL_CIRC_FAN_ON)

    async def set_cooling_temp(self, temp):
        """Set main target temperature in cooling mode."""
        cmd=COOL_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(temp=temp))
            return True
        return False

    async def set_cooling_auto(self):
        """Set auto mode in cooling."""
        return self.validate_and_send(COOL_SET_AUTO)

    async def set_cooling_manual(self):
        """Set manual mode in cooling."""
        return self.validate_and_send(COOL_SET_MANUAL)

    async def cooling_advance(self):
        """Press advance button in cooling mode."""
        return self.validate_and_send(COOL_ADVANCE)

    async def cooling_advance_cancel(self):
        """Press advance cancel button in cooling mode."""
        return self.validate_and_send(COOL_ADVANCE_CANCEL)

    async def turn_cooling_zone_on(self, zone):
        """Turn zone on in cooling mode."""
        cmd=COOL_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_cooling_zone_off(self, zone):
        """Turn zone off in cooling mode."""
        cmd=COOL_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_temp(self, zone, temp):
        """Set zone target temperature in cooling."""
        cmd=COOL_ZONE_SET_TEMP
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone, temp=temp))
            return True
        return False

    async def set_cooling_zone_auto(self, zone):
        """Set zone to auto mode in cooling."""
        cmd=COOL_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_manual(self, zone):
        """Set zone to manual mode in cooling."""
        cmd=COOL_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_advance(self, zone):
        """Press advance button in a zone in cooling mode."""
        cmd=COOL_ZONE_ADVANCE
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_cooling_zone_advance_cancel(self, zone):
        """Press advance cancel button in a zone in cooling mode."""
        cmd=COOL_ZONE_ADVANCE_CANCEL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_evap_on(self):
        """Turn on evap (and system)."""
        return self.validate_and_send(EVAP_ON_CMD)

    async def turn_evap_off(self):
        """Turn off evap (and system)."""
        return self.validate_and_send(EVAP_OFF_CMD)

    async def turn_evap_pump_on(self):
        """Turn water pump on in evap mode."""
        return self.validate_and_send(EVAP_PUMP_ON)

    async def turn_evap_pump_off(self):
        """Turn water pump off in evap mode."""
        return self.validate_and_send(EVAP_PUMP_OFF)

    async def turn_evap_fan_on(self):
        """Turn fan on in evap mode."""
        return self.validate_and_send(EVAP_FAN_ON)

    async def turn_evap_fan_off(self):
        """Turn fan off in evap mode."""
        return self.validate_and_send(EVAP_FAN_OFF)

    async def set_evap_auto(self):
        """Set to auto mode in evap."""
        return self.validate_and_send(EVAP_SET_AUTO)

    async def set_evap_manual(self):
        """Set to manual mode in evap."""
        return self.validate_and_send(EVAP_SET_MANUAL)

    async def set_evap_fanspeed(self, speed):
        """Set fan speed in evap mode."""
        cmd=EVAP_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f'{speed:02d}'))
            return True
        return False

    async def set_heater_fanspeed(self, speed):
        """Set fan speed in heater mode."""
        cmd=HEAT_CIRC_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f'{speed:02d}'))
            return True
        return False

    async def set_cooling_fanspeed(self, speed):
        """Set fan speed in cooling mode."""
        cmd=COOL_CIRC_FAN_SPEED
        if self.validate_command(cmd):
            self.send_command(cmd.format(speed=f'{speed:02d}'))
            return True
        return False

    async def set_evap_comfort(self, comfort):
        """Set comfort level in Evap auto mode."""
        cmd=EVAP_SET_COMFORT
        if self.validate_command(cmd):
            self.send_command(cmd.format(comfort=comfort))
            return True
        return False

    async def turn_evap_zone_on(self, zone):
        """Turn zone off in Evap mode."""
        cmd=EVAP_ZONE_ON
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def turn_evap_zone_off(self, zone):
        """Turn zone off in Evap mode."""
        cmd=EVAP_ZONE_OFF
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_evap_zone_auto(self, zone):
        """Set zone to Auto mode on Evap."""
        cmd=EVAP_ZONE_SET_AUTO
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    async def set_evap_zone_manual(self, zone):
        """Set zone to manual mode on Evap."""
        cmd=EVAP_ZONE_SET_MANUAL
        if self.validate_command(cmd):
            self.send_command(cmd.format(zone=zone))
            return True
        return False

    def get_stored_status(self):
        """Get the current status without a refresh."""
        return self._status

    def validate_command(self, cmd):
        """Validate a command is appropriat to the current operating mode."""
        if cmd in MODE_COMMANDS:
            return True
        if cmd in HEAT_COMMANDS and self._status.heater_mode:
            return True
        if cmd in COOL_COMMANDS and self._status.cooling_mode:
            return True
        if cmd in EVAP_COMMANDS and self._status.evap_mode:
            return True
        return False

    def send_command(self, cmd):
        """Send the command to the unit."""
        seq = str(self._send_sequence).zfill(6)
        #self._sendSequence = self._sendSequence + 1
        _LOGGER.debug("Sending command: %s", "N" + seq + cmd)
        self.send_to_touch("N" + seq + cmd)

    def validate_and_send(self, cmd):
        """Validate and send a command."""
        if self.validate_command(cmd):
            self.send_command(cmd)
            return True
        _LOGGER.error("Validation of command failed. Not sending")
        return False

    def get_status(self):
        """Retrieve initial empty status from the unit."""
        if self.renew_connection():
            _LOGGER.debug("Client Variable: %s / %s", self._client, self._client._closed) # pylint: disable=protected-access
            self.poll_loop()
        else:
            _LOGGER.debug("renewing connection failed, ooops")

        return self._status

    async def async_will_remove_from_hass(self):
        """Call this when removing the integration from home assistant."""
        try:
            self._client.shutdown(socket.SHUT_RDWR)
            self._client.close()
        except: # pylint: disable=bare-except
            _LOGGER.debug("Nothing to close")

    def send_to_touch(self, cmd):
        """Send the command."""
        #_LOGGER.debug("DEBUG: {}".format(cmd))
        self._senderqueue.put(cmd.encode())
