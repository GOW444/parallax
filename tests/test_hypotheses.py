"""Tests for the plan-hypothesis checks and the change summary behind I1-3."""

import pandas as pd

from src import config, features, hypotheses


def test_overall_verdict():
    assert hypotheses.overall_verdict([True, True]) == "confirmed"
    assert hypotheses.overall_verdict([False, False]) == "not confirmed"
    assert hypotheses.overall_verdict([True, False]) == "partly confirmed"


def test_change_summary_splits_rises_and_falls():
    table = pd.DataFrame(
        {
            "country": list("ABCDE"),
            "base_mean": [10.0, 50.0, 20.0, 30.0, 40.0],
            "end_mean": [40.0, 20.0, 21.0, 30.0, 41.0],
            "rank_change": [2.0, -2.0, 0.0, 1.0, -1.0],
        }
    )
    table["change"] = table["end_mean"] - table["base_mean"]
    summary = features.change_summary(table, threshold=10)
    assert summary["n_rose_over_threshold"] == 1  # A: +30
    assert summary["n_fell_over_threshold"] == 1  # B: -30
    assert summary["n_changed_over_threshold"] == 2
    assert summary["median_change_pp"] == 1.0  # the two large moves cancel in the median
    assert summary["largest_rises"][0]["country"] == "A"
    assert summary["largest_falls"][0]["country"] == "B"


def test_check_i1_1_counts_small_states_and_producers():
    skew = {c: 2.0 for c in config.SKEW_CHECK_COLS}
    top = pd.DataFrame(
        {
            "country": ["A", "B", "C", "D"],
            "population": [5e5, 2e6, 3e6, 4e6],
            "is_producer": [False, True, True, True],
        }
    )
    skewed, small, producer = hypotheses.check_i1_1(skew, top)
    assert skewed["supported"]
    assert not small["supported"] and small["value"] == "1 of 4 (A)"
    assert producer["supported"]


def test_check_i1_4_reads_group_results():
    metrics = {"r2_mean": 0.5, "r2_sd": 0.1}
    groups = {
        "by_dominant_source_abs": {
            "kruskal_p": 0.001,
            "groups_tested": ["Hydro", "Coal"],
            "by_group": [
                {"group": "Coal", "median": 100},
                {"group": "Hydro", "median": 200},
                {"group": "Wind", "median": 900},  # untested (too small): must be ignored
            ],
        },
        "by_small_state_abs": {
            "kruskal_p": 0.5,
            "groups_tested": ["small state", "other"],
            "by_group": [{"group": "small state", "median": 1}, {"group": "other", "median": 2}],
        },
    }
    r2, hydro, small = hypotheses.check_i1_4(metrics, groups)
    assert r2["supported"] and hydro["supported"] and not small["supported"]
    table = hypotheses.hypothesis_table([r2, hydro, small])
    assert set(table["overall_verdict"]) == {"partly confirmed"}
    assert table["plan_hypothesis"].iloc[0] == config.PLAN_HYPOTHESES_ITER1["I1-4"]


def test_loop_rows_use_config_details_and_skip_non_triggers():
    from src import logbook

    entries = {
        "I1-1": {
            "statement": "s",
            "evidence": "a.png",
            "triggers_loop": True,
            "transformation": "long text",
        },
        "I2-1": {
            "statement": "s",
            "evidence": "b.png",
            "triggers_loop": False,
            "transformation": "",
        },
    }
    rows = logbook.loop_rows(entries)
    assert [r["inference"] for r in rows] == ["I1-1"]
    assert rows[0]["what_changes"] == config.LOOP_DETAILS["I1-1"]["what_changes"]


def test_ordinal_wording():
    from src import figures

    assert [figures._ordinal(f) for f in (0.224, 0.965, 0.11, 0.013)] == [
        "22nd",
        "96th",
        "11th",
        "1st",
    ]


# ------------------------------------------------------------------ iteration 2 checks
def _counts() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "income_tier": [*config.INCOME_TIER_LABELS, "All"],
            "absolute decoupling": [1, 2, 3, 8, 14],
            "relative decoupling": [3, 4, 4, 1, 12],
            "coupled": [5, 3, 2, 1, 11],
            "GDP fell": [1, 1, 1, 0, 3],
            "All": [10, 10, 10, 10, 40],
        }
    )


def _pairwise(adjacent_significant: list[bool]) -> pd.DataFrame:
    tiers = config.INCOME_TIER_LABELS
    return pd.DataFrame(
        {
            "group_a": tiers[:-1],
            "group_b": tiers[1:],
            "significant_holm": adjacent_significant,
        }
    )


