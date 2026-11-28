"""Tests for the inference number audit (STEPS 151)."""

import json

import numpy as np
import pandas as pd

from src import number_audit as na


def test_extract_numbers_skips_ids_year_ranges_and_unit_digits():
    text = "I2-5: R² 0.72 -> 0.90 in 2000-02, CO2 of -205 gCO2/kWh, 95% CI 1.13-1.27 (n = 165)."
    assert na.extract_numbers(text) == ["0.72", "0.90", "-205", "95", "1.13", "1.27", "165"]


def test_matches_uses_the_printed_precision():
    values = np.array([0.7182, 123.456])
    assert na.matches("0.72", values)
    assert not na.matches("0.73", values)
    assert na.matches("123.5", values)
    assert not na.matches("124.5", values)


def test_matches_accepts_percent_and_absolute_forms():
    assert na.matches("35.8", np.array([0.358]))  # a fraction printed as percent
    assert na.matches("205", np.array([-205.2]))  # a gap quoted without its sign


def test_csv_aggregates_make_a_column_mean_traceable(tmp_path):
    path = tmp_path / "t.csv"
    pd.DataFrame({"method": ["a", "a", "b", "b"], "mae": [1.0, 3.0, 2.0, 6.0]}).to_csv(
        path, index=False
    )
    values = na.file_numbers(path)
    assert na.matches("2.00", values)  # mean of method a
    assert na.matches("4.00", values)  # mean of method b
    assert not na.matches("5.00", values)


def _write_results(tmp_path, statement, evidence):
    (tmp_path / "inferences.json").write_text(
        json.dumps({"I9-1": {"statement": statement, "evidence": evidence}})
    )
    (tmp_path / "m.json").write_text(json.dumps({"r2": 0.8123}))
    (tmp_path / "other.json").write_text(json.dumps({"p": 0.0412}))
    return na.run(tmp_path)


def test_run_flags_a_hand_typed_number(tmp_path):
    result = _write_results(tmp_path, "R² is 0.81 and R² is 0.99.", "results/m.json")
    assert result["summary"]["untraced"] == {"I9-1": ["0.99"]}


def test_run_separates_cited_from_uncited_sources(tmp_path):
    result = _write_results(tmp_path, "R² is 0.81 and p = 0.041.", "results/m.json")
    audit = result["per_inference"]["I9-1"]
    assert audit["cited"] == ["0.81"]
    assert audit["uncited"] == ["0.041 <- other.json"]
    assert result["summary"]["needs_evidence_line_update"] == {"I9-1": ["0.041 <- other.json"]}


def test_significance_thresholds_are_not_results(tmp_path):
    result = _write_results(tmp_path, "R² is 0.81 (p < 0.05).", "results/m.json")
    assert result["per_inference"]["I9-1"]["threshold"] == ["0.05"]
    assert result["summary"]["untraced"] == {}


def test_the_committed_inferences_trace_to_results():
    """Regression guard on the real project: no inference may carry an untraceable number."""
    from src import config

    if not (config.RESULTS / "inferences.json").exists():
        return
    summary = na.run()["summary"]
    assert summary["untraced"] == {}, summary["untraced"]
