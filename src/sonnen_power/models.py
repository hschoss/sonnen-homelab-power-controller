from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class PowerWindow:
    minutes: int
    production_w: float | None
    consumption_w: float | None
    grid_feed_in_w: float | None
    rsoc: int | None
    usoc: int | None
    first_collected_at: datetime | None = None
    last_collected_at: datetime | None = None

    @property
    def estimated_surplus_w(self) -> float | None:
        if self.production_w is None or self.consumption_w is None:
            return self.grid_feed_in_w
        return self.production_w - self.consumption_w


@dataclass(frozen=True)
class Decision:
    decision: str
    reason: str
    rsoc: int | None
    production_w: int | None
    consumption_w: int | None
    grid_feed_in_w: float | None
    estimated_surplus_w: float | None
