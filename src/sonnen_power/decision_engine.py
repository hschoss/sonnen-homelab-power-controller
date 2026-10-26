import logging
import signal
import time
from datetime import UTC, datetime

from sonnen_power.cluster_controller import ClusterController
from sonnen_power.config import Settings
from sonnen_power.db import Database
from sonnen_power.models import PowerWindow
from sonnen_power.policy import BURN, HOLD, LOW_POWER, NORMAL, PowerPolicy

logger = logging.getLogger(__name__)


class DecisionEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.database_url)
        self.policy = PowerPolicy(
            soc_low_threshold=settings.soc_scale_down_threshold,
            soc_low_recovery=settings.soc_low_recovery,
            soc_burn_threshold=settings.soc_burn_threshold,
            soc_burn_drop=settings.soc_scale_up_threshold,
            min_surplus_w_for_burn=settings.min_surplus_w_for_burn,
            surplus_drop_w=settings.surplus_drop_w,
            action_cooldown_minutes=settings.action_cooldown_minutes,
        )
        self.cluster = ClusterController(
            settings.execute_actions,
            settings.control_plane_mac_address,
            settings.wol_broadcast_address,
            settings.wol_port,
            settings.cluster_api_host,
            settings.cluster_api_port,
            folding_namespace=settings.folding_namespace,
            folding_deployment=settings.folding_deployment,
            folding_burn_replicas=settings.folding_burn_replicas,
        )
        self.running = True
        self.current_stage: str = NORMAL
        self.last_action: tuple[str, datetime] | None = None

    def stop(self, *_args: object) -> None:
        self.running = False

    def run_forever(self) -> None:
        signal.signal(signal.SIGTERM, self.stop)
        signal.signal(signal.SIGINT, self.stop)
        logger.info("starting decision engine, initial stage=%s", self.current_stage)
        while self.running:
            self.run_once()
            time.sleep(self.settings.decision_interval_seconds)
        logger.info("stopped decision engine")

    def run_once(self) -> None:
        try:
            windows = {minutes: self._load_window(minutes) for minutes in (5, 15, 30)}
            decision = self.policy.decide(
                windows[5], windows[15], windows[30],
                self.current_stage, self.last_action,
            )
            logger.info(
                "stage=%s decision=%s reason=%s rsoc=%s grid_feed_in=%s",
                self.current_stage, decision.decision, decision.reason,
                decision.rsoc, decision.grid_feed_in_w,
            )
            if decision.decision != HOLD:
                old_stage = self.current_stage
                self.current_stage = decision.decision
                self.last_action = (decision.decision, datetime.now(UTC))
                logger.info("stage transition: %s -> %s", old_stage, self.current_stage)
                self._apply_transition(old_stage, self.current_stage)
        except Exception:
            logger.exception("decision engine iteration failed")

    def _load_window(self, minutes: int) -> PowerWindow | None:
        row = self.db.fetch_power_window(minutes)
        if not row:
            return None
        return PowerWindow(
            minutes=minutes,
            production_w=row["production_w"],
            consumption_w=row["consumption_w"],
            grid_feed_in_w=row["grid_feed_in_w"],
            rsoc=row["rsoc"],
            usoc=row["usoc"],
            first_collected_at=row["first_collected_at"],
            last_collected_at=row["last_collected_at"],
        )

    def _apply_transition(self, old_stage: str, new_stage: str) -> None:
        if new_stage == BURN:
            if old_stage == LOW_POWER:
                self.cluster.power_on_workers()
            self.cluster.enable_folding()
        elif new_stage == NORMAL:
            if old_stage == LOW_POWER:
                self.cluster.power_on_workers()
            elif old_stage == BURN:
                self.cluster.disable_folding()
        elif new_stage == LOW_POWER:
            if old_stage == BURN:
                self.cluster.disable_folding()
            self.cluster.drain_and_power_off_workers()
