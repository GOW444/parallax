"""Tests for the feedback-loop transforms (Phase 3): log1p, CLR, CAGR, tiers, trajectories."""

import numpy as np
import pandas as pd
import pytest

from src import config, features


# ---------------------------------------------------------------------------- log1p
def test_log_transform_adds_columns_and_rejects_negatives():
    frame = pd.DataFrame({"a": [0.0, np.e - 1]})
    out = features.log_transform(frame, ["a"])
    assert np.allclose(out["log_a"], [0.0, 1.0])
    assert "log_a" not in frame  # input untouched
    with pytest.raises(ValueError, match="negative"):
        features.log_transform(pd.DataFrame({"a": [-1.0]}), ["a"])


def test_skew_before_after_reduces_right_skew():
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"x": rng.lognormal(3, 1.2, 500)})
    table = features.skew_before_after(frame, ["x"])
    assert table.loc[0, "skew_raw"] > 2
    assert abs(table.loc[0, "skew_log1p"]) < table.loc[0, "skew_raw"] / 4


# ---------------------------------------------------------------------------- CLR
def _shares() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "coal_share_elec": [50.0, 0.0, 10.0],
            "hydro_share_elec": [30.0, 100.0, 10.0],
            "wind_share_elec": [20.0, 0.0, 80.0],
        }
    )


def test_clr_rows_sum_to_zero_and_columns_are_renamed():
    out = features.clr(_shares())
    assert np.allclose(out.sum(axis=1), 0)
    assert list(out.columns) == ["clr_coal", "clr_hydro", "clr_wind"]


def test_clr_is_invariant_to_scaling_the_row():
    shares = _shares()
    pd.testing.assert_frame_equal(features.clr(shares), features.clr(shares * 0.37))


def test_clr_handles_zeros_through_eps():
    out = features.clr(_shares(), eps=0.1)
    assert np.isfinite(out.to_numpy()).all()
    # a zero share sits further below the row mean when eps is smaller
    assert features.clr(_shares(), eps=0.01).loc[1, "clr_coal"] < out.loc[1, "clr_coal"]


def test_clr_rejects_nan_and_negative():
    with pytest.raises(ValueError, match="NaN"):
        features.clr(_shares().assign(coal_share_elec=[np.nan, 0.0, 10.0]))
    with pytest.raises(ValueError, match="non-negative"):
        features.clr(_shares().assign(coal_share_elec=[-1.0, 0.0, 10.0]))


# ---------------------------------------------------------------------------- CAGR, slope
def test_cagr_known_values():
    start = pd.Series([100.0, 100.0, 0.0])
    end = pd.Series([200.0, 100.0, 50.0])
    out = features.cagr(start, end, years=16)
    assert out.iloc[0] == pytest.approx(2 ** (1 / 16) - 1)  # doubling in 16 years: ~4.4%/yr
    assert out.iloc[1] == 0
    assert np.isnan(out.iloc[2])  # no growth rate from a zero start


def test_yearly_slope_recovers_a_line_and_skips_incomplete_countries():
    years = list(range(2000, 2005))
    panel = pd.DataFrame(
        {
            "country": ["A"] * 5 + ["B"] * 4,
            "year": years + years[:4],
            "v": [2 * y - 4000 for y in years] + [1.0] * 4,
        }
    )
    slopes = features.yearly_slope(panel, "v", (2000, 2004))
    assert slopes.to_dict() == pytest.approx({"A": 2.0})


# ---------------------------------------------------------------------------- tiers
def test_income_tiers_quartiles_and_thresholds():
    gdp = pd.Series(np.arange(1, 9, dtype=float), index=[f"C{i}" for i in range(8)])
    tiers, thresholds = features.income_tiers(gdp)
    assert tiers.iloc[0] == config.INCOME_TIER_LABELS[0]
    assert tiers.iloc[-1] == config.INCOME_TIER_LABELS[-1]
    assert thresholds["n_countries"].tolist() == [2, 2, 2, 2]
    assert thresholds["gdp_pc_from"].iloc[0] == 1 and thresholds["gdp_pc_to"].iloc[-1] == 8


# ---------------------------------------------------------------------------- pre-2019 guard
def test_pre2019_builder_raises_on_future_years():
    panel = pd.DataFrame({"country": ["A", "A"], "year": [2018, 2019]})
    with pytest.raises(ValueError, match="leakage"):
        features.trajectories_pre2019(panel, pd.DataFrame(), pd.Series(dtype=str), ["A"])


# ---------------------------------------------------------------------------- loop helpers
def test_scramble_rows_only_touches_selected_rows_and_keeps_year():
    panel = pd.DataFrame({"year": [2018, 2019], "v": [10.0, 10.0]})
    out = features.scramble_rows(panel, panel["year"] > 2018)
    assert out.loc[0, "v"] == 10.0 and out.loc[1, "v"] != 10.0
    assert out["year"].tolist() == [2018, 2019]
    assert features.changed_columns(panel, out) == ["v"]


def test_neighbour_shift_reports_rank_change_between_spaces():
    shares = pd.DataFrame(
        {"a": [50.0, 49.0, 10.0], "b": [50.0, 51.0, 90.0], "c": [0.0, 0.0, 0.0]},
        index=["X", "Y", "Z"],
    )
    clr_values = features.clr(shares)
    shift = features.neighbour_shift(shares, clr_values)
    assert shift["n_pairs"] == 3 and len(shift["pair"]) == 2
    assert -1 <= shift["spearman_rho_distances"] <= 1


# ---------------------------------------------------------------------------- iteration 2
def test_decoupling_class_covers_all_four_cases():
    from src import config

    gdp = pd.Series([0.03, 0.03, 0.01, -0.01])
    energy = pd.Series([-0.01, 0.01, 0.02, -0.02])
    assert features.decoupling_class(gdp, energy).tolist() == config.DECOUPLING_CLASSES


def test_tier_lowcarbon_reports_median_of_changes():
    traj = pd.DataFrame(
        {
            "income_tier": ["Low"] * 3,
            "lowcarbon_2000": [10.0, 50.0, 90.0],
            "d_lowcarbon": [0.0, 0.0, -60.0],
        }
    )
    row = features.tier_lowcarbon(traj).set_index("tier").loc["Low"]
    assert row["median_start"] == 50 and row["median_end"] == 30  # ends: 10, 50, 30
    assert row["median_change"] == 0  # not 30 - 50
