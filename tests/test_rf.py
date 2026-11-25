"""Tests for the iteration 1 Random Forest helpers: leakage guard, folds, CV, error analysis."""

import numpy as np
import pandas as pd
import pytest

from src import config, features, logbook, models, stats


# ---------------------------------------------------------------- leakage guard
@pytest.mark.parametrize(
    "bad",
    [
        "coal_share_elec",
        "clr_hydro",
        "low_carbon_share_elec",
        "lowcarbon_slope",
        "d_lowcarbon",
        "lowcarbon_2000",
        "carbon_intensity_elec",
        "d_carbon_int",
        "d_coal",
        "d_solarwind",
        "archetype",
        "ghg_pc",
        "greenhouse_gas_emissions",
        "wind_electricity",
    ],
)
def test_assert_no_leakage_blocks_target_derived_columns(bad):
    with pytest.raises(ValueError, match="leakage"):
        models.assert_no_leakage(["gdp_pc", bad])


def test_assert_no_leakage_allows_the_iteration1_features():
    models.assert_no_leakage(config.RF_FEATURES_ITER1)  # must not raise


# ---------------------------------------------------------------- folds
def test_make_folds_is_balanced_reproducible_and_order_free():
    names = [f"C{i:03d}" for i in range(23)]
    folds = models.make_folds(names, n_folds=5)
    assert sorted(folds["fold"].unique()) == [1, 2, 3, 4, 5]
    assert folds["fold"].value_counts().max() - folds["fold"].value_counts().min() <= 1
    shuffled = models.make_folds(list(reversed(names)), n_folds=5)
    pd.testing.assert_frame_equal(folds, shuffled)  # input order does not matter


# ---------------------------------------------------------------- cross-validation
def _toy_rf_data(n: int = 60, noise_only: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(3)
    x = rng.uniform(0, 10, n)
    y = rng.normal(0, 1, n) if noise_only else 5 * x + rng.normal(0, 1, n)
    return pd.DataFrame(
        {"country": [f"C{i:03d}" for i in range(n)], "x": x, "z": rng.normal(size=n), "y": y}
    )


def test_cross_validate_rf_learns_signal_and_beats_baseline():
    data = _toy_rf_data()
    folds = models.make_folds(data["country"].tolist(), n_folds=5)
    metrics, oof, importance = models.cross_validate_rf(data, ["x", "z"], "y", folds)
    assert metrics["r2_mean"] > 0.8
    assert metrics["mae_mean"] < metrics["baseline_mae_mean"]
    assert len(oof) == len(data) and oof["country"].is_unique  # every row predicted once
    assert np.allclose(oof["residual"], oof["y"] - oof["predicted"])
    assert importance.iloc[0]["feature"] == "x"  # the real signal ranks first


def test_cross_validate_rf_runs_the_leakage_guard():
    data = _toy_rf_data().rename(columns={"z": "coal_share_elec"})
    folds = models.make_folds(data["country"].tolist(), n_folds=5)
    with pytest.raises(ValueError, match="leakage"):
        models.cross_validate_rf(data, ["x", "coal_share_elec"], "y", folds)


# ---------------------------------------------------------------- error analysis
def test_compare_groups_detects_shift_and_skips_small_groups():
    values = pd.Series([1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 99, 98])
    groups = pd.Series(["a"] * 5 + ["b"] * 5 + ["tiny"] * 2)
    result = stats.compare_groups(values, groups, min_size=5)
    assert result["groups_tested"] == ["a", "b"]
    assert result["groups_too_small"] == ["tiny"]
    assert result["kruskal_p"] < 0.05


def test_gdp_quartile_orders_poorest_first():
    quartiles = features.gdp_quartile(pd.Series([1, 2, 3, 4, 5, 6, 7, 8]))
    assert quartiles.iloc[0] == config.GDP_QUARTILE_LABELS[0]
    assert quartiles.iloc[-1] == config.GDP_QUARTILE_LABELS[-1]


def test_model_table_drops_incomplete_rows():
    snap = pd.DataFrame(
        {
            "country": ["B", "A", "C"],
            "iso_code": ["BBB", "AAA", "CCC"],
            "x": [1.0, 2.0, np.nan],
            "y": [1.0, np.nan, 3.0],
        }
    )
    assert features.model_table(snap, ["x"], "y")["country"].tolist() == ["B"]


# ---------------------------------------------------------------- inference wording
def test_inference_text_helpers():
    assert logbook.join_words(["a"]) == "a"
    assert logbook.join_words(["a", "b", "c"]) == "a, b and c"
    assert logbook.dominated_text(["Hydro", "Nuclear"]) == "hydro- and nuclear-dominated"
    assert logbook.significance_text(0.0001) == "p < 0.001, significant"
    assert logbook.significance_text(0.379) == "p = 0.379, not significant"
    block = {
        "groups_tested": ["a", "b"],
        "by_group": [{"group": "a", "median": -3.0}, {"group": "b", "median": 4.0}],
    }
    assert logbook.groups_by_sign(block) == (["a"], ["b"])
    assert logbook.group_medians_text(block, signed=True) == "a -3, b +4"


def test_pairwise_mannwhitney_holm_is_not_smaller_than_raw_p():
    values = pd.Series([1, 2, 3, 4, 5, 11, 12, 13, 14, 15, 6, 7, 8, 9, 10], dtype=float)
    groups = pd.Series(["a"] * 5 + ["b"] * 5 + ["c"] * 5)
    table = stats.pairwise_mannwhitney(values, groups, ["a", "b", "c"])
    assert len(table) == 3
    assert (table["p_holm"] >= table["p"] - 1e-12).all()
    ab = table[(table["group_a"] == "a") & (table["group_b"] == "b")].iloc[0]
    assert ab["rank_biserial"] == 1.0  # every a below every b


def test_ols_band_brackets_the_fit():
    rng = np.random.default_rng(1)
    x = rng.uniform(0, 10, 80)
    data = pd.DataFrame({"x": x, "y": 2 * x + rng.normal(0, 1, 80)})
    band = models.ols_band(data, "y", "x")
    assert (band["low"] <= band["fit"]).all() and (band["fit"] <= band["high"]).all()
