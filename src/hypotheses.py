"""Test each iteration 1 inference against the hypothesis A3_PLAN.md wrote before the data.

Why: the plan's hypotheses are guesses (CLAUDE.md: "guesses until the data confirms them").
Each one is split into separate claims; each claim has a rule fixed in config and a verdict
computed from the saved results. The report can then say honestly which guesses held.
"""

import pandas as pd

from src import config


def claim(inference: str, plan_claim: str, rule: str, value: str, supported: bool) -> dict:
    """One testable part of a plan hypothesis, with the evidence and the verdict."""
    return {
        "inference": inference,
        "plan_claim": plan_claim,
        "rule": rule,
        "value": value,
        "supported": bool(supported),
    }


def overall_verdict(supported: list[bool]) -> str:
    """'confirmed' if every claim holds, 'not confirmed' if none does, else 'partly confirmed'."""
    if all(supported):
        return "confirmed"
    return "not confirmed" if not any(supported) else "partly confirmed"


def _count_text(names: list[str], total: int) -> str:
    """'1 of 4 (Iceland)' / '0 of 4'."""
    return f"{len(names)} of {total}" + (f" ({', '.join(names)})" if names else "")


def check_i1_1(skew: dict, top_residuals: pd.DataFrame) -> list[dict]:
    """Skew of the per-person variables; size and producer status of the largest residuals.

    `top_residuals` has country, population and is_producer (oil, gas or coal output > 0 in
    2016) for the N_OLS_NAMED largest raw-OLS residuals.
    """
    skews = {c: skew[c] for c in config.SKEW_CHECK_COLS}
    n = len(top_residuals)
    small = top_residuals.loc[top_residuals["population"] < config.SMALL_STATE_POP, "country"]
    producers = top_residuals.loc[top_residuals["is_producer"], "country"]
    pop_m = config.SMALL_STATE_POP / 1e6
    return [
        claim(
            "I1-1",
            "The per-person variables are heavily skewed",
            f"skewness > {config.SKEW_HEAVY:g} for every per-person variable",
            ", ".join(f"{config.FEATURE_SHORT[c]} {v:.2f}" for c, v in skews.items()),
            min(skews.values()) > config.SKEW_HEAVY,
        ),
        claim(
            "I1-1",
            "The dominating countries are small states",
            f"most of the {n} largest OLS residuals have population < {pop_m:g} M",
            _count_text(small.tolist(), n),
            len(small) > n / 2,
        ),
        claim(
            "I1-1",
            "The dominating countries are fossil producers",
            f"most of the {n} largest OLS residuals produced oil, gas or coal in 2016",
            _count_text(producers.tolist(), n),
            len(producers) > n / 2,
        ),
    ]


def check_i1_2(clusters: pd.DataFrame, assignments: pd.DataFrame) -> list[dict]:
    """Are the K-means clusters about the current mix, about scale, and is the smallest tiny?

    A cluster whose name does not end in ' share' is defined by a scale variable (energy or
    electricity per person); see models.describe_centres().
    """
    k = len(clusters)
    by_source = clusters["name"].str.endswith(" share")
    smallest = clusters.loc[clusters["size"].idxmin()]
    members = assignments[assignments["cluster"] == smallest["cluster"]]
    n_small = int((members["population"] < config.SMALL_STATE_POP).sum())
    pop_m = config.SMALL_STATE_POP / 1e6
    return [
        claim(
            "I1-2",
            "Clusters do not read as transition types",
            "most clusters are defined by one source's current share (a level, not a change)",
            f"{int(by_source.sum())} of {k} clusters",
            by_source.sum() > k / 2,
        ),
        claim(
            "I1-2",
            "Clusters are driven by scale",
            "most clusters are defined by energy or electricity per person",
            f"{int((~by_source).sum())} of {k} clusters",
            (~by_source).sum() > k / 2,
        ),
        claim(
            "I1-2",
            "There is a tiny cluster of high-consumption small states",
            f"the smallest cluster is defined by scale and most members have population < "
            f"{pop_m:g} M",
            f"smallest = '{smallest['name']}' (n = {smallest['size']}), "
            f"{n_small} of {smallest['size']} small states",
            (not smallest["name"].endswith(" share")) and n_small > smallest["size"] / 2,
        ),
    ]


