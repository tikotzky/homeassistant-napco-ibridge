"""Async client for the Napco iBridge GEM-K1 keypad protocol.

Port of the JavaScript reference in ../../node-napco-ibridge/ibridge.js and
discover-panel.js. Speaks the panel's binary protocol over TCP:8000 (status
polling + button presses) and the UDP:30717 discovery broadcast.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
from dataclasses import dataclass, field
import socket
import time
from typing import Final

from custom_components.napco_ibridge.const import (
    ARM_STATE_ARMING_AWAY,
    ARM_STATE_ARMING_NIGHT,
    ARM_STATE_ARMING_STAY,
    ARM_STATE_AWAY,
    ARM_STATE_DISARM,
    ARM_STATE_NIGHT,
    ARM_STATE_NOT_READY,
    ARM_STATE_STAY,
    CONNECT_TIMEOUT_SEC,
    DISCOVERY_PACKET,
    DISCOVERY_PORT,
    DISCOVERY_RESPONSE_LENGTH,
    DISCOVERY_TIMEOUT_SEC,
    FIRST_STATUS_TIMEOUT_SEC,
    LOGGER,
    RECONNECT_INITIAL_DELAY_SEC,
    RECONNECT_MAX_DELAY_SEC,
    STALE_CONNECTION_TIMEOUT_SEC,
    STATUS_POLL_INTERVAL_SEC,
    TCP_PORT,
)


class NapcoIbridgeApiClientError(Exception):
    """Base exception for Napco client errors."""


class NapcoIbridgeApiClientCommunicationError(NapcoIbridgeApiClientError):
    """Raised on network / protocol failures."""


class NapcoIbridgeApiClientAuthenticationError(NapcoIbridgeApiClientError):
    """Reserved for future use; the iBridge has no auth."""


BUTTONS: Final[dict[str, int]] = {
    "ButtonBreak": 0,
    "Button1": 1,
    "Button2": 2,
    "Button3": 3,
    "Button4": 4,
    "Button5": 5,
    "Button6": 6,
    "Button7": 7,
    "Button8": 8,
    "Button9": 9,
    "Button0": 10,
    "ButtonStar": 11,
    "ButtonStartBreak": 12,
    "ButtonShift1": 17,
    "ButtonShift2": 18,
    "ButtonShift3": 19,
    "ButtonShift4": 20,
    "ButtonShift5": 21,
    "ButtonShift6": 22,
    "ButtonShift7": 23,
    "ButtonShift8": 24,
    "ButtonShift9": 25,
    "ButtonShift0": 26,
    "ButtonOnOffEnter": -128,
    "ButtonReset": -127,
    "ButtonNext": -126,
    "ButtonYes": -126,
    "ButtonInteriorStay": -126,
    "ButtonPrev": -125,
    "ButtonNo": -125,
    "ButtonInstantAway": -125,
    "ButtonBypass": -124,
    "ButtonF": -123,
    "ButtonA": -122,
    "ButtonP": -121,
    "ButtonFunctionMenu": -120,
    "ButtonOnOffEnter2": -112,
    "ButtonInteriorStayLong": -101,
    "ButtonInstantAwayLong": -100,
    "ButtonZoneDirectory": -32,
    "ButtonLongPrefix": -16,
}

DIGIT_BUTTONS: Final = (
    "Button0",
    "Button1",
    "Button2",
    "Button3",
    "Button4",
    "Button5",
    "Button6",
    "Button7",
    "Button8",
    "Button9",
)

_PANEL_GEM_K1: Final = 73
_LED_STATES: Final = {
    1: "On",
    2: "SlowBlink",
    3: "Blip",
    4: "CadenceA",
    5: "CadenceB",
    6: "InstantBlink",
    7: "NAKSound",
}


@dataclass
class NapcoStatus:
    """Latest known panel state, merged from all observed frames."""

    arm_status: str = ARM_STATE_NOT_READY
    armed_led: str = "Off"
    status_led: str = "Off"
    trouble_led: str = "Off"
    fire_led: str = "Off"
    fire_trouble_led: str = "Off"
    bypass_led: str = "Off"
    sounder: str = "Off"
    text_line_1: str = ""
    text_line_2: str = ""
    area: int = 0
    cursor_row: int = 0
    cursor_column: int = 0
    raw: dict = field(default_factory=dict)


def _to_signed_byte(value: int) -> int:
    return value & 0xFF


def _append_checksum(payload: bytes) -> bytes:
    if len(payload) < 2:
        msg = "Invalid packet"
        raise NapcoIbridgeApiClientCommunicationError(msg)
    checksum = sum(b & 0xFF for b in payload)
    return payload + bytes([(checksum >> 8) & 0xFF, checksum & 0xFF])


def _status_buffer() -> bytes:
    return _append_checksum(bytes([0xB8, 0x00, 0x09, 0x00, 0x01, 0x49, 0x01]))


def _button_buffer(button_codes: list[int], sequence: int) -> bytes:
    length = len(button_codes) + 9
    header = bytes(
        [
            0xB7,
            (length >> 8) & 0xFF,
            length & 0xFF,
            0x00,
            (sequence + 1) & 0xFF,
            0x49,
            0x01,
        ],
    )
    body = bytes(_to_signed_byte(code) for code in button_codes)
    return _append_checksum(header + body)


def _led_from_byte(byte: int) -> str:
    return _LED_STATES.get(byte, "Off")


def _is_gem_k1_keypad_status(buffer: bytes) -> bool:
    return len(buffer) >= 32 and buffer[0] == 0xBB and buffer[5] == _PANEL_GEM_K1


def _is_keypad_text_update(buffer: bytes) -> bool:
    return buffer[3] == 2 and len(buffer) > 40


def _derive_arm_status(text1: str, text2: str, armed_led: str, status_led: str) -> str:
    is_armed = "ARMED" in (text1 or "") or "ARMED" in (text2 or "")
    if armed_led == "InstantBlink":
        return ARM_STATE_NIGHT if is_armed else ARM_STATE_ARMING_NIGHT
    if status_led == "CadenceB" and armed_led == "On":
        return ARM_STATE_STAY if is_armed else ARM_STATE_ARMING_STAY
    if status_led == "Off" and armed_led == "On":
        return ARM_STATE_AWAY if is_armed else ARM_STATE_ARMING_AWAY
    if status_led == "On" and armed_led == "Off":
        return ARM_STATE_DISARM
    return ARM_STATE_NOT_READY


def _decode_text(buffer: bytes, start: int, end: int) -> str:
    return buffer[start:end].decode("utf-8", errors="replace")


def _parse_frame(buffer: bytes) -> dict | None:
    """Parse one inbound TCP frame; return delta dict or None to ignore."""
    if not _is_gem_k1_keypad_status(buffer):
        return None
    if _is_keypad_text_update(buffer):
        return {
            "cursor_row": buffer[6],
            "cursor_column": buffer[7],
            "area": buffer[40] if len(buffer) == 43 else 0,
            "text_line_1": _decode_text(buffer, 8, 24),
            "text_line_2": _decode_text(buffer, 24, 40),
        }
    return {
        "fire_led": _led_from_byte(buffer[7]),
        "trouble_led": _led_from_byte(buffer[8]),
        "status_led": _led_from_byte(buffer[9]),
        "armed_led": _led_from_byte(buffer[10]),
        "fire_trouble_led": _led_from_byte(buffer[11]),
        "bypass_led": _led_from_byte(buffer[12]),
        "sounder": _led_from_byte(buffer[19]),
    }


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, future: asyncio.Future[str]) -> None:
        self._future = future
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore[assignment]
        sock = transport.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        transport.sendto(DISCOVERY_PACKET, ("255.255.255.255", DISCOVERY_PORT))  # type: ignore[attr-defined]

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        if len(data) != DISCOVERY_RESPONSE_LENGTH:
            return
        if not self._future.done():
            self._future.set_result(addr[0])

    def error_received(self, exc: Exception) -> None:
        if not self._future.done():
            self._future.set_exception(exc)


async def async_discover_panel(timeout: float = DISCOVERY_TIMEOUT_SEC) -> str:
    """Broadcast a discovery packet and return the first responding panel IP."""
    loop = asyncio.get_running_loop()
    future: asyncio.Future[str] = loop.create_future()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: _DiscoveryProtocol(future),
        local_addr=("0.0.0.0", DISCOVERY_PORT),
        family=socket.AF_INET,
        allow_broadcast=True,
    )
    try:
        async with asyncio.timeout(timeout):
            return await future
    except TimeoutError as err:
        msg = "Timed out waiting for panel discovery response"
        raise NapcoIbridgeApiClientCommunicationError(msg) from err
    finally:
        transport.close()


class NapcoIbridgeApiClient:
    """Persistent async client for a single Napco panel."""

    def __init__(self, host: str) -> None:
        self._host = host
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._sequence = 0
        self._status = NapcoStatus()
        self._listeners: list[Callable[[NapcoStatus], None]] = []
        self._connection_listeners: list[Callable[[bool], None]] = []
        self._reader_task: asyncio.Task[None] | None = None
        self._poller_task: asyncio.Task[None] | None = None
        self._watchdog_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._first_status_event = asyncio.Event()
        self._write_lock = asyncio.Lock()
        self._closing = False
        self._last_rx_monotonic = 0.0

    @property
    def host(self) -> str:
        return self._host

    @property
    def status(self) -> NapcoStatus:
        return self._status

    @property
    def is_connected(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    def add_listener(self, callback: Callable[[NapcoStatus], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def _remove() -> None:
            with contextlib.suppress(ValueError):
                self._listeners.remove(callback)

        return _remove

    def add_connection_listener(self, callback: Callable[[bool], None]) -> Callable[[], None]:
        """Subscribe to connection state changes (True=connected, False=lost)."""
        self._connection_listeners.append(callback)

        def _remove() -> None:
            with contextlib.suppress(ValueError):
                self._connection_listeners.remove(callback)

        return _remove

    def _notify_connection(self, *, connected: bool) -> None:
        for listener in list(self._connection_listeners):
            try:
                listener(connected)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Napco connection listener raised")

    async def async_connect(self) -> None:
        """Open the TCP connection and wait for the first status frame."""
        if self.is_connected:
            return
        self._closing = False
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT_SEC):
                self._reader, self._writer = await asyncio.open_connection(
                    self._host,
                    TCP_PORT,
                )
        except (OSError, TimeoutError) as err:
            msg = f"Unable to reach Napco panel at {self._host}:{TCP_PORT}"
            raise NapcoIbridgeApiClientCommunicationError(msg) from err

        self._first_status_event.clear()
        self._last_rx_monotonic = time.monotonic()
        self._reader_task = asyncio.create_task(
            self._read_loop(),
            name=f"napco-ibridge-reader-{self._host}",
        )
        self._poller_task = asyncio.create_task(
            self._poll_loop(),
            name=f"napco-ibridge-poller-{self._host}",
        )
        self._watchdog_task = asyncio.create_task(
            self._watchdog_loop(),
            name=f"napco-ibridge-watchdog-{self._host}",
        )

        try:
            async with asyncio.timeout(FIRST_STATUS_TIMEOUT_SEC):
                await self._first_status_event.wait()
        except TimeoutError as err:
            await self._async_teardown_connection()
            msg = "Connected but never received a status frame from the panel"
            raise NapcoIbridgeApiClientCommunicationError(msg) from err

    async def async_disconnect(self) -> None:
        self._closing = True
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
        self._reconnect_task = None
        await self._async_teardown_connection()

    async def _async_teardown_connection(self) -> None:
        """Cancel connection tasks and close the socket; reconnect state is untouched."""
        for task in (self._poller_task, self._reader_task, self._watchdog_task):
            if task and not task.done() and task is not asyncio.current_task():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._reader_task = None
        self._poller_task = None
        self._watchdog_task = None
        if self._writer is not None:
            with contextlib.suppress(Exception):
                self._writer.close()
                await self._writer.wait_closed()
        self._writer = None
        self._reader = None

    async def async_send_keys(self, key_codes: list[int]) -> None:
        if not self.is_connected:
            msg = "Cannot send keys; panel is not connected"
            raise NapcoIbridgeApiClientCommunicationError(msg)
        async with self._write_lock:
            self._sequence = (self._sequence + 1) & 0xFF
            buffer = _button_buffer(key_codes, self._sequence)
            try:
                assert self._writer is not None
                self._writer.write(buffer)
                await self._writer.drain()
            except OSError as err:
                msg = f"Failed sending keys to panel: {err}"
                raise NapcoIbridgeApiClientCommunicationError(msg) from err

    async def _poll_loop(self) -> None:
        try:
            while not self._closing and self.is_connected:
                async with self._write_lock:
                    try:
                        assert self._writer is not None
                        self._writer.write(_status_buffer())
                        await self._writer.drain()
                    except OSError as err:
                        LOGGER.warning("Napco poll write failed: %s", err)
                        break
                await asyncio.sleep(STATUS_POLL_INTERVAL_SEC)
        except asyncio.CancelledError:
            raise
        self._schedule_reconnect()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while not self._closing:
                try:
                    chunk = await self._reader.read(4096)
                except OSError as err:
                    LOGGER.warning("Napco read failed: %s", err)
                    break
                if not chunk:
                    LOGGER.info("Napco panel %s closed connection", self._host)
                    break
                self._last_rx_monotonic = time.monotonic()
                delta = _parse_frame(chunk)
                if delta is None:
                    continue
                # Any parsed status frame counts as "first status", even if it
                # matches the pre-reconnect state and produces no delta below.
                self._first_status_event.set()
                self._apply_delta(delta)
        except asyncio.CancelledError:
            raise
        self._schedule_reconnect()

    async def _watchdog_loop(self) -> None:
        """Force a reconnect when the panel stops answering status polls."""
        try:
            while not self._closing:
                await asyncio.sleep(STALE_CONNECTION_TIMEOUT_SEC / 2)
                if time.monotonic() - self._last_rx_monotonic > STALE_CONNECTION_TIMEOUT_SEC:
                    LOGGER.warning(
                        "No data from Napco panel %s for over %.0f s; connection is stale",
                        self._host,
                        STALE_CONNECTION_TIMEOUT_SEC,
                    )
                    break
        except asyncio.CancelledError:
            raise
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Start background reconnection after the connection died (idempotent)."""
        if self._closing or (self._reconnect_task and not self._reconnect_task.done()):
            return
        LOGGER.warning("Lost connection to Napco panel %s; reconnecting", self._host)
        self._notify_connection(connected=False)
        self._reconnect_task = asyncio.create_task(
            self._reconnect_loop(),
            name=f"napco-ibridge-reconnect-{self._host}",
        )

    async def _reconnect_loop(self) -> None:
        await self._async_teardown_connection()
        delay = RECONNECT_INITIAL_DELAY_SEC
        while not self._closing:
            try:
                await self.async_connect()
            except NapcoIbridgeApiClientError as err:
                LOGGER.debug(
                    "Reconnect to Napco panel %s failed (%s); retrying in %.0f s",
                    self._host,
                    err,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, RECONNECT_MAX_DELAY_SEC)
                continue
            LOGGER.info("Reconnected to Napco panel %s", self._host)
            self._notify_connection(connected=True)
            return

    def _apply_delta(self, delta: dict) -> None:
        merged_raw = {**self._status.raw, **delta}
        # Bail early if nothing changed (matches the JS behavior).
        if merged_raw == self._status.raw:
            return

        new_status = NapcoStatus(
            armed_led=merged_raw.get("armed_led", self._status.armed_led),
            status_led=merged_raw.get("status_led", self._status.status_led),
            trouble_led=merged_raw.get("trouble_led", self._status.trouble_led),
            fire_led=merged_raw.get("fire_led", self._status.fire_led),
            fire_trouble_led=merged_raw.get("fire_trouble_led", self._status.fire_trouble_led),
            bypass_led=merged_raw.get("bypass_led", self._status.bypass_led),
            sounder=merged_raw.get("sounder", self._status.sounder),
            text_line_1=merged_raw.get("text_line_1", self._status.text_line_1),
            text_line_2=merged_raw.get("text_line_2", self._status.text_line_2),
            area=merged_raw.get("area", self._status.area),
            cursor_row=merged_raw.get("cursor_row", self._status.cursor_row),
            cursor_column=merged_raw.get("cursor_column", self._status.cursor_column),
            raw=merged_raw,
        )
        new_status.arm_status = _derive_arm_status(
            new_status.text_line_1,
            new_status.text_line_2,
            new_status.armed_led,
            new_status.status_led,
        )
        self._status = new_status
        for listener in list(self._listeners):
            try:
                listener(new_status)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Napco listener raised")
