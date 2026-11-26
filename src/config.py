"""Single source of truth for every constant used in the A3 workflow.

Why: keeping paths, year windows, thresholds and colours in one place means the notebook,
the figures and the report can never silently disagree, and every choice can be
explained in the viva from one file.
"""

from pathlib import Path

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RAW_CSV = DATA_RAW / "World Energy Consumption.csv"
IMAGES = ROOT / "images"
RESULTS = ROOT / "results"
REPORT = ROOT / "report"
VIDEO = ROOT / "video"

FIGURES_CSV = RESULTS / "figures.csv"
INFERENCES_JSON = RESULTS / "inferences.json"
INFERENCES_MD = RESULTS / "inferences.md"

# --------------------------------------------------------------------------------------
# Expected raw-file facts (verified on Nov 21; asserted on load so a wrong file fails fast)
# --------------------------------------------------------------------------------------
RAW_SHAPE = (22_012, 129)
RAW_YEAR_RANGE = (1900, 2022)
RAW_N_ENTITIES = 306
N_COUNTRIES_WITH_ISO = 219

# --------------------------------------------------------------------------------------
# Time windows
# --------------------------------------------------------------------------------------
YEAR_START = 2000  # electricity-mix columns start here for ~205 countries
YEAR_END = 2021  # 2022 covers only about half the countries, so it is dropped
SNAPSHOT_YEAR = 2018  # last year with GDP, so iteration 1 snapshot uses it
GDP_LAST_YEAR = 2018  # `gdp` and `energy_per_gdp` end here
PRODUCER_LAST_FULL_YEAR = 2016  # after 2016 the source drops non-producers and ~50 producers
FORECAST_TRAIN_END = 2018
FORECAST_TEST_YEARS = (2019, 2020, 2021)

# 3-year endpoint windows (avoid one noisy endpoint year)
BASE_YEARS = (2000, 2002)  # centred on 2001
END_YEARS_GDP = (2016, 2018)  # centred on 2017 -> 16 years of growth
END_YEARS_DESCRIPTIVE = (2019, 2021)  # centred on 2020, used only for descriptive change
CAGR_YEARS = 16  # 2017 - 2001
PRODUCER_HISTORY_YEARS = (2000, 2016)

# --------------------------------------------------------------------------------------
# Columns
# --------------------------------------------------------------------------------------
ID_COLS = ["country", "iso_code", "year", "population"]

# The 8 electricity-mix shares (percent of generation; together they sum to ~100)
MIX_SHARE_COLS = [
    "coal_share_elec",
    "gas_share_elec",
    "oil_share_elec",
    "nuclear_share_elec",
    "hydro_share_elec",
    "solar_share_elec",
    "wind_share_elec",
    "other_renewables_share_elec",
]

# Generation by source in TWh, in the same order as MIX_SHARE_COLS
MIX_TWH_COLS = [
    "coal_electricity",
    "gas_electricity",
    "oil_electricity",
    "nuclear_electricity",
    "hydro_electricity",
    "solar_electricity",
    "wind_electricity",
    "other_renewable_electricity",
]

# Human-readable source names, in the same order (fossil first, then low-carbon)
SOURCE_NAMES = ["Coal", "Gas", "Oil", "Nuclear", "Hydro", "Solar", "Wind", "Other renewables"]

GENERATION_COL = "electricity_generation"
LOW_CARBON_SHARE_COL = "low_carbon_share_elec"
LOW_CARBON_TWH_COL = "low_carbon_electricity"
TARGET_COL = "carbon_intensity_elec"

# low_carbon_share_elec = nuclear + hydro + solar + wind + other renewables (verified)
LOW_CARBON_PARTS = [
    "nuclear_share_elec",
    "hydro_share_elec",
    "solar_share_elec",
    "wind_share_elec",
    "other_renewables_share_elec",
]

# Columns the coverage rule is applied to (the electricity-grid core of the analysis)
CORE_ELEC_COLS = MIX_SHARE_COLS + [LOW_CARBON_SHARE_COL, TARGET_COL, GENERATION_COL]

