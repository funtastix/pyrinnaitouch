"""Receiver Thread to continually get data from the connection"""
import time
import json
import re
import logging
import queue
from .connection import RinnaiConnection
from .util import daemonthreaded

_LOGGER = logging.getLogger(__name__)


class RinnaiReceiver:
    """Receiver to handle receiving and sending data to the unit"""

    def __init__(self, connection: RinnaiConnection, receiverqueue: queue) -> None:
        self._connection = connection
        self._receiverqueue = receiverqueue
        self._lastdata = ""
        self._counter = 0

    @daemonthreaded
    def receiver(self) -> None:
        """Main send and receive thread to process and send messages."""
        while True:
            self._counter += 1
            # send next message if any
            try:
                message = self._connection.get_queued_command()
                if message.decode() == "sys.exit":
                    self._receiverqueue.put('{"sys.exit":true}')
                    break
                self._connection.send(message)
                _LOGGER.debug("Fired off command: (%s)", message.decode())
                time.sleep(0.05)
                self._counter = 0
            except ConnectionError as connerr:
                _LOGGER.error("Couldn't send command (connection): (%s)", repr(connerr))
                self._connection.renew_connection()
            except queue.Empty:
                pass

            # send empty command ever so often
            try:
                self.send_empty_command()
            except (ConnectionError, TimeoutError, OSError) as err:
                _LOGGER.error(
                    "Couldn't send empty command (connection): (%s)", repr(err)
                )

            # receive status
            try:
                self.receive_data()
            except ConnectionError as connerr:
                _LOGGER.error(
                    "Couldn't decode JSON (connection), skipping (%s)", repr(connerr)
                )
                self._connection.shutdown()
                self._connection.renew_connection()
            except (OSError, TimeoutError) as timeouterr:
                _LOGGER.error(
                    "Socket timed out, renewing connection (%s)", repr(timeouterr)
                )
                self._connection.shutdown()
                self._connection.renew_connection()
            except AttributeError as atterr:
                _LOGGER.error(
                    "Couldn't decode JSON (probably HELLO), skipping (%s)", repr(atterr)
                )
        _LOGGER.debug("Shutting down the receiver thread")

    def receive_data(self) -> None:
        """handle receiving and high level parsing of data."""
        # pylint: disable=anomalous-backslash-in-string
        temp = self._connection.receive_data()
        if temp:
            # _LOGGER.debug("Received data: (%s)", temp.decode())
            data = temp
            if str(data) == "*HELLO*":
                _LOGGER.debug(
                    "Received friendly HELLO from unit,not processing this one"
                )
            else:
                exp = re.search("^.*([0-9]{6}).*(\[[^\[]*\])[^]]*$", str(data))
                seq = int(exp.group(1))
                self._connection.update_send_sequence(seq)
                json_str = exp.group(2)
                if json_str != self._lastdata:
                    _LOGGER.debug("Sequence: %s Json: %s", seq, json_str)
                    status_json = json.loads(json_str)
                    self._receiverqueue.put(status_json)
                    self._lastdata = json_str

    def send_empty_command(self) -> None:
        """Send empty command every 10 receive cycles."""
        if self._counter > 10:
            try:
                cmd = "NA"
                self._connection.send(cmd.encode())
                self._counter = 0
            except ConnectionError as connerr:
                _LOGGER.error("Couldn't send command (connection): (%s)", repr(connerr))
                self._connection.renew_connection()
