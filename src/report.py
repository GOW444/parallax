"""Build report/A3_report.md from results/ (every number is read, never typed).

Why generated: the report quotes about a hundred numbers. Reading each one from the
results files means a re-run of the notebook can never leave the report out of date, and
the viva answer to "where does this number come from?" is always a file name.

Figures are numbered in the order they are placed; captions and the "why this chart"
sentence come from results/figures.csv, which plots.save_figure() fills when the figure is
made. Inference text comes from results/inferences.json.
"""

import json
from pathlib import Path

import pandas as pd

from src import config, logbook

REPORT_DIR = config.ROOT / "report"
REPORT_MD = REPORT_DIR / "A3_report.md"
IMAGE_PREFIX = "../images/"


class FigureCounter:
    """Numbers figures in order of placement and renders their markdown block."""

    def __init__(self, registry: pd.DataFrame):
        self.registry = registry.set_index("filename")
        self.numbers: dict[str, int] = {}

    def ref(self, filename: str) -> str:
        """'Figure n' for a figure that is already placed (raises if it is not)."""
        return f"Figure {self.numbers[filename]}"

    def place(self, filename: str) -> str:
        if filename not in self.registry.index:
            raise KeyError(f"{filename} is not registered in figures.csv")
        if filename in self.numbers:
            raise ValueError(f"{filename} placed twice")
        self.numbers[filename] = len(self.numbers) + 1
        row = self.registry.loc[filename]
        n = self.numbers[filename]
        return (
            f"![Figure {n}]({IMAGE_PREFIX}{filename})\n\n"
            f"**Figure {n}.** {row['what_it_shows']} "
            f"*Why this chart:* {row['why_this_chart']}\n"
        )


def _inference_block(entries: dict, inference_id: str) -> str:
    e = entries[inference_id]
    loop = " **Triggers the feedback loop.**" if e["triggers_loop"] else ""
    return f"> **{inference_id}.** {e['statement']}{loop}\n>\n> *Evidence:* {e['evidence']}\n"


