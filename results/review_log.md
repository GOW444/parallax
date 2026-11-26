# Review log

One entry per REVIEW step in STEPS.md. Each entry records what changed, the bugs found and
fixed, gaps against the plan, and open questions.

---

## REVIEW #1 · Chunk 1 (steps 1–10, setup) · Nov 21, 2026

**Steps done:** 1–10.

**Files created or changed**
- Folders: `data/raw`, `data/processed`, `notebooks`, `src`, `tests`, `images`, `results`, `report`, `video`.
- `World Energy Consumption.csv` moved to `data/raw/` (8,254,280 bytes, unchanged).
- `requirements.txt` (18 pinned packages) and `pyproject.toml` (ruff + pytest settings).
- `src/__init__.py`, `src/config.py`, `src/plots.py`, `src/logbook.py`.
- `tests/test_infra.py` (11 tests).
- `notebooks/A3_workflow.ipynb` (skeleton: intro, 2 setup cells, 5 phase headers).
- A3_PLAN.md §2: environment line updated to match what is installed.

**Checks**
| Check | Result |
|---|---|
| Notebook clean run (nbconvert --execute) | Pass. Only output is a Windows zmq RuntimeWarning from Jupyter's own messaging layer, not from project code |
| `pytest -q` | 11 passed |
| `ruff check` / `ruff format --check` (src, tests, notebooks) | Clean |
| All 32 configured raw columns exist in the CSV | Pass |
| Tests isolated (nothing written to the real `images/` or `results/`) | Pass |
| Figure, data and number audits | Not applicable yet (no figures or data outputs in this chunk) |

**Bugs found and fixed**
1. **Invalid JSON for NaN** (`logbook.save_metrics`).
   - Cause: `np.float64` subclasses `float`, so `json.dump` wrote the invalid token `NaN`
     and never called the converter.
   - Fix: recursive `_to_jsonable()` turns NaN/inf into `null`, and `allow_nan=False` makes
     any future slip fail loudly.
   - Found by the test `test_save_and_load_metrics_handles_numpy`.
2. **Private matplotlib attribute** `fig._suptitle` was replaced with the public
   `fig.get_suptitle()`.
3. **Ruff E402 in the notebook:** imports came after the `sys.path` setup in the same cell.
   The setup was split into a path cell and an imports cell.
4. **Formatting:** 3 files were reformatted with `ruff format`, and one line > 100 characters
   was fixed.

**Safeguards added beyond the plan**
- `save_figure()` **refuses** to save a figure with no title, any axes without x/y labels,
  a non-bare filename, or an empty "what it shows" / "why this chart". Re-saving never
  duplicates the figures.csv row.
- `log_inference()` **refuses** an inference whose evidence cites no figure or results file,
  or one that triggers the loop without naming a transformation.
- `config.py` asserts the expected raw-file facts (shape, years, entity count) so a wrong
  file fails fast, and a test checks that the CAGR exponent (16) equals the gap between the
  endpoint-window centres.

**Gaps against the plan / notes for later chunks**
- **Kaleido test map was centred on the Pacific (plotly 7 default).** Step 38 must set a
  Natural Earth projection centred on 0° longitude. Recorded so it isn't missed.
- **A1 report found:** `DAS732_A1_Report.pdf` is now in the project root. Step 175 is
  unblocked: copy it into `report/` and attach it as the appendix.
- `pyproject.toml` is an addition not listed in A3_PLAN.md §2. It holds tool settings only.

**Open questions for the user**
- Team size (for the speaker split in the video script, step 188).

---

## REVIEW #2 · Chunk 2 (steps 11–20, Phase 1a: load, filter, missingness) · Nov 21, 2026

**Steps done:** 11–20.

**Files created or changed**
- `src/prep.py`: `load_raw`, `drop_aggregates`, `filter_years`, `add_derived`,
  `missingness_by_year`, `producer_features`, `interpolate_within_country`,
  `classify_missing`, `count_missing`, `interpolation_columns`.
- `src/figures.py` (new): builders for individual report figures, so `plots.py` holds only
  shared infrastructure. A small addition to the plan's module list.
- `tests/test_prep.py`: 8 tests (19 in total).
- Notebook: Phase 1 sections 1.1–1.7 (15 cells, tagged `phase1a`).
- Outputs:
  - `images/iter1_missingness_heatmap.png`;
  - `results/dropped_entities.csv`, `missingness_by_year.csv`, `missing_cell_types.csv`,
    `interpolation_log.csv`, `producers_lost_2017.json`, `figures.csv`;
  - `data/processed/producers.csv`.
- A3_PLAN.md §1: two verified facts added (no internal gaps; non-country ISO entities).
- A3_PLAN.md §9: team split rewritten for **3 members**.

**Key numbers (all read from the outputs)**
| Item | Value |
|---|---|
| Raw file | 22,012 × 129, years 1900–2022, 306 entities (assertions pass) |
| Kept / dropped entities | 219 kept; 87 dropped (86 aggregates + Kosovo) |
| Analysis window | 4,798 rows, 32 core columns, 2000–2021 |
| Producers lost in 2017 (produced in 2016, blank in 2017) | oil 50, gas 46, coal 31 (as profiled) |
| Producer features available | 216 of 219 (missing: Antarctica, Micronesia, Tuvalu) |
| Missing cells in the interpolation columns | 8,075: never reported 6,218 · trailing edge 1,791 · leading edge 66 · **internal 0** |
| Cells filled by interpolation | **0** |

**Checks**
| Check | Result |
|---|---|
| Notebook clean run | Pass (0 errors, 9 code cells) |
| pytest | 19 passed |
| ruff check / format | Clean |
| Figure audit (`iter1_missingness_heatmap.png`) | 2381×1472 px, 200 dpi. Title, axis labels, colourbar unit, source note present. Group labels and break labels do not overlap. Cividis colours. Registered in figures.csv |
| Data audit | `producers.csv`: 219 rows, 0 negatives. Derived `gdp_pc` range 439–166,150 int-$, `ghg_pc` 0–10.6 t/person: plausible |

**Bugs found and fixed**
1. **Overlapping break labels** on the heatmap (the producer and GDP lines are two columns
   apart). The labels now sit on opposite sides of their lines.
2. **Interpolation design flaw avoided:** pandas `interpolate(limit=3)` would *partly* fill
   longer gaps and invent a trend. The custom `_short_gap_mask` fills a gap only when the
   whole gap is ≤ 3 years. A test covers this.
3. **Wording:** "219 countries" became "219 countries and territories". The ISO-coded set
   includes territories (Bermuda, Gibraltar, …) and Antarctica.
4. **Lint:** 4 × B905. `zip()` now uses `strict=True`, so mismatched test data fails loudly.
   `figures.py` reformatted.

