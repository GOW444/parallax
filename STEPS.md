# A3: 200-step execution plan

This is the step-by-step version of A3_PLAN.md. The rules come from CLAUDE.md, and the PDF
wins any conflict.

## How this file is used
- **One step at a time, in order.** Each step makes one small, checkable change. Tick `[x]`
  when its output exists and has been checked.
- **Every 10th step is a REVIEW** (protocol below). Nothing from the next chunk starts until
  the review is logged and the user replies **"next"**.
- If a step turns out to be wrong for the actual data, **stop and tell the user**. Do not
  improvise. Plan changes are recorded in A3_PLAN.md and in the review log.
- The target dates keep the CLAUDE.md soft deadline (**submit Nov 27**).

## Code standards (apply to every step)
1. **Constants live only in `src/config.py`**: paths, years, ε, seed, thresholds, column lists,
   colour maps. There are no magic numbers in the notebook or in plotting code.
2. **Logic lives in `src/` modules**: `prep.py`, `features.py`, `stats.py`, `models.py`,
   `plots.py`, `logbook.py`, `workflow_diagram.py`, `report.py`, `slides.py`.
   - Functions are short, with type hints and a docstring that says **why**.
   - No hidden global state.
3. **The notebook only orchestrates**: markdown explains the decision, the code cell calls
   `src`, and key numbers are printed. Prose contains no hard-coded numbers.
4. **Every number shown anywhere is read from `results/`** (JSON/CSV) and never typed by hand.
5. **Every figure goes through `plots.save_figure()`**, which enforces:
   - dpi 200;
   - a title;
   - axis labels with units;
   - the "Data: Our World in Data" note;
   - an upsert of a row in `results/figures.csv` (filename, phase, what it shows, why this
     chart type, inference ID).
6. **Palettes:**
   - categorical: Okabe-Ito;
   - sequential: cividis or viridis;
   - diverging: RdBu_r centred at 0.
   - Fixed colours per energy source, archetype and income tier are set once in `config.py`
     and reused in every figure.
7. **Tests:** every transform gets a `pytest` test on a toy frame (CLR, CAGR, interpolation,
   leakage guard, Mann-Kendall).
8. **Lint:** `ruff check src tests` and `ruff format` stay clean. `random_state=42` everywhere.

## REVIEW protocol (steps 10, 20, …, 200)
1. **Restart and run the notebook end to end:**
   `jupyter nbconvert --to notebook --execute --inplace notebooks/A3_workflow.ipynb`.
   There must be no errors, and warnings must be fixed or explained.
2. **`pytest -q` passes** and **`ruff check src tests`** is clean.
3. **Outputs vs plan:** every file the chunk promised exists, with the exact name from A3_PLAN.md.
4. **Figure audit:** open every new PNG and check:
   - the title, axis units, and log axes labelled as log;
   - the legend;
   - that labels are readable and do not overlap;
   - the colours are the agreed palette;
   - the source note;
   - its row in figures.csv.
5. **Data audit:**
   - row and country counts match the expected values;
   - no unexpected NaN or inf;
   - no leakage (mix shares, CLR, archetype or post-2018 data in RF or forecast inputs).
6. **Number audit:** every inference cites a figure and a number that matches `results/`.
7. **Gap check against A3_PLAN.md and the PDF requirements in CLAUDE.md.**
8. **Log it:** append an entry to `results/review_log.md` with:
   - the steps done and the files created or changed;
   - bugs found and how each was fixed;
   - gaps against the plan;
   - deviations that need the user's approval;
   - open questions.
9. **Report briefly in chat and STOP.** Wait for "next".

---

## Chunk 1 · Setup (steps 1–10) · Nov 21
- [x] **1.** Create the folders `data/raw`, `data/processed`, `notebooks`, `src`, `tests`,
  `images`, `results`, `report`, `video`.
- [x] **2.** Move `World Energy Consumption.csv` into `data/raw/`. Verify the size is unchanged
  (8,254,280 bytes).
- [x] **3.** Ask the user for approval, then install `plotly`, `kaleido`, `python-docx` and
  `ruff`. Export a test plotly map to PNG to confirm kaleido works (it needs Chrome).
