import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


def get_connection(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url, autocommit=True, row_factory=dict_row)


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def fetch_power_window(self, minutes: int) -> dict[str, Any] | None:
        sql = """
        SELECT
          AVG(production_w)::float AS production_w,
          AVG(consumption_w)::float AS consumption_w,
          AVG(grid_feed_in_w)::float AS grid_feed_in_w,
          ROUND(AVG(rsoc))::int AS rsoc,
          ROUND(AVG(usoc))::int AS usoc,
          MIN(collected_at) AS first_collected_at,
          MAX(collected_at) AS last_collected_at,
          COUNT(*) AS sample_count
        FROM sonnen.status
        WHERE collected_at >= now() - (%s || ' minutes')::interval
        """
        try:
            with get_connection(self.database_url) as conn:
                row = conn.execute(sql, (minutes,)).fetchone()
            return row if row and row["sample_count"] > 0 else None
        except Exception:
            logger.exception("failed to fetch power window")
            return None
