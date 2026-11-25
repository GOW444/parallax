# DAS732 A3: Visual Analytics Workflow Execution Plan

- **Dataset:** `World Energy Consumption.csv` (Our World in Data), the same dataset used in A1.
  **No supplementary data is used** (team decision; see CLAUDE.md).
- **Deadline:** Nov 29, 2026, 11:59 pm IST (hard). **Our soft deadline: Nov 27.** Viva: week of Nov 30.
- **Framework:** the Keim et al. visual analytics "diamond" (Data → Visualization ⇄ Models → Knowledge),
  run twice. Between iteration 1 and iteration 2 there is an explicit **feedback loop** that
  significantly transforms the data.
- **Rules:** CLAUDE.md holds the binding rules derived from the assignment PDF. The PDF wins any conflict.

---

## Changes in this revision (Nov 21, after checking the plan against the CSV)

| # | Problem found | Change made |
|---|---|---|
| 1 | Producer columns (`*_prod_per_capita`) record explicit 0s up to 2016. From 2017 they list only main producers (49 oil/gas, 34 coal) and no zeros, so filling 2018 NaN → 0 would wrongly turn ~50 producers (Bahrain, Equatorial Guinea, Timor-Leste, …) into non-producers | Producer features come from **2016** (last year with full coverage) or the **2000–2016 mean**. 2017+ producer values are never filled. §1, §3, §4.4 |
| 2 | Using the archetype as a feature in RF v2 leaks the target: archetypes are clustered on CLR mix and `d_carbon_int`, and carbon intensity is computed from the mix | Archetype and every mix- or carbon-derived feature are **removed from RF v2**. §6.4 |
| 3 | Archetypes and trajectory features used 2019–2021 data, but they then define the groups for the 2019–2021 forecast and feed a 2018 target (future leakage) | Two trajectory tables: **descriptive** (up to 2021, for visuals and archetypes) and **pre-2019** (2000–2018 only, for the forecast and RF v2). §5, §6.4, §6.5 |
| 4 | RF is invariant to log transforms, and income tiers come from `gdp_pc` (already a feature), so RF v2 would gain nothing | RF v2 adds **genuinely new history features** (growth rates, decoupling, producer history, energy intensity, small-state flag). The report must state that logs do not help trees. §6.4 |
| 5 | CAGR exponent was 1/18, but the 3-year mean endpoints are centred on 2001 and 2017 | Exponent is now **1/16**. §5 |
| 6 | CLR parts sum to 0, so a full-covariance Gaussian mixture is singular | GMM uses `covariance_type="diag"`. §6.3 |
| 7 | Summing countries whose coverage changes over the years creates artificial jumps. The global series is autocorrelated, so the plain Mann-Kendall test overstates significance | Global totals use a **balanced panel**. Trend tests use the **Hamed–Rao modified Mann-Kendall** plus Sen's slope. §4.1, §4.2 |
| 8 | "Snapshot hides change" (I1-3) was a method choice, not an inference from data | New figure `iter1_change_2000_2018.png` provides the evidence. §4.1, §4.5 |
| 9 | Clustering on GDP-based features covers about 163 countries, not 200, so silhouette scores were not comparable across iterations | The iteration 1 vs 2 comparison is run on **the same country set**. §6.3 |
| 10 | World Bank income/region file referenced | Removed. **Income tiers are derived from the dataset** (gdp_pc quartiles, 2000–2002 baseline). The region chart becomes an income-tier chart |
| 11 | `~startswith("OWID")` filter does nothing: aggregates simply have no `iso_code`. Kosovo has no ISO code either | Filter is `iso_code.notna()`. The Kosovo exclusion is documented |
| 12 | `pymannkendall`, `graphviz`, `plotly`, `kaleido` are not installed | Mann-Kendall is implemented with scipy, the workflow diagram uses matplotlib, and only plotly + kaleido are added (choropleths) |
| 13 | Timeline ran to Nov 29 | Compressed: submit **Nov 27**. Nov 28–29 is buffer only |
| 14 | Team size and A1 report | Team split marked "adjust to actual team". A1 report must be supplied for the appendix |