def check_i1_3(change: dict, mk_global: dict) -> list[dict]:
    """Typical change vs the spread of changes vs the global trend (iter1_change_summary)."""
    t = change["threshold_pp"]
    m = config.MIN_GROUP_SIZE
    return [
        claim(
            "I1-3",
            "The typical country's low-carbon share changed a lot",
            f"|median change| > {t:g} pp",
            f"median {change['median_change_pp']:+.1f} pp",
            abs(change["median_change_pp"]) > t,
        ),
        claim(
            "I1-3",
            "Many countries changed a lot, in both directions",
            f"at least {m} countries rose and at least {m} fell by more than {t:g} pp",
            f"{change['n_changed_over_threshold']} of {change['n_countries']} "
            f"({change['share_changed_over_threshold']:.0%}): "
            f"{change['n_rose_over_threshold']} rose, {change['n_fell_over_threshold']} fell",
            change["n_rose_over_threshold"] >= m and change["n_fell_over_threshold"] >= m,
        ),
        claim(
            "I1-3",
            "A global summary hides this change",
            f"no significant global trend (Hamed-Rao Mann-Kendall p >= {config.ALPHA})",
            f"p = {mk_global['p_hamed_rao']:.3f}, Sen's slope {mk_global['sen_slope']:+.2f} pp/yr",
            mk_global["p_hamed_rao"] >= config.ALPHA,
        ),
    ]


def _largest_median(block: dict) -> dict:
    """The tested group with the largest median in a stats.compare_groups() result."""
    tested = [g for g in block["by_group"] if g["group"] in block["groups_tested"]]
    return max(tested, key=lambda g: g["median"])


def _medians_text(block: dict) -> str:
    """'Hydro 205, Coal 185, ...' for the tested groups, largest median first."""
    tested = [g for g in block["by_group"] if g["group"] in block["groups_tested"]]
    tested = sorted(tested, key=lambda g: g["median"], reverse=True)
    return ", ".join(f"{g['group']} {g['median']:.0f}" for g in tested)


def check_i1_4(rf_metrics: dict, groups: dict) -> list[dict]:
    """R-squared level; whether hydro/nuclear grids and small states have the biggest errors."""
    by_source = groups["by_dominant_source_abs"]
    by_size = groups["by_small_state_abs"]
    top_source = _largest_median(by_source)
    sizes = {g["group"]: g["median"] for g in by_size["by_group"]}
    a = config.ALPHA
    return [
        claim(
            "I1-4",
            "The Random Forest reaches a moderate R-squared",
            f"cross-validated mean R-squared >= {config.MODERATE_R2:g}",
            f"R-squared {rf_metrics['r2_mean']:.2f} +/- {rf_metrics['r2_sd']:.2f}",
            rf_metrics["r2_mean"] >= config.MODERATE_R2,
        ),
        claim(
            "I1-4",
            "Hydro- or nuclear-dominated grids have the biggest errors",
            f"the dominant source with the largest median |error| is Hydro or Nuclear and "
            f"Kruskal-Wallis p < {a}",
            f"median |error| (gCO2/kWh) {_medians_text(by_source)}; "
            f"p = {by_source['kruskal_p']:.1e}",
            top_source["group"] in ("Hydro", "Nuclear") and by_source["kruskal_p"] < a,
        ),
        claim(
            "I1-4",
            "Small states have bigger errors",
            f"small states have the larger median |error| and Kruskal-Wallis p < {a}",
            f"small state {sizes['small state']:.0f} vs other {sizes['other']:.0f} gCO2/kWh; "
            f"p = {by_size['kruskal_p']:.3f}",
            sizes["small state"] > sizes["other"] and by_size["kruskal_p"] < a,
        ),
    ]


def hypothesis_table(
    claims: list[dict], plan_hypotheses: dict[str, str] = config.PLAN_HYPOTHESES_ITER1
) -> pd.DataFrame:
    """All claims as one table, with the plan hypothesis and the overall verdict per inference."""
    table = pd.DataFrame(claims)
    verdicts = table.groupby("inference")["supported"].apply(lambda s: overall_verdict(list(s)))
    table.insert(1, "plan_hypothesis", table["inference"].map(plan_hypotheses))
    table["overall_verdict"] = table["inference"].map(verdicts)
    return table