def _table(df: pd.DataFrame) -> str:
    """Plain pipe table (no tabulate dependency)."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines) + "\n"


def _load(name: str) -> dict:
    return logbook.load_metrics(name)


def build() -> str:
    """Return the full report markdown."""
    reg = pd.read_csv(config.FIGURES_CSV)
    fig = FigureCounter(reg)
    inf = json.loads(config.INFERENCES_JSON.read_text(encoding="utf-8"))

    p1 = pd.read_csv(config.RESULTS / "phase1_summary.csv")
    tiers = pd.read_csv(config.RESULTS / "income_tier_thresholds.csv")
    loop_tab = pd.read_csv(config.RESULTS / "loop_transformations.csv")
    loop = _load("loop_summary")
    eps = pd.read_csv(config.RESULTS / "loop_clr_eps.csv")
    skew = pd.read_csv(config.RESULTS / "loop_skew.csv")
    sanity = _load("sanity_checks")
    km1 = _load("iter1_kmeans")
    rf1 = _load("iter1_rf_metrics")
    corr = _load("iter1_correlation_test")
    mk = _load("iter1_mk_global")
    stab = _load("iter2_stability")
    rfc = _load("iter2_rf_comparison")
    names = pd.read_csv(config.RESULTS / "archetype_names.csv")
    has_forecast = (config.RESULTS / "iter2_forecast_metrics.csv").exists() and "I2-6" in inf
    fm = pd.read_csv(config.RESULTS / "iter2_forecast_metrics.csv") if has_forecast else None

    raw_row = p1.iloc[0]
    clean_row = p1[p1["stage"].str.startswith("After coverage")].iloc[0]
    balanced_row = p1[p1["stage"].str.startswith("Balanced")].iloc[0]
    clr_default = eps[eps["eps"] == config.CLR_EPS].iloc[0]
    clr_others = eps[eps["eps"].notna() & (eps["eps"] != config.CLR_EPS)]
    eps_text = ", ".join(
        f"ε = {r.eps:g}: silhouette {r.silhouette_at_k_chosen:.2f}, ARI {r.ari_vs_default_eps:.2f}"
        for r in clr_others.itertuples()
    )

    s = []
    add = s.append

    # ------------------------------------------------------------------ front matter
    add("# The Energy Transition, Unrolled: A Two-Iteration Visual Analytics Workflow\n")
    add(
        "**DAS732 Data Visualization, Programming Assignment 3 (A3)** · IIIT Bangalore · "
        "Term 1 2026-27\n\nDataset: *World Energy Consumption* (Our World in Data) · "
        "Tools: Python 3.13 (pandas, scikit-learn, statsmodels, matplotlib, plotly), one "
        "reproducible notebook (`notebooks/A3_workflow.ipynb`)\n"
    )
    add(
        "**Analysis types (PDF task 1), labelled throughout:** "
        "**[Statistics]** trend, correlation, regression and group tests; "
        "**[Unsupervised]** K-means, PCA and Gaussian mixtures; "
        "**[Supervised]** Random Forest regression and time-series forecasting.\n"
    )

    # ------------------------------------------------------------------ 1
    add("## 1. Introduction and research question\n")
    add(
        "> **How are the world's countries moving through the energy transition, and does "
        "getting richer still mean using more energy and running a dirtier electricity "
        "grid?**\n"
    )
    add(
        "The question follows on from our A1 visual exploration (Appendix A). A1 found that the "
        "global energy mix barely moved between 1990 and 2022, that national income predicts "
        "how *much* energy a country uses far better than how *clean* it is, and that the "
        "electricity grid is the one part of the system visibly in motion (A1, Executive "
        "Summary and Cross-Cutting Synthesis). A1 was descriptive: it drew charts of "
        "complete-case panels. A3 adds statistical tests, unsupervised and supervised models, "
        "and a feedback loop in which what the first iteration learns reshapes the data for "
        "a second iteration, following the visual analytics process of Keim et al. [1].\n"
    )

    # ------------------------------------------------------------------ 2
    add("## 2. Dataset\n")
    add(
        f"The only input is OWID's *World Energy Consumption* file [2]: "
        f"{int(raw_row['rows']):,} rows, {int(raw_row['countries'])} entities, years "
        f"{raw_row['years']}. It is a long-format country-year panel of primary energy by "
        "source, electricity generation and its mix, grid carbon intensity, GDP and "
        "population. Its main limits shape every later choice: GDP ends in 2018, the "
        "electricity mix is dense only from 2000, 2022 covers about half of the countries, "
        "and fossil production is listed only for main producers from 2017 on.\n"
    )
    add(
        "**Supplementary data: none.** No external dataset was joined. Region and income "
        "classifications (e.g. World Bank groups) would have been the obvious additions, but "
        "they would introduce a second source with its own definitions, years and country "
        "codes. Instead, income tiers are derived from the dataset itself as quartiles of "
        "each country's mean GDP per person over 2000-02 (Table 1). They are data-derived "
        "groups, not official classifications.\n"
    )
    tiers_show = tiers.copy()
    tiers_show["gdp_pc_from"] = tiers_show["gdp_pc_from"].map(lambda v: f"{v:,.0f}")
    tiers_show["gdp_pc_to"] = tiers_show["gdp_pc_to"].map(lambda v: f"{v:,.0f}")
    tiers_show.columns = ["Tier", "GDP per person from ($)", "to ($)", "Countries"]
    add("**Table 1.** Income tiers (quartiles of mean GDP per person, 2000-02).\n")
    add(_table(tiers_show))

    # ------------------------------------------------------------------ 3
    add("## 3. The visual analytics workflow\n")
    add(
        "Keim et al. [1] describe visual analytics as a loop between data, visualization, "
        "models and knowledge. We run that diamond twice and draw it *unrolled* (Figure 1): "
        "iteration 1 on the raw 2018 snapshot, iteration 2 on the transformed data. One edge, "
        "labelled *Feedback loop*, joins them: it carries four inferences from iteration 1 to "
        "four transformations of the data. Within an iteration the only two-way edge is "
        "Visualization ⇄ Models, the diamond's own interaction step; there are no self-loops.\n"
    )
    add(fig.place("workflow.png"))
    modules = pd.DataFrame(
        [
            (
                "D1 Data",
                "drop aggregates; 2000-2021 window; within-country interpolation; coverage rule",
                "A clean country panel is the precondition for every count, map and model.",
            ),
            (
                "V1 Visualization",
                "missingness, global mix, distributions, scatter, correlations, map, change",
                "See the data's shape, skew, gaps and geography before modelling it.",
            ),
            (
                "M1 Models",
                "[Statistics] Mann-Kendall, OLS + Breusch-Pagan; [Unsupervised] K-means + PCA; [Supervised] Random Forest",
                "Baseline models on raw scales, so their failures can be diagnosed.",
            ),
            (
                "K1 Knowledge",
                "I1-1..I1-4",
                "Each inference names a defect of the raw representation.",
            ),
            (
                "Feedback loop",
                "log1p; CLR; trajectories; income tiers + history",
                "Each transformation answers one inference (Section 6).",
            ),
            (
                "D2 Data",
                "one row per country; log and CLR columns; pre-2019 model table",
                "The unit of analysis becomes a country's path.",
            ),
            (
                "V2 Visualization",
                "decoupling quadrant, tier box plots, log-log fit, slope chart, archetype heatmap / map / small multiples, forecasts",
                "Views of change, not of a single year.",
            ),
            (
                "M2 Models",
                "[Statistics] log-log OLS (HC3), Kruskal-Wallis + Holm, Mann-Kendall; [Unsupervised] K-means vs diagonal GMM; [Supervised] RF v2, Holt / ARIMA",
                "Re-model on the new representation with the same validation design.",
            ),
            (
                "K2 Knowledge",
                "I2-1..I2-6",
                "Answers to the research question, including negative results.",
            ),
        ],
        columns=["Module", "What it does", "Why"],
    )
    add("**Table 2.** Modules of the workflow and the rationale for each.\n")
    add(_table(modules))

    # ------------------------------------------------------------------ 4
    add("## 4. Data handling (beyond A1)\n")
    add(
        "A1 used complete-case panels and no imputation. A3 keeps every country it "
        "defensibly can and documents each step (`results/data_notes.md`):\n"
    )
    notes = (config.RESULTS / "data_notes.md").read_text(encoding="utf-8")
    bullets = [ln for ln in notes.splitlines() if ln.startswith("- ")]
    add("\n".join(bullets) + "\n")
    add(
        f"\nAfter these steps the clean panel has {int(clean_row['rows']):,} country-years for "
        f"{int(clean_row['countries'])} countries; world totals use a balanced panel of "
        f"{int(balanced_row['countries'])} countries so that a country entering the data "
        f"cannot look like growth. Sanity checks: {sanity['duplicate_country_years']} "
        f"duplicate country-years, {sanity['negative_cells']} negative cells, mix sums "
        f"between {sanity['mix_sum_min']:.1f}% and {sanity['mix_sum_max']:.1f}%.\n"
    )
    add(fig.place("iter1_missingness_heatmap.png"))

    # ------------------------------------------------------------------ 5
    add("## 5. Iteration 1: the raw 2018 snapshot\n")
    add(
        "Iteration 1 deliberately uses the data as it comes: one year (2018, the last year "
        "with GDP), raw units and raw percentage shares. Its purpose is to find out what "
        "this representation gets wrong.\n"
    )
    add("### 5.1 Visual exploration\n")
    for f in [
        "iter1_global_mix_area.png",
        "iter1_distributions.png",
        "iter1_gdp_vs_energy_linear.png",
        "iter1_corr_pearson_vs_spearman.png",
        "iter1_lowcarbon_choropleth_2018.png",
        "iter1_change_2000_2018.png",
    ]:
        add(fig.place(f))
    add("### 5.2 [Statistics] Trend, correlation and a raw-scale regression\n")
    add(
        f"GDP and energy per person are strongly associated in 2018 (Pearson r = "
        f"{corr['pearson_r']:.2f}, Spearman ρ = {corr['spearman_rho']:.2f}, n = {corr['n']}); "
        "the gap between the two coefficients is a first sign that a few extreme countries "
        "drive the linear measure. The global low-carbon share of electricity has no "
        f"significant monotonic trend over {mk['years']} (Mann-Kendall p = {mk['p']:.3f}; "
        f"Hamed-Rao p = {mk['p_hamed_rao']:.3f}, which corrects for autocorrelation [4]; "
        f"Sen's slope [5] {mk['sen_slope']:+.2f} pp/yr).\n"
    )
    add(fig.place("iter1_ols_residuals.png"))
    add(_inference_block(inf, "I1-1"))
    add(_inference_block(inf, "I1-3"))
    add("### 5.3 [Unsupervised] K-means and PCA on raw shares\n")
    add(
        f"K-means on the 8 standardised mix shares and 3 intensities (n = {km1['n']}) picks "
        f"k = {km1['k']} by a rule fixed before fitting ({km1['rule']}); mean silhouette "
        f"{km1['silhouette']:.2f} ('{km1['silhouette_band']}' structure [8]). The clusters "
        f"largely re-label each country's dominant source (ARI {km1['ari_vs_dominant_source']:.2f}).\n"
    )
    for f in ["iter1_kmeans_k_selection.png", "iter1_kmeans_pca.png", "iter1_kmeans_map.png"]:
        add(fig.place(f))
    add(_inference_block(inf, "I1-2"))
    add("### 5.4 [Supervised] Random Forest for grid carbon intensity\n")
    add(
        f"A Random Forest (500 trees, 5-fold cross-validation, n = {rf1['n']}) predicts 2018 "
        "grid carbon intensity from income, energy use, population and 2016 fossil production. "
        "**Leakage guard:** carbon intensity is computed from the electricity mix, so no mix "
        "share, mix-derived or emissions column may be a feature; `models.assert_no_leakage` "
        f"checks every feature name before each fit. Result: R² {rf1['r2_mean']:.2f} ± "
        f"{rf1['r2_sd']:.2f} and MAE {rf1['mae_mean']:.0f} gCO2/kWh, against "
        f"{rf1['baseline_mae_mean']:.0f} for a mean predictor.\n"
    )
    for f in [
        "iter1_rf_pred_vs_actual.png",
        "iter1_rf_importance.png",
        "iter1_rf_residual_map.png",
    ]:
        add(fig.place(f))
    add(_inference_block(inf, "I1-4"))

    # ------------------------------------------------------------------ 6
    add("## 6. The feedback loop: from inferences to a transformed dataset\n")
    add(
        "Each iteration 1 inference names a defect, and each defect gets one transformation "
        "(Table 3). Together they change the scale of the variables, the geometry of the mix "
        "and, most importantly, the unit of analysis.\n"
    )
    lt = loop_tab[["inference", "transformation", "what_changes", "figure"]].copy()
    lt.columns = ["Inference", "Transformation", "What changes", "Before/after figure"]
    add("**Table 3.** Inference → transformation.\n")
    add(_table(lt))
    add(
        f"\n**Why this is a significant transformation.** The unit of analysis changes from "
        f"*{loop['unit_before']}* to *{loop['unit_after']}*: {loop['panel_rows']:,} country-year "
        f"rows become {loop['rows_after']} country rows, and {loop['feature_cols_before']} "
        f"snapshot features become {loop['feature_cols_after']} columns, most built from "
        f"several years. The largest absolute skewness falls from {loop['max_abs_skew_before']:.2f} "
        f"to {loop['max_abs_skew_after']:.2f}. The mix changes from {loop['mix_before']} to "
        f"{loop['mix_after']}.\n"
    )
    add(
        f"\n**CLR and its ε.** Shares that sum to 100% are compositional: their correlations "
        f"are partly forced by the constant sum, and Euclidean distances on raw percentages "
        f"overweight the large sources [3]. The centred log-ratio clr(x) = log(x + ε) − "
        f"mean(log(x + ε)) compares ratios between sources. ε = {config.CLR_EPS:g} pp handles "
        f"zero shares; the result is not sensitive to it ({eps_text}; silhouette at the "
        f"default {clr_default.silhouette_at_k_chosen:.2f}).\n"
    )
    add(
        "\n**Two trajectory tables.** A descriptive table uses endpoints up to 2019-21 for "
        "visuals; a model table uses no year after 2018, and its builder raises an error if "
        "given later data, so the Random Forest v2 and the 2019-21 forecast cannot see the "
        "future.\n"
    )
    for f in [
        "loop_before_after_table.png",
        "loop_skew_before_after.png",
        "loop_clr_before_after.png",
    ]:
        add(fig.place(f))
    skew_show = skew.copy()
    skew_show.columns = ["Variable", "n", "Skew (raw)", "Skew (log1p)"]
    add("**Table 4.** Skewness before and after log1p (2018).\n")
    add(_table(skew_show))

    # ------------------------------------------------------------------ 7
    add("## 7. Iteration 2: trajectories, archetypes and re-modelling\n")
    add("### 7.1 [Statistics] Decoupling of energy from GDP, by income tier\n")
    add(
        "Decoupling = growth of GDP per person minus growth of energy per person (CAGR, "
        "2000-02 to 2016-18). *Absolute* decoupling means GDP rose while energy per person "
        "fell; *relative* means both rose but energy more slowly.\n"
    )
    for f in [
        "iter2_decoupling_quadrant.png",
        "iter2_decoupling_by_tier.png",
        "iter2_slope_lowcarbon_by_income.png",
    ]:
        add(fig.place(f))
    add(_inference_block(inf, "I2-1"))
    add("### 7.2 [Statistics] Income elasticity of energy on log scales\n")
    add(fig.place("iter2_loglog_gdp_energy.png"))
    add(_inference_block(inf, "I2-2"))
    add("### 7.3 [Unsupervised] Transition archetypes\n")
    add(
        f"Countries are clustered on {len(config.ARCHETYPE_COLS)} standardised features: "
        f"{len(config.ARCHETYPE_TRAJECTORY_COLS)} trajectory features (growth, decoupling, "
        f"change in the low-carbon, coal and solar+wind shares, carbon-intensity change, "
        f"slope) and the {len(config.ARCHETYPE_CLR_COLS)} CLR mix coordinates. Small states "
        "(< 1 M people) are left out of the fit and assigned to the nearest centroid "
        "afterwards. K-means and a diagonal-covariance Gaussian mixture are compared for "
        f"k = 3..7 by a rule fixed in advance ({config.ARCHETYPE_METHOD_RULE}); K-means with "
        f"k = {stab['k']} is chosen. Archetype names follow a rule too: the largest positive "
        "CLR source plus the direction of the archetype's Mann-Kendall trend.\n"
    )
    nm = names[
        [
            "archetype",
            "short_name",
            "n_with_small_states",
            "sen_slope_pp_per_yr",
            "example_countries",
        ]
    ].copy()
    nm["archetype"] = "A" + nm["archetype"].astype(str)
    nm["sen_slope_pp_per_yr"] = nm["sen_slope_pp_per_yr"].map(lambda v: f"{v:+.2f}")
    nm["example_countries"] = nm["example_countries"].str.replace(";", ",")
    nm.columns = [
        "Archetype",
        "Name (rule-based)",
        "Countries",
        "Sen slope (pp/yr)",
        "Largest members",
    ]
    add("**Table 5.** The archetypes.\n")
    add(_table(nm))
    for f in [
        "iter2_k_selection.png",
        "iter2_vs_iter1_silhouette.png",
        "iter2_archetype_profiles.png",
        "iter2_archetype_map.png",
        "iter2_archetype_small_multiples.png",
    ]:
        add(fig.place(f))
    add(_inference_block(inf, "I2-3"))
    add("### 7.4 [Statistics] Are fossil producers stuck with dirty grids?\n")
    add(fig.place("iter2_producers_carbon.png"))
    add(_inference_block(inf, "I2-4"))
    add("### 7.5 [Supervised] Random Forest v2\n")
    add(
        f"RF v2 adds the history and context features asked for by I1-4 to the iteration 1 "
        f"features and is scored on the same {rfc['n']} countries and the same folds as a "
        f"re-scored v1 ({rfc['n_dropped_from_iter1']} iteration 1 countries lack trajectory "
        "data). The leakage guard is re-run on the new features. A log transform would not "
        "change a Random Forest (trees split on ranks), so any change comes from the new "
        "features, not from rescaling. Importance is read two ways: held-out permutation "
        "importance and SHAP values [13] from a forest refitted on all rows (for explanation "
        "only).\n"
    )
    add(fig.place("iter2_rf_improvement.png"))
    add(fig.place("iter2_rf_importance.png"))
    add(fig.place("iter2_shap_summary.png"))
    add(_inference_block(inf, "I2-5"))
    if has_forecast:
        add("### 7.6 [Supervised] Forecast vs reality, 2019-2021\n")
        add(
            "The same clustering is re-fitted on the pre-2019 table, and each group's median "
            "low-carbon share is forecast from 2000-2018 only (time-based split; the code "
            "asserts that training ends in 2018 and the test years are exactly 2019-2021). "
            "Holt's linear trend (plain and damped) and ARIMA(1,1,0) are compared with the naive "
            "last value.\n"
        )
        mae = fm.pivot(index="group", columns="method", values="mae").round(2).reset_index()
        mae.columns = ["Group", "ARIMA(1,1,0)", "Holt", "Holt damped", "Naive"]
        add("**Table 6.** Forecast MAE (pp), 2019-2021.\n")
        add(_table(mae))
        add(fig.place("iter2_forecast_vs_actual.png"))
        add(_inference_block(inf, "I2-6"))

    # ------------------------------------------------------------------ 8
    add("## 8. Discussion\n")
    add("### 8.1 Answer to the research question\n")
    add(
        "*Does getting richer still mean using more energy?* Across countries, yes: energy per "
        "person rises slightly more than proportionally with GDP per person (I2-2). Over time, "
        "not necessarily: most richer countries cut energy per person while growing (I2-1). "
        "The two statements are about different comparisons and are not in conflict.\n\n"
        "*Does it mean a dirtier grid?* No clear link. The Random Forest could not predict "
        "grid carbon intensity from income, growth or fuel production even after the feedback "
        "loop (I1-4, I2-5), and fossil producers are not significantly dirtier (I2-4). What "
        "sets a grid's carbon intensity is its mix, which reflects resources and policy "
        "choices that income does not capture.\n\n"
        "*How are countries moving?* Along a few broad paths (I2-3): coal-based grids "
        "(including China, the United States and Germany) gained low-carbon share fastest; a "
        "group of hydro-based grids lost share as demand grew faster than hydro capacity; "
        "gas- and hydro-based grids were mostly flat. The flat global trend in iteration 1 "
        "(I1-3) hides these opposing movements, which is what the feedback loop was built "
        "to reveal.\n"
    )
    add("### 8.2 What the feedback loop changed\n")
    add(
        "The loop changed the questions the models could answer more than their scores. "
        "Clustering trajectories produced groups that differ in direction of change, at the "
        "cost of a lower silhouette than the dominant-source clusters of iteration 1; the "
        "supervised model did not improve. Both are reported as found: a feedback loop is a "
        "test of a hypothesis about the data, and some of ours were rejected.\n"
    )
    add("### 8.3 Limitations\n")
    add(
        "- GDP ends in 2018, so every income-based analysis stops there.\n"
        "- OWID's own series contain interpolated and modelled values; we cannot audit them "
        "without external data (e.g. Qatar's GDP growth looks implausible and is not used as "
        "an example).\n"
        "- Producer data break after 2016; producer features use 2000-16 only.\n"
        "- CLR needs a pseudo-count ε for zero shares; results were checked for ε = 0.01, "
        "0.1 and 1.\n"
        "- Income tiers are data-derived quartiles, not official classifications; tiers set "
        "from 2000-02 GDP and growth measured from the same baseline invite regression to "
        "the mean.\n"
        "- About 150-200 countries: tests have limited power, and five cross-validation folds "
        "are too few to test the RF difference formally.\n"
        "- All results are associations between countries or over time; none is causal.\n"
    )

    # ------------------------------------------------------------------ 9
    add("## 9. Conclusion\n")
    add(
        "Iteration 1 showed that a raw 2018 snapshot misleads in four ways: skewed scales, "
        "percentage shares treated as independent numbers, a single year that hides change, "
        "and a model without context. The feedback loop answered each with a transformation, "
        "most importantly by changing the unit of analysis from a country-year to a "
        "country's path. Iteration 2 then showed decoupling concentrated outside the poorest "
        "tier, an income elasticity of energy just above one, transition archetypes that "
        "differ in direction rather than level, and no evidence that income, growth or fossil "
        "production determine how clean a grid is.\n"
    )

    # ------------------------------------------------------------------ 10
    add("## 10. References\n")
    refs = [
        "D. Keim, G. Andrienko, J.-D. Fekete, C. Görg, J. Kohlhammer and G. Melançon (2008). "
        "Visual Analytics: Definition, Process, and Challenges. In *Information Visualization: "
        "Human-Centered Issues and Perspectives*, LNCS 4950, Springer, pp. 154-175. "
        "doi:10.1007/978-3-540-70956-5_7",
        "Our World in Data. World Energy Consumption dataset (energy-data). "
        "https://github.com/owid/energy-data, distributed via Kaggle: "
        "https://www.kaggle.com/datasets/pralabhpoudel/world-energy-consumption",
        "J. Aitchison (1986). *The Statistical Analysis of Compositional Data*. Chapman and "
        "Hall, London.",
        "K. H. Hamed and A. R. Rao (1998). A modified Mann-Kendall trend test for "
        "autocorrelated data. *Journal of Hydrology* 204(1-4): 182-196.",
        "P. K. Sen (1968). Estimates of the regression coefficient based on Kendall's tau. "
        "*Journal of the American Statistical Association* 63(324): 1379-1389.",
        "F. Pedregosa et al. (2011). Scikit-learn: Machine Learning in Python. *Journal of "
        "Machine Learning Research* 12: 2825-2830.",
        "S. Seabold and J. Perktold (2010). statsmodels: Econometric and statistical modeling "
        "with Python. *Proceedings of the 9th Python in Science Conference*.",
        "L. Kaufman and P. J. Rousseeuw (1990). *Finding Groups in Data: An Introduction to "
        "Cluster Analysis*. Wiley, New York.",
        "L. Breiman (2001). Random Forests. *Machine Learning* 45(1): 5-32.",
        "H. B. Mann (1945). Nonparametric tests against trend. *Econometrica* 13(3): 245-259.",
        "S. Holm (1979). A simple sequentially rejective multiple test procedure. "
        "*Scandinavian Journal of Statistics* 6(2): 65-70.",
        "DAS732 A1 report, Team Spectrum (2026). *The World Energy Transition, 1990-2022* "
        "(Appendix A).",
        "S. M. Lundberg and S.-I. Lee (2017). A Unified Approach to Interpreting Model "
        "Predictions. *Advances in Neural Information Processing Systems* 30 (NeurIPS 2017).",
    ]
    add("\n".join(f"[{i}] {r}" for i, r in enumerate(refs, start=1)) + "\n")

    # ------------------------------------------------------------------ 11
    add("## Appendix A. A1 report\n")
    add(
        "The A1 report (*The World Energy Transition, 1990-2022*, Team Spectrum) is attached "
        "in full as `DAS732_A1_Report.pdf`; in the submitted PDF it follows this page. "
        "As the brief states, it is included for completeness and is not assessed as part of "
        "A3.\n"
    )
    add("## Appendix B. Reproducibility\n")
    add(
        "`pip install -r requirements.txt`, then run `notebooks/A3_workflow.ipynb` top to "
        "bottom; it regenerates `data/processed/`, `images/` and `results/` from the raw CSV "
        "with random_state = 42. `python -m src.report` rebuilds this report. `pytest` covers "
        "every transform, guard and test.\n"
    )

    unplaced = sorted(set(reg["filename"]) - set(fig.numbers))
    if unplaced:
        add(f"\n<!-- figures registered but not placed: {', '.join(unplaced)} -->\n")
    return "\n".join(s)


def write() -> Path:
    REPORT_DIR.mkdir(exist_ok=True)
    REPORT_MD.write_text(build(), encoding="utf-8")
    return REPORT_MD


if __name__ == "__main__":
    print(write())