---

## 0. Research question (the data story)

> **How are the world's countries moving through the energy transition, and does getting
> richer still mean using more energy and running a dirtier electricity grid?**

- **Iteration 1** studies a single-year snapshot (2018) of the raw data. It finds problems:
  skew, outliers, compositional shares, a static view that hides change, and missing context.
- **The feedback loop** reshapes the data from country-year snapshots into country
  **trajectories**. It applies log and CLR transforms, flags micro-states, and derives income
  tiers and history features from the dataset itself.
- **Iteration 2** finds **transition archetypes**, quantifies **energy–GDP decoupling**,
  re-models with history features, and checks a forecast against real 2019–2021 data.

> The "expected findings" below are **hypotheses**. Every inference in the report must come
> from the actual outputs. If the data says otherwise, report what the data says.

---

## 1. Known facts about the dataset (verified against the CSV on Nov 21)

| Fact | Consequence |
|---|---|
| 22,012 rows × 129 cols, years 1900–2022 | Country-year panel |
| 306 entities. **219 have an `iso_code`**. Every aggregate (World, regions, income groups, "(EI)", "(EIA)", "(Ember)", "(Shift)", USSR, …) has **no** `iso_code`. No code starts with "OWID" | Keep `iso_code.notna()` to **drop aggregates** and avoid double counting. **Kosovo** (real, but no ISO code) is dropped too, so document it |
| Electricity-mix columns (`*_share_elec`, `carbon_intensity_elec`, `greenhouse_gas_emissions`) cover ~205 countries for **2000–2021** | Main window = **2000–2021** |
| `gdp` ends in **2018** (165 countries in 2018, ~163 with a 2000–2002 baseline). It is PPP-based (OWID/Maddison) | GDP-based analysis uses 2000–2018. 2019–2021 is the **forecast test period** |
| `energy_per_gdp` also ends in 2018 (165 countries) | Same window as GDP |
| **Producer columns** (`oil/gas/coal_prod_per_capita`): ~216 countries **with explicit 0s** up to **2016**. From **2017** only 49 (oil, gas) / 34 (coal) main producers, no zeros. ~50 countries with real production in 2016 become NaN in 2017 | **Never fill 2017+ producer NaN with 0.** Use the 2016 value or the 2000–2016 mean |
| `fossil_share_energy` / `renewables_share_energy` cover only ~68 countries | **Do not use.** Use electricity shares instead |
| 2022 covers only about half the countries | **Drop 2022** |
| The 8 mix shares sum to 100 (range 99.95–100.41, 2000–2021) | Compositional data, so CLR applies |
| **Partial mix rows** (found in Phase 1): 7 countries (Chile, Indonesia, Iran pre-2011, Kazakhstan, Malaysia, Saudi Arabia, Vietnam) leave an unused source blank (nuclear; hydro for Saudi Arabia) instead of 0. **Chile's** per-source TWh exceed its total generation, so its shares sum to 103–112% | **Mix closure** (`prep.close_mix_shares`): a blank share and its TWh are set to 0 only if the other shares already cover the grid and the TWh is also blank (153 cells). Rows off by > 0.5 pp are rescaled to 100 (Chile's 22 rows). `low_carbon_share_elec` is recomputed (Chile changes by up to 6.5 pp). Carbon intensity is untouched |
| Clean panel (after the coverage rule) | **205 countries**, 4,490 rows. Balanced panel **201 countries**. 2018 snapshot: K-means set 205, RF set 165. **Iteration 2 common set: 162** (`results/iter2_country_set.csv`; 43 excluded, 41 of them for a missing 2000–02 or 2016–18 GDP endpoint; 10 small states remain in the set) |
| `low_carbon_share_elec` = nuclear + hydro + solar + wind + other renewables (verified) | Redundant with the mix; note this when both are used |
| `carbon_intensity_elec` is computed from the mix | **Mix shares and anything derived from them are banned as RF features** |
| No duplicate (country, year) | — |
| **No internal gaps** in 2000–2021 (verified in Phase 1). All 8,075 missing cells in the core columns are structural: the country never reports the column (6,218), the series ends early (1,791, mostly GDP after 2018) or starts late (66) | Within-country interpolation fills **0 cells**, and filling more would mean extrapolating. The coverage rule and the analysis windows handle missingness, not imputation |
| The 219 ISO-coded entities include territories (Bermuda, Gibraltar, …) and entities with no grid data (Antarctica, Netherlands Antilles, Micronesia, N. Mariana Islands, Tuvalu) | The coverage rule (Phase 1, step 21) must remove the no-data entities. Verify this |
| Many derived columns (`*_change_twh`, `*_change_pct`, …) | Keep a core set only (below) |
| `greenhouse_gas_emissions` = electricity-sector emissions, in MtCO2e | `ghg_pc = greenhouse_gas_emissions * 1e6 / population` (tonnes/person) |

