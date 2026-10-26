from datetime import UTC, datetime, timedelta

from sonnen_power.models import PowerWindow
from sonnen_power.policy import BURN, HOLD, LOW_POWER, NORMAL, PowerPolicy


def policy() -> PowerPolicy:
    return PowerPolicy()


def window(rsoc: int, production: float, consumption: float, grid: float, minutes: int = 15) -> PowerWindow:
    return PowerWindow(minutes, production, consumption, grid, rsoc, None)


# --- Stage transitions from NORMAL ---

def test_normal_to_low_power_on_low_soc() -> None:
    decision = policy().decide(None, window(30, 100, 500, -400), None, NORMAL)
    assert decision.decision == LOW_POWER


def test_normal_to_burn_on_high_soc_and_surplus() -> None:
    decision = policy().decide(None, window(80, 2200, 1000, 600), None, NORMAL)
    assert decision.decision == BURN


def test_normal_stays_normal_without_surplus() -> None:
    decision = policy().decide(None, window(80, 2200, 1000, 100), None, NORMAL)
    assert decision.decision == HOLD


def test_normal_stays_normal_in_middle_soc() -> None:
    decision = policy().decide(None, window(50, 800, 700, 50), None, NORMAL)
    assert decision.decision == HOLD


# --- Hysteresis: transitions from BURN ---

def test_burn_stays_burn_above_drop_threshold() -> None:
    decision = policy().decide(None, window(70, 2000, 1000, 500), None, BURN)
    assert decision.decision == HOLD


def test_burn_to_normal_on_soc_drop() -> None:
    decision = policy().decide(None, window(60, 2000, 1000, 500), None, BURN)
    assert decision.decision == NORMAL


def test_burn_to_normal_on_surplus_drop() -> None:
    decision = policy().decide(None, window(80, 1000, 900, 100), None, BURN)
    assert decision.decision == NORMAL


# --- Hysteresis: transitions from LOW_POWER ---

def test_low_power_stays_low_at_threshold() -> None:
    decision = policy().decide(None, window(38, 100, 500, -400), None, LOW_POWER)
    assert decision.decision == HOLD


def test_low_power_to_normal_on_recovery() -> None:
    decision = policy().decide(None, window(45, 500, 400, 50), None, LOW_POWER)
    assert decision.decision == NORMAL


# --- Cooldown ---

def test_cooldown_holds_after_action() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    last_action = (BURN, now - timedelta(minutes=5))
    decision = policy().decide(None, window(30, 100, 500, -400), None, BURN, last_action, now)
    assert decision.decision == HOLD
    assert "cooldown" in decision.reason


def test_cooldown_expires() -> None:
    now = datetime(2026, 5, 26, tzinfo=UTC)
    last_action = (BURN, now - timedelta(minutes=35))
    decision = policy().decide(None, window(30, 100, 500, -400), None, NORMAL, last_action, now)
    assert decision.decision == LOW_POWER


# --- Edge cases ---

def test_no_data_returns_hold() -> None:
    decision = policy().decide(None, None, None, NORMAL)
    assert decision.decision == HOLD
    assert "no recent" in decision.reason


def test_none_stage_defaults_to_normal_logic() -> None:
    decision = policy().decide(None, window(80, 2200, 1000, 600), None, None)
    assert decision.decision == BURN
