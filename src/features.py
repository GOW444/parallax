"""Feature construction: world totals (Phase 2) and the feedback-loop transforms (Phase 3).

Every function returns a new DataFrame and never modifies its input.
"""

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from scipy.stats import rankdata, spearmanr

from src import config


# ---------------------------------------------------------------------------- step 31
def global_mix_twh(panel: pd.DataFrame, countries: list[str]) -> pd.DataFrame:
    """World electricity generation by source (TWh) per year, summed over a fixed country set.

    Why a fixed set: if countries entered or left the sum from year to year, the totals
    would jump for reasons that have nothing to do with energy. The balanced panel is used.
    Returns one row per year with one column per source (SOURCE_NAMES) plus 'Total'.
    """
    subset = panel[panel["country"].isin(countries)]
    n_years = config.YEAR_END - config.YEAR_START + 1
    rows_per_country = subset.groupby("country")["year"].nunique()
    if (rows_per_country != n_years).any():
        raise ValueError("global_mix_twh needs a balanced set of countries")
    totals = subset.groupby("year")[config.MIX_TWH_COLS].sum()
    totals.columns = config.SOURCE_NAMES
    totals["Total"] = totals[config.SOURCE_NAMES].sum(axis=1)
    return totals


def low_carbon_share_of_total(twh: pd.DataFrame) -> pd.Series:
    """Low-carbon share (%) of the summed generation, per year."""
    low_carbon_sources = ["Nuclear", "Hydro", "Solar", "Wind", "Other renewables"]
    return twh[low_carbon_sources].sum(axis=1) / twh["Total"] * 100


# ---------------------------------------------------------------------------- step 32
def world_coverage_check(twh: pd.DataFrame, world: pd.DataFrame) -> pd.DataFrame:
    """Compare our balanced-panel sums with OWID's own 'World' row, year by year.

    Returns our total, OWID's world total, the coverage ratio (%) and the largest
    per-source ratio gap, so the report can state how representative the sums are.
    """
    world_by_year = world.set_index("year")
    world_sources = world_by_year[config.MIX_TWH_COLS]
    world_sources.columns = config.SOURCE_NAMES
    ratio_by_source = twh[config.SOURCE_NAMES] / world_sources * 100
    check = pd.DataFrame(
        {
            "balanced_panel_twh": twh["Total"],
            "owid_world_twh": world_sources.sum(axis=1),
            "coverage_pct": twh["Total"] / world_sources.sum(axis=1) * 100,
            "min_source_coverage_pct": ratio_by_source.min(axis=1),
            "max_source_coverage_pct": ratio_by_source.max(axis=1),
        }
    )
    return check.round(2)


# ---------------------------------------------------------------------------- step 41
def endpoint_mean(
    panel: pd.DataFrame, col: str, years: tuple[int, int], require_all: bool = True
) -> pd.Series:
    """Per-country mean of `col` over an inclusive year window (a 3-year endpoint).

    Why a 3-year mean: one noisy year (a drought for hydro, an outage) would otherwise
    decide a country's whole change. With require_all, a country needs every year of the
    window, so all endpoints are averaged over the same years.
    """
    first, last = years
    window = panel[panel["year"].between(first, last)]
    grouped = window.groupby("country")[col]
    means = grouped.mean()
    if require_all:
        complete = grouped.count() == (last - first + 1)
        means = means[complete]
    return means


def endpoint_change(
    panel: pd.DataFrame,
    col: str,
    base_years: tuple[int, int] = config.BASE_YEARS,
    end_years: tuple[int, int] = config.END_YEARS_GDP,
) -> pd.DataFrame:
    """Change in `col` between two 3-year endpoints, with each country's rank at both ends.

    Rank 1 = highest value. A large rank change means a country overtook (or fell behind)
    others, which a single-year snapshot cannot show.
    """
    base = endpoint_mean(panel, col, base_years).rename("base_mean")
    end = endpoint_mean(panel, col, end_years).rename("end_mean")
    table = pd.concat([base, end], axis=1, join="inner")
    table["change"] = table["end_mean"] - table["base_mean"]
    table["base_rank"] = table["base_mean"].rank(ascending=False, method="average")
    table["end_rank"] = table["end_mean"].rank(ascending=False, method="average")
    table["rank_change"] = table["base_rank"] - table["end_rank"]  # > 0 means moved up
    return table.reset_index()


