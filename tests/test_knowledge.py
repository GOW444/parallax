"""The knowledge summary must be built from results/ only (STEPS 159)."""

import numpy as np
import pytest

from src import config, knowledge
from src import number_audit as na

pytestmark = pytest.mark.skipif(
    not (config.RESULTS / "iter2_loglog.json").exists(), reason="results/ not generated yet"
)


def test_summary_has_every_section_and_no_placeholders():
    text = knowledge.build()
    for heading in (
        "Does getting richer still mean using more energy?",
        "Does it mean running a dirtier electricity grid?",
        "How are countries moving through the transition?",
        "Forecast check, 2019-2021",
        "Plan hypotheses the data did not support",
        "Limits on these answers",
    ):
        assert f"## {heading}" in text
    assert config.RESEARCH_QUESTION in text
    assert "nan" not in text.lower().split() and "TODO" not in text


def test_every_number_in_the_summary_appears_in_results():
    text = knowledge.build().replace(config.RESEARCH_QUESTION, "")
    pool = np.concatenate(
        [
            na.file_numbers(p)
            for p in config.RESULTS.iterdir()
            if p.suffix in {".json", ".csv"} and p.name != "number_audit.json"
        ]
        + [na.config_numbers()]
    )
    untraced = [t for t in na.extract_numbers(text) if not na.matches(t, pool)]
    assert untraced == []


def test_limitations_count_the_iteration_2_set_not_every_listed_country(tmp_path):
    """Regression: iter2_country_set.csv lists all countries with an in_set flag."""
    import json

    import pandas as pd

    pd.DataFrame(
        {
            "country": list("ABCDE"),
            "gdp_endpoints": [True, True, True, True, False],
            "in_set": [True, True, True, False, False],
        }
    ).to_csv(tmp_path / "iter2_country_set.csv", index=False)
    (tmp_path / "iter2_rf_comparison.json").write_text(json.dumps({"n_folds": 5}))
    first = knowledge.limitations(tmp_path)[0]
    assert "4 of 5 countries have the GDP endpoints" in first
    assert "3 are in the iteration 2 set" in first