INTENSIVE_COLS = [
    "energy_per_capita",  # kWh per person (primary energy)
    "per_capita_electricity",  # kWh per person
    "carbon_intensity_elec",  # gCO2 per kWh of electricity
    "energy_per_gdp",  # kWh per international-$ (ends 2018)
]

RAW_PRODUCER_COLS = ["oil_prod_per_capita", "gas_prod_per_capita", "coal_prod_per_capita"]

# Raw columns kept from the CSV (everything else is dropped in Phase 1)
CORE_RAW_COLS = (
    ID_COLS
    + ["gdp", "greenhouse_gas_emissions"]
    + INTENSIVE_COLS
    + MIX_SHARE_COLS
    + [LOW_CARBON_SHARE_COL]
    + [GENERATION_COL, LOW_CARBON_TWH_COL]
    + MIX_TWH_COLS
    + RAW_PRODUCER_COLS
)

# Units, used in axis labels and the data dictionary
UNITS = {
    "population": "people",
    "gdp": "international-$ (PPP)",
    "gdp_pc": "international-$ per person (PPP)",
    "greenhouse_gas_emissions": "MtCO2e (electricity sector)",
    "ghg_pc": "tCO2e per person (electricity sector)",
    "energy_per_capita": "kWh per person",
    "per_capita_electricity": "kWh per person",
    "carbon_intensity_elec": "gCO2 per kWh",
    "energy_per_gdp": "kWh per international-$",
    "low_carbon_share_elec": "% of electricity",
    "electricity_generation": "TWh",
}

# Readable labels for figures: (short name, axis label with unit)
VAR_LABELS = {
    "gdp_pc": ("GDP per person", "GDP per person (international-$, PPP)"),
    "energy_per_capita": ("Energy per person", "Primary energy per person (kWh)"),
    "per_capita_electricity": ("Electricity per person", "Electricity per person (kWh)"),
    "energy_per_gdp": ("Energy per GDP", "Energy per GDP (kWh per international-$)"),
    "carbon_intensity_elec": (
        "Grid carbon intensity",
        "Carbon intensity of electricity (gCO2/kWh)",
    ),
    "low_carbon_share_elec": ("Low-carbon share", "Low-carbon share of electricity (%)"),
    "ghg_pc": ("Power-sector GHG per person", "Electricity-sector GHG per person (tCO2e)"),
    "population": ("Population", "Population (people)"),
}

# --------------------------------------------------------------------------------------
# Data-handling thresholds (Phase 1)
# --------------------------------------------------------------------------------------
INTERP_LIMIT = 3  # fill at most 3 consecutive missing years, inside a country only
MAX_MISSING_SHARE = 0.30  # drop a country missing >30% of core electricity cells
MIX_SUM_TOLERANCE = 0.5  # re-normalise mix rows whose sum is off by more than 0.5 pp

# --------------------------------------------------------------------------------------
# Feedback-loop transformations (Phase 3)
# --------------------------------------------------------------------------------------
SMALL_STATE_POP = 1_000_000
CLR_EPS = 0.1  # percentage points added before log, so zero shares are defined
CLR_EPS_GRID = (0.01, 0.1, 1.0)  # sensitivity check
INCOME_TIER_LABELS = ["Low", "Lower-middle", "Upper-middle", "High"]  # data-derived quartiles
# Trajectory tables (A3_PLAN.md section 5). The descriptive table may use 2019-21; the
# pre-2019 table (RF v2, forecast) may not use any year after PRE2019_MAX_YEAR.
PRE2019_MAX_YEAR = 2018
SLOPE_YEARS_DESCRIPTIVE = (2000, 2021)
SLOPE_YEARS_PRE2019 = (2000, 2018)
SOLARWIND_COLS = ["solar_share_elec", "wind_share_elec"]
PRODUCER_HISTORY_COLS = [
    "oil_prod_pc_mean_00_16",
    "gas_prod_pc_mean_00_16",
    "coal_prod_pc_mean_00_16",
]
# Plausible ranges used to validate the trajectory tables (a value outside means a bug)
TRAJ_RANGES = {
    "cagr_gdp_pc": (-0.15, 0.25),  # yearly growth over 16 years
    "cagr_energy_pc": (-0.15, 0.25),
    "decoupling": (-0.3, 0.3),
    "d_lowcarbon": (-100.0, 100.0),  # percentage points
    "d_coal": (-100.0, 100.0),
    "d_solarwind": (-100.0, 100.0),
    "lowcarbon_slope": (-10.0, 10.0),  # pp per year
    "lowcarbon_2000": (0.0, 100.0),
}