### Core columns
```
ID:        country, iso_code, year, population
Derived:   gdp_pc = gdp / population, ghg_pc
Intensive: energy_per_capita (kWh), per_capita_electricity (kWh), carbon_intensity_elec (gCO2/kWh), energy_per_gdp (kWh/$)
Mix (8):   coal_share_elec, gas_share_elec, oil_share_elec, nuclear_share_elec,
           hydro_share_elec, solar_share_elec, wind_share_elec, other_renewables_share_elec
Summary:   low_carbon_share_elec
TWh:       electricity_generation, coal/gas/oil/nuclear/hydro/solar/wind/other_renewable_electricity, low_carbon_electricity
Producer:  oil_prod_per_capita, gas_prod_per_capita, coal_prod_per_capita  (use 2016 / 2000–2016 mean only)
```

---

## 2. Project layout

```
assignment-3/
  CLAUDE.md                      # binding rules from the PDF
  A3_PLAN.md                     # this file
  requirements.txt
  data/raw/World Energy Consumption.csv     # moved here in Phase 1
  data/processed/                # panel_clean.csv, snapshot_2018.csv, trajectories*.csv, ...
  notebooks/A3_workflow.ipynb    # single notebook, one section per phase
  src/                           # helpers (prep.py, features.py, stats.py, plots.py)
  images/                        # every figure: iter1_*.png / loop_*.png / iter2_*.png / workflow.png
  results/                       # metrics JSON/CSV, inferences.md, figures.csv
  report/                        # A3_report.md → .docx, workflow.png, viva_qa.md, A1 appendix
  video/                         # A3_slides.pptx + script.md
```

**Environment:** Python 3.13. All versions are pinned in `requirements.txt`. `plotly`, `kaleido`
(choropleths; Chrome present and export tested), `python-docx` (report export) and `ruff`
(lint) were installed on Nov 21 with the user's approval. `pyproject.toml` holds the ruff and
pytest settings. The Mann-Kendall test (Hamed–Rao) and Sen's slope are
implemented in `src/stats.py` using scipy, so `pymannkendall` is not needed. The workflow
diagram is drawn with matplotlib, so `graphviz` is not needed. Fix `random_state=42` everywhere.

**Figure rules:**
- 150+ dpi PNG.
- A title, and axis labels with units.
- Colour-blind-safe palette.
- Log axes labelled as log.
- Source note "Data: Our World in Data".
- Every figure is saved to `images/` **and** listed in `results/figures.csv` (filename, phase,
  what it shows, inference it supports).

**Inference log:** `results/inferences.md`. Each entry has:
- an ID (I1-1, I2-3, …);
- the statement;
- the evidence (figure + number);
- whether it triggers the feedback loop.

---

## 3. Phase 1: Data preparation (beyond A1)

1. Move the CSV to `data/raw/`. Load it and print shape, dtypes and year range.
2. Keep real countries only: `iso_code.notna()`. Save the list of dropped entities
   (aggregates + Kosovo) to `results/dropped_entities.csv`.
