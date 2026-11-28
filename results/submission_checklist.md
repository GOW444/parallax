# Pre-submission checklist (CLAUDE.md section 5), with evidence

Status as of Nov 28, 2026. **Done** = verified on the repository as it is now. **Done on the
draft** = verified on the current `report/A3_report.md`; the report is generated from templates,
so these properties persist when it is regenerated, but re-check after the report pass.
**Open** = needs people. Nothing below was ticked without a check.

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Statistics, unsupervised and supervised methods each present and labelled | Done on the draft | Report headings tagged `[Statistics]` (5.2, 7.1, 7.2, 7.4), `[Unsupervised]` (5.3, 7.3), `[Supervised]` (5.4, 7.5, 7.6); the diagram lanes and slide titles carry the same tags |
| 2 | Inference → transformation table is in the report | Done on the draft | Report section 6 table, rows I1-1 to I1-4 (also `results/loop_transformations.csv`) |
| 3 | Transformation is significant, with before/after visuals | Done | Unit of analysis country-year → country trajectory (`results/loop_summary.json`); `loop_before_after_table.png`, `loop_skew_before_after.png`, `loop_clr_before_after.png` |
| 4 | Iteration 2 has visualizations | Done | 14 `iter2_*` figures, each with a file, a registry row and an inference ID (`results/figure_audit.json`) and each inspected on a contact sheet |
| 5 | Unrolled diagram: stage colours, one edge labelled exactly "Feedback loop", minimal self-loops | Done (image) | `images/workflow.png` inspected: four stage colours, one cross-iteration edge labelled "Feedback loop" listing the four transformations, no self-loop in either panel; `tests/test_workflow_diagram.py` and `tests/test_standards.py`. **The report and slides still embed the previous picture until regenerated** |
| 6 | Each figure has a number, a caption and a "why this chart" sentence | Done on the draft | 32 figure captions and 32 "Why this chart" sentences in the report; `figures.csv` has a non-empty `why_this_chart` for all 32 |
| 7 | Report says no supplementary data was used; income tiers derived from the dataset with documented thresholds | Done on the draft | Report section 2 ("Supplementary data: none") and Table 1; thresholds in `results/income_tier_thresholds.csv` |
| 8 | Report refers to A1 **and the A1 report is attached as an appendix** | **Open** | The report refers to A1 (section 1, 4, Appendix A page), but `DAS732_A1_Report.pdf` is not merged: no `report/A3_report.pdf` exists |
| 9 | References complete and correct | **Open** | 13 entries present (Keim 2008, OWID, Aitchison 1986, Hamed & Rao 1998, Sen 1968, scikit-learn, statsmodels, Kaufman & Rousseeuw, Breiman, Mann, Holm, A1, Lundberg & Lee). Not checked against the sources: do that in the report pass |
| 10 | `images/` is complete | Done | 32 PNGs = 32 registry rows = every filename named in `A3_PLAN.md`; all 32 used in the report; `report/workflow.png` identical to `images/workflow.png` |
| 11 | Video done, uses PowerPoint slides, each member speaks | **Open** | `video/A3_slides.pptx` (17 slides) and `video/script.md` exist; no recording; slide 17 and the script still have placeholders |
| 12 | Viva Q&A prepared and every member can explain every module | **Open** | `report/viva_qa.md` exists; whether each member can explain every module is for the team to check (`HANDOFF.md`, section 6) |
| 13 | Submitted before Nov 29, 11:59 pm IST | **Open** | `python -m src.package` builds the zip and lists what is missing |

## Brief requirements R1–R7 and D1–D6

| Requirement | Status | Where |
|---|---|---|
| R1 three kinds of analysis | Done | See item 1 |
| R2 visualization and analysis combined; every model output visualized | Done | Every model lane in the diagram ends in a visualization (tested) |
| R3, R4 significant transformation caused by a named inference | Done | Items 2 and 3 |
| R5, R6 second iteration with visualization | Done | Item 4 |
| R7 single notebook | Done | `notebooks/A3_workflow.ipynb`, 190 cells, runs end to end |
| D1 report | Draft done, language and rubric pass open | `report/A3_report.docx` |
| D2 images folder | Done | Item 10 |
| D3 video | **Open** | Item 11 |
| D4 refers to A1 | Done on the draft | Item 8 |
| D5 A1 as appendix | **Open** | Item 8 |
| D6 unrolled diagram with the "Feedback loop" label | Done (image); report copy to regenerate | Item 5 |
