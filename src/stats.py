"""Statistical tests used in the workflow: trend, correlation and group-comparison tests.

Mann-Kendall is implemented here (instead of the `pymannkendall` package) so every step
can be explained in the viva and the result does not depend on an extra dependency.

References
- Mann (1945); Kendall (1975): the rank-based trend test.
- Hamed & Rao (1998), "A modified Mann-Kendall trend test for autocorrelated data",
  Journal of Hydrology 204: 182-196. Variance correction for serial correlation.
- Sen (1968): median-of-pairwise-slopes trend estimator.
"""

import numpy as np
import pandas as pd
from scipy import stats as sps
from statsmodels.stats.multitest import multipletests

from src import config


def sen_slope(values: np.ndarray) -> float:
    """Sen's slope: the median of all pairwise slopes (robust to outliers), per time step."""
    values = np.asarray(values, dtype=float)
    slope, _, _, _ = sps.theilslopes(values, np.arange(len(values)))
    return float(slope)


def _mk_s(values: np.ndarray) -> int:
    """Mann-Kendall S: the number of increasing pairs minus decreasing pairs."""
    n = len(values)
    return int(sum(np.sign(values[j] - values[i]) for i in range(n - 1) for j in range(i + 1, n)))


def _mk_variance(values: np.ndarray) -> float:
    """Variance of S under 'no trend', corrected for tied values."""
    n = len(values)
    _, tie_counts = np.unique(values, return_counts=True)
    tie_term = sum(t * (t - 1) * (2 * t + 5) for t in tie_counts if t > 1)
    return (n * (n - 1) * (2 * n + 5) - tie_term) / 18


def _z_score(s: int, variance: float) -> float:
    """Continuity-corrected standard normal score of S."""
    if s > 0:
        return (s - 1) / np.sqrt(variance)
    if s < 0:
        return (s + 1) / np.sqrt(variance)
    return 0.0


def _autocorrelation(values: np.ndarray, max_lag: int) -> np.ndarray:
    """Sample autocorrelation at lags 0..max_lag (mean-removed, normalised by lag 0).

    A constant series carries no autocorrelation information, so zeros are returned
    (instead of 0/0 = NaN).
    """
    centred = values - values.mean()
    denominator = np.sum(centred**2)
    if denominator == 0:
        return np.zeros(max_lag + 1)
    return np.array(
        [np.sum(centred[: len(values) - k] * centred[k:]) / denominator for k in range(max_lag + 1)]
    )


