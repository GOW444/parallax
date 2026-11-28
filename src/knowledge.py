"""Knowledge summary (STEPS 159): the answer to the research question, with numbers.

Why: the last stage of the Keim et al. diamond is knowledge. This turns the saved results
into one readable page: what the data says about the research question, which of the plan's
hypotheses it contradicted, and what limits the answer. Every number is read from results/
(and checked by tests/test_knowledge.py), never typed.
"""

from pathlib import Path

import pandas as pd

from src import config, logbook


def _tier_row(counts: pd.DataFrame, tier: str) -> pd.Series:
    return counts.set_index("income_tier").loc[tier]


def _decoupling_paragraph(r: Path) -> str:
    counts = pd.read_csv(r / "iter2_decoupling_counts.csv")
    kw = logbook.load_metrics("iter2_kw", r)
    total = _tier_row(counts, "All")
    low, high = (
        _tier_row(counts, config.INCOME_TIER_LABELS[0]),
        _tier_row(counts, config.INCOME_TIER_LABELS[-1]),
    )
    return (
        f"Over time, energy use is decoupling from income: of {total['All']} countries, "
        f"{total['absolute decoupling']} decoupled absolutely (GDP per person up, energy per "
        f"person down) and {total['relative decoupling']} relatively. It is strongest in the "
        f"{config.INCOME_TIER_LABELS[-1]} tier ({high['absolute decoupling']} of {high['All']} "
        f"absolute) and weakest in the {config.INCOME_TIER_LABELS[0]} tier (only "
        f"{low['absolute decoupling']} of {low['All']}; Kruskal-Wallis p = {kw['kruskal_p']:.1e})."
    )


def _elasticity_paragraph(r: Path) -> str:
    loglog = logbook.load_metrics("iter2_loglog", r)
    cmp_ = pd.read_csv(r / "iter2_ols_comparison.csv")
    corr = logbook.load_metrics("iter1_correlation_test", r)
    raw_r2 = cmp_.loc[cmp_["model"].str.startswith("raw"), "r_squared"].iloc[0]
    return (
        f"Across countries, richer still means more energy: the Spearman correlation between "
        f"GDP and energy use per person is {corr['spearman_rho']:.2f} (n = {corr['n']}), and the "
        f"log-log elasticity is {loglog['slope']:.2f} (95% CI {loglog['slope_ci95_low']:.2f}-"
        f"{loglog['slope_ci95_high']:.2f}), explaining R² = {loglog['r_squared']:.2f} against "
        f"{raw_r2:.2f} for the raw fit. An elasticity above one and decoupling "
        "over time are different comparisons (between countries vs along each country's path), so "
        "they do not conflict. Neither is a causal effect of income."
    )


def _grid_paragraph(r: Path) -> str:
    rf1 = logbook.load_metrics("iter1_rf_metrics", r)
    rf = logbook.load_metrics("iter2_rf_comparison", r)
    prod = logbook.load_metrics("iter2_producers", r)
    return (
        "Richer does not clearly mean a dirtier grid. Income, energy use and fossil production "
        "predict 2018 grid carbon intensity only weakly (cross-validated R² "
        f"{rf1['r2_mean']:.2f}); "
        f"adding growth and decoupling history changed the mean absolute error from "
        f"{rf['v1_mae_mean']:.0f} to {rf['v2_mae_mean']:.0f} gCO2/kWh (mean predictor "
        f"{rf['baseline_mae_mean']:.0f}), within fold noise. Fossil producers ({prod['n_in']} "
        f"countries) are not significantly dirtier than the rest (median {prod['median_in']:.0f} "
        f"vs {prod['median_out']:.0f} gCO2/kWh, p = {prod['p']:.2f}). What sets a grid's carbon "
        "intensity is its mix, which cannot be used as a predictor without leakage."
    )