def change_summary(table: pd.DataFrame, threshold: float = config.CHANGE_BIG_PP) -> dict:
    """Size and direction of the endpoint changes from `endpoint_change()`.

    Why split by direction: rises and falls cancel in a median or a global total, so a flat
    average can hide many countries moving a lot in opposite directions (inference I1-3).
    """
    change = table["change"]
    return {
        "n_countries": len(table),
        "threshold_pp": threshold,
        "median_change_pp": float(change.median()),
        "iqr_change_pp": [float(change.quantile(0.25)), float(change.quantile(0.75))],
        "n_changed_over_threshold": int((change.abs() > threshold).sum()),
        "share_changed_over_threshold": float((change.abs() > threshold).mean()),
        "n_rose_over_threshold": int((change > threshold).sum()),
        "n_fell_over_threshold": int((change < -threshold).sum()),
        "median_abs_rank_change": float(table["rank_change"].abs().median()),
        "largest_rises": _named_changes(table.nlargest(config.N_CHANGE_MOVERS, "change")),
        "largest_falls": _named_changes(table.nsmallest(config.N_CHANGE_MOVERS, "change")),
    }


def _named_changes(rows: pd.DataFrame) -> list[dict]:
    """[{'country', 'base', 'end', 'change'}] rounded to 1 decimal, for the inference text."""
    return [
        {
            "country": r.country,
            "base": round(r.base_mean, 1),
            "end": round(r.end_mean, 1),
            "change": round(r.change, 1),
        }
        for r in rows.itertuples()
    ]


