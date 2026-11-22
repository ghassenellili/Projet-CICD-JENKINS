"""Unit tests for the Error Budget Calculator logic (app/calculator.py)."""

import pytest

from app.calculator import (
    calculate_allowed_downtime,
    calculate_burn_rate,
    calculate_request_budget,
    evaluate_release_gate,
)


def test_allowed_downtime_30_days_99_9():
    """99.9% SLO over 30 days allows 43.2 minutes of downtime."""
    result = calculate_allowed_downtime(99.9, 30)
    assert result["slo_target"] == 99.9
    assert result["window_days"] == 30
    assert result["total_window_minutes"] == 43200
    assert result["allowed_downtime_minutes"] == 999.9
    assert result["allowed_downtime_seconds"] == 2592.0


def test_allowed_downtime_invalid_inputs():
    """Invalid SLO targets or window days must raise ValueError."""
    with pytest.raises(ValueError, match="strictly between 0 and 100"):
        calculate_allowed_downtime(100.0, 30)
    with pytest.raises(ValueError, match="strictly between 0 and 100"):
        calculate_allowed_downtime(0, 30)
    with pytest.raises(ValueError, match="between 1 and 366"):
        calculate_allowed_downtime(99.9, 0)


def test_request_budget_healthy():
    """99.9% SLO on 100,000 requests allows 100 failed requests."""
    result = calculate_request_budget(99.9, 100000, 25)
    assert result["allowed_failures"] == 100
    assert result["remaining_failures"] == 75
    assert result["budget_consumed_percent"] == 25.0
    assert result["budget_exhausted"] is False


def test_request_budget_exhausted():
    """When failed requests exceed allowed failures, budget_exhausted is True."""
    result = calculate_request_budget(99.9, 100000, 130)
    assert result["allowed_failures"] == 100
    assert result["remaining_failures"] == -30
    assert result["budget_consumed_percent"] == 130.0
    assert result["budget_exhausted"] is True


def test_request_budget_invalid_counts():
    """Negative failed requests or failed > total must raise ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        calculate_request_budget(99.9, 0, 0)
    with pytest.raises(ValueError, match="cannot exceed total_requests"):
        calculate_request_budget(99.9, 100, 150)


def test_burn_rate_levels():
    """Verify burn rate computation and alert level thresholds."""
    normal = calculate_burn_rate(99.9, 0.05)
    assert normal["burn_rate"] == 0.5
    assert normal["alert_level"] == "NORMAL"

    critical = calculate_burn_rate(99.9, 2.0)
    assert critical["burn_rate"] == 20.0
    assert critical["alert_level"] == "CRITICAL"


def test_release_gate_go_caution_nogo():
    """Verify GO, CAUTION, and NO-GO decisions on release gate evaluation."""
    go_res = evaluate_release_gate(99.9, 100000, 20)
    assert go_res["decision"] == "GO"
    assert go_res["can_deploy"] is True

    caution_res = evaluate_release_gate(99.9, 100000, 85)
    assert caution_res["decision"] == "CAUTION"
    assert caution_res["can_deploy"] is True

    nogo_budget = evaluate_release_gate(99.9, 100000, 120)
    assert nogo_budget["decision"] == "NO-GO"
    assert nogo_budget["can_deploy"] is False

    nogo_incident = evaluate_release_gate(99.9, 100000, 10, active_critical_incident=True)
    assert nogo_incident["decision"] == "NO-GO"
    assert nogo_incident["can_deploy"] is False
