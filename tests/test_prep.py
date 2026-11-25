"""Tests for Phase 1 data preparation (src/prep.py), on small hand-made frames."""

import numpy as np
import pandas as pd
import pytest

from src import config, prep

nan = np.nan


def _panel(values: dict[str, list[float]], years: list[int], col: str = "x") -> pd.DataFrame:
    rows = [
        {"country": c, "year": y, col: v}
        for c, vals in values.items()
        for y, v in zip(years, vals, strict=True)
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- add_derived (step 14)
def test_add_derived_units():
    df = pd.DataFrame({"gdp": [1e9], "population": [1e6], "greenhouse_gas_emissions": [2.0]})
    out = prep.add_derived(df)
    assert out.loc[0, "gdp_pc"] == pytest.approx(1000.0)
    assert out.loc[0, "ghg_pc"] == pytest.approx(2.0)  # 2 Mt / 1M people = 2 t per person
    assert "gdp_pc" not in df.columns  # input not modified


# ---------------------------------------------------------------- interpolation (step 18)
def test_interpolation_fills_short_internal_gap_linearly():
    df = _panel({"A": [1, nan, nan, 4]}, [2000, 2001, 2002, 2003])
    out, filled = prep.interpolate_within_country(df, ["x"], limit=3)
    assert out["x"].tolist() == [1, 2, 3, 4]
    assert filled["x"] == 2


def test_interpolation_never_extrapolates_edges():
    df = _panel({"A": [nan, 5, nan]}, [2000, 2001, 2002])
    out, filled = prep.interpolate_within_country(df, ["x"], limit=3)
    assert out["x"].isna().tolist() == [True, False, True]
    assert filled["x"] == 0


def test_interpolation_leaves_long_gap_completely_untouched():
    df = _panel({"A": [1, nan, nan, nan, nan, 6]}, list(range(2000, 2006)))
    out, filled = prep.interpolate_within_country(df, ["x"], limit=3)
    assert out["x"].isna().sum() == 4  # not partly filled
    assert filled["x"] == 0


def test_interpolation_never_crosses_countries():
    # A ends with a gap, B starts with a gap: neither may borrow from the other
    df = _panel({"A": [1, 2, nan], "B": [nan, 10, 11]}, [2000, 2001, 2002])
    out, _ = prep.interpolate_within_country(df, ["x"], limit=3)
    a = out[out["country"] == "A"]["x"].tolist()
    b = out[out["country"] == "B"]["x"].tolist()
    assert np.isnan(a[2]) and np.isnan(b[0])


# ---------------------------------------------------------------- producers (step 17)
def _producer_frame():
    years = [2000, 2016, 2017]
    rows = []
    # X produces oil up to 2016 and disappears in 2017; the 2017 value must never be used
    for y, v in zip(years, [4.0, 6.0, nan], strict=True):
        rows.append({"country": "X", "year": y, "oil_prod_per_capita": v})
    # Y is a recorded non-producer (explicit 0) up to 2016
    for y, v in zip(years, [0.0, 0.0, nan], strict=True):
        rows.append({"country": "Y", "year": y, "oil_prod_per_capita": v})
    # Z has a huge 2017 value that must not leak into the features
    for y, v in zip(years, [1.0, 1.0, 999.0], strict=True):
        rows.append({"country": "Z", "year": y, "oil_prod_per_capita": v})
    df = pd.DataFrame(rows)
    df["gas_prod_per_capita"] = 0.0
    df["coal_prod_per_capita"] = 0.0
    return df


def test_producer_features_use_only_years_up_to_2016():
    feats, lost = prep.producer_features(_producer_frame())
    feats = feats.set_index("country")
    assert feats.loc["X", "oil_prod_pc_2016"] == 6.0
    assert feats.loc["X", "oil_prod_pc_mean_00_16"] == 5.0
    assert feats.loc["Y", "oil_prod_pc_2016"] == 0.0
    assert feats.loc["Z", "oil_prod_pc_mean_00_16"] == 1.0  # 999 from 2017 ignored
    assert lost["oil"] == 1  # only X: produced in 2016, blank in 2017


# ---------------------------------------------------------------- classify_missing (step 19)
def test_classify_missing_categories():
    df = _panel({"A": [nan, 1, nan, 2, nan], "B": [nan] * 5}, list(range(2000, 2005)))
    row = prep.classify_missing(df, ["x"]).iloc[0]
    assert row["country_never_reports"] == 5  # all of B
    assert row["leading_edge"] == 1
    assert row["internal_gap"] == 1
    assert row["trailing_edge"] == 1


# ---------------------------------------------------------------- aggregates + window (28)
def test_drop_aggregates_keeps_iso_rows_and_labels_kosovo():
    df = pd.DataFrame(
        {
            "country": ["India", "World", "Kosovo", "Africa (EI)"],
            "iso_code": ["IND", None, None, None],
        }
    )
    kept, dropped = prep.drop_aggregates(df, expected_countries=1)
    assert kept["country"].tolist() == ["India"]
    reasons = dict(zip(dropped["entity"], dropped["reason"], strict=True))
    assert reasons["Kosovo"] == "real country without ISO code"
    assert reasons["World"] == "aggregate (no ISO code)"


def test_drop_aggregates_checks_expected_count():
    df = pd.DataFrame({"country": ["India"], "iso_code": ["IND"]})
    with pytest.raises(ValueError, match="expected 2"):
        prep.drop_aggregates(df, expected_countries=2)


def test_filter_years_window_and_core_columns():
    df = pd.DataFrame({col: [1.0, 1.0, 1.0] for col in config.CORE_RAW_COLS})
    df["year"] = [1999, 2000, 2022]
    df["unused_column"] = 0
    out = prep.filter_years(df, 2000, 2021)
    assert out["year"].tolist() == [2000]
    assert list(out.columns) == config.CORE_RAW_COLS


# ---------------------------------------------------------------- mix closure (step 22)
def _mix_row(country: str, shares: list[float], twh: list[float]) -> dict:
    row = {"country": country, "year": 2000, config.LOW_CARBON_SHARE_COL: nan}
    row.update(dict(zip(config.MIX_SHARE_COLS, shares, strict=True)))
    row.update(dict(zip(config.MIX_TWH_COLS, twh, strict=True)))
    return row


def test_close_mix_fills_structural_zero_and_recomputes_low_carbon():
    #           coal gas oil nuclear hydro solar wind other
    shares = [60, 20, 0, nan, 20, 0, 0, 0]
    twh = [6, 2, 0, nan, 2, 0, 0, 0]
    out, log = prep.close_mix_shares(pd.DataFrame([_mix_row("A", shares, twh)]))
    assert out.loc[0, "nuclear_share_elec"] == 0.0
    assert out.loc[0, "nuclear_electricity"] == 0.0  # TWh filled too, so views stay consistent
    assert out.loc[0, config.LOW_CARBON_SHARE_COL] == pytest.approx(20.0)
    assert log.loc[0, "zero_filled_cells"] == 1


def test_close_mix_does_not_zero_fill_when_grid_incomplete_or_twh_present():
    incomplete = _mix_row("A", [50, 20, 0, nan, 20, 0, 0, 0], [5, 2, 0, nan, 2, 0, 0, 0])
    twh_present = _mix_row("B", [60, 20, 0, nan, 20, 0, 0, 0], [6, 2, 0, 3, 2, 0, 0, 0])
    out, _ = prep.close_mix_shares(pd.DataFrame([incomplete, twh_present]))
    assert out["nuclear_share_elec"].isna().all()


def test_close_mix_renormalises_rows_off_by_more_than_tolerance():
    shares = [66, 22, 0, 0, 22, 0, 0, 0]  # sums to 110
    out, log = prep.close_mix_shares(pd.DataFrame([_mix_row("A", shares, [1] * 8)]))
    assert out.loc[0, config.MIX_SHARE_COLS].sum() == pytest.approx(100.0)
    assert out.loc[0, "coal_share_elec"] == pytest.approx(60.0)
    assert log.loc[0, "renormalised_rows"] == 1


# ---------------------------------------------------------------- coverage rule (step 21)
def test_coverage_rule_drops_sparse_countries_only():
    df = _panel({"Full": [1, 2, 3, 4], "Sparse": [1, nan, nan, nan]}, [2000, 2001, 2002, 2003])
    kept, dropped = prep.apply_coverage_rule(df, columns=["x"], max_missing=0.30)
    assert kept["country"].unique().tolist() == ["Full"]
    assert dropped.loc[0, "country"] == "Sparse"
    assert dropped.loc[0, "missing_share"] == 0.75


# ---------------------------------------------------------------- sanity checks (step 22)
def _clean_rows() -> pd.DataFrame:
    row = _mix_row("A", [50, 0, 0, 10, 40, 0, 0, 0], [1] * 8)
    row[config.LOW_CARBON_SHARE_COL] = 50.0
    second = dict(row, year=2001)
    return pd.DataFrame([row, second])


def test_sanity_checks_pass_on_clean_data():
    checks = prep.sanity_checks(_clean_rows())
    assert checks["duplicate_country_years"] == 0 and checks["negative_cells"] == 0


@pytest.mark.parametrize(
    ("breaker", "message"),
    [
        (lambda d: pd.concat([d, d.iloc[[0]]]), "duplicate_country_years"),
        (lambda d: d.assign(coal_electricity=-1.0), "negative_cells"),
        (lambda d: d.assign(coal_share_elec=70.0), "mix_rows_outside_tolerance"),
    ],
)
def test_sanity_checks_raise_on_broken_data(breaker, message):
    with pytest.raises(ValueError, match=message):
        prep.sanity_checks(breaker(_clean_rows()))


# ---------------------------------------------------------------- data dictionary (step 25)
def test_data_dictionary_covers_all_processed_columns():
    cols = config.CORE_RAW_COLS[:-3] + ["gdp_pc", "ghg_pc", "oil_prod_pc_2016"]
    table = prep.data_dictionary(cols)
    assert len(table) == len(cols)
    assert table["unit"].ne("").all()


# ---------------------------------------------------------------- missingness (step 15)
def test_missingness_by_year_percent():
    df = _panel({"A": [1, nan], "B": [nan, nan]}, [2000, 2001])
    pct = prep.missingness_by_year(df, ["x"])
    assert pct.loc["x", 2000] == 50.0
    assert pct.loc["x", 2001] == 100.0


# ---------------------------------------------------------------- endpoints (step 41)
def test_endpoint_change_uses_complete_3_year_windows():
    from src import features

    years = [2000, 2001, 2002, 2016, 2017, 2018]
    df = _panel(
        {"A": [10, 20, 30, 50, 50, 50], "B": [60, 60, 60, 40, 40, 40], "C": [1, nan, 1, 1, 1, 1]},
        years,
    )
    table = features.endpoint_change(df, "x").set_index("country")
    assert "C" not in table.index  # 2001 missing -> incomplete base window
    assert table.loc["A", "change"] == pytest.approx(30.0)  # 50 - mean(10, 20, 30)
    assert table.loc["A", "rank_change"] == 1  # rank 2 -> rank 1
    assert table.loc["B", "rank_change"] == -1
