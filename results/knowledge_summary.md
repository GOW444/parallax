# Knowledge summary

_Generated from `results/` by `src/knowledge.py`. Do not edit by hand._

**Research question.** How are the world's countries moving through the energy transition, and does getting richer still mean using more energy and running a dirtier electricity grid?

## Does getting richer still mean using more energy?

Across countries, richer still means more energy: the Spearman correlation between GDP and energy use per person is 0.95 (n = 165), and the log-log elasticity is 1.20 (95% CI 1.13-1.27), explaining R² = 0.90 against 0.72 for the raw fit. An elasticity above one and decoupling over time are different comparisons (between countries vs along each country's path), so they do not conflict. Neither is a causal effect of income.

Over time, energy use is decoupling from income: of 162 countries, 46 decoupled absolutely (GDP per person up, energy per person down) and 75 relatively. It is strongest in the High tier (29 of 41 absolute) and weakest in the Low tier (only 5 of 41; Kruskal-Wallis p = 8.3e-05).

## Does it mean running a dirtier electricity grid?

Richer does not clearly mean a dirtier grid. Income, energy use and fossil production predict 2018 grid carbon intensity only weakly (cross-validated R² 0.02); adding growth and decoupling history changed the mean absolute error from 166 to 171 gCO2/kWh (mean predictor 178), within fold noise. Fossil producers (45 countries) are not significantly dirtier than the rest (median 490 vs 443 gCO2/kWh, p = 0.44). What sets a grid's carbon intensity is its mix, which cannot be used as a predictor without leakage.

## How are countries moving through the transition?

The global low-carbon share shows no significant trend (Hamed-Rao p = 0.58, Sen slope +0.09 pp/yr), but 69 of 201 countries moved by more than 10 pp (42 up, 27 down). Clustering the country paths gives 5 archetypes: Gas grids, low-carbon share flat (n = 45, +0.03 pp/yr); Hydro grids, low-carbon share flat (n = 43, +0.14 pp/yr); Oil grids, low-carbon share rising (n = 30, +0.62 pp/yr); Coal grids, low-carbon share rising (n = 25, +1.37 pp/yr); Hydro grids, low-carbon share falling (n = 19, -1.36 pp/yr). They are reproducible (mean ARI 0.82 over 20 seeds) but weakly separated (silhouette 0.14): a partition of a continuum, not natural types.

## Forecast check, 2019-2021

Trained on 2000-2018 and tested on 2019-2021, the best method by mean MAE is holt_damped (2.02 pp) against 2.47 pp for the naive last value. Total generation of the balanced panel changed -0.3% in 2020.

## Plan hypotheses the data did not support

- **I1-1**: The dominating countries are small states. Rule: most of the 4 largest OLS residuals have population < 1 M. Found: 1 of 4 (Iceland).
- **I1-1**: The dominating countries are fossil producers. Rule: most of the 4 largest OLS residuals produced oil, gas or coal in 2016. Found: 2 of 4 (Trinidad and Tobago, Bahrain).
- **I1-2**: Clusters are driven by scale. Rule: most clusters are defined by energy or electricity per person. Found: 1 of 8 clusters.
- **I1-2**: There is a tiny cluster of high-consumption small states. Rule: the smallest cluster is defined by scale and most members have population < 1 M. Found: smallest = 'high Solar share' (n = 8), 4 of 8 small states.
- **I1-3**: The typical country's low-carbon share changed a lot. Rule: |median change| > 10 pp. Found: median +0.6 pp.
- **I1-4**: The Random Forest reaches a moderate R-squared. Rule: cross-validated mean R-squared >= 0.3. Found: R-squared 0.02 +/- 0.10.
- **I1-4**: Small states have bigger errors. Rule: small states have the larger median |error| and Kruskal-Wallis p < 0.05. Found: small state 123 vs other 146 gCO2/kWh; p = 0.633.
- **I2-1**: Each richer tier decouples more than the one below it. Rule: every adjacent pair of tiers differs (Holm-corrected p < 0.05). Found: 1 of 3 adjacent pairs differ.
- **I2-2**: The log-log fit is homoscedastic. Rule: Breusch-Pagan p >= 0.05. Found: p = 0.040.
- **I2-3**: The iteration 2 clusters are better separated than iteration 1's. Rule: silhouette in the iteration 2 space > silhouette of the iteration 1 space at the same k = 5 and the same countries. Found: 0.28 (iteration 1) vs 0.14 (iteration 2).
- **I2-4**: Fossil producers have dirtier grids. Rule: producers' median carbon intensity is higher and Mann-Whitney p < 0.05. Found: median 490 vs 443 gCO2/kWh, p = 0.44.
- **I2-5**: The history features improve the Random Forest. Rule: v2 has the lower MAE in at least 4 of 5 paired folds and a negative mean paired change. Found: better in 1 of 5, mean change +4.4 gCO2/kWh.
- **I2-6**: Holt linear trend beats the naive last value. Rule: mean MAE over the pre-2019 groups < naive mean MAE. Found: 2.63 vs 2.47 pp.

## Limits on these answers

- GDP ends in 2018, so every income-based result stops there; 164 of 205 countries have the GDP endpoints needed and 162 are in the iteration 2 set.
- Producer data break after 2016; producer features use 2000-2016 only.
- 5 cross-validation folds are too few to test the Random Forest difference formally.
- Income tiers are data-derived quartiles of 2000-02 GDP per person, and the growth measured from that baseline invites regression to the mean.
- All results are associations between countries or over time; none is causal.
