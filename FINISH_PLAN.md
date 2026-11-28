# A3 finish plan (written Nov 28, 2026)

Scope: every STEPS.md item **except the report and the video**, plus the plan gaps the audit
found. The hard deadline is **Nov 29, 11:59 pm IST**; the Nov 27 soft deadline has passed, so
the order below puts the cheap, high-value work first and the single long notebook run last.

The user has asked for this batch to run through without the usual stop after each REVIEW.
Each review is still done in full and logged in `results/review_log.md`.

## Deferred (explicitly left for the report and video pass)

| Item | Why deferred |
|---|---|
| 170 (report part), 175, 178, 179, 180 | Report: A1 appendix merge, language pass, rubric check |
| 181, 189, 190, 198 | Video: slide outline, recording checklist, slide typo pass |
| Team names (slide 17, README) | Needs the team |
| Regenerating `A3_report.docx`, `A3_slides.pptx` | Done in the report/video pass: `python -m src.report && python -m src.export_docx && python -m src.slides` |
| 200 (FINAL REVIEW) | Cannot close while the report and video are open |

## Phases

### P0 Baseline
- Durable clone at `~/parallax` (the scratch clone is a temp folder).
- **Baseline re-run** of the untouched notebook (scratch clone) and a diff against the
  committed outputs. This isolates non-reproducibility noise before any change of mine.

### P1 Plan-conformance fixes (found by the audit)
| # | Gap | Action |
|---|---|---|
| 1.1 | Workflow diagram panel (a) draws a self-loop on all four stages; the brief wants minimal self-loops and CLAUDE.md D6 says none | Remove them; test the whole figure, not only the unrolled chain; regenerate `images/workflow.png`; add `report/workflow.png` (step 164) |
| 1.2 | RF v2 omits `log_energy_per_gdp_2018`, which A3_PLAN §6.4 and change #4 require, and nothing documents the omission | **Decision gate.** Run the sensitivity first (v2 with and without it, same rows and folds). Plan wins: add it to the v2 feature set and let the numbers move, unless it makes the model leak (it must pass `assert_no_leakage`). Record both results |
| 1.3 | GMM uses `n_init=5` (magic number, noisy BIC; open since Review #12) | Move to `config.GMM_N_INIT = 20`. **Stop and tell the user** if the chosen method or k changes |
| 1.4 | Standards audit: literal `random_state`/`n_init`/hex colours outside `config.py`; `ruff format` flags one file | Fix and add a test that greps for them |

### P2 Chunk 16, steps 151–160
| Step | Deliverable |
|---|---|
| 151 | `src/number_audit.py` + test: every number in `inferences.json` is traced to a value in its cited `results/` files → `results/number_audit.json`. Untraceable tokens are reviewed by hand, not silently allow-listed |
| 152 | `results/iter2_hypothesis_check.csv`: each iteration 2 hypothesis in the plan vs the data, contradicted ones listed |
| 153 | Automated `figures.csv` audit for `iter2_*` and `loop_*` (file, registry row, why, inference ID, dpi) + contact-sheet inspection of every iteration 2 PNG |
| 154 | Consistency pass: archetype/tier colours come only from `config.py`; fonts and labels |
| 155 | Notebook Phase 4 narrative: consistent numbering, a "why" cell before each code cell, no hand-typed numbers in prose, a Phase 4 summary cell |
| 156–157 | Clean run, warnings fixed, pytest, ruff |
| 158 | A3_PLAN §6 checked line by line → review log |
| 159 | `results/knowledge_summary.md` generated from `results/` (the answer to the research question, with numbers) |
| 160 | REVIEW #16 |

### P3 Retrospective reviews #12–#15 and the diagram part of #17
Full protocol on steps 111–150: files promised vs files present, figure audit, data audit
(leakage guards, same rows and folds, forecast window), number audit (from 151), gap check,
log entry, tick `STEPS.md`. Review #17 covers the diagram part only; its report part waits.

### P4 Chunk 20 (non-report)
| Step | Deliverable |
|---|---|
| 192 | Images audit: plan names ↔ `images/` ↔ `figures.csv` ↔ report usage |
| 193 | **Strict reproducibility:** delete `data/processed`, `results` (keeping the hand-written `review_log.md`) and `images` in a throwaway copy, re-run, and compare every JSON/CSV number and PNG with the working tree |
| 194 | Final pytest, ruff check and format, clean notebook run |
| 195 | README: progress, run instructions, folder map (team table stays a placeholder) |
| 196 | `results/submission_checklist.md`: CLAUDE.md §5 with evidence; only verified items are ticked |
| 197 | `src/package.py` builds `submission/` and a zip, and prints what is still missing (video, merged A1 PDF); rebuilt after the report/video pass |
| 199 | `HANDOFF.md`: ordered to-do list for the team, with the Nov 29 deadline |

### P5 Wrap-up
STEPS.md ticks, review-log entries, one project-memory note. **Nothing is committed or
pushed.** The working tree is left for the user to inspect.

## Execution order (a notebook run is the long pole, so edits come first)

1. P1 code fixes and the sensitivity checks
2. P2 code (151, 152, 153, 154, 159) and the notebook edits (155)
3. **One** normal notebook run in `~/parallax`, then pytest and ruff (156, 157)
4. P2 review items (158, 160), P3 reviews, P4 192, 195, 196, 197, 199
5. **Strict reproducibility run** on a throwaway copy of the final tree (193), then 194
