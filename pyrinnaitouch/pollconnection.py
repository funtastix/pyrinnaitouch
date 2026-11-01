"""Handle connectivity with the N-BW2 module and connection reporting.

The connection behaviour follows jerryzou/rinnai_touch_climate (MIT licence),
https://github.com/jerryzou/rinnai_touch_climate, which in turn copies the
Homebridge plugin mantorok1/homebridge-rinnai-touch-platform. The module is
an embedded device with a single TCP slot and is unforgiving about how that
slot is used:

* While no client is connected it broadcasts on UDP port 50000 about once a
  second. The broadcasts stop when a client connects and resume roughly 7 s
  after it disconnects; a connection attempt before then is refused. It can
  refuse a client for minutes if that client reconnects within about a
  second of closing.
* So every connect, first or reconnect, waits until at least 10 s have passed
  since this process last closed a connection to the module, and then for a
  broadcast from the module saying its slot is free.
* The connection counts as up from the first valid status frame, not the TCP
  handshake. The module streams status about once a second, so no data for
  5 s means the connection is dead.
* Commands go one at a time, numbered after the module's last sequence
  number (1-254, then back to 1). Each is confirmed against the status
  stream, retried up to 3 times, and skipped if the status already shows it.
* A bare sequence number is sent as a keepalive every 30 s. That keeps a margin
  even at the shortest TCP timeout the module allows (1 minute; default 5).
"""

from collections import defaultdict
from dataclasses import dataclass
import enum
import json
import logging
from queue import Empty, SimpleQueue
import socket
import threading
import time
from typing import Any, Dict, Optional

from .framing import Frame, FrameParser

_LOGGER = logging.getLogger(__name__)

TCP_PORT = 27847
UDP_PORT = 50000
BROADCAST_MAGIC = b"Rinnai_NBW2_Module"

# All times in seconds.
SETTLE_DELAY = 10.0  # minimum gap between closing a connection and the next connect
BROADCAST_FALLBACK = 300.0  # connect without a broadcast after waiting this long
CONNECT_TIMEOUT = 5.0
FIRST_STATUS_TIMEOUT = 10.0
IDLE_TIMEOUT = 5.0
KEEPALIVE_INTERVAL = 30.0
COMMAND_TIMEOUT = 10.0
COMMAND_ATTEMPTS = 3
CONNECT_ATTEMPTS = 3  # quick retries before backing off
RETRY_DELAY = 0.5
BACKOFF_DELAY = 60.0
RECONNECT_DELAY = 2.0

States = Dict[str, Dict[str, Dict[str, str]]]


class RinnaiConnectionState(enum.Enum):
    """Possible connection states for this class."""

    IDLE = 1
    CONNECTING = 2
    CONNECTED = 3
    REFUSED = 4
    TIMEOUT = 5
    ERROR = 6
    WAITING = 7  # waiting for the module to broadcast that its slot is free


def next_sequence(last: int) -> int:
    """Return the sequence number after ``last`` (1-254, as the Homebridge plugin does)."""
    return (last + 1) % 255 or 1


def parse_states(command: str) -> Optional[States]:
    """Return a command's values as nested dicts, or None if it isn't one."""
    try:
        states = json.loads(command)
    except ValueError:
        return None
    if not isinstance(states, dict):
        return None
    for groups in states.values():
        if not isinstance(groups, dict):
            return None
        for values in groups.values():
            if not isinstance(values, dict) or not all(
                isinstance(value, str) for value in values.values()
            ):
                return None
    return states


@dataclass
class _PendingCommand:
    """A command sent to the module and not yet confirmed."""

    command: str
    states: Optional[States]
    sequence: int
    sent_at: float
    attempt: int
    echoed: bool = False


