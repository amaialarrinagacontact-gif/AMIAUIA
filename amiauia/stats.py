"""AMIAUIA's statistical engine, written from scratch (standard library only)."""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def median(xs: Sequence[float]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2


def stdev(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def percentile(xs: Sequence[float], p: float) -> float:
    """Percentile with linear interpolation (p in 0..100)."""
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def robust_zscores(xs: Sequence[float]) -> list[float]:
    """Z-score based on median and MAD: resistant to outliers."""
    if not xs:
        return []
    med = median(xs)
    mad = median([abs(x - med) for x in xs])
    scale = 1.4826 * mad
    if scale == 0:
        return [0.0 for _ in xs]
    return [(x - med) / scale for x in xs]


def linear_regression(xs: Sequence[float], ys: Sequence[float]) -> dict[str, float]:
    """Ordinary least squares: slope, intercept, R² and residual standard error."""
    n = len(xs)
    if n < 2:
        raise ValueError("At least 2 points are required")
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("All x values are identical")
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    pred = [intercept + slope * x for x in xs]
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, pred))
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    err = math.sqrt(ss_res / (n - 2)) if n > 2 else 0.0
    return {"slope": slope, "intercept": intercept, "r2": r2, "error": err, "n": n}


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95 % confidence interval for a proportion k/n."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, center - margin), min(1.0, center + margin))


def two_proportion_test(k1: int, n1: int, k2: int, n2: int) -> dict[str, float]:
    """Two-sided two-proportion z-test. Returns z and p-value."""
    if n1 == 0 or n2 == 0:
        return {"z": 0.0, "p": 1.0}
    p1, p2 = k1 / n1, k2 / n2
    pp = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n2))
    if se == 0:
        return {"z": 0.0, "p": 1.0}
    z = (p1 - p2) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    return {"z": z, "p": p}


def shannon_entropy(data: bytes) -> float:
    """Entropy in bits per byte (0 = constant, 8 = random/encrypted)."""
    if not data:
        return 0.0
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in Counter(data).values())


def confidence_from_p(p: float) -> float:
    """Turns a p-value into an intuitive 0..1 confidence."""
    return max(0.0, min(0.99, 1 - p))