- [x] **4.** Write `requirements.txt` with the installed versions pinned.
- [x] **5.** Write `src/config.py`:
  - paths;
  - `YEAR_START=2000`, `YEAR_END=2021`, `GDP_LAST_YEAR=2018`, `PRODUCER_LAST_FULL_YEAR=2016`;
  - `SMALL_STATE_POP=1e6`, `CLR_EPS=0.1`, `SEED=42`;
  - column lists (core, mix, TWh, producer);
  - colour maps.
- [x] **6.** Write `src/plots.py`:
  - a shared matplotlib style;
  - `add_source_note()`;
  - `save_figure(fig, filename, phase, shows, why, inference_id)`, which saves at dpi 200 and
    upserts the figure's row in `results/figures.csv`.
- [x] **7.** Write `src/logbook.py`:
  - `save_metrics(name, dict)` → `results/<name>.json`;
  - `log_inference(id, statement, evidence, triggers_loop, transformation)`, which upserts
    into `results/inferences.json` and re-renders `results/inferences.md`.
- [x] **8.** Write `tests/test_infra.py`:
  - `save_figure` creates the PNG, and re-running it does not duplicate the CSV row;
  - `log_inference` upserts;
  - the mix list has 8 entries.
- [x] **9.** Create the notebook skeleton `notebooks/A3_workflow.ipynb`:
  - a title cell;
  - a setup cell (path, imports, style);
  - an empty markdown section for each of Phases 1–5.

  Execute it with nbconvert.
- [x] **10. REVIEW #1:** infrastructure works, and tests and lint are green.

## Chunk 2 · Phase 1a: load, filter, missingness (steps 11–20) · Nov 21
- [x] **11.** Write `prep.load_raw()`. Assert 22,012 × 129, years 1900–2022 and 306 entities,
  and print them.
- [x] **12.** Write `prep.drop_aggregates()`, keeping `iso_code.notna()`. Assert 219 countries.
  Write `results/dropped_entities.csv` with a reason column (aggregate / real country without
  an ISO code, i.e. Kosovo).
- [x] **13.** Write `prep.filter_years(2000, 2021)` and log the rows before and after.
- [x] **14.** Write `prep.add_derived()`: `gdp_pc`, and `ghg_pc` in t/person. Add a unit test
  on a toy frame.
- [x] **15.** Build the missingness table (share missing per core and producer column per year)
  → `results/missingness_by_year.csv`.
- [x] **16.** Figure `iter1_missingness_heatmap.png`:
  - cividis colours, years on the x-axis;
  - annotations for the 2017 producer break and the end of GDP after 2018.
- [x] **17.** Write `prep.producer_features()` → `data/processed/producers.csv`, with
  `*_prod_pc_2016` and `*_prod_pc_mean_00_16`.
  - Log how many producers drop out in 2017 (expected: oil 50, gas 46, coal 31).
  - Add a test that no 2017+ producer value is ever used.
- [x] **18.** Write `prep.interpolate_within_country()`: linear, `limit=3`,
  `limit_area="inside"`, grouped by country. Test that it never fills across countries and
  never fills the edges.
- [x] **19.** Apply the interpolation to the intensive, mix and TWh columns (not producer
  columns). Log the cells filled per column → `results/interpolation_log.csv`.
- [x] **20. REVIEW #2**

## Chunk 3 · Phase 1b: coverage, checks, save (steps 21–30) · Nov 21
- [x] **21.** Coverage rule: drop countries missing more than 30% of the core electricity cells
  → `results/dropped_low_coverage.csv`, and log the count.
- [x] **22.** Sanity checks: the distribution of mix sums, negatives, duplicates.
  - Re-normalise rows whose interpolated mix sum is off by more than 0.5 pp, and log the count.
  - → `results/sanity_checks.json`
- [x] **23.** Balanced panel: countries with generation and all 8 shares in every year
  2000–2021 → `data/processed/balanced_countries.csv`. Log n.
- [x] **24.** Extract the World row (TWh by source, 2000–2021) for validation only
  → `data/processed/world_check.csv`.
- [x] **25.** Save `data/processed/panel_clean.csv` plus `results/data_dictionary.csv`
  (column, unit, source, raw/derived).
- [x] **26.** Save `data/processed/snapshot_2018.csv` (2018 rows joined with the 2016 producer
  features). Log n per feature set (K-means set ≈ 200, RF set ≈ 165).
