# DAS732 A3: Visual Analytics Workflow on World Energy Consumption

The project is a two-iteration Keim et al. (2008) visual analytics workflow (Data →
Visualization ⇄ Models → Knowledge) on Our World in Data's `World Energy Consumption.csv`.
Iteration 1 analyses a raw 2018 snapshot. Its inferences trigger a feedback loop that
reshapes the data, and iteration 2 repeats the workflow on the transformed data.

No supplementary data is used. Income tiers are derived from the dataset itself: quartiles
of each country's mean GDP per person over 2000–02.

## Plan and rules

| File | What it is |
|---|---|
| `DAS732_T1-26-27_A3.pdf` | The official brief. It wins every conflict. |
| `CLAUDE.md` | Rules derived from the brief (must do / must not), plus the pre-submission checklist |
| `A3_PLAN.md` | Execution plan: dataset facts, methods, file names, inferences |
| `STEPS.md` | **The plan to execute:** 200 steps in 20 chunks; every 10th step is a review |
| `results/review_log.md` | What every review checked, the bugs it fixed, and its open questions |
| `PROMPT.md` | Working rules |

**How the plan is executed:**
- Execute `STEPS.md` one step at a time, in order, and tick each step when its output is
  checked.
- Every 10th step is a REVIEW:
  - clean notebook run;
  - `pytest`;
  - `ruff`;
  - figure, data and number audits;
  - gap check;
  - a review-log entry.
- After each review, stop and agree before starting the next chunk.

**Progress:** steps 1–110 are done (Chunks 1–11: data preparation, iteration 1, the feedback
loop and the first part of iteration 2). Next is Chunk 12, steps 111–120: archetype
clustering.

## Layout

```
data/raw/            World Energy Consumption.csv (the only input)
data/processed/      clean panel, 2018 snapshot, trajectory tables (generated)
notebooks/           A3_workflow.ipynb: orchestrates every phase (no logic inside)
src/                 config.py (every constant), prep, features, stats, models,
                     figures, plots, logbook, hypotheses
tests/               pytest tests for every transform, test and guard
images/              every figure (200 dpi), registered in results/figures.csv
results/             every number (JSON/CSV), inferences.md, review_log.md
report/, video/      deliverables (Chunks 17-19)
```

## Reproduce

Requires Python 3.13. Map export (kaleido) needs Google Chrome installed.

```bash
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebooks/A3_workflow.ipynb
pytest -q
ruff check src tests
```

The notebook regenerates everything in `data/processed/`, `images/` and `results/` from the
raw CSV, with `random_state=42` throughout.

## Code standards

- Constants live in `src/config.py`.
- Logic lives in `src/`; the notebook only orchestrates.
- Every figure goes through `plots.save_figure()` / `save_plotly_figure()`, which enforce
  titles, axis labels, the source note and registration.
- Every number in the inferences and the report is read from `results/`, never typed by
  hand.
- **Leakage guard:**
  - no mix-derived feature may predict grid carbon intensity;
  - forecasts use a time-based split (train 2000–2018, test 2019–2021);
  - the pre-2019 trajectory table raises an error if it is given later years.

## Deadline

Submission: **Sun Nov 29, 2026, 11:59 pm IST** (hard). Target: Nov 27.