# --------------------------------------------------------------------------------------
# Modelling
# --------------------------------------------------------------------------------------
SEED = 42
N_FOLDS = 5
RF_N_ESTIMATORS = 500
PERMUTATION_REPEATS = 20

# Iteration 1 Random Forest: target = grid carbon intensity (2018). Features are 2018 levels
# plus 2016 producer values (after 2016 the source drops ~50 producers). No mix shares.
RF_TARGET = TARGET_COL
RF_FEATURES_ITER1 = [
    "gdp_pc",
    "energy_per_capita",
    "per_capita_electricity",
    "population",
    "oil_prod_pc_2016",
    "gas_prod_pc_2016",
    "coal_prod_pc_2016",
]
# Leakage guard: carbon intensity is computed from the generation mix and the power-sector
# emissions, so no feature may contain any of these name fragments. Beyond the plan's list,
# the mix TWh columns and power-sector GHG are banned too (emissions / generation is the
# target itself).
LEAKAGE_BANNED = (
    ["_share_elec", "clr_", "low_carbon", "lowcarbon", "carbon_int", "d_coal", "d_solarwind"]
    + ["archetype", "greenhouse_gas", "ghg"]
    + MIX_TWH_COLS
)
ALPHA = 0.05  # significance level for every test in the project
# I1-1: skewness above this counts as "heavily" skewed (the usual rule of thumb |skew| > 1);
# these are the per-person variables the claim is about
SKEW_HEAVY = 1.0
SKEW_CHECK_COLS = ["energy_per_capita", "gdp_pc", "per_capita_electricity"]
N_OLS_NAMED = 4  # largest raw-OLS residuals named in I1-1
# Phase 3 log1p columns (A3_PLAN.md section 5, from I1-1). A Random Forest is invariant to
# monotone transforms, so the log matters for OLS, distances (K-means) and plots only.
LOG_COLS = ["energy_per_capita", "per_capita_electricity", "gdp_pc", "energy_per_gdp", "ghg_pc"]
# I1-4: the plan expected a "moderate" R-squared; read as a cross-validated mean of at least
# this value (any cut-off above 0.1 gives the same verdict for the observed R-squared)
MODERATE_R2 = 0.3
# The plan's iteration 1 hypotheses (A3_PLAN.md section 4), written before the data was
# analysed; src/hypotheses.py tests each one against the saved results
PLAN_HYPOTHESES_ITER1 = {
    "I1-1": "Raw scales are heavily skewed; a few small producer states dominate.",
    "I1-2": (
        "K-means clusters are driven by scale and outliers (a tiny cluster of "
        "high-consumption small states) and do not read as transition types."
    ),
    "I1-3": "A single-year snapshot hides large change over time.",
    "I1-4": (
        "The Random Forest reaches a moderate R-squared; its biggest errors are hydro- or "
        "nuclear-heavy countries and small states."
    ),
}
# I1-3: a change in low-carbon share larger than this (percentage points, either direction)
# counts as "large"; the figure names this many top risers and fallers in rank
CHANGE_BIG_PP = 10.0
N_CHANGE_MOVERS = 4
# Feedback-loop table (inference -> transformation): what each change does to the data,
# where its output lives and which figure shows it before vs after
LOOP_DETAILS = {
    "I1-1": {
        "transformation": "log1p of the skewed variables; small-state flag (never dropped)",
        "what_changes": "scale",
        "outputs": "results/loop_skew.csv; results/small_states.csv",
        "figure": "loop_skew_before_after.png",
    },
    "I1-2": {
        "transformation": "centred log-ratio (CLR) of the 8 mix shares, eps sensitivity",
        "what_changes": "geometry of the mix (percentages -> log-ratios)",
        "outputs": "results/loop_clr_eps.csv; CLR columns in the trajectory tables",
        "figure": "loop_clr_before_after.png",
    },
    "I1-3": {
        "transformation": "country-year panel reshaped into one row per country (trajectories)",
        "what_changes": "unit of analysis",
        "outputs": "data/processed/trajectories.csv; data/processed/trajectories_pre2019.csv",
        "figure": "loop_before_after_table.png",
    },
    "I1-4": {
        "transformation": "income tiers from 2000-02 GDP; growth, decoupling, producer history",
        "what_changes": "new context features (no mix-derived feature)",
        "outputs": "results/income_tier_thresholds.csv; data/processed/trajectories_pre2019.csv",
        "figure": "loop_before_after_table.png",
    },
}
# Columns of the descriptive trajectory table that use 2019-21 data (end window or slope);
# the notebook proves this list empirically by scrambling every value after 2018
POST2018_COLS = ["d_lowcarbon", "d_coal", "d_solarwind", "d_carbon_int", "lowcarbon_slope"]
# What each trajectory column means (results/trajectory_columns.csv, the report's appendix)
TRAJ_COLUMN_DEFS = {
    "country": "Country name (OWID)",
    "iso_code": "ISO 3166-1 alpha-3 code",
    "population_2018": "Population in 2018 (people)",
    "small_state": "True if population_2018 < 1 M (flag only, never used to drop rows)",
    "income_tier": "Quartile of mean GDP per person 2000-02 (data-derived, not World Bank)",
    "gdp_pc_2000_02": "Mean GDP per person 2000-02 (international-$, PPP)",
    "cagr_gdp_pc": "Yearly growth of GDP per person, 2000-02 mean -> 2016-18 mean (16 years)",
    "cagr_energy_pc": "Yearly growth of energy per person, same endpoints",
    "decoupling": "cagr_gdp_pc - cagr_energy_pc (> 0: GDP grew faster than energy use)",
    "lowcarbon_2000": "Mean low-carbon share of electricity 2000-02 (%)",
    "d_lowcarbon": "Change in low-carbon share from 2000-02 to the end window (pp)",
    "d_coal": "Change in coal share, same endpoints (pp)",
    "d_solarwind": "Change in solar + wind share, same endpoints (pp)",
    "d_carbon_int": "Change in grid carbon intensity, same endpoints (gCO2/kWh)",
    "lowcarbon_slope": "OLS slope of the low-carbon share on year (pp per year)",
    "log_energy_pc_2018": "log(1 + primary energy per person in 2018, kWh)",
    "log_energy_per_gdp_2018": "log(1 + energy per GDP in 2018, kWh per international-$)",
    "log_oil_prod_pc_mean_00_16": "log(1 + mean oil production per person 2000-16, kWh)",
    "log_gas_prod_pc_mean_00_16": "log(1 + mean gas production per person 2000-16, kWh)",
    "log_coal_prod_pc_mean_00_16": "log(1 + mean coal production per person 2000-16, kWh)",
    **{
        f"clr_{c.removesuffix('_share_elec')}": f"CLR of the 2018 {n.lower()} share (log-ratio)"
        for c, n in zip(MIX_SHARE_COLS, SOURCE_NAMES, strict=True)
    },
}
# Iteration 2 decoupling (2001 -> 2017 growth of GDP and energy per person)
DECOUPLING_CLASSES = ["absolute decoupling", "relative decoupling", "coupled", "GDP fell"]
N_QUADRANT_POPULOUS = 3  # most populous countries named in the decoupling quadrant
N_QUADRANT_EXTREMES = 3  # countries with the largest / smallest decoupling named
LOOP_SKEW_PLOT_COLS = ["energy_per_capita", "per_capita_electricity", "gdp_pc"]
# Trajectory columns allowed as model features (none derived from the mix or carbon
# intensity). The notebook asserts that exactly these pass the leakage guard, so a new
# mix-derived column cannot slip through a gap in the name fragments.
TRAJ_CONTEXT_COLS = [
    "population_2018",
    "small_state",
    "income_tier",
    "gdp_pc_2000_02",
    "cagr_gdp_pc",
    "cagr_energy_pc",
    "decoupling",
    "log_energy_pc_2018",
    "log_energy_per_gdp_2018",
    "log_oil_prod_pc_mean_00_16",
    "log_gas_prod_pc_mean_00_16",
    "log_coal_prod_pc_mean_00_16",
]
N_RF_LABELS = 8  # worst predictions named in the predicted-vs-actual plot
N_RF_ERRORS = 15  # rows in the top-errors table
MIN_GROUP_SIZE = 5  # smallest group used in a group comparison test
# 2018 GDP-per-person quartiles of the RF rows: used only to describe where errors fall
GDP_QUARTILE_LABELS = ["Q1 (poorest)", "Q2", "Q3", "Q4 (richest)"]
KMEANS_N_INIT = 20
K_RANGE_ITER1 = range(2, 9)  # k = 2..8
K_RANGE_ITER2 = range(3, 8)  # k = 3..7
MIN_CLUSTER_SIZE = 5
# Iteration 1 K-means features: the 8 mix shares + 3 intensive columns (naive baseline:
# StandardScaler only, no log, no CLR)
ITER1_CLUSTER_COLS = MIX_SHARE_COLS + [
    "energy_per_capita",
    "per_capita_electricity",
    "carbon_intensity_elec",
]
# k-selection rule, fixed before fitting: the k with the highest mean silhouette among the
# k whose every cluster has at least MIN_CLUSTER_SIZE countries (ties -> smaller k)
K_RULE = (
    f"highest silhouette among the k whose every cluster has >= {MIN_CLUSTER_SIZE} countries"
    " (ties -> smaller k)"
)
# Kaufman & Rousseeuw (1990) reading of the mean silhouette: <= 0.25 no substantial
# structure, 0.26-0.50 weak, 0.51-0.70 reasonable, > 0.70 strong
SILHOUETTE_BANDS = ((0.25, "no substantial"), (0.50, "weak"), (0.70, "reasonable"), (1.0, "strong"))
N_PCA_LABELS = 6  # countries farthest from the PCA origin that get a name in the biplot
N_STABILITY_SEEDS = 20

