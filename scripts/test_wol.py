from sonnen_power.config import load_settings
from sonnen_power.logging_config import configure_logging
from sonnen_power.wol import send_magic_packet


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    if not settings.control_plane_mac_address:
        raise SystemExit("CONTROL_PLANE_MAC_ADDRESS is required")
    send_magic_packet(settings.control_plane_mac_address, settings.wol_broadcast_address, settings.wol_port)


if __name__ == "__main__":
    main()
