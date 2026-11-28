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
| `FINISH_PLAN.md` | How the last non-report, non-video steps were planned and run (Nov 28) |
| `HANDOFF.md` | What the team still has to do before submitting |

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

**Progress (Nov 28):**
- **Analysis: complete (steps 1–160).** Data preparation, iteration 1, the feedback loop and all
  of iteration 2: decoupling, elasticity, archetypes, producers, RF v2 with SHAP, and the
  2019–21 forecast. Plan-conformance fixes and audits since Nov 27 are in `FINISH_PLAN.md` and
  `results/review_log.md`:
  - the workflow diagram has no self-loops in either panel;
  - RF v2 now includes the plan's energy-per-GDP feature (sensitivity in
    `results/iter2_rf_sensitivity.json`);
  - `results/number_audit.json`, `results/figure_audit.json`,
    `results/iter2_hypothesis_check.csv` and `results/knowledge_summary.md` are generated.
- **Still open, owned by the team** (ordered list in `HANDOFF.md`):
  - record the video, and fill in names and contributions (marked `TODO(team)`);
  - regenerate the report and slides (results changed), export the report to PDF and append
    `DAS732_A1_Report.pdf` as Appendix A;
  - language pass and rubric check of the report, then `python -m src.package` and submit.

## Layout

```
data/raw/            World Energy Consumption.csv (the only input)
data/processed/      clean panel, 2018 snapshot, trajectory tables (generated)
notebooks/           A3_workflow.ipynb: orchestrates every phase (no logic inside)
src/                 config.py (every constant), prep, features, stats, models,
                     figures, plots, logbook, hypotheses; iteration 2: archetypes,
                     iter2_figures, forecast; Phase 5: workflow_diagram, report,
                     export_docx, slides; audits and delivery: number_audit,
                     figure_audit, knowledge, package
tests/               pytest tests for every transform, test and guard
images/              every figure (200 dpi), registered in results/figures.csv
results/             every number (JSON/CSV), inferences.md, review_log.md
report/              A3_report.md/.docx (generated), viva_qa.md
video/               A3_slides.pptx (generated), script.md
```

## Reproduce

Requires Python 3.13. Map export (kaleido) needs Google Chrome installed.

```bash
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace notebooks/A3_workflow.ipynb
pytest -q
ruff check src tests
python -m src.report        # report/A3_report.md from results/
python -m src.export_docx   # report/A3_report.docx
python -m src.slides        # video/A3_slides.pptx
python -m src.number_audit  # every number in the inferences traces to results/ (exit 1 if not)
python -m src.figure_audit  # every figure: file, registry row, dpi, inference ID
python -m src.package       # submission/ + submission.zip, and a list of what is still missing
```

`FINISH_PLAN.md` documents how the last steps were run, and `HANDOFF.md` lists what the team
still has to do.

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
