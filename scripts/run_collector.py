from sonnen_power.collector import Collector
from sonnen_power.config import load_settings
from sonnen_power.logging_config import configure_logging


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    Collector(settings).run_forever()


if __name__ == "__main__":
    main()
