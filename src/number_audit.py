"""Number audit (STEPS 151): every number in an inference must trace to a value in results/.

Why: the brief and CLAUDE.md forbid hand-typed numbers and unsupported inferences. The
statements are built from f-strings over saved metrics, so a stale or typed number would
silently survive a re-run. This module re-reads each statement, extracts every number and
looks for it (to the precision it is printed at) in the results files the inference cites.

Each number ends up in exactly one class:
- ``cited``: found in a results file named in the inference's evidence line;
- ``uncited``: found in another results file (the evidence line is incomplete: a warning);
- ``config``: a design constant from ``config.py`` (a year, k, a threshold);
- ``threshold``: a significance threshold written as ``p < 0.05`` etc.;
- ``derived``: a documented arithmetic transform of saved values (see ``DERIVED``);
- ``untraced``: none of the above. The audit fails if there are any.

Limit: whole numbers match loosely (any value within +-0.5), so the audit is strongest for
decimals, where a stale or mistyped value cannot match by coincidence.
"""

import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path

import numpy as np
import pandas as pd

from src import config

_ID = re.compile(r"\bI[12]-\d\b")  # inference IDs such as I2-5
_YEAR_RANGE = re.compile(r"\b(?:19|20)\d{2}[-–](?:\d{2}|\d{4})\b")  # 2000-02, 2016-2018
_NUMBER = re.compile(r"(?<![\w.])[-−+]?\d+(?:\.\d+)?")
_EVIDENCE_FILE = re.compile(r"results/([A-Za-z0-9_]+\.(?:json|csv))")
_THRESHOLDS = {"0.05", "0.01", "0.001"}
# Saved CSVs are rounded to 3-4 decimals, so a value printed at more precision than the file
# keeps can differ by that rounding.
_FILE_ROUNDING = 5e-4
_MAX_GROUPS = 12  # a text column with more levels is an identifier, not a grouping


class Sources:
    """Read access for derivation rules: results/*.json and any csv under the repo root."""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def json(self, name: str) -> dict:
        return json.loads((self.results_dir / f"{name}.json").read_text(encoding="utf-8"))

    def csv(self, relative_path: str) -> pd.DataFrame:
        return pd.read_csv(self.results_dir.parent / relative_path)


def _worst_residual_populations_m(src: Sources) -> np.ndarray:
    """Population (millions) of the countries with the largest raw-OLS residuals (I1-1)."""
    worst = src.csv("results/iter1_ols_residuals.csv").head(config.N_OLS_NAMED)
    pop = src.csv("data/processed/snapshot_2018.csv")[["country", "population"]]
    return worst.merge(pop, on="country")["population"].to_numpy(dtype=float) / 1e6


# (inference id, printed token) -> function of the saved files that must reproduce it.
# Add an entry only for a documented derivation, never to silence the audit.
DERIVED: dict[tuple[str, str], Callable[[Sources], float | np.ndarray]] = {
    # "a country with 10% higher GDP per person uses about 12% more energy per person"
    ("I2-2", "12"): lambda s: 100 * (1.1 ** s.json("iter2_loglog")["slope"] - 1),
    # "95% CI": the confidence level is 1 - alpha
    ("I2-2", "95"): lambda s: 100 * (1 - config.ALPHA),
    # "every row sums to 100 (within +-0.004)": largest deviation of the saved min/max sum
    ("I1-2", "0.004"): lambda s: max(
        abs(s.json("iter1_composition_checks")["row_sum_min"] - 100),
        abs(s.json("iter1_composition_checks")["row_sum_max"] - 100),
    ),
    # "Iceland (0.4 M people) ... Singapore (5.8 M people)": population / 1e6 from the snapshot
    ("I1-1", "0.4"): _worst_residual_populations_m,
    ("I1-1", "5.8"): _worst_residual_populations_m,
}
# Scenario or wording constants that are inputs, not results (documented, one line each).
SCENARIOS: dict[tuple[str, str], str] = {
    ("I2-2", "10"): "hypothetical +10% GDP-per-person scenario used to read the elasticity",
}


def extract_numbers(statement: str) -> list[str]:
    """Numbers as printed in a statement, without inference IDs and year ranges."""
    text = _YEAR_RANGE.sub(" ", _ID.sub(" ", statement))
    return [m.group(0).replace("−", "-") for m in _NUMBER.finditer(text)]


def _decimals(token: str) -> int:
    return len(token.split(".")[1]) if "." in token else 0


def matches(token: str, values: np.ndarray) -> bool:
    """True if some value equals the token at the precision it is printed at.

    A value counts if it matches as printed, as a fraction shown in percent (x100), or in
    absolute value (statements often drop the sign of a gap while writing "lower by").
    """
    if values.size == 0:
        return False
    x = float(token)
    tol = 0.5 * 10 ** -_decimals(token) + _FILE_ROUNDING
    for scale in (1.0, 100.0):
        scaled = values * scale
        if np.any(np.abs(scaled - x) <= tol) or np.any(np.abs(np.abs(scaled) - abs(x)) <= tol):
            return True
    return False