# ------------------------------------------------------------------ iteration 2 (STEPS 152)
def check_i2_1(counts: pd.DataFrame, pairwise: pd.DataFrame, kw: dict) -> list[dict]:
    """Decoupling: how common, where it is absolute, whether tiers differ and in what order.

    `counts` is iter2_decoupling_counts.csv (tiers x classes, with an 'All' row), `pairwise`
    the Holm-corrected Mann-Whitney table and `kw` the Kruskal-Wallis result.
    """
    rows = counts.set_index("income_tier")
    total, richest = rows.loc["All"], rows.loc[config.INCOME_TIER_LABELS[-1]]
    decoupled = total["absolute decoupling"] + total["relative decoupling"]
    significant = {
        frozenset((r.group_a, r.group_b)): bool(r.significant_holm) for r in pairwise.itertuples()
    }
    ladder = [
        significant[frozenset(pair)]
        for pair in zip(config.INCOME_TIER_LABELS[:-1], config.INCOME_TIER_LABELS[1:], strict=True)
    ]
    return [
        claim(
            "I2-1",
            "Most countries decouple energy from GDP",
            "more than half of the countries show absolute or relative decoupling",
            f"{decoupled} of {total['All']} ({decoupled / total['All']:.0%})",
            decoupled > total["All"] / 2,
        ),
        claim(
            "I2-1",
            "Decoupling is absolute in the richest tier",
            f"more than half of the {config.INCOME_TIER_LABELS[-1]}-tier countries decoupled "
            "absolutely (GDP up, energy down)",
            f"{richest['absolute decoupling']} of {richest['All']}",
            richest["absolute decoupling"] > richest["All"] / 2,
        ),
        claim(
            "I2-1",
            "Decoupling differs by income tier",
            f"Kruskal-Wallis p < {config.ALPHA}",
            f"p = {kw['kruskal_p']:.1e}",
            kw["kruskal_p"] < config.ALPHA,
        ),
        claim(
            "I2-1",
            "Each richer tier decouples more than the one below it",
            f"every adjacent pair of tiers differs (Holm-corrected p < {config.ALPHA})",
            f"{sum(ladder)} of {len(ladder)} adjacent pairs differ",
            all(ladder),
        ),
    ]


def check_i2_2(ols: pd.DataFrame) -> list[dict]:
    """Logs help OLS: more variance explained and less heteroscedasticity than the raw fit."""
    raw = ols[ols["model"].str.startswith("raw")].iloc[0]
    log = ols[ols["model"].str.startswith("log")].iloc[0]
    return [
        claim(
            "I2-2",
            "The log-log fit explains more variance",
            "R-squared of the log fit > R-squared of the raw fit",
            f"R-squared {raw['r_squared']:.2f} -> {log['r_squared']:.2f}",
            log["r_squared"] > raw["r_squared"],
        ),
        claim(
            "I2-2",
            "The log-log fit is less heteroscedastic",
            "Breusch-Pagan p of the log fit > p of the raw fit",
            f"p = {raw['breusch_pagan_p']:.3f} -> {log['breusch_pagan_p']:.3f}",
            log["breusch_pagan_p"] > raw["breusch_pagan_p"],
        ),
        claim(
            "I2-2",
            "The log-log fit is homoscedastic",
            f"Breusch-Pagan p >= {config.ALPHA}",
            f"p = {log['breusch_pagan_p']:.3f}",
            log["breusch_pagan_p"] >= config.ALPHA,
        ),
    ]