- [x] **27.** Notebook Phase 1 section:
  - a "why" markdown cell for each decision;
  - a step-by-step count table → `results/phase1_summary.csv`.
- [x] **28.** Tests for `drop_aggregates`, `filter_years`, the coverage rule and the sanity
  checks. Run pytest.
- [x] **29.** Generate `results/data_notes.md` from the counts: the producer break, Kosovo,
  GDP ending in 2018, 2022 dropped.
- [x] **30. REVIEW #3:** Phase 1 "done when" checked, phase report given.

## Chunk 4 · Phase 2a: iteration 1 visuals (steps 31–40) · Nov 22
- [x] **31.** Write `features.global_mix_twh()` over the balanced panel → `results/global_mix_twh.csv`.
- [x] **32.** Cross-check against the World row (balanced-panel share of world generation per
  year) → `results/global_mix_check.csv`.
- [x] **33.** Figure `iter1_global_mix_area.png`: stacked area, fixed source order
  (fossil → low-carbon), source colours from the config map, legend outside the plot.
- [x] **34.** Figure `iter1_distributions.png`: 2×2 histograms with skewness annotated
  → `results/iter1_skew.json`.
- [x] **35.** Figure `iter1_gdp_vs_energy_linear.png`:
  - bubble area proportional to population, with a size legend;
  - the top-10 energy users labelled without overlap.
- [x] **36.** Pearson and Spearman correlation matrices on the 2018 snapshot
  → `results/iter1_corr_pearson.csv`, `results/iter1_corr_spearman.csv`.
- [x] **37.** Figure `iter1_corr_pearson_vs_spearman.png`: two heatmaps, a shared −1..1 scale,
  values annotated, one colourbar.
- [x] **38.** Write `plots.choropleth()` (plotly with ISO3 codes, unit in the legend title,
  missing data in grey with a "no data" key, title + source note, kaleido export). Test it on
  dummy data.
- [x] **39.** Figure `iter1_lowcarbon_choropleth_2018.png` on a fixed 0–100% scale.
- [x] **40. REVIEW #4**

## Chunk 5 · Phase 2b: change evidence + statistics (steps 41–50) · Nov 22
- [x] **41.** Per-country change in low-carbon share (2016–18 mean minus 2000–02 mean) and
  ranks → `results/iter1_change.csv`. Compute the rank Spearman ρ.
- [x] **42.** Figure `iter1_change_2000_2018.png`:
  - (a) histogram with a 0 line, the median and the IQR;
  - (b) 2000-rank vs 2018-rank scatter with a diagonal, ρ, and the top movers labelled.
- [x] **43.** Write `stats.mann_kendall(series)` (original + Hamed–Rao variance correction) and
  `stats.sen_slope()` (scipy `theilslopes`).
- [x] **44.** Mann-Kendall tests:
  - a monotone series gives p < 0.05;
  - a constant series is handled;
  - the AR(1) noise false-positive rate is lower with Hamed–Rao.
- [x] **45.** Global low-carbon share over the balanced panel → `results/global_lowcarbon_share.csv`.
  Run the Mann-Kendall test + Sen's slope → `results/iter1_mk_global.json`.
- [x] **46.** Pearson and Spearman, with p-values, for gdp_pc vs energy_pc in 2018
  → `results/iter1_correlation_test.json`.
- [x] **47.** Raw OLS energy_pc ~ gdp_pc: coefficient, R², Breusch-Pagan → `results/iter1_ols.json`.
- [x] **48.** Figure `iter1_ols_residuals.png`: residuals vs fitted, 0 line, LOWESS trend,
  Breusch-Pagan p annotated.
- [x] **49.** Log inference **I1-1** (skew values, Breusch-Pagan p, named outliers).
- [x] **50. REVIEW #5**

## Chunk 6 · Phase 2c: K-means baseline (steps 51–60) · Nov 22
- [x] **51.** Iteration 1 feature matrix: 8 shares + 3 intensive columns (2018, complete rows),
  StandardScaler. Save the country list and log n.
- [x] **52.** K-means for k = 2..8 (n_init=20, rs=42): inertia + silhouette
  → `results/iter1_kmeans_k.csv`.
- [x] **53.** Figure `iter1_kmeans_k_selection.png`: elbow + silhouette panels, chosen k marked.
- [x] **54.** Choose k by a documented rule. Fit, and save sizes + centroids in original units
  → `results/iter1_clusters.csv`.
