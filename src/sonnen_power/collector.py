import json
import logging
import signal
import time

import psycopg

from sonnen_power.config import Settings
from sonnen_power.sonnen_client import SonnenClient

logger = logging.getLogger(__name__)

_INSERT_SQL = """
INSERT INTO sonnen.status (
  collected_at, rsoc, usoc,
  production_w, consumption_w, grid_feed_in_w, pac_total_w,
  battery_charging, battery_discharging, operating_mode, raw
) VALUES (
  now(), %(rsoc)s, %(usoc)s,
  %(production_w)s, %(consumption_w)s, %(grid_feed_in_w)s, %(pac_total_w)s,
  %(battery_charging)s, %(battery_discharging)s, %(operating_mode)s, %(raw)s
)
"""


def _normalize(sample: dict) -> dict:
    return {
        "rsoc": sample.get("RSOC") or sample.get("USOC"),
        "usoc": sample.get("USOC"),
        "production_w": sample.get("Production_W"),
        "consumption_w": sample.get("Consumption_W"),
        "grid_feed_in_w": sample.get("GridFeedIn_W"),
        "pac_total_w": sample.get("Pac_total_W"),
        "battery_charging": sample.get("BatteryCharging"),
        "battery_discharging": sample.get("BatteryDischarging"),
        "operating_mode": str(sample.get("OperatingMode")) if sample.get("OperatingMode") is not None else None,
        "raw": json.dumps(sample),
    }


class Collector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.sonnen = SonnenClient(settings.sonnen_base_url, settings.sonnen_auth_token)
        self.running = True

    def stop(self, *_args: object) -> None:
        self.running = False

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        logger.info("starting collector base_url=%s interval=%ds",
                    self.settings.sonnen_base_url, self.settings.poll_interval_seconds)
        while self.running:
            self.run_once()
            time.sleep(self.settings.poll_interval_seconds)
        self.sonnen.close()
        logger.info("stopped collector")

    def run_once(self) -> None:
        try:
            sample = self.sonnen.status()
            if sample is None:
                return
            row = _normalize(sample)
            with psycopg.connect(self.settings.database_url, autocommit=True) as conn:
                conn.execute(_INSERT_SQL, row)
            logger.info("inserted sample rsoc=%s cons=%s prod=%s gridFeed=%s",
                        row["rsoc"], row["consumption_w"],
                        row["production_w"], row["grid_feed_in_w"])
        except Exception:
            logger.exception("collector iteration failed")
