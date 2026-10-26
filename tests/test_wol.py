import pytest

from sonnen_power.wol import build_magic_packet, normalize_mac


def test_normalize_mac_accepts_common_formats() -> None:
    assert normalize_mac("00:11:22:33:44:55") == "001122334455"
    assert normalize_mac("00-11-22-33-44-55") == "001122334455"
    assert normalize_mac("001122334455") == "001122334455"


def test_normalize_mac_rejects_invalid_mac() -> None:
    with pytest.raises(ValueError):
        normalize_mac("not-a-mac")


def test_build_magic_packet() -> None:
    packet = build_magic_packet("00:11:22:33:44:55")
    assert len(packet) == 102
    assert packet.startswith(b"\xff" * 6)
    assert packet[6:] == bytes.fromhex("001122334455") * 16
