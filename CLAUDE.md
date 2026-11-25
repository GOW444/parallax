# DAS732 A3 — Rules (derived from DAS732_T1-26-27_A3.pdf)

## Execution mode (user instruction): chunked, never all at once
- Execute **`STEPS.md`** (200 steps) strictly one step at a time, in order, and tick each one.
- **Every 10th step is a REVIEW.** Follow the protocol in STEPS.md:
  - clean notebook run, pytest, ruff;
  - figure, data and number audits;
  - gap check against A3_PLAN.md and this file;
  - an entry in `results/review_log.md`.
- **After each review, STOP and wait for the user to say "next".** Never start the next chunk
  on your own.
- Follow the STEPS.md code standards:
  - constants in `src/config.py`;
  - logic in `src/`, with the notebook only orchestrating;
  - every figure through `plots.save_figure()`;
  - every number read from `results/`.

## 0. Order of authority
1. **`DAS732_T1-26-27_A3.pdf`** (the official brief). It wins every conflict.
2. **`PROMPT.md`** working rules.
3. **`A3_PLAN.md`** execution plan (dataset facts, filenames, methods).

If the plan conflicts with the PDF, or is impossible for the actual data, **stop and tell the
user**. Never silently deviate. Work one phase at a time and wait for the user to say "next".

### User decision (overrides A3_PLAN.md and PROMPT.md)
- **Use only `World Energy Consumption.csv`.** No external or supplementary data, so there is
  **no** World Bank `wb_class.csv`. Do not download or ask for it.
- Where the plan uses "income group", derive **income tiers from the dataset itself**: GDP per
  capita = `gdp / population`, split into quantile tiers on the 2000–2002 baseline. Document
  the thresholds.
- Where the plan uses "region", either use these income tiers or leave region out. Do not add
  a country-to-region mapping.
- In the report, state that no supplementary data was used and why (the rubric says
  "supplementary data, **if any**").

---

## 1. MUST DO: hard requirements from the PDF

### Tasks
- **R1. Three kinds of analysis are all required** (PDF task 1):
  - (a) **statistical analysis**
  - (b) **classical data mining / unsupervised ML** (e.g. clustering)
  - (c) **supervised ML** (e.g. classification, regression, forecasting)

  Each one must appear explicitly and be labelled as such in the report.
- **R2. The workflow must combine visualization AND data analysis** (task 2a). Visualizations
  alone, or models alone, do not satisfy it. Every model output needs a visualization of it.
- **R3. Show a clear feedback loop that causes a *significant* data transformation or
  re-modelling** (task 2b). Cosmetic changes such as recolouring, filtering one row or
  changing a chart type do **not** count. The data's shape, scale or unit of analysis must
  change.
- **R4. An inference made on the data must cause the transformation** (task 2.a). Every
  transformation must be traced to a named inference (I1-x → transformation), with evidence.
- **R5. Run a second iteration of the Keim et al. diamond workflow** (Data → Visualization ⇄
  Models → Knowledge) on the transformed data.
- **R6. Iteration 2 MUST include visualization.** Models are optional there, but the plan
  includes them and they add value.
- **R7. Any mix of tools is allowed** (task 3). A single script or notebook for the whole
  workflow is optional but preferred here, for reproducibility.

### Deliverables
- **D1. Report.**
- **D2. Images folder** (`images/`) containing every figure used.
- **D3. Video demo of the data stories.** Using PowerPoint slides inside the video "will be
  appreciated", so make a real `.pptx` deck, not just an outline.
- **D4. The report must refer to the A1 visual exploration** of the core dataset.
- **D5. Add the A1 report as an appendix.** It is not assessed, but it must be present.
- **D6. Include a workflow diagram in the report** showing the sequence of modules mapped to
  the diamond's Data / Visualization / Models / Knowledge stages.
  - It must be **"unrolled"**: Iteration 1 and Iteration 2 drawn as separate stages, not a
    loop drawn back onto itself.
  - The edge between them carries the exact label **"Feedback loop"**.
  - Keep **self-loops to a minimum**: no arrows from a node back to itself, and as few
    back-edges as possible.

### Rubric items that the deliverables must cover explicitly
- **Workflow description**, plus a **rationale for each visualization** (why this chart type),
  plus a note on supplementary data. None is used, so say so and explain why.
- **Mining/analysis methods**, described.
- **Correct inferences, given the inherent nature of the data in time and space.** In practice:
  - respect year coverage (GDP ends 2018, mix columns cover 2000–2021, 2022 is partial);
  - no causal claims from correlations;
  - respect geography (aggregates vs countries, small states, regions).
