import math

import pytest

from amiauia import stats


def test_mean_median_percentile():
    xs = [1, 2, 3, 4, 100]
    assert stats.mean(xs) == 22
    assert stats.median(xs) == 3
    assert stats.percentile([0, 10], 50) == 5


def test_robust_zscores_flag_outlier():
    zs = stats.robust_zscores([10, 11, 9, 10, 12, 10, 200])
    assert zs[-1] > 10
    assert all(abs(z) < 3 for z in zs[:-1])


def test_exact_linear_regression():
    r = stats.linear_regression([0, 1, 2, 3], [1, 3, 5, 7])
    assert r["slope"] == pytest.approx(2)
    assert r["intercept"] == pytest.approx(1)
    assert r["r2"] == pytest.approx(1)


def test_wilson_contains_proportion():
    lo, hi = stats.wilson_interval(30, 100)
    assert lo < 0.3 < hi


def test_two_proportion_significant():
    t = stats.two_proportion_test(40, 100, 10, 100)
    assert t["p"] < 0.001
    assert stats.two_proportion_test(10, 100, 10, 100)["p"] == pytest.approx(1)


def test_entropy():
    assert stats.shannon_entropy(b"aaaa") == 0
    assert stats.shannon_entropy(bytes(range(256))) == pytest.approx(8)
    assert math.isclose(stats.shannon_entropy(b"ab"), 1)