3. Keep `2000 <= year <= 2021`.
4. Create `gdp_pc` and `ghg_pc`.
5. Missingness:
   - Heatmap of the missing share per core column per year → `images/iter1_missingness_heatmap.png`.
     It must make the 2017 break in the producer columns visible.
   - **Producer columns:** do **not** fill 2017+ NaN. Build per-country producer features:
     - `oil/gas/coal_prod_pc_2016` (2016 value; 2016 records non-producers as explicit 0);
     - `oil/gas/coal_prod_pc_mean_00_16` (2000–2016 mean).

     Save them to `data/processed/producers.csv`. Log the number of countries whose producer
     value disappears in 2017.
   - **Within-country, time-only** linear interpolation, `limit=3` gaps. Never fill across
     countries and never extrapolate beyond a country's last observed year.
   - Drop countries missing more than 30% of the core electricity columns in the window.
     Log how many were dropped.
6. Sanity checks:
   - the mix shares sum to about 100 (report the distribution of the sum);
   - no negative values;
   - no duplicate (country, year).
7. **Balanced panel:** the list of countries with `electricity_generation` and all 8 mix shares
   present in **every** year 2000–2021. Save it to `data/processed/balanced_countries.csv`.
   Global totals use it.
8. Save `data/processed/panel_clean.csv` and a 2018 snapshot `data/processed/snapshot_2018.csv`
   (with the 2016 producer features joined).

**Done when:**
- the clean panel exists;
- the counts of countries, years and rows are printed and logged;
- the balanced-panel size is logged;
- the missingness figure is saved.

---

## 4. Phase 2: Iteration 1, snapshot analysis on raw scales

### 4.1 Visualizations
| File | Chart | Purpose |
|---|---|---|
| `iter1_global_mix_area.png` | Stacked area: electricity generation by source (TWh), 2000–2021, summed over the **balanced panel**. Cross-check against the OWID "World" row (used only for the check, never in the analysis) | Global trend |
| `iter1_distributions.png` | Histograms of energy_per_capita, gdp_pc, carbon_intensity_elec, per_capita_electricity | Show skew |
| `iter1_gdp_vs_energy_linear.png` | Scatter gdp_pc vs energy_per_capita (linear axes), bubble = population, top-10 labelled | Outliers dominate |
| `iter1_corr_pearson_vs_spearman.png` | Two heatmaps side by side | Nonlinearity/outliers |
| `iter1_lowcarbon_choropleth_2018.png` | Choropleth of low_carbon_share_elec | Spatial view |
| `iter1_change_2000_2018.png` | (a) Histogram of each country's change in low-carbon share, 2000–2002 → 2016–2018. (b) Rank-vs-rank scatter of 2000 vs 2018 low-carbon share, with Spearman ρ. Countries that move far are labelled | **Evidence for I1-3**: how much change a single snapshot hides |

### 4.2 Statistics
- Pearson and Spearman correlation (with p-values) between gdp_pc and energy_per_capita, 2018.
- **Hamed–Rao modified Mann-Kendall** trend test (corrects for autocorrelation) on the global
  low-carbon share = Σ low_carbon_electricity / Σ electricity_generation over the balanced
  panel, 2000–2021. Report the trend, p (original and modified) and Sen's slope (pp/yr) via
  `scipy.stats.theilslopes`.
- OLS energy_per_capita ~ gdp_pc (raw). Residual-vs-fitted plot → `iter1_ols_residuals.png`.
  Breusch-Pagan test for heteroscedasticity.

### 4.3 Unsupervised: K-means on the 2018 snapshot
- Features: the 8 mix shares + energy_per_capita + per_capita_electricity + carbon_intensity_elec,
  StandardScaler only (no log, no CLR; this is the naive baseline). About 200 countries.
