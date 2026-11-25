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
