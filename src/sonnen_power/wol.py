import logging
import re
import socket

logger = logging.getLogger(__name__)

MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|^[0-9A-Fa-f]{12}$")


def normalize_mac(mac_address: str) -> str:
    if not MAC_RE.match(mac_address):
        raise ValueError(f"invalid MAC address: {mac_address}")
    return mac_address.replace(":", "").replace("-", "").lower()


def build_magic_packet(mac_address: str) -> bytes:
    mac = bytes.fromhex(normalize_mac(mac_address))
    return b"\xff" * 6 + mac * 16


def send_magic_packet(mac_address: str, broadcast_address: str, port: int = 9) -> None:
    packet = build_magic_packet(mac_address)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast_address, port))
        logger.info("sent Wake-on-LAN packet to %s via %s:%s", mac_address, broadcast_address, port)
    except OSError:
        logger.exception("failed to send Wake-on-LAN packet")
        raise
