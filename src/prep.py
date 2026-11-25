"""Phase 1 data preparation: load, filter, derive, inspect missingness and interpolate.

Every function returns a new DataFrame (inputs are never modified in place), so each
step in the notebook can be inspected and explained on its own.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src import config


# ---------------------------------------------------------------------------- step 11
def load_raw(path: Path = config.RAW_CSV) -> pd.DataFrame:
    """Load the OWID CSV and fail fast if it is not the file the plan was written for."""
    df = pd.read_csv(path, dtype={"country": "string", "iso_code": "string"})
    if df.shape != config.RAW_SHAPE:
        raise ValueError(f"expected shape {config.RAW_SHAPE}, got {df.shape}")
    years = (int(df["year"].min()), int(df["year"].max()))
    if years != config.RAW_YEAR_RANGE:
        raise ValueError(f"expected years {config.RAW_YEAR_RANGE}, got {years}")
    if df["country"].nunique() != config.RAW_N_ENTITIES:
        raise ValueError(f"expected {config.RAW_N_ENTITIES} entities")
    return df


# ---------------------------------------------------------------------------- step 12
def drop_aggregates(
    df: pd.DataFrame, expected_countries: int | None = config.N_COUNTRIES_WITH_ISO
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep only rows with an ISO code; return (countries, dropped-entity table).

    Why: OWID mixes countries with aggregates (World, continents, income groups, "(EI)",
    "(EIA)", "(Ember)", "(Shift)", USSR, ...). Aggregates carry no ISO code. Keeping them
    would count the same energy twice. Kosovo is a real country but has no ISO code in
    this file, so it is dropped too and labelled separately so the report can say so.
    """
    has_iso = df["iso_code"].notna()
    dropped_names = sorted(df.loc[~has_iso, "country"].unique())
    reasons = [
        "real country without ISO code" if name == "Kosovo" else "aggregate (no ISO code)"
        for name in dropped_names
    ]
    dropped = pd.DataFrame({"entity": dropped_names, "reason": reasons})
    countries = df.loc[has_iso].reset_index(drop=True)
    n_found = countries["country"].nunique()
    if expected_countries is not None and n_found != expected_countries:
        raise ValueError(f"expected {expected_countries} countries with an ISO code, got {n_found}")
    return countries, dropped


# ---------------------------------------------------------------------------- step 13
def filter_years(
    df: pd.DataFrame, start: int = config.YEAR_START, end: int = config.YEAR_END
) -> pd.DataFrame:
    """Keep the analysis window and only the core columns used anywhere in the workflow."""
    in_window = df["year"].between(start, end)
    return df.loc[in_window, config.CORE_RAW_COLS].reset_index(drop=True)


# ---------------------------------------------------------------------------- step 14
def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Add per-person columns that the raw file does not provide.

    gdp_pc: GDP (PPP, international-$) per person.
    ghg_pc: electricity-sector emissions in tonnes CO2e per person
            (raw column is in million tonnes, hence * 1e6).
    """
    out = df.copy()
    out["gdp_pc"] = out["gdp"] / out["population"]
    out["ghg_pc"] = out["greenhouse_gas_emissions"] * 1e6 / out["population"]
    return out


# ---------------------------------------------------------------------------- step 15
def missingness_by_year(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Percent of countries missing each column in each year (rows = columns, cols = years)."""
    pct = df.groupby("year")[columns].apply(lambda g: g.isna().mean() * 100)
    return pct.T.round(1)