def hamed_rao_factor(values: np.ndarray, alpha: float = 0.05) -> float:
    """Raw variance inflation factor n/n* of Hamed & Rao (1998).

    The series is detrended with Sen's slope, converted to ranks, and the autocorrelation of
    the ranks is computed. Only lags whose autocorrelation is significant at `alpha`
    contribute: n/n* = 1 + 2 / (n(n-1)(n-2)) * sum_k (n-k)(n-k-1)(n-k-2) * rho_k.
    The raw factor can fall below 1 (or even below 0) under negative autocorrelation;
    mann_kendall() floors it at 1.
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    detrended = values - sen_slope(values) * np.arange(n)
    ranks = sps.rankdata(detrended)
    rho = _autocorrelation(ranks, n - 1)
    bound = sps.norm.ppf(1 - alpha / 2) / np.sqrt(n)
    total = sum(
        (n - k) * (n - k - 1) * (n - k - 2) * rho[k] for k in range(1, n) if abs(rho[k]) > bound
    )
    return 1 + 2 / (n * (n - 1) * (n - 2)) * total


def mann_kendall(values, alpha: float = 0.05) -> dict:
    """Mann-Kendall trend test, original and Hamed-Rao corrected, plus Sen's slope.

    Why both: yearly energy series are autocorrelated (this year resembles last year), which
    makes the original test far too confident. The Hamed-Rao version widens the variance
    accordingly. Both are reported so the difference is visible.
    """
    values = np.asarray(pd.Series(values).dropna(), dtype=float)
    n = len(values)
    if n < 4:
        raise ValueError("Mann-Kendall needs at least 4 observations")
    s = _mk_s(values)
    variance = _mk_variance(values)
    if variance <= 0:  # constant series: no trend can be detected
        return {
            "n": n,
            "s": s,
            "tau": 0.0,
            "z": 0.0,
            "p": 1.0,
            "z_hamed_rao": 0.0,
            "p_hamed_rao": 1.0,
            "variance_factor": 1.0,
            "variance_factor_raw": 1.0,
            "sen_slope": 0.0,
            "trend": "no trend",
        }
    raw_factor = hamed_rao_factor(values, alpha)
    # Conservative floor: the correction may widen the variance (positive autocorrelation,
    # the case it was designed for) but never make the test MORE confident than the
    # original, and a negative variance would be meaningless.
    factor = max(raw_factor, 1.0)
    z = _z_score(s, variance)
    z_hr = _z_score(s, variance * factor)
    p = 2 * (1 - sps.norm.cdf(abs(z)))
    p_hr = 2 * (1 - sps.norm.cdf(abs(z_hr)))
    slope = sen_slope(values)
    if p_hr < alpha:
        trend = "increasing" if z_hr > 0 else "decreasing"
    else:
        trend = "no significant trend"
    return {
        "n": n,
        "s": s,
        "tau": s / (0.5 * n * (n - 1)),
        "z": float(z),
        "p": float(p),
        "z_hamed_rao": float(z_hr),
        "p_hamed_rao": float(p_hr),
        "variance_factor": float(factor),
        "variance_factor_raw": float(raw_factor),
        "sen_slope": slope,
        "trend": trend,
    }


def correlation_tests(x, y) -> dict:
    """Pearson r and Spearman rho with p-values and n, on pairwise-complete data."""
    data = pd.DataFrame({"x": x, "y": y}).dropna()
    pearson = sps.pearsonr(data["x"], data["y"])
    spearman = sps.spearmanr(data["x"], data["y"])
    return {
        "n": len(data),
        "pearson_r": float(pearson.statistic),
        "pearson_p": float(pearson.pvalue),
        "spearman_rho": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
    }


# ---------------------------------------------------------------------------- step 59
def closure_diagnostics(shares: pd.DataFrame, tol: float = 1e-6) -> dict:
    """Checks that show the mix shares are a composition (parts of a fixed whole).

    - row sums: every row adds up to ~100, so the parts are not free variables;
    - covariance eigenvalues: with a fixed sum, one eigenvalue is ~0, so 8 shares carry
      only 7 independent dimensions (the rank is the count of eigenvalues above `tol`
      times the largest one);
    - pairwise correlations: the constant sum pushes correlations negative (raising one
      share must lower the others), which Aitchison (1986) calls spurious correlation.
    """
    row_sums = shares.sum(axis=1)
    eigenvalues = np.linalg.eigvalsh(np.cov(shares.to_numpy(), rowvar=False))
    corr = shares.corr().to_numpy()
    off_diagonal = corr[~np.eye(len(corr), dtype=bool)]
    return {
        "n_rows": len(shares),
        "n_parts": shares.shape[1],
        "row_sum_min": float(row_sums.min()),
        "row_sum_max": float(row_sums.max()),
        "smallest_eigenvalue": float(eigenvalues.min()),
        "largest_eigenvalue": float(eigenvalues.max()),
        "rank": int((eigenvalues > tol * eigenvalues.max()).sum()),
        "share_negative_correlations": float((off_diagonal < 0).mean()),
        "mean_pairwise_correlation": float(off_diagonal.mean()),
    }


# ---------------------------------------------------------------------------- step 69
def compare_groups(values: pd.Series, groups: pd.Series, min_size: int) -> dict:
    """Kruskal-Wallis test: do `values` differ between groups (each with >= min_size rows)?

    Rank-based, so it needs no normality and is not driven by a few extreme residuals.
    Smaller groups are listed but left out of the test, because a median of 2-3 countries
    is not a stable summary.
    """
    frame = pd.DataFrame({"value": values, "group": groups}).dropna()
    sizes = frame["group"].value_counts()
    kept = sizes[sizes >= min_size].index
    tested = frame[frame["group"].isin(kept)]
    samples = [g["value"].to_numpy() for _, g in tested.groupby("group")]
    test = sps.kruskal(*samples)
    summary = (
        frame.groupby("group")["value"]
        .agg(n="size", median="median", mean="mean")
        .sort_values("median")
    )
    return {
        "n_tested": len(tested),
        "groups_tested": sorted(kept),
        "groups_too_small": sorted(set(sizes.index) - set(kept)),
        "kruskal_h": float(test.statistic),
        "kruskal_p": float(test.pvalue),
        "by_group": summary.reset_index().to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------- step 106
def pairwise_mannwhitney(values: pd.Series, groups: pd.Series, order: list[str]) -> pd.DataFrame:
    """Two-sided Mann-Whitney U for every pair of groups, with Holm-corrected p-values.

    The post-hoc step after a significant Kruskal-Wallis: which pairs differ? Holm controls
    the family-wise error over all pairs and is uniformly more powerful than Bonferroni.
    Rank-biserial r = 1 - 2U / (n_a n_b) gives the effect size (-1..1).
    """
    frame = pd.DataFrame({"value": values, "group": groups}).dropna()
    rows = []
    for i, a in enumerate(order):
        for b in order[i + 1 :]:
            x = frame.loc[frame["group"] == a, "value"]
            y = frame.loc[frame["group"] == b, "value"]
            test = sps.mannwhitneyu(x, y, alternative="two-sided")
            rows.append(
                {
                    "group_a": a,
                    "group_b": b,
                    "n_a": len(x),
                    "n_b": len(y),
                    "median_a": float(x.median()),
                    "median_b": float(y.median()),
                    "u": float(test.statistic),
                    "rank_biserial": float(1 - 2 * test.statistic / (len(x) * len(y))),
                    "p": float(test.pvalue),
                }
            )
    table = pd.DataFrame(rows)
    reject, p_holm, _, _ = multipletests(table["p"], alpha=config.ALPHA, method="holm")
    table["p_holm"] = p_holm
    table["significant_holm"] = reject
    return table


def two_group_mannwhitney(values: pd.Series, in_group: pd.Series) -> dict:
    """Two-sided Mann-Whitney U of `values` where in_group is True vs False.

    Rank-based, so a few very dirty or very clean grids cannot drive the result. Returns
    both medians, U, p and the rank-biserial effect size r = 1 - 2U / (n_a n_b).
    """
    data = pd.DataFrame({"v": values, "g": in_group.astype(bool)}).dropna()
    a, b = data.loc[data["g"], "v"], data.loc[~data["g"], "v"]
    u, p = sps.mannwhitneyu(a, b, alternative="two-sided")
    return {
        "n_in": len(a),
        "n_out": len(b),
        "median_in": float(a.median()),
        "median_out": float(b.median()),
        "u": float(u),
        "p": float(p),
        "rank_biserial": float(1 - 2 * u / (len(a) * len(b))),
    }