# --------------------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------------------
FIG_DPI = 200
SOURCE_NOTE = "Data: Our World in Data"

# Okabe-Ito palette: designed to be distinguishable for common colour-vision deficiencies
OKABE_ITO = [
    "#E69F00",  # orange
    "#56B4E9",  # sky blue
    "#009E73",  # bluish green
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#F0E442",  # yellow (weak on white: use last)
    "#000000",  # black
]

# Fixed colour per energy source, reused in every figure
SOURCE_COLORS = {
    "Coal": "#5F5F5F",
    "Gas": "#E69F00",
    "Oil": "#D55E00",
    "Nuclear": "#CC79A7",
    "Hydro": "#0072B2",
    "Solar": "#F0E442",
    "Wind": "#56B4E9",
    "Other renewables": "#009E73",
}

# Ordered colours for income tiers (viridis samples: ordinal, colour-blind safe)
TIER_COLORS = {
    "Low": "#440154",
    "Lower-middle": "#3B528B",
    "Upper-middle": "#21918C",
    "High": "#5EC962",
}

# Short readable name for every clustering feature (legends, loading arrows)
FEATURE_SHORT = {
    **{col: f"{name} share" for col, name in zip(MIX_SHARE_COLS, SOURCE_NAMES, strict=True)},
    "energy_per_capita": "Energy per person",
    "per_capita_electricity": "Electricity per person",
    "carbon_intensity_elec": "Carbon intensity",
    "gdp_pc": "GDP per person",
    "population": "Population",
    "oil_prod_pc_2016": "Oil production per person (2016)",
    "gas_prod_pc_2016": "Gas production per person (2016)",
    "coal_prod_pc_2016": "Coal production per person (2016)",
}

