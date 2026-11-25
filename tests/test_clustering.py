"""Tests for the iteration 1 clustering helpers (features, models, stats, plots)."""

import numpy as np
import pandas as pd
import pytest

from src import config, features, models, plots, stats


def _shares(rows: list[list[float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=config.MIX_SHARE_COLS)


# ---------------------------------------------------------------- features
def test_cluster_matrix_keeps_only_complete_rows():
    snap = pd.DataFrame(
        {
            "country": ["B", "A", "C"],
            "iso_code": ["BBB", "AAA", "CCC"],
            "population": [1, 2, 3],
            "x": [1.0, np.nan, 3.0],
            "y": [1.0, 2.0, 3.0],
        }
    )
    out = features.cluster_matrix(snap, ["x", "y"])
    assert out["country"].tolist() == ["B", "C"]  # A dropped, sorted by name
    assert out.index.tolist() == [0, 1]


def test_dominant_source_names_the_largest_share():
    frame = _shares([[60, 10, 0, 0, 30, 0, 0, 0], [0, 0, 0, 0, 5, 0, 95, 0]])
    assert features.dominant_source(frame).tolist() == ["Coal", "Wind"]


def test_iter2_country_set_flags_each_requirement():
    years = range(config.YEAR_START, config.YEAR_END + 1)
    rows = []
    for country in ("Full", "NoGdp"):
        for year in years:
            row = {"country": country, "year": year}
            for col in config.MIX_SHARE_COLS:
                row[col] = 12.5
            row.update(
                {
                    config.LOW_CARBON_SHARE_COL: 62.5,
                    config.TARGET_COL: 300.0,
                    "gdp_pc": np.nan if country == "NoGdp" and year == 2001 else 10_000.0,
                    "energy_per_capita": 20_000.0,
                    "per_capita_electricity": 5_000.0,
                    "energy_per_gdp": 1.5,
                }
            )
            rows.append(row)
    panel = pd.DataFrame(rows)
    producers = pd.DataFrame({"country": ["Full", "NoGdp"], "oil_prod_pc_mean_00_16": [0.0, 0.0]})
    table = features.iter2_country_set(panel, producers).set_index("country")
    assert table.loc["Full", "in_set"]
    assert not table.loc["NoGdp", "in_set"]
    assert not table.loc["NoGdp", "gdp_endpoints"] and table.loc["NoGdp", "grid_every_year"]


# ---------------------------------------------------------------- models
def _three_blobs() -> np.ndarray:
    rng = np.random.default_rng(0)
    centres = [(0, 0), (10, 0), (0, 10)]
    sizes = [30, 20, 10]
    return np.vstack([rng.normal(c, 0.5, size=(n, 2)) for c, n in zip(centres, sizes, strict=True)])


def test_kmeans_scan_and_choose_k_find_three_blobs():
    scan = models.kmeans_scan(_three_blobs(), range(2, 6))
    assert models.choose_k(scan) == 3
    assert scan.set_index("k").loc[3, "silhouette"] > 0.7


def test_choose_k_respects_min_cluster_size_and_ties():
    scan = pd.DataFrame(
        {"k": [2, 3, 4], "silhouette": [0.5, 0.5, 0.9], "min_cluster_size": [10, 10, 2]}
    )
    assert models.choose_k(scan, min_size=5) == 2  # k=4 too small; tie 2 vs 3 -> 2
    with pytest.raises(ValueError):
        models.choose_k(scan, min_size=50)


def test_fit_kmeans_numbers_clusters_by_size():
    labels, centres = models.fit_kmeans(_three_blobs(), 3)
    sizes = np.bincount(labels)[1:]
    assert sizes.tolist() == [30, 20, 10]
    assert centres.shape == (3, 2)


def test_describe_centres_uses_most_extreme_value():
    cols = ["coal_share_elec", "energy_per_capita"]
    names = models.describe_centres(np.array([[2.0, 0.5], [0.1, -3.0]]), cols)
    assert names == ["high Coal share", "low Energy per person"]


def test_silhouette_band_edges():
    assert models.silhouette_band(0.2) == "no substantial"
    assert models.silhouette_band(0.36) == "weak"
    assert models.silhouette_band(0.6) == "reasonable"
    assert models.silhouette_band(0.9) == "strong"


def test_pca_2d_loadings_lie_inside_unit_circle():
    z, _ = models.standardise(pd.DataFrame(_three_blobs(), columns=["a", "b"]), ["a", "b"])
    scores, summary = models.pca_2d(z, ["a", "b"])
    assert scores.shape == (60, 2)
    assert summary["cumulative_explained"] == pytest.approx(1.0)
    for load in summary["loadings"].values():
        assert np.hypot(load["PC1"], load["PC2"]) <= 1 + 1e-9


# ---------------------------------------------------------------- stats
def test_closure_diagnostics_detects_lost_dimension():
    rng = np.random.default_rng(1)
    raw = rng.dirichlet(np.ones(8), size=100) * 100
    result = stats.closure_diagnostics(_shares(raw.tolist()))
    assert result["rank"] == 7
    assert result["row_sum_min"] == pytest.approx(100)
    assert result["mean_pairwise_correlation"] < 0


# ---------------------------------------------------------------- plots
def test_cluster_colors_reuse_source_colours_then_fallback():
    names = ["high Hydro share", "high Energy per person", "high Hydro share", "low Coal share"]
    colours = plots.cluster_colors(names)
    assert colours[0] == config.SOURCE_COLORS["Hydro"]
    assert colours[1:] == config.CLUSTER_FALLBACK_COLORS[:3]
    assert len(set(colours)) == len(colours)
