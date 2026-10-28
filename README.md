
# pyrinnaitouch - python interface to Rinnai Touch Wifi Controllers

![Pylint](https://github.com/funtastix/pyrinnaitouch/workflows/Pylint/badge.svg)

This is a python interface to the [Rinnai Touch Wifi Controller](https://www.rinnai.com.au/online/controllers/heating-and-cooling-controllers/rinnai-touch-wi-fi/).

The specifications for the interface are contained in the [included pdf](./NBW2API_Iss1.3.pdf).

## Usage

This package is not a standalone application for end user implementation.

The aim of this package is to be used by software developers and integrators to implement
the Rinnai Touch Wifi interface on home automation platforms (principally Home Assistant )

## Change

The fork is based on pyrinnaitouch 0.13.4b1 and is versioned 0.13.4b1.post3, so Home Assistant replaces an already installed 0.13.4b1. Its connection handling is rewritten as described in How it works. Compared with 0.13.4b1:

Connection thread stopping silently. An unexpected error, such as a byte that isn't valid UTF-8 arriving from the bridge, used to stop the background connection thread for good. Status then froze, commands were never sent and no reconnect was attempted, while the integration still showed as connected. The thread now logs the error and reconnects.
Reconnecting too soon. The original reconnected straight after a timeout or error, which the bridge refuses and can hold against the client for minutes. Every connection now waits for the release delay and the bridge's broadcast.

Commands that didn't take effect. Commands used to be fire-and-forget. They are now confirmed against the status and retried, and commands already in effect are not sent.
Replayed commands. Commands queued while disconnected are discarded on reconnect instead of being sent in a burst minutes later.
Less traffic. A bare keepalive every 30 seconds replaces an idle command every 10 seconds, and Home Assistant only updates when the status changes.
Data parsing. Incoming data is parsed with a proper JSON decoder that copes with messages split across packets and with junk bytes.

## Credit

The [pescea interface](https://github.com/lazdavila/pescea) was used as a template and
for inspiration in developing this library (which got it off to a good start, so thanks!)