def check_i2_3(
    silhouettes: dict, stability: dict, centroids: pd.DataFrame, names: pd.DataFrame
) -> list[dict]:
    """Archetypes: separation vs iteration 1, stability, and the plan's example archetypes."""
    k = stability["k"]
    rows = silhouettes["rows"]
    it1 = next(
        r for r in rows if r["space"].startswith("Iteration 1") and r["space"].endswith(f"k = {k}")
    )
    it2 = next(r for r in rows if r["space"].startswith("Iteration 2"))
    c = centroids.set_index("archetype")
    label = dict(zip(names["archetype"], names["short_name"], strict=True))
    solar = c["d_solarwind"].idxmax()
    legacy = c[
        (c["lowcarbon_2000"] > config.ARCHETYPE_LEVEL_Z)
        & (
            (c["clr_hydro"] > config.ARCHETYPE_LEVEL_Z)
            | (c["clr_nuclear"] > config.ARCHETYPE_LEVEL_Z)
        )
    ]
    return [
        claim(
            "I2-3",
            "The iteration 2 clusters are better separated than iteration 1's",
            f"silhouette in the iteration 2 space > silhouette of the iteration 1 space at the "
            f"same k = {k} and the same countries",
            f"{it1['silhouette']:.2f} (iteration 1) vs {it2['silhouette']:.2f} (iteration 2)",
            it2["silhouette"] > it1["silhouette"],
        ),
        claim(
            "I2-3",
            "The archetypes are stable across seeds",
            f"mean ARI over {stability['n_seeds']} seeds >= {config.MIN_STABLE_ARI:g}",
            f"mean {stability['ari_mean']:.2f}, min {stability['ari_min']:.2f}",
            stability["ari_mean"] >= config.MIN_STABLE_ARI,
        ),
        claim(
            "I2-3",
            "There is a 'fast wind/solar adopters' archetype",
            f"some archetype's centroid is > {config.ARCHETYPE_STRONG_Z:g} sd above average on "
            "the change in solar+wind share",
            f"A{solar} ({label[solar]}): {c.loc[solar, 'd_solarwind']:+.2f} sd",
            bool(c.loc[solar, "d_solarwind"] > config.ARCHETYPE_STRONG_Z),
        ),
        claim(
            "I2-3",
            "There is a 'legacy clean (hydro/nuclear)' archetype",
            f"some archetype has a high 2000 low-carbon share and a high hydro or nuclear CLR "
            f"(both > {config.ARCHETYPE_LEVEL_Z:g} sd)",
            ", ".join(f"A{a} ({label[a]})" for a in legacy.index) or "none",
            len(legacy) > 0,
        ),
    ]


def check_i2_4(producers: dict) -> list[dict]:
    """Producers vs non-producers: are producers' grids dirtier?"""
    return [
        claim(
            "I2-4",
            "Fossil producers have dirtier grids",
            f"producers' median carbon intensity is higher and Mann-Whitney p < {config.ALPHA}",
            f"median {producers['median_in']:.0f} vs {producers['median_out']:.0f} gCO2/kWh, "
            f"p = {producers['p']:.2f}",
            producers["median_in"] > producers["median_out"] and producers["p"] < config.ALPHA,
        )
    ]


def check_i2_5(rf: dict) -> list[dict]:
    """RF v2 vs v1 on the same rows and folds, and v2 vs the mean predictor."""
    n_folds = rf["n_folds"]
    return [
        claim(
            "I2-5",
            "The history features improve the Random Forest",
            f"v2 has the lower MAE in at least {config.RF_V2_MIN_FOLDS_BETTER} of {n_folds} "
            "paired folds and a negative mean paired change",
            f"better in {rf['folds_v2_better_mae']} of {n_folds}, mean change "
            f"{rf['mean_d_mae']:+.1f} gCO2/kWh",
            rf["folds_v2_better_mae"] >= config.RF_V2_MIN_FOLDS_BETTER and rf["mean_d_mae"] < 0,
        ),
        claim(
            "I2-5",
            "RF v2 beats the mean predictor",
            "v2 mean MAE < mean-predictor mean MAE",
            f"{rf['v2_mae_mean']:.0f} vs {rf['baseline_mae_mean']:.0f} gCO2/kWh",
            rf["v2_mae_mean"] < rf["baseline_mae_mean"],
        ),
    ]


def check_i2_6(forecast_metrics: pd.DataFrame, covid: dict) -> list[dict]:
    """Do the trend methods beat the naive last value, and did 2020 show a demand shock?"""
    mean_mae = forecast_metrics.groupby("method")["mae"].mean()
    labels = {
        "holt": "Holt linear trend",
        "holt_damped": "damped Holt",
        "arima_110": "ARIMA(1,1,0)",
    }
    claims = [
        claim(
            "I2-6",
            f"{label} beats the naive last value",
            "mean MAE over the pre-2019 groups < naive mean MAE",
            f"{mean_mae[m]:.2f} vs {mean_mae['naive']:.2f} pp",
            mean_mae[m] < mean_mae["naive"],
        )
        for m, label in labels.items()
    ]
    change = covid["balanced_panel_generation_change_2020_pct"]
    claims.append(
        claim(
            "I2-6",
            "2020 shows a COVID demand shock",
            "electricity generation of the balanced panel fell in 2020",
            f"{change:+.1f}% in 2020 vs "
            f"{covid['balanced_panel_generation_change_2019_pct']:+.1f}% in 2019",
            change < 0,
        )
    )
    return claims