**Findings and gaps against the plan**
- **Interpolation fills 0 cells** (plan §3 step 5 expected some filling). The data has no
  internal gaps, so the step works as designed. The notebook (1.6) and the report must say
  that missingness is structural and handled by the coverage rule and windows, not by
  imputation. No approval needed: the plan's rule is followed; the data just has nothing to
  fill.
- **Non-country ISO entities** (Antarctica, Netherlands Antilles, Micronesia, N. Mariana
  Islands, Tuvalu) have no grid data. **Step 21 must confirm the coverage rule removes them.**
- **Pipeline order:** `add_derived` (step 14) runs *after* interpolation in the notebook, so
  per-person columns come from final values. This is a logical order and does not change the
  step content.

**Open questions:** none.

---

## REVIEW #3 · Chunk 3 (steps 21–30, Phase 1b: coverage, checks, save) · Nov 22, 2026

**Steps done:** 21–30. **Phase 1 is complete.**

**Files created or changed**
- `src/config.py`: added `LOW_CARBON_PARTS` and `CORE_ELEC_COLS`.
- `src/prep.py`: added `close_mix_shares`, `apply_coverage_rule`, `sanity_checks`,
  `balanced_countries`, `world_check_rows`, `data_dictionary`.
- `src/logbook.py`: added `write_notes`.
- `tests/test_prep.py`: 12 new tests (31 in total).
- Notebook: Phase 1 sections 1.8–1.15 (17 cells, tagged `phase1b`).
- Outputs:
  - `data/processed/panel_clean.csv`, `snapshot_2018.csv`, `balanced_countries.csv`,
    `world_check.csv`;
  - `results/mix_closure_log.csv`, `dropped_low_coverage.csv`, `sanity_checks.json`,
    `data_dictionary.csv`, `snapshot_feature_set_sizes.json`, `phase1_summary.csv`,
    `data_notes.md`.
- A3_PLAN.md §1: mix-closure facts and the clean-panel sizes added.

**Phase 1 summary (from `results/phase1_summary.csv`)**
| Stage | Rows | Countries |
|---|---|---|
| Raw file | 22,012 | 306 |
| Countries only (ISO code) | 16,512 | 219 |
| Window 2000–2021 + core columns | 4,798 | 219 |
| After coverage rule (clean panel) | 4,490 | 205 |
| Balanced panel (world totals) | 4,422 | 201 |
| Snapshot 2018 | 205 | 205 |

2018 feature sets with complete data: K-means 205, RF 165, GDP-vs-energy 165.

**Checks**
| Check | Result |
|---|---|
| Notebook clean run | Pass, 0 errors |
| pytest | 31 passed |
| ruff check / format | Clean (after fixes below) |
| Sanity checks (built in; they raise on failure) | 0 duplicates, 0 negatives, mix sums 99.71–100.41, 0 rows outside ±0.5, low-carbon = sum of parts exactly |
| Coverage rule removes the no-data entities flagged in Review #2 | **Confirmed.** Antarctica, Netherlands Antilles, Micronesia, N. Mariana Islands and Tuvalu are among the 14 dropped |
| Raw producer columns absent from `panel_clean.csv` | Confirmed (cannot be misused) |
| Data dictionary covers every processed column | 37 of 37 |
| No inf values; no duplicate countries in the snapshot | Confirmed |
| Figure audit | No new figures in this chunk |

**Bugs found and fixed**
1. **Balanced panel silently excluded 7 countries** (Indonesia, Saudi Arabia, Iran, Chile,
   Kazakhstan, Malaysia, Vietnam).
   - Cause: mix closure set the missing *share* to 0 but left the matching *TWh* blank, and
     the balanced panel requires all TWh columns.
   - Effect: world totals would have missed large electricity systems.
   - Fix: the share and its TWh are zero-filled together, and a test asserts the TWh fill.
   - Result: balanced panel 194 → **201**. The only exclusions are East Timor, Montenegro and
     South Sudan (did not exist for the whole window) and Palestine (2000 missing).
2. **Lint:** 2 × E501 (long lines in a notebook cell and a test). 3 files reformatted.

**Deviations from the plan (flagged for the user)**
- **Mix closure is new** (plan §3 step 6 only asked to *report* the sum distribution). It is
  needed because 7 countries leave unused sources blank instead of 0 and Chile's shares sum
  to up to 112%. Without it, those countries drop out of the clustering and the world totals.
  - The rule is deliberately narrow: a share is zero-filled only when the other shares
    already cover the grid *and* the TWh is also blank.
  - Rows are rescaled only when off by > 0.5 pp.
  - All changes are logged per country in `mix_closure_log.csv`.
  - **Chile's low-carbon share changes by up to 6.5 pp.** This must be stated in the report
    as a limitation.
- **Raw producer columns are removed from the clean panel.** This is stricter than the plan,
  so they cannot be used by accident after 2016.

**Gaps for later chunks**
- Report §4 (data handling) must describe: no internal gaps / 0 interpolated cells; mix
  closure (including Chile); the coverage rule (14 dropped); producer features restricted to
  pre-2017 data.

**Open questions:** none.

---

## REVIEW #4 · Chunk 4 (steps 31–40, Phase 2a: iteration 1 visuals) · Nov 22, 2026

**Steps done:** 31–40.

**Files created or changed**
- `src/features.py` (new): `global_mix_twh`, `low_carbon_share_of_total`, `world_coverage_check`.
- `src/figures.py`: `global_mix_area`, `distributions`, `gdp_vs_energy_linear`, `correlation_pair`.
- `src/plots.py`: `label_points` (non-overlapping labels with leader lines), `choropleth`,
  `save_plotly_figure`.
- `src/config.py`: added `VAR_LABELS` (one readable name + unit per variable for every figure).
- `tests/test_infra.py`: 3 map tests (34 tests in total).
- Notebook: Phase 2 sections 2.1–2.5 (12 cells, tagged `phase2a`). `numpy` added to the setup
  imports.
- Outputs:
  - figures: `iter1_global_mix_area.png`, `iter1_distributions.png`,
    `iter1_gdp_vs_energy_linear.png`, `iter1_corr_pearson_vs_spearman.png`,
    `iter1_lowcarbon_choropleth_2018.png`;
  - results: `global_mix_twh.csv`, `global_mix_check.csv`, `iter1_skew.json`,
    `iter1_corr_pearson.csv`, `iter1_corr_spearman.csv`.

