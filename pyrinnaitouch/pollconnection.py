"""Handle connectivity with non-blocking sockets and connection reporting."""

from collections import defaultdict
import enum
import json
import logging
from queue import Empty, SimpleQueue
import re
import selectors
import socket
import threading
import time
from time import sleep

_LOGGER = logging.getLogger(__name__)


class RinnaiConnectionState(enum.Enum):
    """Possible connection states for this class."""

    IDLE = 1
    CONNECTING = 2
    CONNECTED = 3
    REFUSED = 4
    TIMEOUT = 5
    ERROR = 6


class RinnaiPollConnection:  # pylint: disable=too-many-instance-attributes
    """Manage the non-blocking connection to the unit."""

    # Global map of IP addresses currently in use. Only used to track when multiple
    # connections are attempted, since we know how poorly the hardware handles this.
    clients = defaultdict(int)

    def __init__(self, ip_address: str, status_queue: SimpleQueue) -> None:
        """Initialise the connection object."""
        self._ip_address = ip_address
        self._port = 27847
        self._command_sequence = 1
        self._last_command_time = 0
        self._last_received_time = 0
        self._command_timeout_seconds = 10
        self._hello_received = False
        self._last_received_sequence_num = 0
        self._command_wait = False
        self._command_wait_timeout_seconds = 5
        #self._connection_reconnect_delay_seconds = 1
        self._udp_address = "0.0.0.0"
        self._udp_port = 50000

        RinnaiPollConnection.clients[ip_address] += 1
        if RinnaiPollConnection.clients[ip_address] > 1:
            _LOGGER.error(
                "Attempting duplicate connection to unit at %s, which the hardware "
                "will not support",
                ip_address,
            )
            raise RuntimeError("Cannot have two connections to the same address")

        # Queue of commands (each as a string) to send to the unit.
        self._sendqueue = SimpleQueue()

        # Checked in all manner of places, should only be set on shutdown.
        self._thread_exit_flag = False

        # These don't get created until start_thread is called
        self._socket: socket.socket = None
        self._socketthread: threading.Thread = None
        self._socketstate = RinnaiConnectionState.IDLE

        self._readbuffer = bytearray()
        self._writebuffer = bytearray()

        # List of functions to call whenever _socketstate changes
        # Provides a single argument, RinnaiConnectionState
        self._connection_state_handlers = []

        # Outbound queue of JSON status
        self._status_queue = status_queue

        _LOGGER.debug("Poll connection inited")

    def send_command(self, command):
        """Queue a command to be sent to the unit."""
        self._sendqueue.put(command)

    def __del__(self):
        """Destructor to ensure the thread is stopped and the socket closed."""
        self.stop_thread()

    def stop_thread(self) -> None:
        """Stop the thread, close the socket, and decrement the connection tracker."""
        if self._socketthread is not None and self._socketthread.is_alive():
            self._thread_exit_flag = True
            self._socketthread.join(5)
            if self._socketthread.is_alive():
                _LOGGER.error("Could not stop monitoring thread")
                # Attempt to daemonise the thread since this should still allow the
                # process to exit.
                self._socketthread.daemon = True
            else:
                self._socketthread = None
                _LOGGER.debug("Monitoring thread confirmed stopped")

        if self._socket is not None:
            # Do our best to tidy up the socket.
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                _LOGGER.debug("Socket shutdown failed, likely was not connected")

            try:
                self._socket.close()
            except OSError:
                _LOGGER.debug("Socket close failed, likely was not open")

            self._socket = None

        # Let anybody listening to the status know that we're exiting.
        self._status_queue.put("sys.exit")

        RinnaiPollConnection.clients[self._ip_address] -= 1
        if RinnaiPollConnection.clients[self._ip_address] < 0:
            _LOGGER.error(
                "Somehow we have a negative number of connections; something has "
                "gone very wrong"
            )
            # Try to restore some sanity
            RinnaiPollConnection.clients[self._ip_address] = 0

    def _update_socket_state(self, socketstate: RinnaiConnectionState) -> None:
        """Update the connection state and call all registered handlers."""
        # Ignore unchanged states.
        if not isinstance(socketstate, RinnaiConnectionState):
            raise TypeError("Invalid socket state")

        if self._socketstate != socketstate:
            self._socketstate = socketstate
            for handler in self._connection_state_handlers:
                try:
                    handler(self._socketstate)
                except (ValueError, TypeError) as e:
                    _LOGGER.error("Invalid socket state handler (%s)", e)
            _LOGGER.debug("Socket state is now %s", self._socketstate)

    def socket_state(self) -> RinnaiConnectionState:
        """Return the current state of the socket."""
        return self._socketstate

    def register_socket_state_handler(self, handler) -> None:
        """Register a new handler interested in socket state updates.

        The new handler immediately gets called with the current status, and if
        successfully executed is added to the handler list. Duplicate handlers are
        ignored.
        """
        if handler not in self._connection_state_handlers:
            try:
                handler(self._socketstate)
                self._connection_state_handlers.append(handler)
            except TypeError as te:
                _LOGGER.error(
                    "Registration failed - could not call socket handler: %s", te
                )

    def unregister_socket_state_handler(self, handler) -> None:
        """Unregister a socket state handler."""
        if handler in self._connection_state_handlers:
            self._connection_state_handlers.remove(handler)

    def start_thread(self) -> None:
        """Attempt connection to the unit. Results are reflected via connection_state
        property."""

        if self._socketthread is None or not self._socketthread.is_alive():
            _LOGGER.debug("Starting connection thread")
            self._socketthread = threading.Thread(
                target=self._event_loop, name="RinnaiPollConnection"
            )
            self._socketthread.start()
        else:
            _LOGGER.error("Cannot start multiple connection threads")

    def _event_loop(self) -> None:
        """Thread that polls the socket and command queue and reacts accordingly."""
        _LOGGER.debug("Starting event loop within thread")
        while not self._thread_exit_flag:
            # Connect, then monitor. Repeat ad infinitum, unless we've been told
            # to exit.
            self._create_socket_and_connect()
            # Note that this only returns on disconnect/socket error, or when the thread
            # exit flag is set.
            self._monitor_socket_and_queue()

    def _monitor_socket_and_queue(self) -> None:
        # Create the selector and register for read events on the socket and the send
        # queue.  Write events on the socket aren't selected for until we have something
        # to say.
        selector = selectors.DefaultSelector()
        selector.register(self._socket, selectors.EVENT_READ)

        self._readbuffer.clear()
        self._writebuffer.clear()

        while (
            not self._thread_exit_flag
            and self._socketstate == RinnaiConnectionState.CONNECTED
        ):
            mask = selectors.EVENT_READ
            if len(self._writebuffer) > 0:
                mask |= selectors.EVENT_WRITE
                _LOGGER.debug("Selecting for write")

            selector.modify(self._socket, selectors.EVENT_READ)

            events = selector.select(0.1)
            for _key, mask in events:
                if mask & selectors.EVENT_READ:
                    # There is data available on the socket. Receive it into the buffer
                    # for now, process after we've been through all the events.
                    self._last_received_time = time.time()
                    try:
                        newbytes = self._socket.recv(8096)
                        _LOGGER.debug("Read %d bytes from socket", len(newbytes))

                        if len(newbytes) == 0:
                            # The socket has disconnected. This will be caught on the
                            # next loop and reconnection attempted.
                            _LOGGER.info("Socket disconnected. Reconnecting")
                            self._update_socket_state(RinnaiConnectionState.IDLE)
                        else:
                            self._readbuffer.extend(newbytes)
                            _LOGGER.debug(
                                "Receive buffer now has %d bytes of data to process",
                                len(self._readbuffer),
                            )

                    except OSError as ose:
                        _LOGGER.error("Socket error on recv: %s. Reconnecting", ose)
                        self._update_socket_state(RinnaiConnectionState.IDLE)

                if mask & selectors.EVENT_WRITE:
                    # We are able to write to the socket, and have something to say.
                    self._attempt_send()

            # Now process the command queue. We don't wait for anything to arrive here,
            # the waiting only happens in the select socket call.

            while True:
                try:
                    if (self._command_wait and ((time.time() - self._last_command_time) < self._command_wait_timeout_seconds)):
                        break
                    command = self._sendqueue.get_nowait()
                    # A command is ready to be sent. Format it, place it into the
                    # writebuffer and attempt to send it.
                    self._command_sequence = max(self._command_sequence + 1, self._last_received_sequence_num + 1)
                    self._command_sequence %=255
                    sequence_header = "N" + str(self._command_sequence).zfill(6)
                    self._writebuffer.extend(sequence_header.encode())
                    self._writebuffer.extend(command.encode())
                    _LOGGER.debug("Sending command %d", self._command_sequence)
                    self._attempt_send()
                    self._command_wait = True
                
                except Empty:
                    # Nothing in the queue for now. Consider sending an empty command
                    # if it's been long enough, and then break out of this loop.
                    if (
                        time.time() - self._last_command_time
                        > self._command_timeout_seconds
                    ):
                        self._command_sequence = max(self._command_sequence + 1, self._last_received_sequence_num + 1)
                        self._command_sequence %=255
                        sequence_header = "N" + str(self._command_sequence).zfill(6)
                        self._writebuffer.extend(sequence_header.encode())
                        self._writebuffer.extend(b"NA")
                        _LOGGER.debug("Sending idle command %d", self._command_sequence)
                        self._attempt_send()

                        # Update the time here in case the socket doesn't become
                        # write available quickly.
                        self._last_command_time = time.time()
                        self._command_wait = True
                        
                    break

            if time.time() - self._last_received_time > 30:
                _LOGGER.error(
                    "Resetting connection as no data received for at least 30 seconds"
                )
                self._update_socket_state(RinnaiConnectionState.TIMEOUT)

            self._process_received_data()

    def _attempt_send(self) -> None:
        # Attempt to send the contents of the write buffer. Only remove bytes that are
        # successfully sent,  which may not be all that we requested. Any bytes
        # remaining in the buffer will be caught in the next select call.
        try:
            num_sent = self._socket.send(self._writebuffer)
            _LOGGER.debug("Sent %d of %d bytes", num_sent, len(self._writebuffer))
            self._writebuffer = self._writebuffer[num_sent:]

            self._last_command_time = time.time()
            if len(self._writebuffer) > 0:
                _LOGGER.warning(
                    "There are %d bytes remaining to send. There may be network "
                    "congestion, or the connection is about to fail",
                    len(self._writebuffer),
                )
        except OSError as ose:
            _LOGGER.error("Socket error on send: %s. Reconnecting", ose)
            self._update_socket_state(RinnaiConnectionState.IDLE)

    def _process_received_data(self) -> None:
        # _LOGGER.debug("Number of bytes in buffer: %d", len(self._readbuffer))

        # Constants
        HELLO = b"*HELLO*"  # pylint: disable=invalid-name
        START_MARKER = b"N"  # pylint: disable=invalid-name
        # At least 7 bytes are required for either the *HELLO* or NXXXXXX portions.
        # No point trying if less data than that is in the buffer.
        while len(self._readbuffer) >= 7:
            if self._readbuffer.startswith(HELLO):
                if not self._hello_received:
                    _LOGGER.info("Hello message successfully received from unit")
                    self._readbuffer = self._readbuffer[len(HELLO) :]
                else:
                    _LOGGER.error(
                        "Hello message received more than once! Has the unit reset "
                        "somehow?"
                    )
            elif self._readbuffer.startswith(START_MARKER):
                if match := re.match(r"N(\d{6})(\[.*?\])", self._readbuffer.decode()):
                    # First match is sequence number
                    # Second match is the JSON status to be parsed. Note that the match
                    # requires the closing bracket to be present, to ensure we have a
                    # complete status.
                    self._last_received_sequence_num = int(match.group(1)[1:])
                    _LOGGER.debug(
                        "Received sequence number %d", self._last_received_sequence_num
                    )
                    if (self._command_wait and (self._last_received_sequence_num >= self._command_sequence)):
                        self._command_wait = False
                        _LOGGER.debug("Command wait end")

                    try:
                        json_status = json.loads(
                            self._readbuffer[match.start(2) : match.end(2)]
                        )
                        self._status_queue.put(json_status)
                    except json.JSONDecodeError:
                        _LOGGER.error("Could not parse JSON data")

                    self._readbuffer = self._readbuffer[match.end() :]
                else:
                    _LOGGER.debug("Did not match regexp: %s", self._readbuffer)
            # Something has already gone wrong, but maybe we can recover by looking for
            # the next marker.
            elif match := re.match(r"N(\d{6})", self._readbuffer.decode()):
                # Cut everything before the NXXXXXX pattern.
                _LOGGER.warning("Error parsing data, attempting recovery")
                _LOGGER.debug("Discarded %s", self._readbuffer[: match.start(1) - 1])
                self._readbuffer = self._readbuffer[match.start(1) :]
            else:
                _LOGGER.error(
                    "Buffer does not start with '*HELLO*' or 'N'. Something hasn't "
                    "parsed correctly, reconnecting"
                )
                _LOGGER.debug("Current buffer: %s", self._readbuffer)
                self._update_socket_state(RinnaiConnectionState.ERROR)

    def _create_socket_and_connect(self) -> None:
        #time.sleep(self._connection_reconnect_delay_seconds)
        #self._update_socket_state(RinnaiConnectionState.CONNECTING)
        
        while (
            self._socketstate == RinnaiConnectionState.IDLE
            and not self._thread_exit_flag
        ):
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.bind((self._udp_address, self._udp_port))
                data, addr = self._socket.recvfrom(1024)
                Rinnai = b'Rinnai_NBW2_Module'                                         
                if data.startswith(Rinnai):                                             
                    _LOGGER.debug("Broadcast data: %s", data.hex())                                          
                    _LOGGER.debug("Broadcast received from address: %s", addr[0])                                              
                    self._update_socket_state(RinnaiConnectionState.CONNECTING)
            except OSError as e:
                self._update_socket_state(RinnaiConnectionState.ERROR)
                _LOGGER.error("Unexpected broadcast error: %s", e)
                
        # If an old socket exists, try and clean it up.
        if self._socket is not None:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
            except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                # It's not worth reporting anything here as we already knew the socket
                # was a bit broken.
                pass

        while (
            self._socketstate != RinnaiConnectionState.CONNECTED
            and not self._thread_exit_flag
        ):
            try:
                # Set up the socket and update the state
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.settimeout(5)
                self._socket.connect((self._ip_address, self._port))

                # If we've made it to here, we connected successfully.
                self._update_socket_state(RinnaiConnectionState.CONNECTED)

                # Reset the timestamps and command sequence number
                self._last_command_time = time.time()
                self._last_received_time = self._last_command_time
                self._command_sequence = 1

                # Switch to non-blocking mode.
                self._socket.settimeout(0)

            except ConnectionRefusedError:
                self._update_socket_state(RinnaiConnectionState.REFUSED)
                sleep(5)
            except TimeoutError:
                self._update_socket_state(RinnaiConnectionState.TIMEOUT)
                sleep(5)
            except (ConnectionError, BlockingIOError, InterruptedError):
                # All of these things could be transient, so try again after a
                # small wait.
                sleep(10)
            except OSError as e:
                self._update_socket_state(RinnaiConnectionState.ERROR)
                _LOGGER.error('Unexpected connection error: "%s", will retry', e)
                sleep(10)
