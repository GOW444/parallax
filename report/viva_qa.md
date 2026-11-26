# Viva Q&A (every member should be able to answer all of these)

Numbers live in `results/` and `results/inferences.md`; quote them from there.

## Data handling
**Why drop rows without an ISO code?**
They are aggregates (World, continents, income groups, "(EI)/(Ember)" regions). Keeping them
would double count every country. Kosovo is a real country without an ISO code in this file.
It is dropped, and this is documented in `results/data_notes.md`.

**Why 2000–2021?**
The electricity mix is dense only from 2000, and 2022 covers about half of the countries.
GDP ends in 2018, so income-based analysis stops at 2018.

**How did you treat missing values?**
Linear interpolation only within a country, along time, and at most 3 years. Never across
countries. In practice it filled 0 cells: all missingness is structural (a series never
reported or ending early). A coverage rule then drops countries missing more than 30% of
grid data.

**Why producer features from 2016?**
From 2017 the file lists only main producers. Producers that are blank in 2017 are missing,
not zero, so producer features use 2000–16 only.

## Feedback loop
**What makes the transformation "significant"?**
The unit of analysis changes from a country in one year to a country's path over
2000–2018. Thousands of country-year rows become one row per country. The new columns are
built from many years (growth, decoupling, changes, slopes). On top of that, the scale
changes (log) and the geometry of the mix changes (CLR).

**What triggered it?**
Four inferences:
- I1-1, skew → log;
- I1-2, compositional shares → CLR;
- I1-3, a snapshot hides change → trajectories;
- I1-4, the RF lacks context → tiers and history.

See Table 3 in the report.

**Why CLR, and why ε = 0.1?**
Shares sum to 100. Raw-percentage distances overweight big sources, and correlations are
partly forced by the constant sum (Aitchison 1986). CLR compares log-ratios. ε handles zero
shares; we checked ε = 0.01, 0.1 and 1 (`results/loop_clr_eps.csv`).

**Why two trajectory tables?**
- The descriptive table uses endpoints up to 2019–21, for the charts.
- The model table uses nothing after 2018, so the RF v2 and the 2019–21 forecast cannot see
  the future. Its builder raises an error if given later years.

## Statistics
**Why Hamed–Rao Mann-Kendall?**
Yearly series are autocorrelated, which makes the plain test over-confident. Hamed–Rao
inflates the variance to correct for this.

**What is decoupling?**
GDP growth minus energy growth (per person, CAGR).
- Absolute decoupling: GDP up, energy down.
- Relative decoupling: both up, energy slower.

**Elasticity > 1 but rich countries decouple: a contradiction?**
No.
- The elasticity compares countries in 2018 (cross-section).
- Decoupling follows each country over time.

They answer different questions, and neither is causal.

**Why Kruskal-Wallis and Holm?**
Rank-based tests don't assume normality and are not driven by outliers. Holm controls
false positives over the 6 pairwise comparisons.

**Regression to the mean?**
Tiers come from 2000–02 GDP, and growth is measured from the same baseline. A country with
an unusually low baseline lands in a low tier and also shows extra growth.

## Unsupervised
**How was k chosen?**
By a rule fixed before fitting: the highest silhouette among the k whose every cluster has
at least 5 countries. GMM is chosen only if its BIC-best k beats K-means on silhouette.

**Why a diagonal GMM?**
Full covariance in 17 dimensions with about 150 countries has too many parameters.

**Did clustering improve in iteration 2?**
Not on silhouette. It is lower than iteration 1 on the same countries, and we say so. The
iteration 1 clusters were tighter because they re-labelled the dominant source. The
archetypes differ in the direction of change, which is the research question. They are
stable across seeds (ARI).

**Why leave small states out of the fit?**
A few tiny grids with extreme shares could pull centroids. They are assigned afterwards to
the nearest centroid with the same scaler and flagged `assigned_post_hoc`.

## Supervised
**Why no mix shares or archetypes in the RF?**
Carbon intensity is computed from the mix. Using it would be leakage.
`models.assert_no_leakage` checks feature names before every fit.

**Why does a log transform not change a Random Forest?**
Trees split on thresholds, so only the ordering of values matters. Any v2 change comes from
the new features.

**Did RF v2 improve?**
No reliable gain on the same folds (`results/iter2_rf_comparison.json`). With 5 folds we
don't claim significance. Interpretation: grid cleanliness depends on the mix (resources and
policy), which income and history don't capture.

**Why KFold for the RF but a time split for the forecast?**
The RF rows are countries in one year, so they are exchangeable. The forecast is a time
series, so training must precede testing (train 2000–2018, test 2019–2021, asserted in code).

**What did COVID do?**
See `results/iter2_covid.json` for the 2020 generation change and the sign of the 2020
forecast errors. Three test years cannot separate COVID from trend.

## Workflow and deliverables
**Why "unrolled"?**
The brief asks for the feedback loop to be drawn by repeating the diamond, joined by an
edge labelled "Feedback loop", with minimal self-loops. Ours has none, and one
cross-iteration edge (tested in `tests/test_workflow_diagram.py`).

**Supplementary data?**
None. Only the OWID file is used. Income tiers are data-derived quartiles, not World Bank
groups.