**Key numbers (read from the outputs)**
| Item | Value |
|---|---|
| Balanced panel vs OWID World row | 99.93–99.99% of world generation in every year; per source 99.6–101.5%, so the sums are representative |
| Global low-carbon share | 35.8% (2000) → **lowest 32.0% (2007)** → 38.2% (2021): **not monotonic** |
| Skewness, 2018 | energy/person 2.41 · GDP/person 2.38 · electricity/person 4.83 · carbon intensity −0.34 |
| Largest Pearson–Spearman gaps | electricity/person × GHG/person 0.34; GDP × electricity/person 0.25; GDP × energy/GDP 0.20 |
| GDP vs grid carbon intensity | r = −0.02, ρ = 0.02: essentially no association |
| Top energy users per person | small producer or high-income states (Qatar, Iceland, Singapore, Bahrain, Trinidad & Tobago, …) |

**Checks**
| Check | Result |
|---|---|
| Notebook clean run | Pass, 0 errors, no stray outputs |
| pytest | 34 passed |
| ruff check / format | Clean |
| Figure audit: all 6 PNGs viewed at final resolution | Titles, units, legends, source notes present. No overlapping text. All 200 dpi. All registered in figures.csv. No orphan PNGs |

**Bugs found and fixed**
1. **`label_points` placed labels millions of pixels off-canvas** ("Image size ... too large").
   - Cause: the scatter called it before setting the axis limits, so the data-to-axes
     conversion used temporary limits.
   - Fix: limits are set first; arrows now anchor in data coordinates; the helper **raises a
     clear error** if any point lies outside the axes.
2. **Fractional tick labels:** years (2002.5) on the area chart and counts (2.5 countries) on
   the histograms. Fixed with whole-year and integer tick locators.
3. **Stacked-area annotation crossed its own line.** The fossil/low-carbon boundary is now a
   legend entry.
4. **Correlation panels collided:** the right panel's row labels overlapped the left heatmap.
   Wider figure and panel spacing.
5. **Histogram stats boxes covered the tallest bars** (carbon intensity, ~690 gCO2/kWh). Added
   45% headroom above the bars.
6. **Map colourbar title touched the top tick label.** The title now runs along the bar.
7. **The plotly PNG had no dpi metadata** (Word sizes images by it). `save_plotly_figure`
   now stamps 200 dpi, and a test checks it.
8. **A stray `WindowsPath(...)` output** in a notebook cell. The cell now ends with a useful
   table.

**Improvements beyond the plan**
- The GDP–energy scatter also labels the **3 most populous countries** (China, India, USA),
  so the reader sees where most people live, not only the outliers.
- The correlation figure **outlines the cells where |ρ − r| ≥ 0.2**, which makes the
  non-linearity evidence visible.

**Notes for the next chunks**
- **Mann-Kendall (step 45) must be read carefully.** The global low-carbon share falls until
  2007 and then rises, so a single monotonic trend over 2000–2021 can be weak or
  non-significant even though there is clear change. The I1-3 wording must reflect this. Do
  not claim a steady rise.
- `iter1_lowcarbon_choropleth_2018.png` has no inference ID yet. Assign it at step 73/74.

**Open questions:** none.

---

## REVIEW #5 · Chunk 5 (steps 41–50, Phase 2b: change evidence and statistics) · Nov 22, 2026

**Steps done:** 41–50.

**Files created or changed**
- `src/stats.py` (new): `mann_kendall` (original + Hamed–Rao), `hamed_rao_factor`,
  `sen_slope`, `correlation_tests`.
- `src/models.py` (new): `fit_ols` (with Breusch-Pagan).
- `src/features.py`: `endpoint_mean`, `endpoint_change`.
- `src/figures.py`: `change_2000_2018`, `ols_residuals`.
- `tests/test_stats.py` (new, 11 tests) and an endpoint test in `test_prep.py` (46 tests in
  total).
- `pyproject.toml`: pytest now turns every `RuntimeWarning` into a failure.
- Notebook: Phase 2 sections 2.6–2.9 + I1-1 (11 cells, tagged `phase2b`).
- Outputs:
  - figures: `iter1_change_2000_2018.png`, `iter1_ols_residuals.png`;
  - results: `iter1_change.csv`, `iter1_change_summary.json`, `global_lowcarbon_share.csv`,
    `iter1_mk_global.json`, `iter1_correlation_test.json`, `iter1_ols.json`,
    `iter1_ols_residuals.csv`, `inferences.json` / `inferences.md` (**I1-1 logged**).

**Key numbers (read from the outputs)**
| Item | Value |
|---|---|
| Change in low-carbon share, 2000–02 → 2016–18 (201 countries) | median +0.6 pp; **69 (34%) changed by > 10 pp**; median rank move 15 places; rank ρ = 0.91 |
| Largest movers | Sierra Leone +63 pp, Falkland Is. +50 pp; Congo −59 pp, Tanzania −53 pp, Rwanda −54 pp (hydro-dominated grids adding fossil generation) |
| Global low-carbon share, Mann-Kendall 2000–2021 | τ = 0.14, p = 0.37; **Hamed–Rao p = 0.58** (variance × 2.60); Sen +0.09 pp/yr; **no significant monotonic trend** |
| Same from the 2007 minimum (post hoc, descriptive only) | Sen +0.49 pp/yr, Hamed–Rao p = 0.009. Saved with an explicit note that the breakpoint was chosen after seeing the data |
| GDP vs energy per person (2018, n = 165) | Pearson r = 0.85, Spearman ρ = 0.95 (both p < 0.001) |
| Raw OLS energy ~ GDP | slope 1.48 kWh per int-$ (95% CI 1.34–1.63), R² = 0.72, **Breusch-Pagan p = 0.001** |
| Largest OLS residuals | Iceland (0.4 M people), Trinidad & Tobago (1.5 M), Bahrain (1.5 M), Singapore (5.8 M); Ireland is the largest negative |

**Checks**
| Check | Result |
|---|---|
| Notebook clean run | Pass, 0 errors |
| pytest (RuntimeWarnings are errors) | 46 passed |
| ruff check / format | Clean |
| Figure audit (both new PNGs viewed at final resolution) | Titles, units, legends, source note. No overlaps after the fixes below. 200 dpi. Registered |
| Registry | 8 figures registered, no orphan or missing files |
| Number audit (I1-1) | Every number in the statement is generated from `iter1_skew.json`, `iter1_ols.json`, `iter1_ols_residuals.csv` |

**Bugs found and fixed**
1. **Hamed–Rao edge case 1 (NaN):** a perfectly linear series detrends to a constant, so the
   rank autocorrelation was 0/0. It returned the right answer only by accident (NaN
   comparisons are false). Now returns zero autocorrelation explicitly, with a test.
2. **Hamed–Rao edge case 2 (sqrt of a negative):** strong negative autocorrelation made the
   raw variance factor negative (−→ NaN z and p). The factor is now **floored at 1**
   (conservative: the correction can widen the variance but never makes the test more
   confident than the original). The raw factor is still reported. A test covers this.