- k = 2..8: elbow + silhouette → `iter1_kmeans_k_selection.png`.
- PCA biplot coloured by cluster → `iter1_kmeans_pca.png`. Cluster map → `iter1_kmeans_map.png`.
- Table of cluster sizes and centroids → `results/iter1_clusters.csv`.
- Also compute the iteration 1 silhouette **on the ~163-country set used in iteration 2**, so
  the comparison in §6.3 is fair.
- *Hypothesis:* clusters are driven by scale and outliers (a tiny cluster of high-consumption
  small states) and do not read as transition types.

### 4.4 Supervised: Random Forest, does being a fossil producer predict a dirty grid?
- Target: `carbon_intensity_elec` (2018).
- Features: gdp_pc, energy_per_capita, per_capita_electricity, population (all 2018), plus
  `oil/gas/coal_prod_pc_2016`.
  - **Why 2016:** after 2016 the source drops non-producers *and* ~50 smaller producers, so
    2018 producer data is unusable. State this in the report.
- **Do not use the mix shares.** Carbon intensity is calculated from them (leakage). State
  this in the report.
- Rows: countries with all features present (~165). **Save the exact country list**, because
  RF v2 must use the same rows.
- 5-fold CV (shuffle, rs=42). **Save the fold assignment** for reuse in RF v2. Report R², MAE
  and RMSE (mean ± sd) → `results/iter1_rf_metrics.json`.
- Predicted vs actual → `iter1_rf_pred_vs_actual.png`.
- Feature importance (permutation) → `iter1_rf_importance.png`.
- Top-15 absolute errors table with country names → `results/iter1_rf_errors.csv`.
- Residual choropleth → `iter1_rf_residual_map.png` (do errors cluster in space?).
- *Hypothesis:* moderate R². The biggest errors are hydro- or nuclear-heavy countries and
  small states.

### 4.5 Iteration 1 inferences (write to `results/inferences.md`)
Expected themes, each to be confirmed with numbers:
- **I1-1** Raw scales are heavily skewed. A few small producer states dominate
  (`iter1_distributions.png`, `iter1_gdp_vs_energy_linear.png`, Breusch-Pagan p).
- **I1-2** The mix shares are compositional (they sum to ~100), so Euclidean K-means on them is
  misleading (`iter1_kmeans_pca.png`, silhouette, cluster sizes).
- **I1-3** A single-year snapshot hides large change over time (`iter1_change_2000_2018.png`:
  spread of the changes, how far ranks move, plus the Mann-Kendall trend).
- **I1-4** Model errors are concentrated in particular kinds of countries. Single-year features
  lack context such as income level, growth history, producer history and country size
  (`iter1_rf_errors.csv`, `iter1_rf_residual_map.png`).

**Done when:** all iteration 1 figures, metrics and inferences exist, and each inference
cites a figure and a number.

---

## 5. Phase 3: Feedback loop, the significant transformation

Each inference maps to a transformation. Document this table in the report.

| Inference | Transformation |
|---|---|
| I1-1 skew/outliers | `log1p` on energy_per_capita, per_capita_electricity, gdp_pc, energy_per_gdp, ghg_pc. Flag `small_state = population < 1M`; analyse small states separately and never delete them silently. *(Logs help OLS and K-means. Random Forests are invariant to monotone transforms; say so.)* |
| I1-2 compositional | **CLR transform** of the 8 mix shares: `clr(x) = log(x+ε) − mean(log(x+ε))`, ε = 0.1 (pp). Report sensitivity to ε (0.01 vs 0.1 vs 1) on the silhouette |
| I1-3 static | **Reshape the panel (country-year) into trajectories (one row per country)**, features below |
| I1-4 missing context | **Derive income tiers from the dataset:** quartiles of each country's mean gdp_pc over 2000–2002 → Low / Lower-middle / Upper-middle / High (data-derived, *not* World Bank groups). Save the thresholds. Add history features (growth, decoupling, producer history) |

### Trajectory features (one row per country), two tables
Endpoints use **3-year means** to avoid one noisy endpoint year.