def _movement_paragraph(r: Path) -> str:
    names = pd.read_csv(r / "archetype_names.csv")
    stab = logbook.load_metrics("iter2_stability", r)
    mk = logbook.load_metrics("iter1_mk_global", r)
    change = logbook.load_metrics("iter1_change_summary", r)
    parts = "; ".join(
        f"{row.short_name} (n = {row.n_with_small_states}, {row.sen_slope_pp_per_yr:+.2f} pp/yr)"
        for row in names.itertuples()
    )
    return (
        f"The global low-carbon share shows no significant trend (Hamed-Rao p = "
        f"{mk['p_hamed_rao']:.2f}, Sen slope {mk['sen_slope']:+.2f} pp/yr), but "
        f"{change['n_changed_over_threshold']} of {change['n_countries']} countries moved by more "
        f"than {change['threshold_pp']:g} pp ({change['n_rose_over_threshold']} up, "
        f"{change['n_fell_over_threshold']} down). Clustering the country paths gives "
        f"{stab['k']} archetypes: {parts}. They are reproducible (mean ARI {stab['ari_mean']:.2f} "
        f"over {stab['n_seeds']} seeds) but weakly separated (silhouette "
        f"{stab['silhouette']:.2f}): a partition of a continuum, not natural types."
    )


def _forecast_paragraph(r: Path) -> str:
    fm = pd.read_csv(r / "iter2_forecast_metrics.csv")
    covid = logbook.load_metrics("iter2_covid", r)
    mean_mae = fm.groupby("method")["mae"].mean()
    best = mean_mae.idxmin()
    return (
        f"Trained on {config.YEAR_START}-{config.PRE2019_MAX_YEAR} and tested on "
        f"{config.PRE2019_MAX_YEAR + 1}-{config.YEAR_END}, the best method by mean MAE is "
        f"{best} ({mean_mae[best]:.2f} pp) against {mean_mae['naive']:.2f} pp for the naive last "
        f"value. Total generation of the balanced panel changed "
        f"{covid['balanced_panel_generation_change_2020_pct']:+.1f}% in 2020."
    )


def contradicted_hypotheses(results_dir: Path) -> list[str]:
    """Every plan claim the data did not support, from both hypothesis-check tables."""
    out = []
    for name in ("iter1_hypothesis_check.csv", "iter2_hypothesis_check.csv"):
        path = results_dir / name
        if not path.exists():
            continue
        table = pd.read_csv(path)
        for row in table[~table["supported"]].itertuples():
            out.append(
                f"**{row.inference}**: {row.plan_claim}. Rule: {row.rule}. Found: {row.value}."
            )
    return out


def limitations(r: Path) -> list[str]:
    """Limits on the answers above, each with the number that sets it."""
    countries = pd.read_csv(r / "iter2_country_set.csv")
    rf = logbook.load_metrics("iter2_rf_comparison", r)
    return [
        f"GDP ends in {config.GDP_LAST_YEAR}, so every income-based result stops there; "
        f"{int(countries['gdp_endpoints'].sum())} of {len(countries)} countries have the GDP "
        f"endpoints needed and {int(countries['in_set'].sum())} are in the iteration 2 set.",
        f"Producer data break after {config.PRODUCER_LAST_FULL_YEAR}; producer features use "
        f"{config.PRODUCER_YEARS[0]}-{config.PRODUCER_YEARS[1]} only.",
        f"{rf['n_folds']} cross-validation folds are too few to test the Random Forest "
        "difference formally.",
        "Income tiers are data-derived quartiles of 2000-02 GDP per person, and the growth "
        "measured from that baseline invites regression to the mean.",
        "All results are associations between countries or over time; none is causal.",
    ]


def build(results_dir: Path = config.RESULTS) -> str:
    """The knowledge summary as markdown."""
    lines = [
        "# Knowledge summary",
        "",
        "_Generated from `results/` by `src/knowledge.py`. Do not edit by hand._",
        "",
        f"**Research question.** {config.RESEARCH_QUESTION}",
        "",
        "## Does getting richer still mean using more energy?",
        "",
        _elasticity_paragraph(results_dir),
        "",
        _decoupling_paragraph(results_dir),
        "",
        "## Does it mean running a dirtier electricity grid?",
        "",
        _grid_paragraph(results_dir),
        "",
        "## How are countries moving through the transition?",
        "",
        _movement_paragraph(results_dir),
        "",
        "## Forecast check, 2019-2021",
        "",
        _forecast_paragraph(results_dir),
        "",
        "## Plan hypotheses the data did not support",
        "",
        *[f"- {item}" for item in contradicted_hypotheses(results_dir)],
        "",
        "## Limits on these answers",
        "",
        *[f"- {item}" for item in limitations(results_dir)],
        "",
    ]
    return "\n".join(lines)


def write(results_dir: Path = config.RESULTS) -> Path:
    """Write results/knowledge_summary.md."""
    path = results_dir / "knowledge_summary.md"
    path.write_text(build(results_dir), encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write())