3. **Hidden warnings:** both bugs above only surfaced as warnings, so pytest now fails on any
   `RuntimeWarning`.
4. **I1-1 was factually wrong.** It called all four top-residual countries "small states",
   but only Iceland is under the 1 M small-state threshold (the others have 1.5–5.8 M
   people). Reworded to "small-population economies (all under 6 M)", and the transformation
   names log1p as the main remedy, the < 1 M flag being secondary.
5. **I1-1 wording:** lower-casing turned "GDP" into "gdp". Labels are now used as they are.
6. **Overlaps in the figures:** the OLS stats box covered Iceland's point and label (then,
   after the first fix, Ireland's), so it moved to the empty top-right. The rank panel's
   legend sat on data points; the tied-rank note collided with the panel title.
7. **Unexplained vertical column in the rank panel:** the 50 countries at 0% low-carbon in
   2000–02 share one tied rank. This is now explained in the x-axis label.
8. **Duplicate merge in the I1-1 cell** was replaced by one merge that is reused.

**Findings that shape the story (to carry forward)**
- **The global low-carbon trend is not monotonic.** A single 2000–2021 trend test finds
  nothing while countries moved a lot (34% by > 10 pp). This is exactly the evidence I1-3
  needs: a single snapshot or a single global series hides the change. Wording must not
  claim a steady global rise.
- **The < 1 M small-state threshold (A3_PLAN.md §5) catches only Iceland among the OLS
  outliers.** The log transform must be presented as the main remedy for I1-1. No threshold
  change is proposed, since changing it after seeing the data would be arbitrary.
- **The LOWESS of the raw-OLS residuals bends downward**, so the straight line also misses a
  non-linear relationship. This is another argument for the log-log model in iteration 2.

**Open questions:** none.


---

## REVIEW #6 · Chunk 6 (steps 51–60): K-means baseline · 2026-11-22

**Checks**
| Check | Result |
|---|---|
| Clean notebook run (`nbconvert --execute`) | No errors, no stderr in any of the 81 cells |
| pytest (RuntimeWarnings are errors) | 57 passed (11 new in `tests/test_clustering.py`) |
| ruff check / format (src, tests, notebook) | Clean |
| Outputs vs plan | `iter1_kmeans_k.csv`, `iter1_clusters.csv`, `iter1_pca.json`, `iter1_silhouette_common.json`, figures `iter1_kmeans_k_selection.png`, `iter1_kmeans_pca.png`, `iter1_kmeans_map.png`; extra: `iter1_kmeans.json`, `iter1_cluster_assignments.csv`, `iter1_kmeans_countries.csv`, `iter2_country_set.csv`, `iter1_composition_checks.json` |
| Figure audit (3 PNGs viewed at final resolution) | Titles, axis units, legends, source note, 200 dpi, registered with inference I1-2. No overlaps after the fixes below |
| Registry | 11 figures registered, no orphans |
| Data audit | 205 rows = expected K-means set; 0 NaN / inf in assignments; cluster sizes sum to 205; saved centroids equal member means (max gap 0.0005 = rounding); max loading length 0.97 ≤ 1 |
| Leakage | Not applicable to clustering (unsupervised, no target). The scaler is fitted only on the rows it clusters |
| Number audit (I1-2) | Every number is generated from `iter1_kmeans.json`, `iter1_clusters.csv`, `iter1_cluster_assignments.csv`, `iter1_composition_checks.json`, `iter1_pca.json` |

**Decisions**
- **k rule fixed in `config.K_RULE` before fitting:** highest silhouette among the k whose
  every cluster has ≥ 5 countries. It gives **k = 8**, at the edge of the plan's range
  2..8; the silhouette rises slowly with no clear peak. The range was not widened after
  seeing this (that would be a data-driven change of rule), and the figure and I1-2 both say so.
- **Silhouette is read against Kaufman & Rousseeuw (1990) bands.** 0.36 = "weak structure".
  → **Add Kaufman, L. & Rousseeuw, P. J. (1990), *Finding Groups in Data*, Wiley, to the
  report references.**
- **The common iteration 2 set is fixed now: 162 countries** (the plan estimated ~163). The
  iteration 1 silhouette on it is 0.33 (full-fit labels) and 0.34 (refit). Both are saved;
  the refit is the like-for-like comparison for §6.3.

**Bugs found and fixed**
1. **PCA loadings were slightly too long.** weight × √eigenvalue mixes sklearn's n−1
   variance with StandardScaler's n, so "correlations" overshot by √(n/(n−1)), and one
   test vector reached 1.008. Loadings are now computed as actual correlations, and a unit
   test checks that they stay inside the unit circle.
2. **Cluster colours contradicted the source colours.** The hydro cluster was in wind's
   colour, the coal cluster in hydro's, and the oil cluster in gas's. Now
   `plots.cluster_colors()` gives a cluster named after a source that source's colour.
   Other clusters take black and then Paul Tol colours.
3. **Overlapping loading labels:** Coal and Gas point the same way. Labels now sit in two
   columns outside the circle, spread vertically, with dotted leader lines.
4. **The figure title printed the config name** "MIN_CLUSTER_SIZE" instead of 5.
5. **A joblib warning and traceback appeared in the notebook.** joblib calls `wmic`, which
   Windows 11 no longer ships. Fixed in `src/__init__.py` by setting `LOKY_MAX_CPU_COUNT`,
   which only affects the worker count, never a result.
6. **The I1-2 wording said "sums to 100.0-100.0"** → now "100 (within ±0.004)".
7. **A stale I1-1 heading said "a few small states"**, which contradicted the Chunk 5
   correction → now "small, energy-intensive economies".
8. **`_spread` was private but used across modules** → renamed `plots.spread_positions`.

**Plan hypothesis vs data (A3_PLAN.md §4.3)**
- The hypothesis was "clusters driven by scale and outliers (a tiny cluster of
  high-consumption small states)". It is **only partly confirmed**:
  - **Confirmed:** one cluster (C6, n = 10) is defined by energy per person and puts
    Iceland (28 gCO2/kWh) with Brunei (500 gCO2/kWh).
  - **Not confirmed:** the dominant pattern is different. 7 of 8 clusters re-label the
    dominant source (ARI 0.66), and the smallest cluster (C8, n = 8) is split off by a
    minor source (solar, sd 4.1 pp) that standardising inflates, even though 88% of its
    grids are mostly oil.
- I1-2 states what the data shows. The I1-2 → CLR transformation still follows, because the
  composition evidence (rank 7 of 8, 64% negative correlations, minor-part inflation)
  supports it.

**Open questions:** none.


---

