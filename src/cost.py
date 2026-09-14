import math
import os


def hardware_hourly_cost() -> float | None:
    raw = os.environ.get("LOCAL_HARDWARE_COST_PER_HOUR_USD")
    if raw is None or not raw.strip():
        return None
    value = float(raw)
    if not math.isfinite(value) or value < 0:
        raise ValueError(
            "LOCAL_HARDWARE_COST_PER_HOUR_USD must be finite and nonnegative"
        )
    return value


def self_hosted_cost_per_1000(
    hourly_cost: float | None, requests_per_hour: float
) -> float | None:
    if hourly_cost is None or requests_per_hour <= 0:
        return None
    return hourly_cost / requests_per_hour * 1000


def cost_at_traffic(requests: int, cost_per_1000: float | None) -> float | None:
    return None if cost_per_1000 is None else requests / 1000 * cost_per_1000