- [x] **55.** PCA (2 components): explained variance + loadings → `results/iter1_pca.json`.
- [x] **56.** Figure `iter1_kmeans_pca.png`: points coloured by cluster, labelled loading
  arrows, % variance in the axis labels, outliers named.
- [x] **57.** Figure `iter1_kmeans_map.png` (categorical choropleth).
- [x] **58.** Write `features.iter2_country_set()` (2000–02 GDP baseline + complete data).
  Compute the iteration 1 silhouette on that set → `results/iter1_silhouette_common.json`.
- [x] **59.** Log inference **I1-2** (cluster sizes, the smallest cluster's members,
  silhouette, PC1 drivers).
- [x] **60. REVIEW #6**

## Chunk 7 · Phase 2d: Random Forest baseline (steps 61–70) · Nov 23
- [x] **61.** RF table: 2018 gdp_pc, energy_pc, per-capita electricity, population + 2016
  producer features; target = carbon intensity. Save the countries → `results/rf_countries.csv`.
- [x] **62.** Write `models.assert_no_leakage(cols)`. It bans the mix shares, `clr_`,
  `low_carbon`, `carbon_int`, `d_coal`, `d_solarwind`, `lowcarbon_` and `archetype`. Add a
  unit test.
- [x] **63.** KFold(5, shuffle, rs=42) fold assignments → `results/rf_folds.csv`.
- [x] **64.** Cross-validated RF (500 trees, rs=42):
  - R², MAE, RMSE per fold, mean ± sd, plus a mean-predictor baseline
    → `results/iter1_rf_metrics.json`;
  - out-of-fold predictions → `results/iter1_rf_oof.csv`.
- [x] **65.** Figure `iter1_rf_pred_vs_actual.png`: out-of-fold predictions vs actual, 1:1
  line, metrics box, worst 8 labelled.
- [x] **66.** Permutation importance on held-out folds (20 repeats) → `results/iter1_rf_importance.csv`
  and figure `iter1_rf_importance.png` (bars with error bars).
- [x] **67.** Top-15 absolute errors → `results/iter1_rf_errors.csv`, with country, actual,
  predicted and residual. The dominant source is shown for interpretation only and is never
  used as a feature.
- [x] **68.** Figure `iter1_rf_residual_map.png` (diverging colours centred at 0).
- [x] **69.** Log inference **I1-4**: where the errors concentrate, by GDP quartile, country
  size and dominant source, with numbers.
- [x] **70. REVIEW #7**

## Chunk 8 · Phase 2e: iteration 1 wrap-up (steps 71–80) · Nov 23
- [x] **71.** Log inference **I1-3** from the change figure + the global Mann-Kendall result.
- [x] **72.** Compare every I1 inference with the plan's hypothesis. Where the data disagrees,
  rewrite the statement to match the data.
- [x] **73.** Set `triggers_loop` + the target transformation for I1-1 to I1-4.
- [x] **74.** figures.csv audit: every `iter1_*` PNG is registered with a "why"; no orphan PNGs.
- [x] **75.** Notebook Phase 2 narrative, with numbers read from `results/`.
- [x] **76.** Visual consistency pass over all iteration 1 figures side by side: fonts, source
  colours, label style.
- [x] **77.** Run on a clean kernel. Fix pandas/sklearn warnings.
- [x] **78.** `ruff format`, `ruff check` and `pytest`.
- [x] **79.** Check A3_PLAN.md §4 "done when", file by file.
- [x] **80. REVIEW #8:** Phase 2 complete, phase report given.

## Chunk 9 · Phase 3a: transformations (steps 81–90) · Nov 23
- [x] **81.** `features.log_transform()` (log1p). Skew before and after → `results/loop_skew.csv`.
- [x] **82.** Small-state flag (2018 population < 1M) → `results/small_states.csv`.
- [x] **83.** `features.clr()`. Tests:
  - rows sum to 0;
  - invariant to scaling;
  - zeros are handled through ε.
- [x] **84.** CLR of the 2018 mix. ε sensitivity (0.01 / 0.1 / 1) on the silhouette
  → `results/loop_clr_eps.csv`.