# Clusters named after a source ("high Hydro share") reuse that source's colour, so a colour
# means the same thing in every figure. Other clusters take these extra colours in order
# (black, then Paul Tol's colour-blind-safe wine, teal and olive).
CLUSTER_FALLBACK_COLORS = ["#000000", "#882255", "#44AA99", "#999933"]

SEQUENTIAL_CMAP = "cividis"
DIVERGING_CMAP = "RdBu_r"

# --------------------------------------------------------------------------------------
# Iteration 2: archetype clustering (Chunk 12-13)
# --------------------------------------------------------------------------------------
# Trajectory features that describe HOW a country's grid and economy moved (growth,
# decoupling, change in the mix) plus the CLR-transformed 2018 mix. Producer history and
# log levels are left out so the archetypes describe change, not size.
ARCHETYPE_TRAJECTORY_COLS = [
    "cagr_gdp_pc",
    "cagr_energy_pc",
    "decoupling",
    "lowcarbon_2000",
    "d_lowcarbon",
    "d_coal",
    "d_solarwind",
    "d_carbon_int",
    "lowcarbon_slope",
]
ARCHETYPE_CLR_COLS = [f"clr_{s}" for s in ["coal", "gas", "oil", "nuclear", "hydro", "solar",
                                           "wind", "other_renewables"]]
