# A3 video script (target 7 min)

Speakers follow the team split in A3_PLAN.md §9:
- **A**: data and feedback loop, plus the forecast.
- **B**: statistics and clustering.
- **C**: supervised models and delivery.

Replace A/B/C with names. Every member speaks. Slide numbers refer to `video/A3_slides.pptx`.
Numbers are on the slides, so read them from there; do not improvise new ones.

| Time | Slide | Speaker | What to say |
|---|---|---|---|
| 0:00–0:20 | 1 Title | C | Who we are; one dataset (OWID World Energy Consumption), two iterations of the visual analytics workflow. |
| 0:20–0:50 | 2 Question | C | The research question. What A1 found (stasis in the mix; income predicts quantity, not cleanliness). A3 adds statistics, two kinds of machine learning and a feedback loop. No supplementary data: income tiers come from the dataset's own GDP. |
| 0:50–1:30 | 3 Workflow | A | Walk the diagram left to right: Data → Visualization ⇄ Models → Knowledge, twice. The one edge between the rows is the *Feedback loop*: four inferences → four transformations. |
| 1:30–2:00 | 4 Skew | B | Raw scales: long right tails; the OLS residual fan (Breusch-Pagan). A few small, energy-intensive economies dominate. Inference I1-1. |
| 2:00–2:30 | 5 Change | B | The global low-carbon share looks flat (Mann-Kendall, Hamed-Rao), but a third of countries moved more than 10 pp, up or down. A snapshot cannot see paths. Inference I1-3. |
| 2:30–3:00 | 6 K-means | B | Weak structure. The clusters mostly re-label the biggest source. Shares sum to 100%, so they are a composition. Inference I1-2. |
| 3:00–3:30 | 7 RF v1 | C | Random Forest for grid carbon intensity. Leakage guard: no mix shares. It barely beats the mean predictor, and its errors follow the hidden mix. Inference I1-4. |
| 3:30–4:10 | 8 Feedback loop | A | Table: log1p, CLR, trajectories, income tiers + history. Why it is significant: the unit of analysis changes from a country-year to a country's path. Two tables; the pre-2019 table raises an error if given later years. |
| 4:10–4:40 | 9 Decoupling | B | Absolute vs relative decoupling; most High-tier countries decoupled absolutely; only the Low tier differs (Kruskal-Wallis, Holm). Caveat: regression to the mean. |
| 4:40–5:00 | 10 Elasticity | B | Log-log slope ≈ 1.2: across countries, energy rises a bit faster than income. This does not contradict decoupling over time: they are different comparisons. |
| 5:00–5:40 | 11–12 Archetypes | B | Five archetypes from trajectories + CLR. Coal grids are rising fastest; one hydro group is falling. Stable across seeds, but weakly separated: a partition of a continuum. Show the map. |
| 5:40–6:00 | 13 Producers | A | The hypothesis that producers are stuck with dirty grids is not supported (p ≈ 0.44). Norway and Canada are counter-examples. |
| 6:00–6:30 | 14 RF v2 | C | Same countries, same folds. The history features did not help: the change is within fold noise. What sets carbon intensity is the mix, which is banned as a feature. An honest negative result. |
| 6:30–6:50 | 15 Forecast | A | Trained to 2018, tested on 2019–21; compared with the naive last value; what 2020 did. |
| 6:50–7:20 | 16–17 Takeaways, team | C | Three answers to the question, the limitations, and the team. |

## Live demo (viva)

- Open `notebooks/A3_workflow.ipynb` and show one `plots.save_figure` call.
- Show the leakage guard raising an error: `models.assert_no_leakage(["coal_share_elec"])`.
- Show the pre-2019 guard: `features.trajectories_pre2019` on the full panel raises a ValueError.
- Run `pytest -q`.
