from datetime import UTC, datetime, timedelta

from sonnen_power.models import Decision, PowerWindow


BURN = "burn"
NORMAL = "normal"
LOW_POWER = "low_power"
HOLD = "hold"

STAGES = (BURN, NORMAL, LOW_POWER)


class PowerPolicy:
    def __init__(
        self,
        soc_low_threshold: int = 35,
        soc_low_recovery: int = 40,
        soc_burn_threshold: int = 70,
        soc_burn_drop: int = 65,
        min_surplus_w_for_burn: int = 500,
        surplus_drop_w: int = 200,
        action_cooldown_minutes: int = 30,
    ) -> None:
        self.soc_low_threshold = soc_low_threshold
        self.soc_low_recovery = soc_low_recovery
        self.soc_burn_threshold = soc_burn_threshold
        self.soc_burn_drop = soc_burn_drop
        self.min_surplus_w_for_burn = min_surplus_w_for_burn
        self.surplus_drop_w = surplus_drop_w
        self.action_cooldown_minutes = action_cooldown_minutes

    def decide(
        self,
        window_5m: PowerWindow | None,
        window_15m: PowerWindow | None,
        window_30m: PowerWindow | None,
        current_stage: str | None = None,
        last_action: tuple[str, datetime] | None = None,
        now: datetime | None = None,
    ) -> Decision:
        now = now or datetime.now(UTC)
        primary = window_15m or window_5m or window_30m
        if primary is None:
            return self._decision(HOLD, "no recent sonnen data available", None)

        cooldown_reason = self._cooldown_reason(last_action, now)
        if cooldown_reason:
            return self._decision(HOLD, cooldown_reason, primary)

        new_stage = self._determine_stage(primary, current_stage)

        if new_stage == current_stage:
            return self._decision(HOLD, f"staying in {current_stage}", primary)

        return self._decision(new_stage, self._transition_reason(current_stage, new_stage, primary), primary)

    def _determine_stage(self, window: PowerWindow, current_stage: str | None) -> str:
        rsoc = window.rsoc
        if rsoc is None:
            return current_stage or NORMAL

        surplus = window.grid_feed_in_w if window.grid_feed_in_w is not None else 0.0

        if current_stage == LOW_POWER:
            if rsoc > self.soc_low_recovery:
                return NORMAL
            return LOW_POWER

        if current_stage == BURN:
            if rsoc < self.soc_burn_drop or surplus < self.surplus_drop_w:
                return NORMAL
            return BURN

        # current_stage is NORMAL or None
        if rsoc < self.soc_low_threshold:
            return LOW_POWER
        if rsoc > self.soc_burn_threshold and surplus >= self.min_surplus_w_for_burn:
            return BURN
        return NORMAL

    def _transition_reason(self, old: str | None, new: str, window: PowerWindow) -> str:
        rsoc = window.rsoc
        surplus = window.grid_feed_in_w
        if new == LOW_POWER:
            return f"RSOC {rsoc}% below {self.soc_low_threshold}% — powering down workers"
        if new == BURN:
            return f"RSOC {rsoc}% above {self.soc_burn_threshold}% with {surplus:.0f}W surplus — enabling Folding@Home"
        if old == LOW_POWER:
            return f"RSOC {rsoc}% recovered above {self.soc_low_recovery}% — powering up workers"
        if old == BURN:
            if rsoc < self.soc_burn_drop:
                return f"RSOC {rsoc}% dropped below {self.soc_burn_drop}% — disabling Folding@Home"
            return f"surplus {surplus:.0f}W dropped below {self.surplus_drop_w}W — disabling Folding@Home"
        return f"transitioning to {new}"

    def _cooldown_reason(self, last_action: tuple[str, datetime] | None, now: datetime) -> str | None:
        if not last_action:
            return None
        action, action_time = last_action
        if action == HOLD:
            return None
        if action_time.tzinfo is None:
            action_time = action_time.replace(tzinfo=UTC)
        until = action_time + timedelta(minutes=self.action_cooldown_minutes)
        if now < until:
            return f"cooldown active until {until.isoformat()}"
        return None

    def _decision(self, decision: str, reason: str, window: PowerWindow | None) -> Decision:
        return Decision(
            decision=decision,
            reason=reason,
            rsoc=window.rsoc if window else None,
            production_w=round(window.production_w) if window and window.production_w is not None else None,
            consumption_w=round(window.consumption_w) if window and window.consumption_w is not None else None,
            grid_feed_in_w=window.grid_feed_in_w if window else None,
            estimated_surplus_w=window.estimated_surplus_w if window else None,
        )