| Feature | Definition | `trajectories.csv` (descriptive) | `trajectories_pre2019.csv` (forecast/RF) |
|---|---|---|---|
| cagr_gdp_pc | (mean 2016–18 / mean 2000–02)^(1/16) − 1, since the mid-points are 2001 → 2017 | ✓ | ✓ |
| cagr_energy_pc | same formula on energy_per_capita | ✓ | ✓ |
| decoupling | cagr_gdp_pc − cagr_energy_pc (> 0 means GDP grew faster than energy use: **relative** decoupling; **absolute** decoupling also needs cagr_energy_pc < 0) | ✓ | ✓ |
| d_lowcarbon | low_carbon_share_elec change from the 2000–02 mean | to 2019–21 mean | to 2016–18 mean |
| d_coal | coal_share_elec change, same endpoints | ✓ | ✓ |
| d_solarwind | (solar+wind)_share_elec change, same endpoints | ✓ | ✓ |
| d_carbon_int | carbon_intensity_elec change, same endpoints | ✓ | ✓ |
| lowcarbon_slope | OLS slope of low_carbon_share_elec (pp/yr) | 2000–2021 | 2000–2018 |
| lowcarbon_2000 | 2000–02 mean | ✓ | ✓ |
| log_energy_pc_2018 | level (log1p) | ✓ | ✓ |
| log_energy_per_gdp_2018 | level (log1p) | ✓ | ✓ |
| prod_*_mean_00_16 | oil/gas/coal producer history (log1p) | ✓ | ✓ |
| clr_* (8) | CLR of the mix | 2018 | 2018 |
| income_tier, small_state | flags | ✓ | ✓ |

- **Why two tables:** the descriptive table (up to 2021) is for the iteration 2 visuals and
  archetypes. The pre-2019 table uses **no data after 2018**, so the 2019–2021 forecast and
  RF v2 cannot see the future.
- **Coverage:** GDP-based features need a 2000–02 GDP baseline, so about 163 countries remain.
  Log the exact n and list the excluded countries.

### Outputs
- `data/processed/trajectories.csv`, `data/processed/trajectories_pre2019.csv`,
  `results/income_tier_thresholds.csv`
- `loop_before_after_table.png` (or a markdown table): rows, columns and unit of analysis,
  before vs after.
- `loop_skew_before_after.png`: histograms of 2–3 variables, raw vs log.
- `loop_clr_before_after.png`: one country pair or the PCA of raw shares vs CLR.

**Done when:** both trajectory tables exist, the transformation table is in
`results/inferences.md`, and the before/after visuals are saved.

---

## 6. Phase 4: Iteration 2, transition archetypes

### 6.1 Visualizations
| File | Chart |
|---|---|
| `iter2_decoupling_quadrant.png` | x = cagr_gdp_pc, y = cagr_energy_pc, 45° line + zero lines, colour = income tier, small states as hollow markers, key countries labelled |
| `iter2_loglog_gdp_energy.png` | log gdp_pc vs log energy_pc (2018) + OLS line, annotated with the slope (income elasticity) and R² |
| `iter2_slope_lowcarbon_by_income.png` | Slope chart of low-carbon share 2000 → 2021, income-tier medians |
| `iter2_archetype_map.png` | Choropleth of archetypes |
| `iter2_archetype_small_multiples.png` | low_carbon_share_elec over time per archetype (median line + IQR band) |
| `iter2_archetype_profiles.png` | Heatmap of standardised centroid values per archetype |

### 6.2 Statistics
- Log-log OLS: elasticity of energy with respect to GDP per capita, with 95% CI (HC3 robust
  SE). Re-run Breusch-Pagan and report whatever it shows.
- Kruskal-Wallis: does `decoupling` differ across income tiers? Post-hoc pairwise Mann-Whitney
  with Holm correction.
  - *Caveat:* tiers are defined from baseline gdp_pc and decoupling uses gdp_pc growth.
    Mention regression to the mean as a limitation.
- Hamed–Rao Mann-Kendall + Sen's slope per archetype on the median low-carbon share.

