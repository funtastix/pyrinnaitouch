"""Split the module's TCP byte stream into status frames.

Ported from jerryzou/rinnai_touch_climate (MIT licence),
https://github.com/jerryzou/rinnai_touch_climate

The module sends ``N`` + a 6-digit sequence number + a JSON array, with no
delimiter between frames, and TCP may cut a frame anywhere. Bytes are
buffered and only complete frames are returned; a partial frame waits for
the next ``feed()``. Garbage is skipped up to the next frame start.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re
from typing import Any, Dict, List, Optional

_LOGGER = logging.getLogger(__name__)

HELLO = b"*HELLO*"

# A frame starts with N and six digits; a status frame continues with "[".
_FRAME_START = re.compile(rb"N(\d{6})")
_STATUS_START = re.compile(rb"N\d{6}\[")

# A status frame is ~2 KB. Anything far bigger without a parsable frame is
# not going to become one.
MAX_BUFFER = 64 * 1024

_DECODER = json.JSONDecoder()


@dataclass(frozen=True)
class Frame:
    """One complete status message."""

    sequence: int
    status: List[Dict[str, Any]]
    raw: str


class FrameParser:
    """Incremental parser for the module's status stream."""

    def __init__(self) -> None:
        """Start with an empty buffer."""
        self._buffer = bytearray()

    def __len__(self) -> int:
        """Return the number of buffered, not yet parsed bytes."""
        return len(self._buffer)

    def feed(self, data: bytes) -> List[Frame]:
        """Add received bytes and return every complete frame in order."""
        self._buffer += data
        frames: List[Frame] = []
        while (frame := self._next_frame()) is not None:
            frames.append(frame)
        if len(self._buffer) > MAX_BUFFER:
            _LOGGER.debug("Dropping %d unparsable bytes", len(self._buffer))
            self._buffer.clear()
        return frames

    def _next_frame(self) -> Optional[Frame]:
        """Pop one frame off the buffer, or return None to wait for more."""
        buf = self._buffer
        while True:
            # The module greets a new client with *HELLO*; it is not a frame.
            hello = buf.find(HELLO)
            if hello != -1:
                _LOGGER.debug("Hello message received from unit")
                del buf[hello : hello + len(HELLO)]
                continue

            match = _FRAME_START.search(buf)
            if match is None:
                # Keep only what could be the start of "N000000" or "*HELLO*".
                del buf[:-6]
                return None
            sequence = int(match.group(1))
            if match.start() > 0:
                _LOGGER.debug("Skipping %d bytes of garbage", match.start())
                del buf[: match.start()]

            body = 7  # len("N000000")
            if len(buf) == body:
                return None
            if buf[body : body + 1] != b"[":
                # A bare sequence number without a status: nothing to parse.
                del buf[:body]
                continue

            # latin-1 maps every byte to a character, so decoding can't fail.
            text = buf.decode("latin-1")
            try:
                status, end = _DECODER.raw_decode(text, body)
            except json.JSONDecodeError:
                following = _STATUS_START.search(buf, 1)
                if following is None:
                    return None  # most likely incomplete: wait for more bytes
                _LOGGER.debug("Dropping a malformed frame: %r", text[:80])
                del buf[: following.start()]
                continue

            raw = text[body:end]
            del buf[:end]
            if not isinstance(status, list) or not all(
                isinstance(item, dict) for item in status
            ):
                _LOGGER.debug("Ignoring a frame that is not a status list: %r", raw)
                continue
            return Frame(sequence, status, raw)