## REVIEW #7 · Chunk 7 (steps 61–70): Random Forest baseline · 2026-11-23

**Checks**
| Check | Result |
|---|---|
| Clean notebook run | No errors, no stderr in any of the 96 cells |
| pytest | 77 passed (20 new in `tests/test_rf.py`: leakage guard ×14 cases, folds, CV on toy data, group test, quartiles, wording helpers) |
| ruff check / format | Clean |
| Outputs vs plan | `rf_countries.csv`, `rf_folds.csv`, `iter1_rf_metrics.json`, `iter1_rf_oof.csv`, `iter1_rf_importance.csv`, `iter1_rf_errors.csv`, figures `iter1_rf_pred_vs_actual.png`, `iter1_rf_importance.png`, `iter1_rf_residual_map.png`; extra: `iter1_rf_error_groups.json` |
| Figure audit (3 PNGs viewed at final resolution) | Titles, units, legends, source note, 200 dpi, diverging map centred at 0 with a symmetric range, registered with inference I1-4 |
| Registry | 14 figures registered, no orphans |
| Data audit | 165 rows = expected RF set; out-of-fold predictions cover every country exactly once; folds 5 × 33; 0 NaN / inf |
| Leakage audit | `assert_no_leakage` runs before every fit; the saved feature list passes it. No mix share, mix TWh, low-carbon, carbon-intensity or emissions column is a feature. Inputs are from 2018 or earlier (producers 2016). The dominant source is used only for colour and grouping, never as a feature |
| Number audit (I1-4) | Pooled R² and MAE recomputed from `iter1_rf_oof.csv` match the JSON exactly (0.0299, 167.302). Every number in I1-4 is generated from saved files |

