from __future__ import annotations

import math


def binomial_tail_p_value(n: int, k: int, p0: float) -> float:
    if n <= 0:
        return 1.0
    k = max(0, min(k, n))
    if p0 <= 0:
        return 0.0 if k > 0 else 1.0
    if p0 >= 1:
        return 1.0 if k < n else 0.0

    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
    return min(max(total, 0.0), 1.0)


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    phat = k / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)
    lower = (center - margin) / denom
    upper = (center + margin) / denom
    return max(0.0, lower), min(1.0, upper)