# ---------------------------------------------------------------------------- step 51
def cluster_matrix(snapshot: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Rows of the snapshot with every clustering column present (complete-case).

    Why complete-case and no imputation: K-means needs a value in every column, and an
    imputed mix share would invent part of a country's electricity mix. Returns country,
    iso_code, population and `cols`, sorted by country, with a fresh index.
    """
    keep = ["country", "iso_code", "population"] + cols
    rows = snapshot[keep].dropna(subset=cols)
    return rows.sort_values("country").reset_index(drop=True)


def dominant_source(frame: pd.DataFrame) -> pd.Series:
    """Name of the largest of the 8 mix shares in each row (e.g. 'Hydro').

    Used only to interpret clusters (how far K-means just re-labels the biggest source);
    it is never a model feature.
    """
    by_col = dict(zip(config.MIX_SHARE_COLS, config.SOURCE_NAMES, strict=True))
    return frame[config.MIX_SHARE_COLS].idxmax(axis=1).map(by_col)


# ---------------------------------------------------------------------------- step 58
def _years(window: tuple[int, int]) -> list[int]:
    return list(range(window[0], window[1] + 1))


def iter2_requirements() -> dict[str, tuple[list[str], list[int]]]:
    """What a country needs for every iteration 2 feature: name -> (columns, years).

    Each entry mirrors one group of trajectory features in A3_PLAN.md §5, so the common
    country set is fixed now and iteration 1 vs 2 comparisons use exactly the same rows.
    """
    gdp_windows = _years(config.BASE_YEARS) + _years(config.END_YEARS_GDP)
    return {
        # cagr_gdp_pc and decoupling need GDP per person at both 3-year endpoints
        "gdp_endpoints": (["gdp_pc"], gdp_windows),
        # cagr_energy_pc
        "energy_endpoints": (["energy_per_capita"], gdp_windows),
        # d_lowcarbon, d_coal, d_solarwind, d_carbon_int, lowcarbon_slope, CLR 2018
        "grid_every_year": (
            config.MIX_SHARE_COLS + [config.LOW_CARBON_SHARE_COL, config.TARGET_COL],
            _years((config.YEAR_START, config.YEAR_END)),
        ),
        # 2018 levels (these also cover the iteration 1 clustering columns)
        "snapshot_levels": (
            ["energy_per_capita", "per_capita_electricity", "energy_per_gdp"],
            [config.SNAPSHOT_YEAR],
        ),
    }


def iter2_country_set(panel: pd.DataFrame, producers: pd.DataFrame) -> pd.DataFrame:
    """One row per country: a True/False column per requirement, and `in_set` (all True).

    Producer history (prod_*_mean_00_16) is the fifth requirement. Keeping the reasons,
    not just the final list, lets the report name every excluded country and say why.
    """
    countries = sorted(panel["country"].unique())
    table = pd.DataFrame(index=pd.Index(countries, name="country"))
    for name, (cols, years) in iter2_requirements().items():
        window = panel[panel["year"].isin(years)]
        complete_rows = window[window[cols].notna().all(axis=1)]
        n_complete = complete_rows.groupby("country")["year"].nunique()
        table[name] = n_complete.reindex(countries, fill_value=0) == len(years)
    history_cols = [c for c in producers.columns if c.endswith("_mean_00_16")]
    with_history = producers.dropna(subset=history_cols)["country"]
    table["producer_history"] = table.index.isin(with_history)
    table["in_set"] = table.all(axis=1)
    return table.reset_index()


# ---------------------------------------------------------------------------- step 61
def model_table(snapshot: pd.DataFrame, feature_cols: list[str], target: str) -> pd.DataFrame:
    """Country, iso_code, the features and the target, for rows where all are present.

    Complete-case on purpose: a Random Forest needs every feature, and imputing a value
    such as GDP would put a guess into the model. Sorted by country with a fresh index.
    """
    rows = snapshot[["country", "iso_code"] + feature_cols + [target]]
    rows = rows.dropna(subset=feature_cols + [target])
    return rows.sort_values("country").reset_index(drop=True)


# ---------------------------------------------------------------------------- step 69
def gdp_quartile(gdp_pc: pd.Series) -> pd.Series:
    """Quartile (Q1 = poorest) of GDP per person within the rows given.

    Used only to describe where model errors fall. These are 2018 snapshot quartiles of the
    RF rows, not the 2000-02 income tiers that iteration 2 builds in the feedback loop.
    """
    return pd.qcut(gdp_pc, 4, labels=config.GDP_QUARTILE_LABELS)


# ============================================================================ Phase 3: loop
# ---------------------------------------------------------------------------- step 81
def log_transform(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Copy of `frame` with log_<col> = log1p(col) added for each column (inference I1-1).

    Why log1p rather than log: per-person power-sector GHG can be exactly 0, and
    log1p(0) = 0. A negative value would be a data error, so it raises instead of
    silently producing NaN.
    """
    out = frame.copy()
    for col in cols:
        if (out[col] < 0).any():
            raise ValueError(f"log_transform: {col} has negative values")
        out[f"log_{col}"] = np.log1p(out[col])
    return out


def skew_before_after(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Skewness of each column raw and after log1p (pandas' bias-corrected skew, as in I1-1)."""
    logged = log_transform(frame, cols)
    return pd.DataFrame(
        {
            "column": cols,
            "n": [int(frame[c].notna().sum()) for c in cols],
            "skew_raw": [float(frame[c].skew()) for c in cols],
            "skew_log1p": [float(logged[f"log_{c}"].skew()) for c in cols],
        }
    )


# ---------------------------------------------------------------------------- step 82
def small_state_flag(population: pd.Series) -> pd.Series:
    """True where population < config.SMALL_STATE_POP (1 M): flagged, never dropped."""
    return population < config.SMALL_STATE_POP


# ---------------------------------------------------------------------------- step 83
def clr(shares: pd.DataFrame, eps: float = config.CLR_EPS) -> pd.DataFrame:
    """Centred log-ratio transform of a composition, row by row (Aitchison 1986).

    1. Close each row to 100, so the result cannot depend on the row total (scale
       invariance).
    2. Add `eps` percentage points, so a zero share has a finite log.
    3. clr_j = log(x_j + eps) - mean_k log(x_k + eps). Every row of the result sums to 0,
       and Euclidean distance between CLR rows compares ratios between sources (the
       Aitchison distance) instead of raw percentage-point gaps.

    Columns are renamed coal_share_elec -> clr_coal, etc.
    """
    if shares.isna().any().any():
        raise ValueError("clr: shares contain NaN (impute or drop rows first)")
    if (shares < 0).any().any():
        raise ValueError("clr: shares must be non-negative")
    totals = shares.sum(axis=1)
    if (totals <= 0).any():
        raise ValueError("clr: every row needs a positive total")
    closed = shares.div(totals, axis=0) * 100
    logs = np.log(closed + eps)
    out = logs.sub(logs.mean(axis=1), axis=0)
    out.columns = ["clr_" + c.removesuffix("_share_elec") for c in shares.columns]
    return out


# ---------------------------------------------------------------------------- step 85
def income_tiers(gdp_base: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """Quartile income tiers from the dataset's own GDP per person (no external groups).

    `gdp_base` is each country's mean GDP per person over the 2000-02 baseline. Returns
    (tier per country, thresholds table). The baseline is used so that the tier describes
    where a country started, not where it ended up, and so it uses no year after 2002.
    """
    tiers, edges = pd.qcut(gdp_base, 4, labels=config.INCOME_TIER_LABELS, retbins=True)
    counts = tiers.value_counts().reindex(config.INCOME_TIER_LABELS)
    thresholds = pd.DataFrame(
        {
            "tier": config.INCOME_TIER_LABELS,
            "gdp_pc_from": edges[:-1],
            "gdp_pc_to": edges[1:],
            "n_countries": counts.to_numpy(),
        }
    )
    return tiers.astype(str), thresholds


# ---------------------------------------------------------------------------- step 86
def cagr(start: pd.Series, end: pd.Series, years: int = config.CAGR_YEARS) -> pd.Series:
    """Compound annual growth rate (end / start) ** (1 / years) - 1.

    Endpoints are 3-year means centred on 2001 and 2017, hence 16 years. A non-positive
    endpoint has no growth rate, so it gives NaN (caught by validate_trajectories).
    """
    valid = (start > 0) & (end > 0)
    ratio = (end / start).where(valid)
    return ratio ** (1 / years) - 1


def yearly_slope(panel: pd.DataFrame, col: str, years: tuple[int, int]) -> pd.Series:
    """Per-country OLS slope of `col` on year (units per year), complete windows only."""
    first, last = years
    window = panel[panel["year"].between(first, last)].dropna(subset=[col])
    slopes = {}
    for country, rows in window.groupby("country"):
        if len(rows) == last - first + 1:
            slopes[country] = float(np.polyfit(rows["year"], rows[col], 1)[0])
    return pd.Series(slopes, name=f"{col}_slope", dtype=float)


# ---------------------------------------------------------------------------- steps 87-88
def build_trajectories(
    panel: pd.DataFrame,
    producers: pd.DataFrame,
    income_tier: pd.Series,
    countries: list[str],
    change_end: tuple[int, int],
    slope_years: tuple[int, int],
) -> pd.DataFrame:
    """One row per country: the feedback-loop reshape of the country-year panel (I1-3).

    The unit of analysis changes from "a country in one year" to "a country's path".
    Endpoints are 3-year means; growth runs 2000-02 -> 2016-18 (GDP ends 2018); the
    changes in the mix run 2000-02 -> `change_end`; the low-carbon slope uses `slope_years`.
    """
    idx = pd.Index(sorted(countries), name="country")
    panel = panel.assign(solarwind_share_elec=panel[config.SOLARWIND_COLS].sum(axis=1, min_count=2))

    def base(col: str) -> pd.Series:
        return endpoint_mean(panel, col, config.BASE_YEARS).reindex(idx)

    def end_growth(col: str) -> pd.Series:
        return endpoint_mean(panel, col, config.END_YEARS_GDP).reindex(idx)

    def change(col: str) -> pd.Series:
        return endpoint_mean(panel, col, change_end).reindex(idx) - base(col)

    snap = panel[panel["year"] == config.SNAPSHOT_YEAR].set_index("country").reindex(idx)
    prod = producers.set_index("country").reindex(idx)
    low = config.LOW_CARBON_SHARE_COL
    t = pd.DataFrame(index=idx)
    t["iso_code"] = snap["iso_code"]
    t["population_2018"] = snap["population"]
    t["small_state"] = small_state_flag(t["population_2018"])
    t["income_tier"] = income_tier.reindex(idx)
    t["gdp_pc_2000_02"] = base("gdp_pc")
    t["cagr_gdp_pc"] = cagr(base("gdp_pc"), end_growth("gdp_pc"))
    t["cagr_energy_pc"] = cagr(base("energy_per_capita"), end_growth("energy_per_capita"))
    # > 0: GDP grew faster than energy use (relative decoupling)
    t["decoupling"] = t["cagr_gdp_pc"] - t["cagr_energy_pc"]
    t["lowcarbon_2000"] = base(low)
    t["d_lowcarbon"] = change(low)
    t["d_coal"] = change("coal_share_elec")
    t["d_solarwind"] = change("solarwind_share_elec")
    t["d_carbon_int"] = change(config.TARGET_COL)
    t["lowcarbon_slope"] = yearly_slope(panel, low, slope_years).reindex(idx)
    t["log_energy_pc_2018"] = np.log1p(snap["energy_per_capita"])
    t["log_energy_per_gdp_2018"] = np.log1p(snap["energy_per_gdp"])
    for col in config.PRODUCER_HISTORY_COLS:
        t[f"log_{col}"] = np.log1p(prod[col])
    t = t.join(clr(snap[config.MIX_SHARE_COLS]))
    return t.reset_index()


def trajectories_descriptive(
    panel: pd.DataFrame, producers: pd.DataFrame, income_tier: pd.Series, countries: list[str]
) -> pd.DataFrame:
    """Descriptive table: mix changes to 2019-21 and slope over 2000-2021 (visuals only)."""
    return build_trajectories(
        panel,
        producers,
        income_tier,
        countries,
        change_end=config.END_YEARS_DESCRIPTIVE,
        slope_years=config.SLOPE_YEARS_DESCRIPTIVE,
    )


def trajectories_pre2019(
    panel: pd.DataFrame, producers: pd.DataFrame, income_tier: pd.Series, countries: list[str]
) -> pd.DataFrame:
    """Model table for RF v2 and the 2019-21 forecast: no year after 2018 may be used.

    Raises if the input panel contains any later year, so the future cannot leak in even
    by accident (the caller must filter the panel first).
    """
    latest = int(panel["year"].max())
    if latest > config.PRE2019_MAX_YEAR:
        raise ValueError(
            f"leakage: pre-2019 trajectories got data up to {latest}; "
            f"filter the panel to year <= {config.PRE2019_MAX_YEAR} first"
        )
    return build_trajectories(
        panel,
        producers,
        income_tier,
        countries,
        change_end=config.END_YEARS_GDP,
        slope_years=config.SLOPE_YEARS_PRE2019,
    )


# ---------------------------------------------------------------------------- step 89
def validate_trajectories(table: pd.DataFrame) -> list[str]:
    """Problems found in a trajectory table (empty list = valid).

    Checks: one row per country, no NaN or inf in any numeric feature, every tier
    assigned, CLR rows summing to 0, and values inside config.TRAJ_RANGES.
    """
    problems = []
    if not table["country"].is_unique:
        problems.append("duplicate countries")
    numeric = table.select_dtypes("number")
    bad = numeric.columns[~np.isfinite(numeric).all()].tolist()
    if bad:
        problems.append(f"NaN/inf in {bad}")
    if not table["income_tier"].isin(config.INCOME_TIER_LABELS).all():
        problems.append("missing or unknown income tier")
    clr_cols = [c for c in table.columns if c.startswith("clr_")]
    if clr_cols and not np.allclose(table[clr_cols].sum(axis=1), 0, atol=1e-9):
        problems.append("CLR rows do not sum to 0")
    for col, (low, high) in config.TRAJ_RANGES.items():
        outside = table.loc[~table[col].between(low, high), "country"].tolist()
        if outside:
            problems.append(f"{col} outside [{low}, {high}]: {outside}")
    return problems


def describe_table(table: pd.DataFrame, name: str) -> pd.DataFrame:
    """n, missing, min, median, max of every numeric column (for trajectories_summary.csv)."""
    numeric = table.select_dtypes("number")
    return pd.DataFrame(
        {
            "table": name,
            "column": numeric.columns,
            "n": numeric.notna().sum().to_numpy(),
            "n_missing": numeric.isna().sum().to_numpy(),
            "min": numeric.min().to_numpy(),
            "median": numeric.median().to_numpy(),
            "max": numeric.max().to_numpy(),
        }
    )


# ---------------------------------------------------------------------------- step 93
def neighbour_shift(shares: pd.DataFrame, clr_values: pd.DataFrame) -> dict:
    """How much CLR changes which countries count as close (same rows in both frames).

    Compares all pairwise Euclidean distances on raw shares (percentage points) with those
    on CLR values (the Aitchison distance): the Spearman correlation between the two, and
    the pair whose distance percentile rises most (close in pp, far in log-ratios). The
    pair is chosen by this rule, not by eye.
    """
    d_raw, d_clr = pdist(shares.to_numpy()), pdist(clr_values.to_numpy())
    pct_raw, pct_clr = rankdata(d_raw) / len(d_raw), rankdata(d_clr) / len(d_clr)
    k = int(np.argmax(pct_clr - pct_raw))
    first, second = np.triu_indices(len(shares), 1)
    names = shares.index.tolist()
    return {
        "n_countries": len(shares),
        "n_pairs": len(d_raw),
        "spearman_rho_distances": float(spearmanr(d_raw, d_clr)[0]),
        "pair": [names[first[k]], names[second[k]]],
        "pair_raw_distance_pp": float(d_raw[k]),
        "pair_raw_percentile": float(pct_raw[k]),
        "pair_clr_distance": float(d_clr[k]),
        "pair_clr_percentile": float(pct_clr[k]),
    }


# ---------------------------------------------------------------------------- step 96
def loop_summary(
    snapshot: pd.DataFrame,
    panel: pd.DataFrame,
    trajectories: pd.DataFrame,
    skew_table: pd.DataFrame,
    iter1_features: list[str],
    multi_year_cols: list[str],
) -> dict:
    """Before/after facts showing the feedback loop changed the data significantly.

    Every count is computed here from the tables themselves; the descriptive words (unit
    of analysis, representation) state what the code does, so the figure and report can
    quote them without hand-typed numbers. `multi_year_cols` are the columns shown (by
    scrambling) to use years other than the snapshot year; the rest are either copied from
    the 2018 snapshot or transformed 2018 values (log1p, CLR, flags).
    """
    id_cols = ["country", "iso_code"]
    after_features = [c for c in trajectories.columns if c not in id_cols]
    snap = snapshot.set_index("country").loc[trajectories["country"]].select_dtypes("number")

    def is_copy(col: str) -> bool:
        """True if the column equals some numeric 2018 snapshot column (e.g. population)."""
        values = trajectories[col]
        if not pd.api.types.is_numeric_dtype(values) or values.dtype == bool:
            return False
        return any(
            np.allclose(snap[s].to_numpy(float), values.to_numpy(float), equal_nan=True)
            for s in snap.columns
        )

    copied = [c for c in after_features if c not in multi_year_cols and is_copy(c)]
    transformed = [c for c in after_features if c not in multi_year_cols and c not in copied]
    return {
        "unit_before": f"a country in one year ({config.SNAPSHOT_YEAR} snapshot)",
        "unit_after": (
            f"a country's path, {config.YEAR_START}-{config.PRE2019_MAX_YEAR} (one row per country)"
        ),
        "rows_before": len(snapshot),
        "panel_rows": len(panel),
        "rows_after": len(trajectories),
        "years_before": str(config.SNAPSHOT_YEAR),
        "years_after_models": f"{config.YEAR_START}-{config.PRE2019_MAX_YEAR}",
        "years_after_descriptive": f"{config.YEAR_START}-{config.YEAR_END}",
        "feature_cols_before": len(set(iter1_features)),
        "feature_cols_after": len(after_features),
        "multi_year_cols": [c for c in after_features if c in multi_year_cols],
        "transformed_2018_cols": transformed,
        "copied_2018_cols": copied,
        "max_abs_skew_before": float(skew_table["skew_raw"].abs().max()),
        "max_abs_skew_after": float(skew_table["skew_log1p"].abs().max()),
        "mix_before": "8 shares in % (each row sums to 100)",
        "mix_after": "8 CLR log-ratios (each row sums to 0)",
        "income_before": "none",
        "income_after": f"{len(config.INCOME_TIER_LABELS)} tiers from 2000-02 GDP quartiles",
        "time_before": "none (one year)",
        "time_after": "growth (CAGR), decoupling, 16-year changes, yearly slope",
        "changes": {"unit_of_analysis": True, "scale": True, "geometry_of_mix": True},
    }


# ---------------------------------------------------------------------------- step 97
def scramble_rows(frame: pd.DataFrame, rows: pd.Series, seed: int = config.SEED) -> pd.DataFrame:
    """Copy of `frame` with every numeric value in `rows` multiplied by a random factor.

    Used to prove empirically which trajectory columns depend on which years: a column that
    does not change when those years are scrambled cannot be using them. Factors are in
    [0.5, 1.5], so non-negative values stay non-negative; `year` is never touched.
    """
    out = frame.copy()
    cols = [c for c in out.select_dtypes("number").columns if c != "year"]
    rng = np.random.default_rng(seed)
    n_rows = int(rows.sum())
    out.loc[rows, cols] = out.loc[rows, cols] * rng.uniform(0.5, 1.5, (n_rows, len(cols)))
    return out


def changed_columns(before: pd.DataFrame, after: pd.DataFrame) -> list[str]:
    """Columns whose values differ between two tables with the same rows and columns."""
    changed = []
    for col in before.columns:
        a, b = before[col], after[col]
        if pd.api.types.is_numeric_dtype(a):
            same = np.allclose(a.to_numpy(float), b.to_numpy(float), equal_nan=True)
        else:
            same = a.equals(b)
        if not same:
            changed.append(col)
    return changed


# ============================================================================ Phase 4: iter 2
# ---------------------------------------------------------------------------- step 101
def decoupling_class(cagr_gdp: pd.Series, cagr_energy: pd.Series) -> pd.Series:
    """Classify each country's 2001->2017 growth path (labels from config.DECOUPLING_CLASSES).

    - absolute decoupling: GDP per person grew while energy per person fell;
    - relative decoupling: both grew, GDP faster (below the 45-degree line);
    - coupled: energy per person grew at least as fast as GDP per person;
    - GDP fell: GDP per person shrank, so "decoupling" is not defined in the usual sense.
    """
    absolute, relative, coupled, gdp_fell = config.DECOUPLING_CLASSES
    out = pd.Series(coupled, index=cagr_gdp.index, dtype=object)
    out[(cagr_gdp > 0) & (cagr_energy < 0)] = absolute
    out[(cagr_gdp > 0) & (cagr_energy >= 0) & (cagr_energy < cagr_gdp)] = relative
    out[cagr_gdp <= 0] = gdp_fell
    return out


# ---------------------------------------------------------------------------- step 108
def tier_lowcarbon(traj: pd.DataFrame) -> pd.DataFrame:
    """Per income tier: median and IQR of the low-carbon share at both ends, and the median
    of each country's own change (which is not the difference of the two medians).

    `traj` is the descriptive table: start = 2000-02 mean, end = start + d_lowcarbon
    (2019-21 mean).
    """
    frame = traj.assign(end=traj["lowcarbon_2000"] + traj["d_lowcarbon"])
    rows = []
    for tier in config.INCOME_TIER_LABELS:
        g = frame[frame["income_tier"] == tier]
        rows.append(
            {
                "tier": tier,
                "n": len(g),
                "median_start": float(g["lowcarbon_2000"].median()),
                "q1_start": float(g["lowcarbon_2000"].quantile(0.25)),
                "q3_start": float(g["lowcarbon_2000"].quantile(0.75)),
                "median_end": float(g["end"].median()),
                "q1_end": float(g["end"].quantile(0.25)),
                "q3_end": float(g["end"].quantile(0.75)),
                "median_change": float(g["d_lowcarbon"].median()),
            }
        )
    return pd.DataFrame(rows)