# ---------------------------------------------------------------------------- step 17
def producer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per-country fossil-producer features that avoid the post-2016 coverage break.

    Why: up to 2016 the source records non-producers as explicit 0. From 2017 it lists
    only the main producers and leaves everyone else blank, including ~50 countries that
    really produce. Filling 2017+ blanks with 0 would therefore mislabel real producers,
    so only data up to PRODUCER_LAST_FULL_YEAR is ever used.

    Returns (features, lost_counts): one row per country with
    <fuel>_prod_pc_2016 and <fuel>_prod_pc_mean_00_16 (kWh per person), and the number
    of countries per fuel that had production > 0 in 2016 but are blank in 2017.
    """
    last = config.PRODUCER_LAST_FULL_YEAR
    first, _ = config.PRODUCER_HISTORY_YEARS
    history = df[df["year"].between(first, last)]
    features = pd.DataFrame(index=pd.Index(sorted(df["country"].unique()), name="country"))
    lost_counts = {}
    for col in config.RAW_PRODUCER_COLS:
        fuel = col.split("_")[0]  # "oil", "gas", "coal"
        by_year = df.pivot(index="country", columns="year", values=col)
        features[f"{fuel}_prod_pc_{last}"] = by_year[last]
        features[f"{fuel}_prod_pc_mean_00_16"] = history.groupby("country")[col].mean()
        produced = by_year[last] > 0
        blank_next = by_year[last + 1].isna()
        lost_counts[fuel] = int((produced & blank_next).sum())
    return features.reset_index(), lost_counts


# ---------------------------------------------------------------------------- step 18
def _short_gap_mask(series: pd.Series, limit: int) -> pd.Series:
    """True for NaNs that sit inside a gap of at most `limit` years with data on both sides."""
    is_nan = series.isna()
    gap_id = (~is_nan).cumsum()  # every NaN run shares the id of the value before it
    gap_len = is_nan.groupby(gap_id).transform("sum")
    has_before = series.ffill().notna()
    has_after = series.bfill().notna()
    return is_nan & (gap_len <= limit) & has_before & has_after


def interpolate_within_country(
    df: pd.DataFrame, columns: list[str], limit: int = config.INTERP_LIMIT
) -> tuple[pd.DataFrame, pd.Series]:
    """Linearly interpolate short internal gaps, one country at a time, along time only.

    Rules (each one is tested):
    - never borrows values from another country;
    - never extrapolates before a country's first or after its last observed year;
    - fills a gap only if the WHOLE gap is <= `limit` years. Longer gaps stay missing
      instead of being partly filled, which would invent a trend.

    Returns (filled frame, number of cells filled per column).
    """
    out = df.sort_values(["country", "year"]).reset_index(drop=True)
    filled = pd.Series(0, index=columns, dtype=int)
    for col in columns:
        groups = out.groupby("country", sort=False)[col]
        mask = groups.transform(lambda s: _short_gap_mask(s, limit)).astype(bool)
        interpolated = groups.transform(lambda s: s.interpolate(method="linear"))
        out.loc[mask, col] = interpolated[mask]
        filled[col] = int(mask.sum())
    return out, filled


def interpolation_columns() -> list[str]:
    """Columns that may be interpolated: smooth physical series, never producer columns."""
    return (
        ["gdp", "greenhouse_gas_emissions"]
        + config.INTENSIVE_COLS
        + config.MIX_SHARE_COLS
        + [config.LOW_CARBON_SHARE_COL, config.GENERATION_COL, config.LOW_CARBON_TWH_COL]
        + config.MIX_TWH_COLS
    )


def classify_missing(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Count missing cells per column by where they sit in each country's series.

    Categories: the country never reports the column; before its first value (leading
    edge); after its last value (trailing edge); between two values (internal gap).
    Only internal gaps can be interpolated without extrapolating.
    """
    ordered = df.sort_values(["country", "year"])
    country = ordered["country"]
    rows = []
    for col in columns:
        present = ordered[col].notna()
        missing = ~present
        any_value = present.groupby(country).transform("any")
        seen_before = present.groupby(country).cumsum() > 0
        seen_after = present[::-1].groupby(country[::-1]).cumsum()[::-1] > 0
        rows.append(
            {
                "column": col,
                "country_never_reports": int((missing & ~any_value).sum()),
                "leading_edge": int((missing & any_value & ~seen_before).sum()),
                "trailing_edge": int((missing & any_value & seen_before & ~seen_after).sum()),
                "internal_gap": int((missing & seen_before & seen_after).sum()),
            }
        )
    return pd.DataFrame(rows)


