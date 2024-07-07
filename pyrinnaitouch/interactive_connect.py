from pollconnection import RinnaiPollConnection, RinnaiConnectionState
import logging
from typing import Final

_LOGGER = logging.getLogger(__name__)


def socket_state_handler(state: RinnaiConnectionState):
    _LOGGER.info("New state: %s", state)


# def main():
FORMAT_DATE: Final = "%Y-%m-%d"
FORMAT_TIME: Final = "%H:%M:%S"
FORMAT_DATETIME: Final = f"{FORMAT_DATE} {FORMAT_TIME}"

fmt = "%(asctime)s.%(msecs)03d %(levelname)s (%(threadName)s) [%(name)s :%(lineno)d] %(message)s"
logging.basicConfig(format=fmt, datefmt=FORMAT_DATETIME, level=logging.DEBUG)


_LOGGER.info("Info is on")
_LOGGER.debug("Debug logging is on")


# if __name__ == "__main__":
#    main()
conn = RinnaiPollConnection("192.168.1.58")

conn.register_socket_state_handler(socket_state_handler)

conn.start_thread()
