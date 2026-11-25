# Prompt to paste into Claude Code (run from inside the A3/ folder)

```text
# ROLE
You are a data scientist helping my team complete DAS732 Assignment 3 (Visual Analytics
Workflow, Keim et al. diamond model) on the OWID "World Energy Consumption" dataset.

# SOURCE OF TRUTH
Read @A3_PLAN.md fully before doing anything. Follow it phase by phase. It defines the
research question, the data facts, the folder layout, every figure filename, the methods
and the "done when" criteria. If something in the plan is impossible or wrong for the
actual data, stop and tell me; don't silently change it.

# INPUTS
- Dataset: data/raw/World Energy Consumption.csv (the ONLY data source).
- No supplementary/external data. Income tiers are derived from the dataset's own GDP per
  capita (see A3_PLAN.md §5 and CLAUDE.md).

# HOW TO WORK
1. Work in ONE notebook: notebooks/A3_workflow.ipynb, with one markdown-headed section per
   phase. Put reusable code in src/ (prep.py, features.py, plots.py) and import it.
2. Do ONE phase at a time, in order: Phase 1 → 2 → 3 → 4 → 5.
3. After each phase:
   - Execute the notebook end-to-end (jupyter nbconvert --execute --inplace) and fix any errors.
   - Check the phase's "done when" criteria from the plan.
   - Print a short phase report in chat: files created, key numbers, inferences written,
     anything that deviated from the plan, open questions.
   - STOP and wait for me to reply "next" before starting the following phase.

# RULES (non-negotiable)
- Evidence first: the "expected findings/hypotheses" in the plan are guesses. Every
  inference must come from the actual outputs, citing a figure filename and a number.
  If the data contradicts a hypothesis, say so and adapt the story.
- No data leakage: never use the electricity mix shares as features for predicting
  carbon_intensity_elec. Forecasts use a time-based split only (train 2000–2018, test 2019–2021).
- Drop OWID aggregate entities; interpolate only within a country along time.
- Fit scalers/transforms only on the data they are meant for; random_state=42 everywhere.
- Every figure: saved to images/ with the exact filename from the plan, 150+ dpi, title,
  labelled axes with units, colour-blind-safe palette, "Data: Our World in Data" note,
  and a row added to results/figures.csv (filename, phase, what it shows, inference ID).
- Every inference: appended to results/inferences.md with ID, statement, evidence and
  whether it triggers the feedback loop.
- Metrics go to results/ as JSON/CSV. Never type numbers into the report by hand; read
  them from results/.
- Keep the code readable for a viva: short functions, comments explaining WHY, no clever
  one-liners. Each team member must be able to explain it.
- Don't install anything outside requirements.txt without telling me; create
  requirements.txt in Phase 1.

# PHASE 5 SPECIFICS
- Generate the unrolled workflow diagram in code (graphviz or matplotlib), colour-coded by
  Data / Visualization / Model / Knowledge, with an edge labelled exactly "Feedback loop".
- Write report/A3_report.md following the plan's section list, embedding the figures with
  numbered captions and a one-line "why this chart" for each. Then also export it to .docx.
- Write video/script.md (6–8 min, timings, speaker per section) and video/slides_outline.md.
- Write report/viva_qa.md with short, accurate answers grounded in our actual results.

# START
Confirm you've read the plan, list the phases in one line each, check that the dataset
exists, then begin Phase 1.
```
