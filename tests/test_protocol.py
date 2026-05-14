"""Unit tests for the Napco binary protocol helpers (no HA, no network)."""

from __future__ import annotations

from custom_components.napco_ibridge.api.client import (
    BUTTONS,
    _append_checksum,
    _button_buffer,
    _derive_arm_status,
    _parse_frame,
    _status_buffer,
)
from custom_components.napco_ibridge.const import ARM_STATE_AWAY, ARM_STATE_DISARM, ARM_STATE_NOT_READY, ARM_STATE_STAY


def test_status_buffer_matches_reference() -> None:
    # Reference bytes derived from the JS implementation (with sequence forced to 0x01).
    assert _status_buffer() == bytes(
        [0xB8, 0x00, 0x09, 0x00, 0x01, 0x49, 0x01, 0x01, 0x4B],
    )


def test_checksum_appends_two_bytes() -> None:
    payload = bytes([0x01, 0x02, 0x03])
    out = _append_checksum(payload)
    assert out[:-2] == payload
    assert out[-2:] == bytes([0x00, 0x06])


def test_button_buffer_layout() -> None:
    buf = _button_buffer([BUTTONS["Button1"], BUTTONS["ButtonOnOffEnter"]], sequence=5)
    # Header + body + 2-byte checksum
    expected_length = 7 + 2 + 2
    assert len(buf) == expected_length
    assert buf[0] == 0xB7
    # Length field encodes len(keys) + 9
    assert (buf[1] << 8 | buf[2]) == 2 + 9
    assert buf[4] == 6  # sequence + 1
    # Body: Button1 (0x01) then ButtonOnOffEnter (-128 → 0x80)
    assert buf[7:9] == bytes([0x01, 0x80])


def test_arm_status_disarmed() -> None:
    assert _derive_arm_status("READY TO ARM", "", armed_led="Off", status_led="On") == ARM_STATE_DISARM


def test_arm_status_away_armed() -> None:
    assert _derive_arm_status("ARMED", "ALL SECURE", armed_led="On", status_led="Off") == ARM_STATE_AWAY


def test_arm_status_stay_armed() -> None:
    assert _derive_arm_status("ARMED STAY", "", armed_led="On", status_led="CadenceB") == ARM_STATE_STAY


def test_arm_status_unknown_falls_back() -> None:
    assert _derive_arm_status("", "", armed_led="Off", status_led="Off") == ARM_STATE_NOT_READY


def test_parse_frame_ignores_non_gem_k1() -> None:
    assert _parse_frame(b"\x00" * 40) is None


def test_parse_frame_decodes_led_block() -> None:
    # Header: 0xBB at byte 0, panel id (73) at byte 5, frame-type byte 3 != 2.
    frame = bytearray(40)
    frame[0] = 0xBB
    frame[3] = 0x01  # not a text update
    frame[5] = 73  # PANEL_GEM_K1
    frame[7] = 1  # fire_led = On
    frame[10] = 1  # armed_led = On
    delta = _parse_frame(bytes(frame))
    assert delta is not None
    assert delta["fire_led"] == "On"
    assert delta["armed_led"] == "On"
