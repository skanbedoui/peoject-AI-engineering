from __future__ import annotations

# Replace these assumptions with the measured machine and local electricity rate.
HARDWARE_COST_PER_HOUR = 0.30
REQUESTS_PER_HOUR = 120.0


def self_hosted_cost_per_1000(
    hardware_cost_per_hour: float = HARDWARE_COST_PER_HOUR,
    requests_per_hour: float = REQUESTS_PER_HOUR,
) -> float:
    if requests_per_hour <= 0:
        raise ValueError("requests_per_hour must be positive")
    return hardware_cost_per_hour / requests_per_hour * 1000


def cost_at_traffic(requests: int, cost_per_1000: float | None = None) -> float:
    unit_cost = self_hosted_cost_per_1000() if cost_per_1000 is None else cost_per_1000
    return requests / 1000 * unit_cost