def test_check_i2_1_ladder_needs_every_adjacent_pair():
    kw = {"kruskal_p": 1e-4}
    ladder, *_ = reversed(hypotheses.check_i2_1(_counts(), _pairwise([True, False, False]), kw))
    assert not ladder["supported"] and ladder["value"] == "1 of 3 adjacent pairs differ"
    full = hypotheses.check_i2_1(_counts(), _pairwise([True, True, True]), kw)
    assert [c["supported"] for c in full] == [True, True, True, True][:3] + [True]
    # most decouple (26 of 40), richest tier mostly absolute (8 of 10)
    assert full[0]["value"].startswith("26 of 40") and full[1]["value"] == "8 of 10"


def test_check_i2_2_separates_improvement_from_homoscedasticity():
    ols = pd.DataFrame(
        {
            "model": ["raw: energy ~ gdp", "log: log energy ~ log gdp"],
            "r_squared": [0.7, 0.9],
            "breusch_pagan_p": [0.001, 0.04],
        }
    )
    more, less, homo = hypotheses.check_i2_2(ols)
    assert more["supported"] and less["supported"] and not homo["supported"]


def test_check_i2_3_reads_the_plan_examples_from_the_centroids():
    k = 2
    centroids = pd.DataFrame(
        {
            "archetype": [1, 2],
            "d_solarwind": [1.5, 0.0],
            "lowcarbon_2000": [-1.0, 1.0],
            "clr_hydro": [0.0, 1.0],
            "clr_nuclear": [0.0, 0.0],
        }
    )
    names = pd.DataFrame({"archetype": [1, 2], "short_name": ["Coal", "Hydro"]})
    sil = {
        "rows": [
            {"space": f"Iteration 1 space (raw shares), k = {k}", "silhouette": 0.3},
            {"space": "Iteration 1 space (raw shares), k = 8", "silhouette": 0.4},
            {"space": f"Iteration 2 space (trajectory + CLR), k = {k}", "silhouette": 0.1},
        ]
    }
    stab = {"k": k, "n_seeds": 20, "ari_mean": 0.82, "ari_min": 0.7}
    better, stable, solar, legacy = hypotheses.check_i2_3(sil, stab, centroids, names)
    assert not better["supported"] and "0.30 (iteration 1) vs 0.10" in better["value"]
    assert stable["supported"] and solar["supported"] and legacy["supported"]
    assert legacy["value"] == "A2 (Hydro)"


def test_check_i2_4_needs_higher_median_and_significance():
    (dirty,) = hypotheses.check_i2_4({"median_in": 490.0, "median_out": 443.0, "p": 0.44})
    assert not dirty["supported"]
    (dirty,) = hypotheses.check_i2_4({"median_in": 490.0, "median_out": 443.0, "p": 0.01})
    assert dirty["supported"]


def test_check_i2_5_uses_the_fold_rule_from_config():
    rf = {
        "n_folds": 5,
        "folds_v2_better_mae": 2,
        "mean_d_mae": 3.4,
        "v2_mae_mean": 170.0,
        "baseline_mae_mean": 178.0,
    }
    better, beats_mean = hypotheses.check_i2_5(rf)
    assert not better["supported"] and beats_mean["supported"]
    rf.update(folds_v2_better_mae=config.RF_V2_MIN_FOLDS_BETTER, mean_d_mae=-1.0)
    assert hypotheses.check_i2_5(rf)[0]["supported"]


def test_check_i2_6_compares_each_method_with_the_naive_baseline():
    metrics = pd.DataFrame(
        {
            "method": ["naive", "holt", "holt_damped", "arima_110"] * 2,
            "mae": [2.0, 3.0, 1.0, 1.5, 2.0, 3.0, 1.0, 1.5],
        }
    )
    covid = {
        "balanced_panel_generation_change_2020_pct": -0.3,
        "balanced_panel_generation_change_2019_pct": 1.3,
    }
    holt, damped, arima, shock = hypotheses.check_i2_6(metrics, covid)
    assert not holt["supported"] and damped["supported"] and arima["supported"]
    assert shock["supported"] and shock["value"] == "-0.3% in 2020 vs +1.3% in 2019"


def test_hypothesis_table_accepts_the_iteration_2_plan_text():
    claims = hypotheses.check_i2_4({"median_in": 490.0, "median_out": 443.0, "p": 0.44})
    table = hypotheses.hypothesis_table(claims, config.PLAN_HYPOTHESES_ITER2)
    assert table.loc[0, "overall_verdict"] == "not confirmed"
    assert table.loc[0, "plan_hypothesis"] == config.PLAN_HYPOTHESES_ITER2["I2-4"]