class RinnaiPollConnection:  # pylint: disable=too-many-instance-attributes
    """Manage the connection to the unit in a background thread."""

    # Global map of IP addresses currently in use. Only used to track when multiple
    # connections are attempted, since we know how poorly the hardware handles this.
    clients = defaultdict(int)

    # Monotonic time each module's last connection was closed, shared across
    # instances so that a reloaded integration waits for the old connection's
    # release.
    _last_closed: Dict[str, float] = {}

    def __init__(self, ip_address: str, status_queue: SimpleQueue) -> None:
        """Initialise the connection object."""
        self._ip_address = ip_address
        self._port = TCP_PORT
        self._udp_port = UDP_PORT

        # Queue of commands (each as a string) to send to the unit.
        self._sendqueue = SimpleQueue()

        # Checked in all manner of places, should only be set on shutdown.
        self._thread_exit_flag = False
        self._stopped = False

        # These don't get created until start_thread is called
        self._socket: Optional[socket.socket] = None
        self._socketthread: Optional[threading.Thread] = None
        self._socketstate = RinnaiConnectionState.IDLE

        # List of functions to call whenever _socketstate changes
        # Provides a single argument, RinnaiConnectionState
        self._connection_state_handlers = []

        # Outbound queue of JSON status
        self._status_queue = status_queue

        # Per-connection state, reset in _session
        self._parser = FrameParser()
        self._status_data: Dict[str, Any] = {}
        self._last_raw: Optional[str] = None
        self._last_received_sequence_num = 0
        self._last_received_time = 0.0
        self._last_send_time = 0.0
        self._pending: Optional[_PendingCommand] = None

        # Broadcasting addresses we've already warned about
        self._warned_hosts = set()

        # Checked last, so that every attribute exists for __del__ if this raises.
        RinnaiPollConnection.clients[ip_address] += 1
        if RinnaiPollConnection.clients[ip_address] > 1:
            _LOGGER.error(
                "Attempting duplicate connection to unit at %s, which the hardware "
                "will not support",
                ip_address,
            )
            raise RuntimeError("Cannot have two connections to the same address")

        _LOGGER.debug("Poll connection inited")

    def send_command(self, command):
        """Queue a command to be sent to the unit."""
        self._sendqueue.put(command)

    def _discard_queued_commands(self) -> None:
        """Empty the command queue, logging anything that is dropped."""
        dropped = 0
        while True:
            try:
                self._sendqueue.get_nowait()
                dropped += 1
            except Empty:
                break
        if dropped:
            _LOGGER.warning(
                "Discarded %d command(s) queued while disconnected", dropped
            )

    def __del__(self):
        """Destructor to ensure the thread is stopped and the socket closed."""
        self.stop_thread()

    def stop_thread(self) -> None:
        """Stop the thread, close the socket, and decrement the connection tracker."""
        if self._stopped:
            return
        self._stopped = True

        if self._socketthread is not None and self._socketthread.is_alive():
            self._thread_exit_flag = True
            # Every wait in the thread checks the exit flag at least once a second,
            # except a TCP connect in progress, which gives up after CONNECT_TIMEOUT.
            self._socketthread.join(CONNECT_TIMEOUT + 2)
            if self._socketthread.is_alive():
                _LOGGER.error("Could not stop monitoring thread")
                # Attempt to daemonise the thread since this should still allow the
                # process to exit.
                self._socketthread.daemon = True
            else:
                self._socketthread = None
                _LOGGER.debug("Monitoring thread confirmed stopped")

        self._close_socket()

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
                except Exception as e:  # pylint: disable=broad-exception-caught
                    # A failing handler must not take down the connection thread.
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

    # Connection cycle

    def _event_loop(self) -> None:
        """Thread that keeps one connection to the unit, reconnecting as needed."""
        _LOGGER.debug("Starting event loop within thread")
        failures = 0
        while not self._thread_exit_flag:
            reached_connected = False
            try:
                if self._wait_for_slot():
                    reached_connected = self._session()
            except ConnectionRefusedError:
                _LOGGER.warning("Connection refused by unit at %s", self._ip_address)
                self._update_socket_state(RinnaiConnectionState.REFUSED)
            except (TimeoutError, socket.timeout) as err:
                _LOGGER.warning(
                    "Timed out connecting to unit at %s: %s", self._ip_address, err
                )
                self._update_socket_state(RinnaiConnectionState.TIMEOUT)
            except OSError as err:
                _LOGGER.warning(
                    "Connection error with unit at %s: %s", self._ip_address, err
                )
                self._update_socket_state(RinnaiConnectionState.ERROR)
            except Exception:  # pylint: disable=broad-exception-caught
                # Never let an unexpected error kill this thread: without it there are
                # no status updates, no commands sent and no reconnects.
                _LOGGER.exception("Unexpected error in connection thread, reconnecting")
                self._update_socket_state(RinnaiConnectionState.ERROR)
            finally:
                self._close_socket()

            if self._thread_exit_flag:
                break
            if reached_connected:
                failures = 0
                delay = RECONNECT_DELAY
            else:
                failures += 1
                if failures % CONNECT_ATTEMPTS:
                    delay = RETRY_DELAY
                else:
                    delay = BACKOFF_DELAY
                    _LOGGER.warning(
                        "%d connection attempts failed; next try in %.0f s",
                        failures,
                        delay,
                    )
            self._sleep(delay)
        _LOGGER.debug("Event loop exiting")

    def _sleep(self, seconds: float) -> None:
        """Sleep, but wake within half a second if the thread is told to exit."""
        end = time.monotonic() + seconds
        while not self._thread_exit_flag:
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.5))

    def _wait_for_slot(self) -> bool:
        """Wait until the module broadcasts that its TCP slot is free.

        Returns False if the thread is exiting.
        """
        self._update_socket_state(RinnaiConnectionState.WAITING)

        closed = RinnaiPollConnection._last_closed.get(self._ip_address)
        if closed is not None:
            wait = closed + SETTLE_DELAY - time.monotonic()
            if wait > 0:
                _LOGGER.debug(
                    "Waiting %.1f s for the module to release the last connection",
                    wait,
                )
                self._sleep(wait)

        try:
            udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                udpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            udpsock.settimeout(1.0)
            udpsock.bind(("", self._udp_port))
        except OSError as err:
            _LOGGER.warning(
                "Cannot listen for broadcasts on UDP port %d (%s); connecting "
                "without waiting for one",
                self._udp_port,
                err,
            )
            return not self._thread_exit_flag

        deadline = time.monotonic() + BROADCAST_FALLBACK
        with udpsock:
            while not self._thread_exit_flag:
                if time.monotonic() > deadline:
                    _LOGGER.warning(
                        "No broadcast from the unit at %s for %.0f s; connecting "
                        "without one. Another client (such as the Rinnai app) may be "
                        "connected, or broadcasts may not be reaching this host",
                        self._ip_address,
                        BROADCAST_FALLBACK,
                    )
                    return True
                try:
                    data, addr = udpsock.recvfrom(1024)
                except (TimeoutError, socket.timeout):
                    continue
                if not data.startswith(BROADCAST_MAGIC):
                    continue
                if addr[0] == self._ip_address:
                    # Bytes 32-33 hold the module's TCP port, high byte first.
                    if len(data) >= 34:
                        self._port = int.from_bytes(data[32:34], "big") or TCP_PORT
                    _LOGGER.debug(
                        "Broadcast received from %s; its slot is free", addr[0]
                    )
                    return True
                if addr[0] not in self._warned_hosts:
                    self._warned_hosts.add(addr[0])
                    _LOGGER.warning(
                        "A Rinnai Touch module is broadcasting from %s, but this "
                        "connection is set up for %s; has the module's IP address "
                        "changed?",
                        addr[0],
                        self._ip_address,
                    )
        return False

    def _session(self) -> bool:
        """Run one TCP connection; return True if it got to connected.

        Errors before the first status frame propagate, so the caller counts a
        failed attempt. Losing an established connection returns.
        """
        self._update_socket_state(RinnaiConnectionState.CONNECTING)
        _LOGGER.debug("Connecting to %s:%d", self._ip_address, self._port)
        self._socket = socket.create_connection(
            (self._ip_address, self._port), timeout=CONNECT_TIMEOUT
        )
        # Short timeout so the loop below also gets to commands and keepalives.
        self._socket.settimeout(0.1)

        self._parser = FrameParser()
        self._status_data = {}
        self._last_raw = None
        self._pending = None
        opened_at = time.monotonic()
        self._last_received_time = opened_at
        self._last_send_time = opened_at
        connected = False

        while not self._thread_exit_flag:
            try:
                data = self._socket.recv(4096)
            except (TimeoutError, socket.timeout):
                data = None
            except OSError as err:
                if not connected:
                    raise
                self._lost(f"socket error: {err}", RinnaiConnectionState.ERROR)
                return True

            now = time.monotonic()
            if data is not None:
                if not data:
                    if not connected:
                        raise ConnectionError("the module closed the connection")
                    self._lost(
                        "the module closed the connection", RinnaiConnectionState.IDLE
                    )
                    return True
                self._last_received_time = now
                for frame in self._parser.feed(data):
                    self._handle_frame(frame)
                    if not connected:
                        connected = True
                        self._on_connected()

            if not connected:
                if now - opened_at > FIRST_STATUS_TIMEOUT:
                    raise TimeoutError("no status received after connecting")
                continue

            if now - self._last_received_time > IDLE_TIMEOUT:
                self._lost(f"no data for {IDLE_TIMEOUT:g} s", RinnaiConnectionState.TIMEOUT)
                return True

            try:
                self._process_commands(now)
            except OSError as err:
                self._lost(f"sending failed: {err}", RinnaiConnectionState.ERROR)
                return True
        return connected

    def _on_connected(self) -> None:
        # Drop commands queued while we were disconnected. They were issued
        # against a stale status and replaying them now would act on the
        # unit long after the user asked.
        self._discard_queued_commands()
        _LOGGER.info("Connected to the Rinnai Touch module at %s", self._ip_address)
        self._update_socket_state(RinnaiConnectionState.CONNECTED)

    def _lost(self, reason: str, state: RinnaiConnectionState) -> None:
        _LOGGER.warning(
            "Lost the connection to the Rinnai Touch module at %s: %s; reconnecting",
            self._ip_address,
            reason,
        )
        self._update_socket_state(state)

    def _close_socket(self) -> None:
        """Close the TCP socket, if any, and note when for the settle delay."""
        sock, self._socket = self._socket, None
        self._pending = None
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            _LOGGER.debug("Socket shutdown failed, likely was not connected")
        try:
            sock.close()
        except OSError:
            _LOGGER.debug("Socket close failed, likely was not open")
        RinnaiPollConnection._last_closed[self._ip_address] = time.monotonic()

    # Status

    def _handle_frame(self, frame: Frame) -> None:
        """Take in a status frame and pass it on if it changed."""
        self._last_received_sequence_num = frame.sequence
        if self._pending is not None and frame.sequence == self._pending.sequence:
            self._pending.echoed = True

        # Every frame carries the full status, so replace rather than merge.
        data: Dict[str, Any] = {}
        for item in frame.status:
            for group1, value in item.items():
                if isinstance(value, dict):
                    data[group1] = value
        self._status_data = data

        if frame.raw != self._last_raw:
            self._last_raw = frame.raw
            self._status_queue.put(frame.status)

    def _get(self, group1: str, group2: str, key: str) -> Optional[str]:
        """Return one value from the latest status, or None if not reported."""
        groups = self._status_data.get(group1)
        values = groups.get(group2) if isinstance(groups, dict) else None
        value = values.get(key) if isinstance(values, dict) else None
        return value if isinstance(value, str) else None

    def _iter_states(self, states: States):
        for group1, groups in states.items():
            for group2, values in groups.items():
                for key, value in values.items():
                    yield self._get(group1, group2, key), value

    def _has_states(self, states: States) -> bool:
        """Return True if the status already shows every value in a command."""
        return all(current == value for current, value in self._iter_states(states))

    def _reports_states(self, states: States) -> bool:
        """Return True if the status reports every key a command sets."""
        return all(current is not None for current, _ in self._iter_states(states))

    # Commands

    def _process_commands(self, now: float) -> None:
        """Confirm the pending command, or send the next one or a keepalive."""
        pending = self._pending
        if pending is not None:
            if self._is_confirmed(pending):
                _LOGGER.debug("Command %d confirmed", pending.sequence)
                self._pending = None
            elif now - pending.sent_at > COMMAND_TIMEOUT:
                if pending.attempt < COMMAND_ATTEMPTS:
                    _LOGGER.warning(
                        "The module did not confirm %s (attempt %d of %d), resending",
                        pending.command,
                        pending.attempt,
                        COMMAND_ATTEMPTS,
                    )
                    self._send_command_now(
                        pending.command, pending.states, pending.attempt + 1
                    )
                else:
                    _LOGGER.error(
                        "The module did not confirm %s after %d attempts, giving up",
                        pending.command,
                        COMMAND_ATTEMPTS,
                    )
                    self._pending = None
            if self._pending is not None:
                return

        try:
            command = self._sendqueue.get_nowait()
        except Empty:
            if now - self._last_send_time >= KEEPALIVE_INTERVAL:
                sequence = next_sequence(self._last_received_sequence_num)
                _LOGGER.debug("Sending keepalive %d", sequence)
                self._send(f"N{sequence:06d}")
            return

        states = parse_states(command)
        if states is not None and self._has_states(states):
            _LOGGER.debug("Skipping %s: already in that state", command)
            return
        self._send_command_now(command, states, 1)

    def _is_confirmed(self, pending: _PendingCommand) -> bool:
        if pending.states is not None and self._reports_states(pending.states):
            return self._has_states(pending.states)
        # The status doesn't report these values, so the best we can do is the
        # module echoing our sequence number.
        return pending.echoed

    def _send_command_now(
        self, command: str, states: Optional[States], attempt: int
    ) -> None:
        sequence = next_sequence(self._last_received_sequence_num)
        _LOGGER.debug("Sending command %d: %s", sequence, command)
        self._send(f"N{sequence:06d}{command}")
        self._pending = _PendingCommand(
            command, states, sequence, time.monotonic(), attempt
        )

    def _send(self, payload: str) -> None:
        sock = self._socket
        if sock is None:
            raise ConnectionError("not connected")
        sock.sendall(payload.encode())
        self._last_send_time = time.monotonic()