def count_missing(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Number of missing cells per column (used before/after interpolation)."""
    return df[columns].isna().sum().astype(np.int64)


# ---------------------------------------------------------------------------- step 22
def close_mix_shares(
    df: pd.DataFrame, tolerance: float = config.MIX_SUM_TOLERANCE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Make the 8 electricity-mix shares a proper composition (complete, summing to 100).

    1. Structural zeros: a share that is missing while the other shares already add up to
       the whole grid (>= 100 - tolerance) AND whose TWh column is also missing is a source
       the country does not use (e.g. nuclear in Chile or Saudi Arabia). Both the share and
       its TWh are set to 0, so share and TWh views stay consistent. Leaving them blank
       would drop those countries from every analysis needing all 8 sources.
    2. Closure: complete rows whose sum is off by more than `tolerance` pp are rescaled to
       100. This fixes source inconsistencies (Chile's per-source TWh exceed its total
       generation by up to 12%). Later CLR transforms use only ratios, which rescaling
       does not change.
    3. low_carbon_share_elec is recomputed from the closed shares so the two always agree.

    Returns (closed frame, per-country log of the changes).
    """
    mix, parts = config.MIX_SHARE_COLS, config.LOW_CARBON_PARTS
    out = df.copy()
    shares = out[mix]
    n_missing = shares.isna().sum(axis=1)
    partial = (n_missing > 0) & (n_missing < len(mix))
    whole_grid_present = shares.sum(axis=1) >= 100 - tolerance

    zero_filled = pd.Series(0, index=out.index)
    for share_col, twh_col in zip(mix, config.MIX_TWH_COLS, strict=True):
        is_zero = partial & whole_grid_present & out[share_col].isna() & out[twh_col].isna()
        out.loc[is_zero, [share_col, twh_col]] = 0.0
        zero_filled += is_zero.astype(int)

    complete = out[mix].notna().all(axis=1)
    total = out[mix].sum(axis=1)
    off = complete & ((total - 100).abs() > tolerance)
    out.loc[off, mix] = out.loc[off, mix].div(total[off], axis=0) * 100

    old_low_carbon = out[config.LOW_CARBON_SHARE_COL].copy()
    out.loc[complete, config.LOW_CARBON_SHARE_COL] = out.loc[complete, parts].sum(axis=1)
    low_carbon_change = (out[config.LOW_CARBON_SHARE_COL] - old_low_carbon).abs()

    changes = pd.DataFrame(
        {
            "country": out["country"],
            "zero_filled_cells": zero_filled,
            "renormalised_rows": off.astype(int),
            "max_sum_before": total.where(off),
            "max_low_carbon_change_pp": low_carbon_change.where(complete),
        }
    )
    log = changes.groupby("country").agg(
        zero_filled_cells=("zero_filled_cells", "sum"),
        renormalised_rows=("renormalised_rows", "sum"),
        max_sum_before=("max_sum_before", "max"),
        max_low_carbon_change_pp=("max_low_carbon_change_pp", "max"),
    )
    touched = (log["zero_filled_cells"] > 0) | (log["renormalised_rows"] > 0)
    return out, log[touched].reset_index()


# ---------------------------------------------------------------------------- step 21
def apply_coverage_rule(
    df: pd.DataFrame,
    columns: list[str] = config.CORE_ELEC_COLS,
    max_missing: float = config.MAX_MISSING_SHARE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Drop countries missing more than `max_missing` of their core electricity cells.

    Why: a country with mostly empty grid data cannot be placed reliably in any chart or
    model. Returns (kept rows, table of dropped countries with their missing share).
    """
    missing_share = df.groupby("country")[columns].apply(lambda g: g.isna().to_numpy().mean())
    too_sparse = missing_share[missing_share > max_missing]
    dropped = too_sparse.round(3).rename("missing_share").sort_values().reset_index()
    kept = df[~df["country"].isin(too_sparse.index)].reset_index(drop=True)
    return kept, dropped


# ---------------------------------------------------------------------------- step 22
def sanity_checks(
    df: pd.DataFrame, tolerance: float = config.MIX_SUM_TOLERANCE
) -> dict[str, float | int]:
    """Check the cleaned panel and raise if any rule is broken; return the evidence.

    Rules: no duplicate (country, year); no negative values; every complete mix row sums
    to 100 within `tolerance`; low_carbon_share_elec equals the sum of its 5 parts.
    """
    mix = config.MIX_SHARE_COLS
    numeric = df.select_dtypes("number").drop(columns="year")
    complete = df[mix].notna().all(axis=1)
    mix_sum = df.loc[complete, mix].sum(axis=1)
    low_carbon_gap = (
        df.loc[complete, config.LOW_CARBON_SHARE_COL]
        - df.loc[complete, config.LOW_CARBON_PARTS].sum(axis=1)
    ).abs()
    checks = {
        "rows": len(df),
        "countries": int(df["country"].nunique()),
        "duplicate_country_years": int(df.duplicated(["country", "year"]).sum()),
        "negative_cells": int((numeric < 0).sum().sum()),
        "complete_mix_rows": int(complete.sum()),
        "mix_sum_min": float(mix_sum.min()),
        "mix_sum_max": float(mix_sum.max()),
        "mix_rows_outside_tolerance": int(((mix_sum - 100).abs() > tolerance).sum()),
        "low_carbon_max_gap_pp": float(low_carbon_gap.max()),
    }
    failures = [
        name
        for name in ("duplicate_country_years", "negative_cells", "mix_rows_outside_tolerance")
        if checks[name] > 0
    ]
    if checks["low_carbon_max_gap_pp"] > 1e-6:
        failures.append("low_carbon_max_gap_pp")
    if failures:
        raise ValueError(f"sanity checks failed: {failures} -> {checks}")
    return checks


# ---------------------------------------------------------------------------- step 23
def balanced_countries(df: pd.DataFrame) -> list[str]:
    """Countries with generation and all 8 mix shares in EVERY year of the window.

    Why: summing countries whose coverage changes from year to year creates artificial
    jumps in world totals. A fixed set of countries keeps global trends honest.
    """
    needed = [config.GENERATION_COL] + config.MIX_SHARE_COLS + config.MIX_TWH_COLS
    n_years = config.YEAR_END - config.YEAR_START + 1
    complete_rows = df[df[needed].notna().all(axis=1)]
    years_per_country = complete_rows.groupby("country")["year"].nunique()
    return sorted(years_per_country[years_per_country == n_years].index)


# ---------------------------------------------------------------------------- step 25
_SOURCE_BY_PREFIX = dict(
    zip(
        [c.removesuffix("_share_elec") for c in config.MIX_SHARE_COLS],
        config.SOURCE_NAMES,
        strict=True,
    )
)
_SOURCE_BY_TWH = dict(zip(config.MIX_TWH_COLS, config.SOURCE_NAMES, strict=True))
_FIXED_DESCRIPTIONS = {
    "country": ("Country or territory name", "-", "raw OWID"),
    "iso_code": ("ISO 3166-1 alpha-3 code", "-", "raw OWID"),
    "year": ("Calendar year", "year", "raw OWID"),
    "population": ("Population", "people", "raw OWID"),
    "gdp": ("Gross domestic product (PPP, ends 2018)", "international-$", "raw OWID"),
    "greenhouse_gas_emissions": (
        "Greenhouse-gas emissions from electricity generation",
        "MtCO2e",
        "raw OWID",
    ),
    "energy_per_capita": ("Primary energy consumption per person", "kWh per person", "raw OWID"),
    "per_capita_electricity": ("Electricity generation per person", "kWh per person", "raw OWID"),
    "carbon_intensity_elec": ("Carbon intensity of electricity", "gCO2 per kWh", "raw OWID"),
    "energy_per_gdp": (
        "Primary energy per unit of GDP (ends 2018)",
        "kWh per international-$",
        "raw OWID",
    ),
    "low_carbon_share_elec": (
        "Share of electricity from nuclear + renewables (recomputed from closed shares)",
        "% of generation",
        "raw OWID, closed in Phase 1",
    ),
    "electricity_generation": ("Total electricity generation", "TWh", "raw OWID"),
    "low_carbon_electricity": ("Electricity generated from low-carbon sources", "TWh", "raw OWID"),
    "gdp_pc": ("GDP per person = gdp / population", "international-$ per person", "derived"),
    "ghg_pc": (
        "Electricity-sector emissions per person = greenhouse_gas_emissions x 1e6 / population",
        "tCO2e per person",
        "derived",
    ),
}


def _describe_column(col: str) -> tuple[str, str, str]:
    """(description, unit, origin) for one column of the cleaned data."""
    if col in _FIXED_DESCRIPTIONS:
        return _FIXED_DESCRIPTIONS[col]
    if col.endswith("_share_elec"):
        source = _SOURCE_BY_PREFIX[col.removesuffix("_share_elec")]
        return (
            f"Share of electricity from {source.lower()}",
            "% of generation",
            "raw OWID, closed in Phase 1",
        )
    if col in _SOURCE_BY_TWH:
        return (f"Electricity generated from {_SOURCE_BY_TWH[col].lower()}", "TWh", "raw OWID")
    if "_prod_pc_" in col:
        fuel = col.split("_")[0]
        period = "2016 value" if col.endswith("_2016") else "2000-2016 mean"
        return (
            f"{fuel.capitalize()} production per person, {period}",
            "kWh per person",
            "derived (pre-2017 data only)",
        )
    raise KeyError(f"no description for column {col!r}")


def data_dictionary(columns: list[str]) -> pd.DataFrame:
    """Table of every column in the processed data: description, unit and origin."""
    rows = [(col, *_describe_column(col)) for col in columns]
    return pd.DataFrame(rows, columns=["column", "description", "unit", "origin"])


# ---------------------------------------------------------------------------- step 24
def world_check_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """OWID's own 'World' aggregate (TWh by source), used ONLY to validate our sums."""
    cols = ["year", config.GENERATION_COL] + config.MIX_TWH_COLS
    in_window = raw["year"].between(config.YEAR_START, config.YEAR_END)
    world = raw.loc[(raw["country"] == "World") & in_window, cols]
    return world.sort_values("year").reset_index(drop=True)