ARCHETYPE_COLS = ARCHETYPE_TRAJECTORY_COLS + ARCHETYPE_CLR_COLS
ARCHETYPE_METHOD_RULE = (
    "highest silhouette among the k (and methods) whose every cluster has >= "
    f"{MIN_CLUSTER_SIZE} countries; GMM is used only if its BIC-best k also meets the size rule "
    "and its silhouette beats K-means (ties -> K-means, smaller k)"
)
ARCHETYPE_LABELS = {
    "cagr_gdp_pc": "GDP growth",
    "cagr_energy_pc": "energy growth",
    "decoupling": "decoupling",
    "lowcarbon_2000": "start low-carbon share",
    "d_lowcarbon": "gain in low-carbon share",
    "d_coal": "coal change",
    "d_solarwind": "solar+wind gain",
    "d_carbon_int": "carbon-intensity change",
    "lowcarbon_slope": "slope of low-carbon share",
    **{f"clr_{s}": f"{s.replace('_', ' ')} (CLR)" for s in
       ["coal", "gas", "oil", "nuclear", "hydro", "solar", "wind", "other_renewables"]},
}
# A country is a "fossil producer" if its mean fossil production per person over 2000-16
# (oil + gas + coal, kWh) is at least its mean primary energy use per person over the same
# years, i.e. it produces at least as much fossil energy as it consumes (a net-exporter proxy
# built only from this dataset).
PRODUCER_RATIO = 1.0
PRODUCER_YEARS = (2000, 2016)
# Iteration 2 Random Forest: the iteration 1 features plus leak-free history and context
# from the pre-2019 trajectory table (I1-4). No mix-derived column (guarded by
# assert_no_leakage).
RF_FEATURES_HISTORY = [
    "cagr_gdp_pc",
    "cagr_energy_pc",
    "decoupling",
    "income_tier_code",
    "small_state_code",
    "log_oil_prod_pc_mean_00_16",
    "log_gas_prod_pc_mean_00_16",
    "log_coal_prod_pc_mean_00_16",
]
RF_FEATURES_ITER2 = RF_FEATURES_ITER1 + RF_FEATURES_HISTORY
FEATURE_SHORT.update(
    {
        "cagr_gdp_pc": "GDP growth 2001-17",
        "cagr_energy_pc": "Energy growth 2001-17",
        "decoupling": "Decoupling 2001-17",
        "income_tier_code": "Income tier (2000-02)",
        "small_state_code": "Small state",
        "log_oil_prod_pc_mean_00_16": "Oil production history",
        "log_gas_prod_pc_mean_00_16": "Gas production history",
        "log_coal_prod_pc_mean_00_16": "Coal production history",
    }
)