- [x] **85.** Income tiers: quartiles of mean gdp_pc over 2000–02 → `results/income_tier_thresholds.csv`
  + counts per tier.
- [x] **86.** `features.endpoint_mean()` and `features.cagr(start, end, years=16)`. Test them
  against known values.
- [x] **87.** Build `data/processed/trajectories.csv` (descriptive, endpoints up to 2021). Log
  n and the excluded countries.
- [x] **88.** Build `data/processed/trajectories_pre2019.csv`. The builder **raises** if the
  input contains any year > 2018. Add a test.
- [x] **89.** Validate both tables: no NaN or inf in model features, plausible ranges
  → `results/trajectories_summary.csv`.
- [x] **90. REVIEW #9**

## Chunk 10 · Phase 3b: loop visuals + documentation (steps 91–100) · Nov 24
- [x] **91.** Figure `loop_before_after_table.png`: unit of analysis, rows, columns, years and
  transforms, before vs after (all values computed).
- [x] **92.** Figure `loop_skew_before_after.png`: 3 variables, raw vs log, skew annotated.
- [x] **93.** Figure `loop_clr_before_after.png`: PCA of raw shares vs CLR for the same
  countries, coloured by dominant source.
- [x] **94.** Inference → transformation table, written to inferences.md and
  `results/loop_transformations.csv`.
- [x] **95.** Notebook Phase 3 narrative.
- [x] **96.** "Significant transformation" evidence: unit of analysis, row count and new
  feature count → `results/loop_summary.json`.
- [x] **97.** Leakage check: the pre-2019 table has no column using data from 2019 or later.
  The descriptive table is marked "not for RF/forecast".
- [x] **98.** Clean run, pytest, ruff.
- [x] **99.** Check A3_PLAN.md §5 "done when".
- [x] **100. REVIEW #10:** Phase 3 complete, phase report given.

## Chunk 11 · Phase 4a: decoupling + elasticity (steps 101–110) · Nov 24
- [x] **101.** Decoupling class per country (absolute / relative / coupled / other) + counts
  per tier → `results/iter2_decoupling_classes.csv`.
- [x] **102.** Figure `iter2_decoupling_quadrant.png`:
  - 45° line and 0 lines;
  - colour = income tier;
  - small states as hollow markers;
  - key countries labelled.
- [x] **103.** Log-log OLS with HC3: elasticity, 95% CI, R², Breusch-Pagan → `results/iter2_loglog.json`.
- [x] **104.** Figure `iter2_loglog_gdp_energy.png`: log axes labelled, fit line + CI band,
  elasticity and R² annotated.
- [x] **105.** Raw vs log OLS comparison (R², Breusch-Pagan p) → `results/iter2_ols_comparison.csv`.
- [x] **106.** Kruskal-Wallis on decoupling by tier + pairwise Mann-Whitney with Holm
  correction → `results/iter2_kw.json`, `results/iter2_pairwise.csv`.
- [x] **107.** Figure `iter2_decoupling_by_tier.png`: box + strip plot, n per tier, KW p.
- [x] **108.** Tier medians of low-carbon share, 2000 vs 2021 → `results/iter2_tier_lowcarbon.csv`.
- [x] **109.** Figure `iter2_slope_lowcarbon_by_income.png`.
- [x] **110. REVIEW #11**

## Chunk 12 · Phase 4b: archetype clustering (steps 111–120) · Nov 24
- [x] **111.** Archetype matrix: descriptive trajectory features + CLR, standardised, without
  small states. The feature list lives in config. Log n.
- [x] **112.** K-means for k = 3..7: silhouette + inertia → `results/iter2_kmeans_k.csv`.
- [x] **113.** GMM (diagonal covariance) for k = 3..7: BIC + silhouette → `results/iter2_gmm_k.csv`.
- [x] **114.** Figure `iter2_k_selection.png`.
- [x] **115.** Choose method and k by a documented rule (silhouette, BIC, every cluster ≥ 5
  countries, interpretability). Fit and save the labels.
- [x] **116.** Assign small states to the nearest centroid using the same scaler. Flag them
  `assigned_post_hoc`.
- [x] **117.** Stability: ARI across 20 seeds → `results/iter2_stability.json`.
- [x] **118.** Figure `iter2_vs_iter1_silhouette.png`, using the same country set.
- [x] **119.** Standardised centroid profiles → `results/iter2_centroids.csv`.
- [ ] **120. REVIEW #12**

