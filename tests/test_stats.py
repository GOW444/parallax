"""Tests for src/stats.py (Mann-Kendall, Sen's slope, correlation) and src/models.py (OLS)."""

import numpy as np
import pandas as pd
import pytest

from src import models, stats


# ---------------------------------------------------------------- Sen's slope
def test_sen_slope_exact_line_and_robust_to_outlier():
    line = 2.0 * np.arange(10) + 5
    assert stats.sen_slope(line) == pytest.approx(2.0)
    line[9] = 1000  # one wild value barely moves the median of pairwise slopes
    assert stats.sen_slope(line) == pytest.approx(2.0)


# ---------------------------------------------------------------- Mann-Kendall
def test_mk_detects_monotone_increase():
    result = stats.mann_kendall(np.arange(20, dtype=float))
    assert result["s"] == 20 * 19 // 2  # every pair increases
    assert result["tau"] == pytest.approx(1.0)
    assert result["p"] < 0.001
    assert result["trend"] == "increasing"


def test_mk_detects_monotone_decrease():
    result = stats.mann_kendall(np.arange(20, 0, -1, dtype=float))
    assert result["trend"] == "decreasing"
    assert result["sen_slope"] == pytest.approx(-1.0)


def test_mk_constant_series_has_no_trend():
    result = stats.mann_kendall(np.full(10, 3.0))
    assert result["p"] == 1.0 and result["trend"] == "no trend"


def test_mk_matches_textbook_variance_without_ties():
    n = 12
    expected = n * (n - 1) * (2 * n + 5) / 18
    assert stats._mk_variance(np.arange(n, dtype=float)) == pytest.approx(expected)


def test_mk_rejects_too_short_series():
    with pytest.raises(ValueError, match="at least 4"):
        stats.mann_kendall([1.0, 2.0, 3.0])


def test_hamed_rao_reduces_false_positives_on_autocorrelated_noise():
    """AR(1) noise with no trend: the original test rejects far too often, Hamed-Rao less."""
    rng = np.random.default_rng(42)
    n_series, n, phi = 300, 22, 0.8
    rejections_original = rejections_hr = 0
    for _ in range(n_series):
        noise = np.zeros(n)
        for t in range(1, n):
            noise[t] = phi * noise[t - 1] + rng.normal()
        result = stats.mann_kendall(noise)
        rejections_original += result["p"] < 0.05
        rejections_hr += result["p_hamed_rao"] < 0.05
    assert rejections_original / n_series > 0.15  # badly inflated above the nominal 5%
    assert rejections_hr < rejections_original


def test_hamed_rao_factor_is_finite_for_a_perfect_line():
    # detrending a perfect line leaves a constant: no autocorrelation information, factor 1
    assert stats.hamed_rao_factor(np.arange(15, dtype=float)) == pytest.approx(1.0)


def test_mk_variance_factor_is_floored_at_one():
    # strongly alternating series -> negative lag-1 autocorrelation -> raw factor < 1
    values = np.array([0, 10, 1, 11, 2, 12, 3, 13, 4, 14, 5, 15, 6, 16], dtype=float)
    result = stats.mann_kendall(values)
    assert result["variance_factor"] >= 1.0
    assert np.isfinite(result["z_hamed_rao"]) and np.isfinite(result["p_hamed_rao"])


# ---------------------------------------------------------------- correlation
def test_correlation_tests_drop_missing_pairs():
    x = [1, 2, 3, 4, np.nan]
    y = [2, 4, 6, 8, 10]
    result = stats.correlation_tests(x, y)
    assert result["n"] == 4
    assert result["pearson_r"] == pytest.approx(1.0)
    assert result["spearman_rho"] == pytest.approx(1.0)


# ---------------------------------------------------------------- OLS
def test_fit_ols_recovers_slope_and_flags_heteroscedasticity():
    rng = np.random.default_rng(0)
    x = np.linspace(1, 100, 200)
    y = 3 * x + rng.normal(0, x)  # noise grows with x
    summary, per_row = models.fit_ols(pd.DataFrame({"x": x, "y": y}), "y", "x")
    assert summary["slope"] == pytest.approx(3, abs=0.3)
    assert summary["breusch_pagan_p"] < 0.01
    assert len(per_row) == 200 and "residual" in per_row