def _flatten(obj) -> Iterable[float]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten(v)
    elif isinstance(obj, list | tuple):
        for v in obj:
            yield from _flatten(v)
    elif isinstance(obj, int | float) and not isinstance(obj, bool):
        yield float(obj)


def _aggregates(frame: pd.DataFrame) -> list[float]:
    """Simple summaries of a table that a statement may quote: whole-column and per-group
    mean, median, min, max, sum and size. Group columns are text columns with few levels."""
    numeric = frame.select_dtypes("number")
    out: list[float] = [float(len(frame))]
    for col in numeric:
        series = numeric[col].dropna()
        if len(series):
            out += [series.mean(), series.median(), series.min(), series.max(), series.sum()]
    for key in frame.select_dtypes(exclude="number"):
        if 1 < frame[key].nunique() <= _MAX_GROUPS:
            grouped = numeric.groupby(frame[key])
            for agg in (grouped.mean(), grouped.median(), grouped.sum()):
                out += agg.to_numpy(dtype=float).ravel().tolist()
            out += grouped.size().to_numpy(dtype=float).tolist()
    return out


def file_numbers(path: Path) -> np.ndarray:
    """Every numeric value stored in a results JSON or CSV file (plus CSV aggregates)."""
    if path.suffix == ".json":
        values = list(_flatten(json.loads(path.read_text(encoding="utf-8"))))
    else:
        frame = pd.read_csv(path)
        values = frame.select_dtypes("number").to_numpy(dtype=float).ravel().tolist()
        values += _aggregates(frame)
    arr = np.asarray(values, dtype=float)
    return arr[np.isfinite(arr)]


def config_numbers() -> np.ndarray:
    """Numeric design constants in config.py (years, k ranges, alpha, ...)."""
    values: list[float] = []
    for name in dir(config):
        if name.isupper():
            values.extend(_flatten(getattr(config, name)))
    return np.asarray(values, dtype=float)


def _is_threshold(statement: str, token: str) -> bool:
    return token in _THRESHOLDS and re.search(rf"[<>]\s*{re.escape(token)}", statement) is not None


def audit_inference(
    inference_id: str, entry: dict, results_dir: Path, all_numbers: dict[str, np.ndarray]
) -> dict:
    """Classify every number in one inference (see module docstring for the classes)."""
    statement = entry["statement"]
    cited_names = _EVIDENCE_FILE.findall(entry.get("evidence", ""))
    cited = (
        np.concatenate([all_numbers[n] for n in cited_names if n in all_numbers])
        if cited_names
        else np.array([])
    )
    uncited_pool = np.concatenate([v for n, v in all_numbers.items() if n not in cited_names])
    cfg = config_numbers()

    sources = Sources(results_dir)

    classes = ("cited", "uncited", "config", "threshold", "derived", "scenario", "untraced")
    out: dict[str, list[str]] = {k: [] for k in classes}
    for token in extract_numbers(statement):
        key = (inference_id, token.lstrip("+-"))
        if _is_threshold(statement, token):
            out["threshold"].append(token)
        elif matches(token, cited):
            out["cited"].append(token)
        elif key in DERIVED and matches(token, np.atleast_1d(DERIVED[key](sources)).astype(float)):
            out["derived"].append(token)
        elif key in SCENARIOS:
            out["scenario"].append(token)
        elif _decimals(token) == 0 and float(token) in cfg:
            out["config"].append(token)
        elif matches(token, uncited_pool):
            # smallest files first: a tiny JSON is far more likely the true source than a
            # big table that matches a one-decimal number by coincidence
            files = sorted(
                (n for n, v in all_numbers.items() if matches(token, v)),
                key=lambda n: len(all_numbers[n]),
            )
            out["uncited"].append(f"{token} <- {', '.join(files[:3])}")
        elif matches(token, cfg):
            out["config"].append(token)
        else:
            out["untraced"].append(token)
    return {"n_numbers": sum(len(v) for v in out.values()), "cited_files": cited_names, **out}


def run(results_dir: Path = config.RESULTS) -> dict:
    """Audit every inference in results/inferences.json and write results/number_audit.json."""
    inferences = json.loads((results_dir / "inferences.json").read_text(encoding="utf-8"))
    all_numbers = {
        p.name: file_numbers(p)
        for p in sorted(results_dir.iterdir())
        if p.suffix in {".json", ".csv"} and p.name not in {"inferences.json", "number_audit.json"}
    }
    report = {
        i: audit_inference(i, e, results_dir, {k: v for k, v in all_numbers.items()})
        for i, e in inferences.items()
    }
    summary = {
        "inferences": len(report),
        "numbers_checked": sum(r["n_numbers"] for r in report.values()),
        "untraced": {i: r["untraced"] for i, r in report.items() if r["untraced"]},
        "needs_evidence_line_update": {i: r["uncited"] for i, r in report.items() if r["uncited"]},
    }
    result = {"summary": summary, "per_inference": report}
    (results_dir / "number_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    summary = run()["summary"]
    print(json.dumps(summary, indent=2))
    raise SystemExit(1 if summary["untraced"] else 0)