### 6.3 Unsupervised: clustering trajectories (descriptive archetypes)
- Features: the descriptive trajectory features + CLR mix (standardised). Exclude small states
  from fitting, then assign them to the nearest centroid afterwards.
- K-means and Gaussian Mixture (**`covariance_type="diag"`**, because CLR parts sum to 0 and a
  full covariance is singular), k = 3..7. Choose by silhouette + BIC + interpretability →
  `iter2_k_selection.png`.
- Compare silhouette with iteration 1 **on the same country set** →
  `iter2_vs_iter1_silhouette.png`. Note that silhouette depends on the feature space, so
  interpret the comparison alongside cluster interpretability, not on its own.
- Stability: re-run with 20 seeds and report the Adjusted Rand Index.
- Name the archetypes from their centroids, e.g. "Legacy clean (hydro/nuclear)",
  "Fast wind/solar adopters", "Coal-locked growers", "Fossil producers",
  "Low-energy developing". **Names must match the data.**

### 6.4 Supervised v2: Random Forest with history features
- Same target (2018 `carbon_intensity_elec`), **same countries and same CV folds** as iteration 1.
- Features = iteration 1 features + new **leak-free** history features from
  `trajectories_pre2019.csv`:
  - cagr_gdp_pc, cagr_energy_pc, decoupling;
  - prod_*_mean_00_16;
  - log_energy_per_gdp_2018;
  - small_state;
  - income_tier.
- **Banned (leakage):**
  - mix shares and CLR;
  - low_carbon_*, d_lowcarbon, d_coal, d_solarwind, d_carbon_int, lowcarbon_slope;
  - **archetype** (clustered on the mix).
- In the report, state honestly that the log transform does not change RF results. Any gain
  must come from the new features. If there is no gain, report that and explain it.
- Bar chart of R²/MAE, iteration 1 vs iteration 2 → `iter2_rf_improvement.png`.
- SHAP summary → `iter2_shap_summary.png`.

### 6.5 Forecast checked against reality
- **Forecast groups must not use 2019–2021 data:** re-fit the chosen clustering (same k, same
  method) on `trajectories_pre2019.csv` features. Report the ARI agreement with the
  descriptive archetypes.
- For each pre-2019 group's median low_carbon_share_elec: fit Holt's linear trend (and/or
  ARIMA(1,1,0)) on 2000–2018, forecast 2019–2021, and compare with actuals (MAE, MAPE).
  Include a naive baseline (last value carried forward).
- Plot → `iter2_forecast_vs_actual.png`. Note the 2020 COVID demand shock.
- **Time-based split only.** Explain why a random split would leak the future.

### 6.6 Final knowledge (write to `results/inferences.md`)
Answer each question with numbers:
- **I2-1** Is energy use decoupling from GDP (relative or absolute)? In which income tiers?
- **I2-2** What is the income elasticity of energy, and how does it compare with the raw-scale view?
- **I2-3** Which archetypes exist, and which is decarbonising fastest?
- **I2-4** Are fossil producers stuck with carbon-intensive grids?
- **I2-5** How did the model change after the feedback loop, and why (or why not)?
- **I2-6** How good were the 2019–2021 forecasts against the naive baseline, and what did COVID do?

---

## 7. Phase 5: Workflow diagram, report, video

### 7.1 Workflow diagram (unrolled) → `images/workflow.png` and `report/workflow.png`
- Drawn with **matplotlib**.
- Colour-coded by diamond stage (Data / Visualization / Model / Knowledge).
- Two rows (Iteration 1, Iteration 2), joined by an edge labelled exactly **"Feedback loop"**
  that lists the transformations.
