from sonnen_power.config import load_settings
from sonnen_power.decision_engine import DecisionEngine
from sonnen_power.logging_config import configure_logging


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    DecisionEngine(settings).run_forever()


if __name__ == "__main__":
    main()
