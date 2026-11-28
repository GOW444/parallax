# Hand-off: what the team still has to do

**Deadline: Sun Nov 29, 2026, 11:59 pm IST (hard, no late submissions).** The Nov 27 soft
deadline has passed, so do these in order and submit early on Nov 29. **Every member must
attend the viva (week of Nov 30); anyone absent gets 0 for A3.**

The analysis, notebook, tests and audits are finished. What is left is the report, the video
and the submission itself.

## 0. Check the repo is green (2 min)

```bash
pytest -q && ruff check src tests && python -m src.number_audit && python -m src.figure_audit
```

All four must pass. `python -m src.package` lists exactly what is still missing.

## 1. Regenerate the report and slides (5 min) — **do this first**

Results changed after the report and slides were generated (RF v2 gained the plan's
energy-per-GDP feature, so its numbers moved slightly; the workflow diagram lost its
self-loops; new audit files exist). Both files are generated, so just rebuild them:

```bash
python -m src.report && python -m src.export_docx && python -m src.slides
```

Then re-read these places, because they describe things that changed:
- report §3 and Figure 1 (the workflow diagram, now with no self-loops in either panel);
- report §7.5 and slide 14 (RF v2: feature list now includes energy per GDP; numbers
  moved slightly; the conclusion "no gain" is unchanged, see `results/iter2_rf_sensitivity.json`);
- `src/report.py` near line 376 and `report/viva_qa.md`: any sentence that lists the RF v2
  features by hand.

## 2. Names and contributions (10 min)

- Slide 17 and `README.md` still say `TODO(team)`: one line per member (name, roll number,
  modules owned, part spoken in the video). The slide text is in `src/slides.py`.
- `video/script.md` uses speakers A, B and C; replace them with names. Every member speaks.

## 3. Report: A1 appendix, language, rubric (≈1 h)

1. Open `report/A3_report.docx` in Word and read it once through for language and grammar
   (STEPS 178). Check each figure has a number, a caption and a "why this chart" sentence.
2. Check it against `CLAUDE.md` section 5 (STEPS 179). `results/submission_checklist.md`
   records which items are already verified on the current draft.
3. Export to PDF from Word, then append `DAS732_A1_Report.pdf` as **Appendix A** and save the
   result as `report/A3_report.pdf` (the A1 report is required but not assessed).

## 4. Video (6–8 min) (≈1.5 h)

- Record following `video/script.md`, with `video/A3_slides.pptx` on screen. The numbers are
  on the slides: read them, do not improvise new ones.
- Demo cells for the viva are listed at the bottom of the script (leakage guard, pre-2019
  guard, `pytest -q`).
- Save the recording in `video/` (`.mp4`); `src/package.py` looks for it there.

## 5. Package and submit

```bash
python -m src.package     # must exit 0; builds submission/ and submission.zip
```

Submit before the deadline, and keep the zip.

## 6. Viva prep: what to be ready to explain

`report/viva_qa.md` has the questions. Besides those, these decisions are documented but
easy to be caught out on:
- **RF v2 has 162 countries, RF v1 has 165.** Both are scored on the same 162 so the
  comparison is fair (`results/rf_comparison.csv`).
- **Archetypes are clustered on path features and the CLR mix only**, not on income level or
  producer history, "so the archetypes describe change, not size" (`config.py`). The plan's
  §6.3 example names ("Fossil producers", "Low-energy developing") would need those features,
  so the rule-based names differ from the plan's examples. This was a deliberate choice.
- **The archetypes are weakly separated** (silhouette below the iteration 1 clusters) but
  stable across seeds. The report says so. Do not call them "natural types".
- **Qatar's GDP growth looks implausible** in this dataset; it cannot be checked without
  external data, so it is never used as an example.
- **Five folds are too few** to test RF v1 against v2 formally; the report calls the
  comparison descriptive.
- **Producers are not significantly dirtier** (contradicts the plan's expectation) and
  **trend methods do not all beat the naive forecast**: results in
  `results/iter2_hypothesis_check.csv`.

## Not done by the agent (needs a person)

Video recording, names and contributions, language pass of report and slides, the A1
appendix merge, Word's PDF export, and the submission itself. Nothing was committed or
pushed: review `git status` and commit when you are satisfied.