## Chunk 13 · Phase 4c: archetype interpretation (steps 121–130) · Nov 25
- [x] **121.** Figure `iter2_archetype_profiles.png`: diverging heatmap, features grouped.
- [x] **122.** Name the archetypes by a documented centroid rule → `results/archetype_names.csv`.
  Check the names against the member countries.
- [x] **123.** Figure `iter2_archetype_map.png`.
- [x] **124.** Median + IQR of low-carbon share per archetype per year → `results/iter2_archetype_series.csv`.
- [x] **125.** Figure `iter2_archetype_small_multiples.png`: shared y-axis, n per archetype
  in the panel titles.
- [x] **126.** Hamed–Rao Mann-Kendall + Sen's slope per archetype → `results/iter2_mk_archetypes.csv`.
- [x] **127.** Producer vs non-producer carbon intensity (Mann-Whitney) → `results/iter2_producers.json`.
  Figure `iter2_producers_carbon.png`.
- [x] **128.** Log inferences **I2-3** and **I2-4**.
- [x] **129.** Log inferences **I2-1** and **I2-2**.
- [ ] **130. REVIEW #13**

## Chunk 14 · Phase 4d: Random Forest v2 (steps 131–140) · Nov 25
- [x] **131.** RF v2 table: iteration 1 features + leak-free pre-2019 history features, on
  the RF countries. If any countries lack trajectory data, use the intersection for **both**
  models and document it.
- [x] **132.** Run `assert_no_leakage` on the v2 features.
- [x] **133.** Cross-validation on the **same folds** → `results/iter2_rf_metrics.json`.
- [x] **134.** If the rows changed, re-score iteration 1 on the same rows
  → `results/rf_comparison.csv`.
- [x] **135.** Fold-by-fold paired differences, with a note on small n (no overclaiming).
- [x] **136.** Figure `iter2_rf_improvement.png`: R² and MAE bars with fold-sd error bars.
- [x] **137.** SHAP TreeExplainer values → `results/iter2_shap_values.csv`.
- [x] **138.** Figure `iter2_shap_summary.png` (beeswarm).
- [x] **139.** Change in the worst errors, v1 vs v2 → `results/iter2_rf_error_change.csv`.
  Log inference **I2-5**.
- [ ] **140. REVIEW #14**

## Chunk 15 · Phase 4e: forecast vs reality (steps 141–150) · Nov 25
- [x] **141.** Re-fit the chosen clustering on the pre-2019 features (same k and method). ARI
  vs the descriptive archetypes → `results/iter2_pre2019_groups.json`.
- [x] **142.** Median low-carbon share per pre-2019 group per year → `results/iter2_group_series.csv`.
- [x] **143.** Holt's linear trend (plain + damped) fitted on 2000–2018.
- [x] **144.** ARIMA(1,1,0), plus the naive last-value baseline.
- [x] **145.** Forecast 2019–2021. MAE and MAPE per group and method → `results/iter2_forecast_metrics.csv`.
- [x] **146.** Guard: assert the training data ends at 2018 and the test years are exactly
  2019–2021.
- [x] **147.** Figure `iter2_forecast_vs_actual.png`: small multiples per group with train,
  forecast + interval band, actual values, and 2020 marked.
- [x] **148.** COVID check: the 2020 change in generation over the balanced panel, and the 2020
  residuals per group → `results/iter2_covid.json`.
- [x] **149.** Log inference **I2-6**.
- [ ] **150. REVIEW #15**

## Chunk 16 · Phase 4f: iteration 2 wrap-up (steps 151–160) · Nov 25
- [ ] **151.** Automated check that every number in inferences.json matches a `results/` value.
- [ ] **152.** Record honestly every hypothesis the data contradicted.
- [ ] **153.** figures.csv audit for the iteration 2 figures.
- [ ] **154.** Visual consistency pass: archetype and tier colours fixed, fonts, labels.
- [ ] **155.** Notebook Phase 4 narrative.
- [ ] **156.** Clean run, fix warnings.
- [ ] **157.** pytest + ruff.
- [ ] **158.** Check A3_PLAN.md §6 "done when".
- [ ] **159.** Generate `results/knowledge_summary.md`: the answer to the research question,
  with numbers.