- Minimal self-loops.
```
ITERATION 1
[Raw OWID] → [Drop aggregates, 2000–2021, interpolate, producer 2016] → [Viz: distributions, scatter, corr, change]
 → [Stats: Spearman, Mann-Kendall, OLS] → [K-means 2018] → [Viz: PCA, map]
 → [RF carbon intensity] → [Viz: errors, residual map] → [Inferences I1-1..4]
                         │  Feedback loop: log + CLR, panel→trajectories, income tiers + history features
                         ↓
ITERATION 2
[Trajectory data] → [Viz: decoupling, log-log] → [K-means/GMM archetypes] → [Viz: map, small multiples]
 → [RF v2 + SHAP] → [Holt/ARIMA forecast vs 2019–21] → [Knowledge I2-1..6]
```

### 7.2 Report (`report/A3_report.md`, exported to .docx at the end)
1. Introduction and research question
2. Dataset (refer to the A1 exploration). State that **no supplementary data** was used and why
3. Visual analytics workflow (diagram + rationale for each module)
4. Data handling (Phase 1, including the 2017 producer-coverage break)
5. Iteration 1: visualizations, methods, inferences
6. Feedback loop: inference → transformation table, before/after
7. Iteration 2: visualizations, methods, results
8. Discussion: answers to the research question. Limitations:
   - GDP ends in 2018;
   - OWID interpolation;
   - producer data break after 2016;
   - compositional caveats and ε choice;
   - income tiers are data-derived, not official;
   - regression to the mean;
   - small n (~163–200 countries).
9. Conclusion
10. References: Keim et al. 2008; the OWID energy dataset; Aitchison 1986 (CLR); Hamed & Rao
    1998 (modified Mann-Kendall); Sen 1968 (Sen's slope); scikit-learn; statsmodels; SHAP
    (Lundberg & Lee 2017)
11. Appendix: A1 report (**file still needed from the team**)

Each figure gets a number, a caption and a sentence on **why this chart type was chosen**.

### 7.3 Video (6–8 min), slides in `video/A3_slides.pptx`
- A real PowerPoint deck is required (the rubric rewards it).
- Story: question → raw-data problems → feedback loop → archetypes and decoupling → model and
  forecast → takeaways.
- Write `video/script.md` with timings and who speaks each part (every member speaks).

---

## 8. Timeline (soft deadline Nov 27)

| Date | Work |
|---|---|
| Nov 21 | Set up the layout, requirements.txt, split roles. Phase 1 |
| Nov 22 | Phase 2 |
| Nov 23 | Phase 3 |
| Nov 24 | Phase 4 |
| Nov 25 | Phase 5: diagram + report draft |
| Nov 26 | Slides + video. Check the images folder against figures.csv |
| Nov 27 | Final checklist (CLAUDE.md §5). **Submit** |
| Nov 28–29 | Buffer only (hard deadline Nov 29, 11:59 pm IST) |
| Nov 30+ | Viva rehearsal. Every member attends the viva |

## 9. Team split (3 people, confirmed Nov 21)
Every member must still be able to explain every module in the viva (marks are individual).
- **A: Data and feedback loop.** Phase 1 (including the producer-coverage fix), the feedback
  loop (log, CLR, trajectories, income tiers) and the 2019–2021 forecast.
- **B: Statistics and clustering.** Mann-Kendall, OLS/log-log elasticity, decoupling and
  Kruskal-Wallis, both clustering rounds, archetype naming and maps.
- **C: Supervised models and delivery.** Both RF models, SHAP, the workflow diagram, report
  assembly, slides and the video edit.

## 10. Viva prep (`report/viva_qa.md`)
- Why drop aggregates? Why was Kosovo dropped?
- Why CLR, and why ε = 0.1?
- Why no mix shares and no archetype in the RF (leakage)?
- Why producer features from 2016?
- Why does a log transform not change a Random Forest?
- Why stop GDP at 2018?
- Why two trajectory tables (descriptive vs pre-2019)?
- How was k chosen? Why a diagonal-covariance GMM? Did the iteration 2 clusters improve, and
  how was that compared fairly?
- What does decoupling > 0 mean, and what is relative vs absolute decoupling?
- Why Hamed–Rao instead of the plain Mann-Kendall test?
- Why a time-based split for the forecast? What did COVID do to 2020?
- Limitations?
