"""Core business logic for the SRE Error Budget Calculator."""

from typing import Any, Dict


def validate_slo_target(slo_target: float) -> float:
    """Validate that the SLO target percentage is strictly between 0 and 100."""
    if isinstance(slo_target, bool) or not isinstance(slo_target, (int, float)):
        raise ValueError("slo_target must be a number.")
    if slo_target <= 0 or slo_target >= 100:
        raise ValueError("slo_target must be strictly between 0 and 100 (e.g. 99.9).")
    return float(slo_target)


def validate_window_days(window_days: int) -> int:
    """Validate that the evaluation window in days is a positive integer."""
    if isinstance(window_days, bool) or not isinstance(window_days, int):
        raise ValueError("window_days must be an integer.")
    if window_days <= 0 or window_days > 366:
        raise ValueError("window_days must be between 1 and 366.")
    return window_days


def calculate_allowed_downtime(slo_target: float, window_days: int = 30) -> Dict[str, Any]:
    """
    Calculate the total allowed downtime (error budget in minutes & seconds)
    for a given SLO target percentage and window in days.
    """
    slo = validate_slo_target(slo_target)
    days = validate_window_days(window_days)

    total_window_minutes = days * 24 * 60
    error_budget_fraction = (100.0 - slo) / 100.0
    allowed_downtime_minutes = round(total_window_minutes * error_budget_fraction, 2)
    allowed_downtime_seconds = round(allowed_downtime_minutes * 60, 1)

    return {
        "slo_target": slo,
        "window_days": days,
        "total_window_minutes": total_window_minutes,
        "allowed_downtime_minutes": allowed_downtime_minutes,
        "allowed_downtime_seconds": allowed_downtime_seconds,
    }


def calculate_request_budget(
    slo_target: float, total_requests: int, failed_requests: int
) -> Dict[str, Any]:
    """
    Calculate the request-based error budget, remaining allowed failures,
    burn percentage, and exhaustion status.
    """
    slo = validate_slo_target(slo_target)

    if isinstance(total_requests, bool) or not isinstance(total_requests, int) or total_requests <= 0:
        raise ValueError("total_requests must be a positive integer.")
    if isinstance(failed_requests, bool) or not isinstance(failed_requests, int) or failed_requests < 0:
        raise ValueError("failed_requests must be a non-negative integer.")
    if failed_requests > total_requests:
        raise ValueError("failed_requests cannot exceed total_requests.")

    error_budget_fraction = (100.0 - slo) / 100.0
    allowed_failures = int(round(total_requests * error_budget_fraction))
    remaining_failures = allowed_failures - failed_requests
    actual_availability = round(((total_requests - failed_requests) / total_requests) * 100.0, 4)

    if allowed_failures > 0:
        budget_consumed_pct = round((failed_requests / allowed_failures) * 100.0, 2)
    else:
        budget_consumed_pct = 100.0 if failed_requests > 0 else 0.0

    return {
        "slo_target": slo,
        "total_requests": total_requests,
        "failed_requests": failed_requests,
        "allowed_failures": allowed_failures,
        "remaining_failures": remaining_failures,
        "actual_availability": actual_availability,
        "budget_consumed_percent": budget_consumed_pct,
        "budget_exhausted": remaining_failures < 0,
    }


def calculate_burn_rate(
    slo_target: float, observed_error_rate_percent: float
) -> Dict[str, Any]:
    """
    Calculate the SRE burn rate: how fast the service consumes its error budget
    relative to the ideal rate (burn_rate = 1.0 means exactly 100% consumed at end of window).
    """
    slo = validate_slo_target(slo_target)
    if (
        isinstance(observed_error_rate_percent, bool)
        or not isinstance(observed_error_rate_percent, (int, float))
        or observed_error_rate_percent < 0
        or observed_error_rate_percent > 100
    ):
        raise ValueError("observed_error_rate_percent must be a number between 0 and 100.")

    allowed_error_rate_percent = 100.0 - slo
    burn_rate = round(float(observed_error_rate_percent) / allowed_error_rate_percent, 2)

    if burn_rate > 14.4:
        alert_level = "CRITICAL"
    elif burn_rate > 6.0:
        alert_level = "HIGH"
    elif burn_rate > 1.0:
        alert_level = "WARNING"
    else:
        alert_level = "NORMAL"

    return {
        "slo_target": slo,
        "allowed_error_rate_percent": round(allowed_error_rate_percent, 4),
        "observed_error_rate_percent": float(observed_error_rate_percent),
        "burn_rate": burn_rate,
        "alert_level": alert_level,
    }


def evaluate_release_gate(
    slo_target: float,
    total_requests: int,
    failed_requests: int,
    active_critical_incident: bool = False,
) -> Dict[str, Any]:
    """
    Decide whether a new production release is allowed (GO / CAUTION / NO-GO)
    based on remaining error budget and active incidents.
    """
    if not isinstance(active_critical_incident, bool):
        raise ValueError("active_critical_incident must be a boolean.")

    budget = calculate_request_budget(slo_target, total_requests, failed_requests)
    consumed = budget["budget_consumed_percent"]

    if active_critical_incident:
        decision = "NO-GO"
        reason = "Release blocked: an active critical incident is currently ongoing."
    elif budget["budget_exhausted"] or consumed >= 100.0:
        decision = "NO-GO"
        reason = "Release blocked: error budget is exhausted (>= 100% consumed)."
    elif consumed >= 80.0:
        decision = "CAUTION"
        reason = "Release allowed with caution: over 80% of error budget is consumed."
    else:
        decision = "GO"
        reason = "Release approved: error budget is healthy."

    return {
        "decision": decision,
        "can_deploy": decision in ("GO", "CAUTION"),
        "reason": reason,
        "budget": budget,
        "active_critical_incident": active_critical_incident,
    }
