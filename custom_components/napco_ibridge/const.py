"""Constants for napco_ibridge."""

from __future__ import annotations

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN: Final = "napco_ibridge"
MANUFACTURER: Final = "Napco"
MODEL: Final = "GEM-K1 (iBridge)"

PARALLEL_UPDATES: Final = 1

# Network protocol
TCP_PORT: Final = 8000
DISCOVERY_PORT: Final = 30717
DISCOVERY_PACKET: Final = bytes([0xFF, 0x04, 0x02, 0xFB])
DISCOVERY_RESPONSE_LENGTH: Final = 84
DISCOVERY_TIMEOUT_SEC: Final = 2.0
CONNECT_TIMEOUT_SEC: Final = 5.0
STATUS_POLL_INTERVAL_SEC: Final = 1.0
FIRST_STATUS_TIMEOUT_SEC: Final = 5.0

# Connection supervision. The panel answers each 1 s status poll, so a silent
# link for STALE_CONNECTION_TIMEOUT_SEC means the connection is dead (covers
# half-open sockets that never raise an error).
STALE_CONNECTION_TIMEOUT_SEC: Final = 10.0
RECONNECT_INITIAL_DELAY_SEC: Final = 1.0
RECONNECT_MAX_DELAY_SEC: Final = 60.0

# Config entry keys
CONF_HOST: Final = "host"
CONF_CODE: Final = "code"

# Arm state values published by client
ARM_STATE_DISARM: Final = "DISARM"
ARM_STATE_STAY: Final = "STAY"
ARM_STATE_AWAY: Final = "AWAY"
ARM_STATE_NIGHT: Final = "NIGHT"
ARM_STATE_ARMING_STAY: Final = "ARMING_STAY"
ARM_STATE_ARMING_AWAY: Final = "ARMING_AWAY"
ARM_STATE_ARMING_NIGHT: Final = "ARMING_NIGHT"
ARM_STATE_NOT_READY: Final = "NOT_READY"

ARM_STATES: Final = (
    ARM_STATE_DISARM,
    ARM_STATE_STAY,
    ARM_STATE_AWAY,
    ARM_STATE_NIGHT,
    ARM_STATE_ARMING_STAY,
    ARM_STATE_ARMING_AWAY,
    ARM_STATE_ARMING_NIGHT,
    ARM_STATE_NOT_READY,
)