**Decisions**
- **The leakage ban list is stricter than the plan's.** Beyond the STEPS.md list it also bans
  the mix TWh columns and power-sector GHG: carbon intensity is emissions ÷ generation, so
  these columns are the target's own ingredients. This follows the plan's principle ("every
  mix- or carbon-derived feature removed").
- **Permutation importance is measured as the rise in MAE (gCO2/kWh)** on held-out folds,
  not as the R² drop. It is in the target's units, and R² on 33-country folds is unstable.
- **Errors are grouped by 2018 GDP quartile, named "Q1 (poorest)" … "Q4 (richest)".** This
  keeps them distinct from the 2000–02 income tiers that the feedback loop will build.

**Bugs found and fixed**
1. **A junk expression (`metric * 0 + mean`)** in the baseline line of the figure was
   replaced by the plain average, with a comment saying why it is an average.
2. **The legend covered two named errors** (Hong Kong, Lebanon), so it moved outside the axes.
3. **Country labels crossing other dots were hard to read.** `label_points` now draws a light
   white backing behind every label, which also benefits the earlier scatter figures; they
   were re-checked.
4. **I1-4 contained a hand-typed claim** ("hydro and nuclear predicted too dirty…"). It is
   now generated from the signs of the group medians.
5. **I1-4 overclaimed "the most useful feature is Population".** Its importance is 12 ± 12.
   The statement now lists only the features whose mean rise is larger than their sd, and
   says the largest rise is small next to the MAE.
6. **Non-significant tests were not called non-significant.** Every p-value in the
   statement now carries its verdict.
7. **Grammar:** "Hydro and Nuclear-dominated" → "hydro- and nuclear-dominated".

**Plan hypothesis vs data (A3_PLAN.md §4.4)**
- **"Moderate R²": not confirmed.** The RF barely beats the mean predictor (R² 0.02 ± 0.10 vs
  −0.01; MAE 167 vs 177 gCO2/kWh).
- **"Biggest errors are hydro- or nuclear-heavy countries": confirmed, and extended.** The
  error is systematic in both directions: hydro −205 and nuclear −159 (predicted too dirty),
  and coal +185, oil +151 (predicted too clean). Kruskal-Wallis p < 0.001.
- **"…and small states": not confirmed.** Small states' median absolute error is 123 vs 146
  for the others (p = 0.63). Income quartiles do not differ either (p = 0.38).

**Risk to carry forward (Chunk 14, RF v2):** the information the model lacks is mainly the
mix itself, which stays banned for leakage reasons. The context features may improve RF v2
only a little. That is still a valid, reportable result: the report must compare v1 and v2
honestly on the same folds and must not tune v2 until it "wins".

**Open questions:** none.

---

## REVIEW #8: Chunk 8, Phase 2e: iteration 1 wrap-up (steps 71–80), Nov 23

**Checks**
- Clean-kernel notebook run: 104 cells, no errors, no stderr.
- `pytest -q`: 81 passed (4 new in `tests/test_hypotheses.py`). `ruff format` and
  `ruff check src tests` are clean.
- Figures: 14 registered, 14 PNGs, no orphans, none missing, every one has a "why this
  chart". All iteration 1 figures have an inference ID except the missingness heatmap
  (a Phase 1 data-handling figure, correctly left without one).
- Inferences: I1-1 to I1-4 all exist, all trigger the loop with a transformation, and
  every cited figure or results file exists.
- Number audit: the I1-3 counts (42 rose, 27 fell, median +0.6 pp, n = 201) were recomputed
  from `iter1_change.csv` and match `iter1_change_summary.json`.
- A3_PLAN.md §4 "done when" is met: every §4.1–4.4 figure and metrics file exists, and each
  inference cites a figure and a number.

**Steps done, files created or changed**
- **71. I1-3 logged.** Its statement is generated from `iter1_change_summary.json`,
  `iter1_mk_global.json` and `global_lowcarbon_share.csv`.
- **72. Plan hypotheses vs data.**
  - New `src/hypotheses.py` splits each plan hypothesis into separate claims.
  - Each claim has a rule fixed in config; the verdict is computed from the results.
  - Output: `results/iter1_hypothesis_check.csv`.
  - All four hypotheses are **partly confirmed** (see below).
- **73. Transformations made precise.**
  - **I1-1:** names the exact log1p columns (`config.LOG_COLS`), says Random Forests are
    invariant to monotone transforms, and says small states are never dropped silently.
  - **I1-3:** states the change in the unit of analysis and the pre-2019 table.
- **74. figures.csv audit:** done (see Checks).
- **75. Phase 2 narrative:** sections 2.21–2.23 added, and `results/phase2_summary.md` is
  generated from `results/`.
- **76. Visual consistency pass:** all 14 iteration 1 figures checked side by side on a
  contact sheet.
- **77–78.** Clean run, ruff and pytest (see Checks).
- **Changed:**
  - `src/config.py`: ALPHA, SKEW_HEAVY, SKEW_CHECK_COLS, N_OLS_NAMED, LOG_COLS, MODERATE_R2,
    PLAN_HYPOTHESES_ITER1, CHANGE_BIG_PP, N_CHANGE_MOVERS;
  - `src/features.py`: `change_summary`;
  - `src/figures.py`: `change_2000_2018`;
  - `src/plots.py`: choropleth text colour;
  - `src/logbook.py`: the default alpha now comes from config.

**Bugs found and fixed**
1. **Magic numbers in the notebook:**
   - the 10 pp change threshold (§2.6, used twice);
   - `.head(4)` and the word "four" in I1-1;
   - the skew cut-off `> 1`;
   - a duplicate p-value formatter in I1-1.

   All of them now come from config or `logbook.format_p`.
2. **The change-figure title overclaimed** "A single snapshot hides large change", although
   the median country moved +0.6 pp. The title is now generated: the median change, then the
   share of countries moving more than 10 pp. The histogram shows the ±10 pp thresholds and
   the split into rises and falls.
3. **I1-1 still implied the plan's "small producer states".** It now says, from the data,
   that only Iceland is under 1 M people and only Trinidad and Tobago and Bahrain produced
   fossil fuels in 2016.
4. **Plotly maps had blue-grey titles** (plotly's default `#2a3f5f`), unlike the black
   matplotlib titles. They are now black.
5. **Open item closed:** `iter1_lowcarbon_choropleth_2018.png` had no inference ID. It is
   now linked to I1-3 (Congo, Rwanda and Tanzania look mid-range in 2018 after being near
   100% in 2000–02) and is cited in its evidence.

**Plan hypotheses vs data (`results/iter1_hypothesis_check.csv`)**
- **I1-1, partly confirmed.**
  - Heavy skew: confirmed (2.38 to 4.83).
  - Dominating countries are small states: not confirmed (1 of 4).
  - Dominating countries are fossil producers: not confirmed (2 of 4).
- **I1-2, partly confirmed.**
  - Clusters are not transition types: confirmed (7 of 8 are defined by a source share).
  - Clusters are driven by scale: not confirmed (1 of 8).
  - A tiny cluster of high-consumption small states: not confirmed (the smallest cluster is
    "high Solar share", with 4 of 8 small states).
- **I1-3, partly confirmed.**
  - The typical country changed a lot: not confirmed (median +0.6 pp).
  - Many countries changed a lot, in both directions: confirmed (69 of 201: 42 up, 27 down).
  - The global trend hides it: confirmed (Hamed–Rao p = 0.576).
- **I1-4, partly confirmed.**
  - Moderate R²: not confirmed (0.02).
  - Hydro or nuclear grids have the biggest errors: confirmed (hydro has the largest median
    |error|, 205; nuclear is third).
  - Small states have bigger errors: not confirmed (p = 0.633).

**Gaps against the plan / PDF:** none for Phase 2.
- Still open for later chunks: copy the A1 report into `report/` (Chunk 17/18), and the
  Kaufman & Rousseeuw (1990) reference for the report.

**Deviations needing approval:** none.
- The hypothesis rules (MODERATE_R2 = 0.3, "most of" = more than half, SKEW_HEAVY = 1) are
  analysis conventions, recorded in config.

**Open questions:** none. Phase 2 (iteration 1) is complete.

---

## REVIEW #9: Chunk 9, Phase 3a: transformations (steps 81–90), Nov 23

**Checks**
- Clean-kernel notebook run: 118 cells, no errors, no stderr.
- `pytest -q`: 93 passed (10 new in `tests/test_transforms.py`, 2 new leakage cases).
  `ruff check src tests` is clean.
- Every promised file exists, with the plan's names:
  - `results/`: `loop_skew.csv`, `small_states.csv`, `loop_clr_eps.csv`,
    `income_tier_thresholds.csv`, `trajectories_summary.csv` and `trajectories_log.json`;
  - `data/processed/`: `trajectories.csv` and `trajectories_pre2019.csv`.
- Figures: no new figures in this chunk (the loop figures are Chunk 10). There are still 14,
  with no orphans.
- **Data audit:**
  - both tables have 162 rows, one per country, with no NaN or inf;
  - every income tier is assigned, CLR rows sum to 0, and all ranges are plausible;
  - the columns that don't depend on the end window are identical in both tables.
- **Hand checks:**
  - India's GDP growth rate (5.30 %/yr) and Germany's low-carbon slope (0.559 pp/yr up to
    2018, 0.811 up to 2021) were recomputed by hand and match;
  - Germany's 2019–21 change matches;
  - `d_lowcarbon` in the pre-2019 table equals the iteration 1 change table (difference
    ≤ 0.0003, from the 3-decimal rounding of that CSV).
- **Leakage:**
  - the pre-2019 builder raises on the full panel (shown in the notebook);
  - the pre-2019 table uses data up to 2018 only;
  - exactly the 12 context columns pass the leakage guard.
- RF v1 metrics are unchanged after the guard fix (R² 0.0192, MAE 167.302).

**Steps done, files created or changed**
- **81.** `features.log_transform`, `skew_before_after`. Skew falls from 1.78–4.83 (raw)
  to between −0.75 and 0.72 after log1p.
- **82.** `features.small_state_flag`: 45 small states in the 2018 snapshot, 10 of them in
  the iteration 2 set. They are flagged, never dropped.
- **83.** `features.clr`: closes each row to 100 first, which makes it exactly scale
  invariant. Tests cover:
  - rows summing to 0;
  - scale invariance;
  - zeros handled through ε;
  - rejecting NaN and negative values.
- **84.** `models.clr_eps_sensitivity` → `loop_clr_eps.csv` (see the findings below).
- **85.** `features.income_tiers`: quartiles of 2000–02 GDP per person over the 162
  countries. Thresholds 446 / 2,239 / 6,818 / 16,804 / 56,490 $; tier sizes 41 / 40 / 40 / 41.
- **86.** `features.cagr` and `yearly_slope`, tested against known values.
  `endpoint_mean` already existed (step 41).
- **87–88.** `build_trajectories`, with thin wrappers `trajectories_descriptive` and
  `trajectories_pre2019`. The pre-2019 wrapper raises on any year after 2018. The data goes
  from 4,490 country-year rows to 162 country rows × 28 columns; 43 countries are excluded,
  with reasons in `iter2_country_set.csv`.
- **89.** `validate_trajectories` and `describe_table` → `trajectories_summary.csv`.
- **Config:**
  - PRE2019_MAX_YEAR;
  - SLOPE_YEARS_*;
  - SOLARWIND_COLS;
  - PRODUCER_HISTORY_COLS;
  - TRAJ_RANGES;
  - TRAJ_CONTEXT_COLS.

**Bugs found and fixed**
1. **Leakage-guard gap (serious).**
   - **Problem:** the banned fragment `lowcarbon_` did not match `d_lowcarbon`, a change in
     the mix that must never be a model feature.
   - **Fix:** the fragment is now `lowcarbon`, and `d_lowcarbon` and `lowcarbon_2000` were
     added to the tests.
   - **New check:** the notebook now asserts that the columns passing the guard equal
     `config.TRAJ_CONTEXT_COLS` exactly, so the next gap cannot go unnoticed.
   - RF v1 was not affected: its features never included these columns.
2. **A misleading print** said "205 countries x 22 years" for 4,490 rows, which implies
   4,510. It now prints the year range instead.

**Findings to carry into the report (honest, not what the plan hoped)**
- **CLR does not raise the silhouette.** On the same 162 countries, at k = 8:
  - CLR with ε = 0.01 / 0.1 / 1 scores 0.29 / 0.27 / 0.28;
  - z-scored raw shares score 0.42.

  Silhouettes from different feature spaces are not comparable. The case for CLR is the
  composition evidence in I1-2, not a higher score. Chunk 12's iteration 1 vs 2 comparison
  must say this and must not present silhouette as "proof" that the loop helped.
- **ε matters.** Clusters at ε = 0.01 or 1 agree with ε = 0.1 at ARI 0.67–0.68, because zero
  shares are common. This is reported as a modelling choice.
- **k = 8 again sits at the edge of the range** for every ε. The iteration 2 archetype
  clustering (k = 3..7, trajectory features) is a separate question.

**Gaps against the plan / PDF**
- None for steps 81–90.
- The plan's "~163" countries is 162 (recorded in A3_PLAN.md since Chunk 6).
- The before/after visuals and the inference → transformation table in `inferences.md` are
  planned for Chunk 10 (steps 91–95).

**Deviations needing approval:** none.
- Income tiers are computed over the 162 iteration 2 countries (the analysis population),
  not over all 164 countries with a 2000–02 GDP. The 2 extra countries are excluded for
  other missing data, so tiers stay balanced (41 / 40 / 40 / 41) inside the analysed set.
  Noted for the report.

**Open questions:** none.

---

## REVIEW #10: Chunk 10, Phase 3b: loop visuals and documentation (steps 91–100), Nov 24

**Checks**
- Clean-kernel notebook run: 130 cells, no errors, no stderr.
- `pytest -q`: 97 passed (4 new). `ruff check src tests` is clean.
- Figures: 17 registered, 17 PNGs, no orphans. The three new loop figures were inspected and
  carry inference IDs I1-3, I1-1 and I1-2.
- A3_PLAN.md §5 "done when" is met:
  - both trajectory tables exist;
  - the inference → transformation table is in `results/inferences.md` and in
    `results/loop_transformations.csv`;
  - the before/after visuals are saved.
- **Leakage proof (step 97).**
  - Every value after 2018 was scrambled and both tables rebuilt.
  - The pre-2019 table did not change at all.
  - In the descriptive table exactly the 5 columns in `config.POST2018_COLS` changed.
  - `trajectories.csv` is marked "DESCRIPTIVE ONLY, NOT FOR RF OR FORECAST" in
    `data/processed/trajectories_README.md`.
  - `results/trajectory_columns.csv` defines all 28 columns and flags the 12 allowed as
    model features and the 5 that use 2019–21.

**Steps done, files created or changed**
- **91.** `loop_before_after_table.png` (`figures.loop_before_after_table`): every number
  comes from `results/loop_summary.json`.
- **92.** `loop_skew_before_after.png`: the 3 variables, raw vs log1p, with skew read from
  `loop_skew.csv`.
- **93.** `loop_clr_before_after.png`: a PCA of z-scored shares vs CLR for the same 162
  countries, coloured by dominant source, plus `results/loop_clr_pca.json`.
- **94.** `logbook.loop_rows` and `write_loop_table`, driven by `config.LOOP_DETAILS`. The
  CSV and the markdown table are built from the same inference log.
- **95.** Notebook sections 3.7–3.12, plus a generated `results/phase3_summary.md`.
- **96.** `features.loop_summary` → `results/loop_summary.json`:
  - unit of analysis: country-year becomes country path;
  - 4,490 → 162 rows;
  - 16 iteration 1 features → 26 columns: 14 built from several years, 11 transformed
    2018 values, 1 unchanged;
  - max |skew| 4.83 → 0.75.
- **97.** `features.scramble_rows` and `changed_columns`, the column dictionary and the
  README.
- **Config:** LOOP_DETAILS, LOOP_SKEW_PLOT_COLS, POST2018_COLS, TRAJ_COLUMN_DEFS.

**Bugs found and fixed**
1. **"26 new columns" overclaimed.** It counted `population_2018`, which is simply the
   snapshot's population.
   - Columns are now classified empirically, by scrambling every year except 2018 (plus
     the producer history, and recomputing the tiers): 14 multi-year, 11 transformed,
     1 unchanged.
   - Two traps were avoided: producer history and income tiers are built outside the
     panel, so a naive scramble would have misclassified them.
2. **Misleading pair markers on the CLR figure.**
   - **Problem:** the Luxembourg–Russia pair was chosen on 8-dimensional raw-pp distances
     but drawn on 2-D PCA projections of z-scored shares, where it looked far apart
     "before" and closer "after", the opposite of the claim.
   - **Fix:** the markers were removed; the figure now states the distance correlation
     (rho = 0.66) and the example pair in text, with the reason in the docstring.
3. **Pink (Nuclear's colour) was used for neutral elements:** the table header and the raw
   histograms. These now use neutral colours, so a colour keeps one meaning across
   figures.
4. **Wording fixes:**
   - "22% percentile" → "22nd percentile" (new `_ordinal` helper, tested);
   - "gdp" was lowercased in an axis label, now fixed;
   - a long note ran past the figure width and now wraps;
   - the skew figure's title now states the computed max |skew| change.
5. **Heredoc newline quirk (again):** a `\n` inside a Python string became a real newline
   and was repaired with the Edit tool. Rule kept: do multi-line Python edits through
   Write/Edit, not bash heredocs.

**Gaps against the plan / PDF:** none.
- R3 (significant transformation) and R4 (each one traced to an inference) are now
  evidenced by a figure, a JSON file and a table.

**Deviations needing approval:** none.

**Open questions:** carried from Review #9. Iteration 1 and iteration 2 clusterings will be
compared on what they reveal, not on silhouette across feature spaces, unless the user
prefers otherwise.

---

## REVIEW #11: Chunk 11, Phase 4a: decoupling and elasticity (steps 101–110), Nov 24

**Checks**
- Clean-kernel notebook run: 142 cells, no errors, no stderr.
- `pytest -q`: 101 passed (4 new). `ruff check src tests` is clean.
- Figures: 21 registered, 21 PNGs, no orphans. The 4 new iteration 2 figures were each
  inspected after every fix.
- Every promised results file exists:
  - `iter2_decoupling_classes.csv` (+ `iter2_decoupling_counts.csv`);
  - `iter2_loglog.json`, `iter2_ols_comparison.csv`;
  - `iter2_kw.json`, `iter2_pairwise.csv`;
  - `iter2_tier_lowcarbon.csv`.
- **Number audit:** the class counts were recomputed by hand from the saved growth rates
  (46 absolute, 75 relative, 32 coupled, 9 GDP fell) and match the saved table. There are
  162 rows, one per country, with no NaN.

**Steps done, files created or changed**
- **101.** `features.decoupling_class`; per-country classes and a tier × class table.
- **102.** `iter2_decoupling_quadrant.png`: 45° and zero lines, colour by tier, hollow small
  states, region counts. The named countries are chosen by rule: the 3 most populous plus
  the 3 largest and 3 smallest decoupling values.
- **103–105.** `models.ols_band` (refactored with `fit_ols` through a shared `_ols_fit`).
  The log-log OLS with HC3 gives:
  - elasticity 1.20 (95% CI 1.13–1.27);
  - R² 0.90 (raw: 0.72);
  - Breusch-Pagan p 0.040 (raw: 0.001);
  - `iter2_loglog_gdp_energy.png`.
- **106–107.** `stats.pairwise_mannwhitney` (Holm correction, rank-biserial effect size)
  and `iter2_decoupling_by_tier.png`.
- **108–109.** `features.tier_lowcarbon` and `iter2_slope_lowcarbon_by_income.png`.

**Findings (for I2-1 and I2-2 at step 129; not logged yet, as STEPS.md schedules them)**
- **Decoupling differs by tier** (Kruskal-Wallis p < 0.001), but only the Low tier differs
  from each of the others (Holm p 0.004 / 0.001 / < 0.001). Lower-middle, Upper-middle and
  High do not differ from each other (Holm p = 1.0).
- **29 of 41 High-tier countries decoupled absolutely.** The Low tier is mostly coupled
  (17 of 41), with median decoupling −0.14 pp/yr.
- **Across countries, energy rises more than proportionally with GDP** (elasticity > 1),
  while within the High tier energy per person fell over time. Cross-section and time
  series answer different questions; the report must say so and make no causal claim.
- **Log scales help but do not cure heteroscedasticity** (Breusch-Pagan p 0.040). The
  report must say this, not "fixed".
- **Low-carbon share:** the High tier's median rose 22% → 39% (median change +8.4 pp). The
  Low tier's median fell 58% → 54%, but its median per-country change is 0.0, so the
  difference of medians is not the typical change. The figure notes this.

**Bugs found and fixed**
1. **Labels were placed against the wrong axis view.** `decoupling_quadrant` called
   `label_points` before setting the axis limits, which that function requires to be final,
   so labels ended up far from their points. The limits are now set first.
2. **`spread_positions` was given unsorted values** in the slope chart, so labels were
   pushed far from their lines. They are now sorted first, and the leader lines attach to
   the start of the text.
3. **The box-plot note box hid a data point** (a Lower-middle country at −7.8). The note
   moved into the subtitle.
4. **Overlaps:** the "relative decoupling" note covered the Mongolia label, the "Mali" label
   covered the Congo point, and the slope-chart footnote crossed the IQR bars. All three
   were moved.
5. **Code quality:**
   - `_p_text` duplicated `logbook.format_p` and was replaced by it;
   - `Line2D` and `multipletests` imports moved to the module tops;
   - a `chr(10)` workaround was replaced by an explicit display label.

**Data-quality caveat (for the report's limitations)**
- In this dataset, Qatar's GDP per person rises from 39k (2000) to 145k (2018), a 7.9%/yr
  CAGR, while its population quadruples. That makes Qatar the 3rd largest decoupler.
- The value cannot be cross-checked without external data, which the user's rule
  forbids. It is reported as given, labelled only because the rule names the extremes,
  and must not be used as a showcase example.

**Gaps against the plan / PDF**
- None for steps 101–110.
- Regression to the mean is stated as a caveat in the notebook (A3_PLAN.md §6.2).
- The OLS uses the same 165 countries as the iteration 1 OLS (needed for a like-for-like
  raw vs log comparison), not the 162 iteration 2 countries. Noted.

**Deviations needing approval:** none.

**Open questions:** carried from Review #9 (iteration 1 vs 2 silhouette comparison).


## Chunk 12 (steps 111-119), Nov 26: archetype clustering (REVIEW #12 not yet signed off)

- Added `src/archetypes.py`, `src/archetype_figures.py`, config constants and 8 notebook cells.
- 152 countries (162 minus 10 small states, assigned post hoc to the nearest centroid).
- K-means k = 5 chosen by the documented rule; GMM never beat it.
- Honest findings: silhouette 0.14 ("no substantial structure"), lower than the iteration 1
  space (0.33 at k = 8, 0.28 at k = 5), so archetypes are a partition of a continuum, not
  natural groups. Seed stability is better: ARI mean 0.82 (min 0.74).
- Archetype low-carbon paths differ: A3/A4 rise, A5 falls, A1/A2 flat (Mann-Kendall in
  `iter2_mk_archetypes.csv`).
- Not done: I2-3/I2-4 text, producer test (step 127), GMM BIC is noisy (n_init = 5).
- Caveat: silhouettes in different feature spaces are not strictly comparable.


## Chunks 13-14 (steps 121-139) + diagram code (161-163), Nov 26

- Archetypes get rule-based short names (largest positive CLR source + Mann-Kendall direction):
  Gas/flat, Hydro/flat, Oil/rising, Coal/rising (fastest, +1.37 pp/yr), Hydro/falling (-1.36 pp/yr).
- I2-1 to I2-5 logged from results/ values.
- **Contradicted hypothesis (I2-4):** producers (fossil production >= own energy use, 2000-16,
  n = 45) are not significantly dirtier (medians 490 vs 443 gCO2/kWh, p = 0.44, r = -0.08).
- **RF v2 (I2-5):** same 162 countries and folds; R2 0.02 -> 0.03, MAE 166 -> 170. Within
  fold noise (v2 better in 2 of 5 folds). Only coal production history adds importance.
- **Deviation:** SHAP is not in requirements.txt, so steps 137-138 use held-out permutation
  importance (iter2_rf_importance.png) instead of a SHAP beeswarm.
- `src/archetype_figures.py` was renamed `src/iter2_figures.py`.
- `src/workflow_diagram.py` + tests: unrolled two-row diamond, one edge "Feedback loop", no
  self-loops.