- [ ] **160. REVIEW #16:** Phase 4 complete, phase report given.

## Chunk 17 · Phase 5a: workflow diagram + report start (steps 161–170) · Nov 25–26
- [x] **161.** `src/workflow_diagram.py`: the nodes (id, label, diamond stage, iteration) are
  defined as data.
- [x] **162.** Draw the iteration 1 row, colour-coded Data / Visualization / Model /
  Knowledge, with a legend.
- [x] **163.** Draw the iteration 2 row, plus one edge labelled exactly **"Feedback loop"**
  listing the transformations. No self-loops, and arrows never cross text.
- [x] **164.** Save `images/workflow.png` + `report/workflow.png` and register them in figures.csv.
- [ ] **165.** `src/report.py`: builds `report/A3_report.md` from a template. Numbers are
  inserted from `results/`, and figures are numbered automatically.
- [ ] **166.** Report §1–2: introduction, research question, dataset, reference to A1, and
  why no supplementary data was used.
- [ ] **167.** Report §3: the workflow diagram + a rationale table for each module.
- [ ] **168.** Report §4: data handling (including the producer break and Kosovo).
- [ ] **169.** Report §5: iteration 1 figures with captions + "why this chart".
- [ ] **170. REVIEW #17**

## Chunk 18 · Phase 5b: report finish (steps 171–180) · Nov 26
- [ ] **171.** Report §6: feedback loop (inference → transformation table, before/after).
- [ ] **172.** Report §7: iteration 2 results.
- [ ] **173.** Report §8: discussion + limitations.
- [ ] **174.** Report §9 conclusion + §10 references (check author, year, title, venue, DOI/URL).
- [ ] **175.** Report §11: A1 report appendix. **Blocked until the team supplies the A1 file.**
- [ ] **176.** Export `report/A3_report.docx` with python-docx: headings, figures at a
  consistent width, captions, tables.
- [ ] **177.** Inspect the docx: figure order and numbering, image sizes, no broken tables.
- [ ] **178.** Language and grammar pass: consistent terms (archetype and tier names), and
  numbers match `results/`.
- [ ] **179.** Check the report against the rubric (CLAUDE.md §5).
- [ ] **180. REVIEW #18**

## Chunk 19 · Phase 5c: slides + video script (steps 181–190) · Nov 26
- [ ] **181.** Slide storyline (12–16 slides) mapped to the script sections → `video/slides_outline.md`.
- [ ] **182.** `src/slides.py` (python-pptx): title, research question, workflow slides.
- [ ] **183.** Iteration 1 slides (the problems found).
- [ ] **184.** Feedback loop slides.
- [ ] **185.** Iteration 2 slides (decoupling, archetypes, RF, forecast).
- [ ] **186.** Takeaways, limitations and team-contribution slides → `video/A3_slides.pptx`.
- [ ] **187.** Programmatic pptx check: every image is inside the slide bounds, no empty
  placeholders, text fits.
- [ ] **188.** `video/script.md`: 6–8 min, timings, speaker per section (every member speaks).
- [ ] **189.** `video/recording_checklist.md`: settings, which notebook cells to demo live,
  the order of the slides. The team records the video.
- [ ] **190. REVIEW #19**

## Chunk 20 · Final checks (steps 191–200) · Nov 27
- [ ] **191.** `report/viva_qa.md`: answers grounded in `results/` numbers.
- [ ] **192.** Images folder audit: every image is used in the report and every figure exists,
  with names matching the plan.
- [ ] **193.** Reproducibility: delete `data/processed`, `results` and `images`, re-run
  everything, and confirm the key metrics are identical.
- [ ] **194.** Final pytest + ruff + clean notebook run.
- [ ] **195.** `README.md`: how to run, folder map, who did what.
- [ ] **196.** Tick off the CLAUDE.md §5 checklist, with evidence for each item.
- [ ] **197.** Build the submission package (report docx, images/, notebook, src/, video
  slides) → `submission/` + a zip.
- [ ] **198.** Final typo pass over the report and slides.
- [ ] **199.** Hand-off list for the team: record the video, check the A1 appendix, submit by
  Nov 27, everyone attends the viva.
- [ ] **200. FINAL REVIEW #20:** the full PDF requirement check, then a summary for the user.