- **Data handling beyond A1.** Pre-processing and post-processing must go further than A1,
  with each step justified.
- **Dataset-appropriate statistics and models.** Examples: time-based splits for time series,
  CLR for compositional shares, log transforms for skewed data, and a check for leakage.
- **Quality of inferences.** Show non-trivial reasoning chains backed by visualizations.
- **Report quality.** Formatting, figure layout, numbered captions, **correct references**,
  language and grammar.
- **Video quality.** Slides, clear story, steady pacing.

---

## 2. MUST NOT

- **Do not use the IEEE VAST 2026 Challenge as a substitute for these tasks.** Its resources
  may only help in framing the tasks.
- **Do not end iteration 2 without visualization.**
- **Do not let a feedback loop's transformation be trivial or untriggered.** Each one must be
  significant and come from an inference.
- **Do not draw the workflow diagram as a single loop.** It must be unrolled, the
  "Feedback loop" label must not be missing, and self-loops should be few.
- **Do not state an inference that is not backed by an actual output** (a figure plus a
  number). The hypotheses in A3_PLAN.md are guesses until the data confirms them.
- **Do not leak data.**
  - No electricity-mix shares as features for `carbon_intensity_elec`.
  - No random splits for forecasting: train 2000–2018, test 2019–2021.
  - Fit scalers and transforms only on the data they are meant for.
- **Do not double count.** Drop OWID aggregate entities such as World, regions, income groups
  and "(EI)/(EIA)/(Ember)/(Shift)".
- **Do not interpolate across countries.** Interpolate only within a country, along time.
- **Do not hand-type numbers into the report.** Read them from `results/`.
- **Do not cite references that were not actually used, or cite them inaccurately.**
- **Do not install packages outside `requirements.txt`** without telling the user.
- **Do not miss the deadline.** It is hard, with no late submissions.

---

## 3. Logistics (from the PDF)
- **Submission:** 11:59 pm IST, **Sun Nov 29, 2026**. This is a **hard** deadline. Treat
  ~Nov 27 as the soft deadline.
- **Viva and demo:** in person, week of **Nov 30, 2026**. The submitted video may be played there.
- **Every team member must attend.** Anyone absent gets **0** for A3. Marks are **individual**,
  based on each person's contribution and viva performance. Every member must be able to
  explain every module, so keep the code readable and commented with the WHY.
- **Weight:** 20% of the final grade.
  - Viva: 10 marks.
  - Deliverables: 10 marks.

  Assessment is mainly the demo and viva. Deliverables are a secondary reference.

---

## 4. Working conventions (from PROMPT.md and A3_PLAN.md)

**Notebook and code**
- One notebook: `notebooks/A3_workflow.ipynb`, with one section per phase.
- Helper code goes in `src/`.
- Use `random_state=42` everywhere.

**Figures**
- Save every figure to `images/` under the plan's exact filename.
- Each figure needs:
  - 150+ dpi;
  - a title;
  - axis labels with units;
  - a colour-blind-safe palette;
  - the note "Data: Our World in Data".
- Log every figure in `results/figures.csv`.

**Inferences**
- Log every inference in `results/inferences.md` with:
  - its ID;
  - the statement;
  - the evidence (figure + number);
  - whether it triggers the feedback loop.

**After each phase**
1. Execute the notebook end to end.
2. Check the phase's "done when" criteria.
3. Give a short phase report.
4. Stop and wait for the user to say "next".

---

## 5. Pre-submission checklist
- [ ] Statistics, unsupervised and supervised methods are each present and labelled
- [ ] Iteration 1 inferences → transformation table (inference → transformation) is in the report
- [ ] The transformation is significant (unit of analysis/scale changed), with before/after visuals
- [ ] Iteration 2 has visualizations
- [ ] Unrolled workflow diagram has Data/Viz/Model/Knowledge colours, an edge labelled exactly "Feedback loop", and minimal self-loops
- [ ] Each figure has a number, a caption and a "why this chart" sentence
- [ ] The report states that no supplementary data was used, and income tiers are derived from the dataset with documented thresholds
- [ ] The report refers to the A1 exploration, and the **A1 report is attached as an appendix**
- [ ] References are complete and correct (Keim et al. 2008, OWID, Aitchison 1986, libraries)
- [ ] `images/` folder is complete
- [ ] Video is done, uses PowerPoint slides, and gives each member a speaking part
- [ ] Viva Q&A is prepared and every member can explain every module
- [ ] Submitted before Nov 29, 11:59 pm IST, ideally by Nov 27
