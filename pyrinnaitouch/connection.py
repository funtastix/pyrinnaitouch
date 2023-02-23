"""Handle connectivity"""
import logging
import socket
import time
import queue

_LOGGER = logging.getLogger(__name__)

class RinnaiConnection:
    """Manage the connection to the unit"""

    clients = {}

    def __init__(self, ip_address: str) -> None:
        self._touch_ip = ip_address
        self._touch_port = 27847
        self._send_sequence = 1
        self._client = None
        self._lastclosed = 0
        self._jsonerrors = 0
        self._senderqueue = queue.Queue()
        if ip_address not in RinnaiConnection.clients:
            RinnaiConnection.clients[ip_address] = self._client
        else:
            self._client = RinnaiConnection.clients[ip_address]

    def __str__(self) -> str:
        return self._client.__str__() + "/" + str(self._client._closed) # pylint: disable=protected-access

    def update_send_sequence(self, seq: int) -> None:
        """Determine new send sequence"""
        if seq >= 255:
            seq = 0
        else:
            seq = seq + 1
        self._send_sequence = seq

    def shutdown(self) -> None:
        """Shut down the connection"""
        try:
            self._client.shutdown(socket.SHUT_RDWR)
            self._client.close()
            self._lastclosed = time.time()
        except (OSError, ConnectionError) as ocerr:
            _LOGGER.debug("Exception during client shutdown %s", ocerr)

    def send(self, message: bytes) -> None:
        """Send a message to the unit"""
        self._client.sendall(message)

    def get_queued_command(self) -> bytes:
        """Non-blocking method to retrieve any queued commands. May throw queue.Empty exception"""
        return self._senderqueue.get(False)

    def receive_data(self) -> bytes:
        """Receive data from the unit"""
        return self._client.recv(8096)

    def log_json_error(self) -> None:
        """Log that a JSON parsing error has occurred from data received on this connection"""
        self._jsonerrors = self._jsonerrors + 1

    def renew_connection(self) -> bool:
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
                RinnaiConnection.clients[self._touch_ip] = self._client
                _LOGGER.debug("Connected to %s", self._client.getpeername())
                return True
            except ConnectionRefusedError as crerr:
                _LOGGER.debug("Error during renewConnection %s", crerr)
            except ConnectionError as cerr:
                _LOGGER.debug("Error during renewConnection %s", cerr)
            except Exception as eerr: # pylint: disable=broad-except
                _LOGGER.debug("Error during renewConnection %s", eerr)
        return False

    def connect_to_touch(self, touch_ip: str, port: int) -> None:
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
            #should really take a few hours break to recover!
            raise crerr

    def dispatch_command(self, cmd: str) -> None:
        """Dispatch the command via the sender queue."""
        seq = str(self._send_sequence).zfill(6)
        _LOGGER.debug("Sending command: %s", "N" + seq + cmd)
        self._senderqueue.put(("N" + seq + cmd).encode())
