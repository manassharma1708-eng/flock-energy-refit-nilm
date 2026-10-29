# Results

## 1. Overview

This section summarises:

- washing-machine exploratory analysis across multiple households
- cycle detection results
- cross-house behavioural differences
- model design and baselines
- household-level validation
- final untouched-house evaluation
- failure analysis
- smart-meter resolution sensitivity

The final modelling objective was to estimate washing-machine power from whole-home aggregate electricity demand at one-minute resolution.

---

# 2. Washing-machine exploratory analysis

The official cleaned REFIT dataset was used for washing-machine analysis.

The following households were included:

| House | Washing-machine channel |
|---:|---|
| 2 | Appliance2 |
| 5 | Appliance3 |
| 6 | Appliance2 |
| 15 | Appliance3 |
| 19 | Appliance2 |

The first four households were used for the main EDA and development workflow. House 19 was subsequently added as an untouched final model-evaluation household.

---

## 2.1 Cycle-detection rule

A simple rule-based detector was used to identify washing-machine operating cycles.

A minute was considered active when:

```text
Washing-machine power > 20 W
```

To avoid splitting a single physical wash programme because of short low-power periods:

- inactive gaps of up to 5 minutes inside an event were merged
- events shorter than 15 minutes were discarded
- a detected event had to reach at least 100 W peak power

This rule was intentionally kept simple and interpretable.

It is not intended to reproduce a manufacturer-specific wash programme. Its purpose is to provide a consistent definition of activity across households.

---

# 3. Household availability and cycle summary

For the four development households, the following summary was obtained:

| House | Missing aggregate | Off time | Detected cycles | Median duration | Median energy |
|---:|---:|---:|---:|---:|---:|
| 2 | 24.70% | 96.53% | 345 | 95 min | 0.600 kWh |
| 5 | 13.25% | 94.18% | 800 | 41 min | 0.247 kWh |
| 6 | 15.35% | 98.43% | 136 | 95.5 min | 0.640 kWh |
| 15 | 13.70% | 97.55% | 255 | 90 min | 0.672 kWh |

A total of:

**1,536 washing-machine cycles**

were detected across these four households.

---

## 3.1 Cross-house differences

The detected cycles show substantial differences between households.

Houses 2, 6, and 15 have median cycle durations close to approximately 90–96 minutes and median cycle energy around 0.60–0.67 kWh.

House 5 differs considerably:

- median cycle duration: approximately 41 minutes
- median energy: approximately 0.25 kWh

This demonstrates that washing-machine signatures are not constant across households.

Possible reasons include:

- different appliance models
- different wash programmes
- different load sizes
- user behaviour
- monitoring differences

This variation is important for the modelling task because a model trained on one set of homes may not transfer perfectly to another.

---

# 4. EDA figures

The following plots were generated.

## 4.1 Representative 24-hour trace

File:

```text
figures/washer_24h_trace.png
```

This figure shows household aggregate demand and washing-machine power over a representative 24-hour period.

The washing-machine signal is only one component of total household demand.

During active periods, other appliances may operate simultaneously, which makes the washing-machine contribution difficult to isolate from the aggregate signal.

---

## 4.2 Detected cycles

File:

```text
figures/detected_washer_cycles.png
```

This figure shows example detected washing-machine cycles aligned from cycle start.

The cycle shapes vary substantially.

Some contain large heating-related peaks, while others contain longer low-power stages.

This variation contributes to the difficulty of cross-house disaggregation.

---

## 4.3 Cross-house energy comparison

File:

```text
figures/washer_energy_cross_house.png
```

The distribution of estimated energy per cycle differs significantly between households.

House 5 is particularly different from the other selected homes.

This provides direct evidence that household-level validation is more realistic than random row-level splitting.

---

## 4.4 Cycle starts by hour

File:

```text
figures/washer_cycle_starts_hour.png
```

This figure summarises detected washing-machine cycle starts by hour of day.

The distribution provides a behavioural view of when households typically initiate laundry.

This type of information could potentially support demand-response or off-peak load-shifting applications.

---

## 4.5 Cycle starts by weekday

File:

```text
figures/washer_cycle_starts_weekday.png
```

This figure compares the frequency of detected washing-machine cycle starts across days of the week.

These patterns are useful for understanding behavioural variation but should not be interpreted as universal household behaviour because the sample contains only a small number of UK homes.

---

# 5. Modelling objective

The modelling task was:

```text
Whole-home aggregate electricity demand
                ↓
      Appliance-disaggregation model
                ↓
 Estimated washing-machine power
```

The target was washing-machine power at one-minute resolution.

The model was trained using the official cleaned REFIT data.

---

# 6. Feature engineering

The model uses only information derived from aggregate household power and calendar time.

Features include:

- current aggregate power
- 1-minute aggregate lag
- 2-minute aggregate lag
- 5-minute aggregate lag
- 10-minute aggregate lag
- 3-minute rolling mean
- 5-minute rolling mean
- 15-minute rolling mean
- 5-minute rolling standard deviation
- one-minute power difference
- hour of day
- day of week

All rolling and lag features are based on current or past observations only.

Future measurements are not used.

---

# 7. Model choice

The main model is:

```text
HistGradientBoostingRegressor
```

Gradient boosting was selected because it:

- handles nonlinear relationships
- trains efficiently on large tabular datasets
- works well with engineered time-series features
- does not require GPU resources
- remains easy to explain
- avoids unnecessary deep-learning complexity

The assignment emphasises correct reasoning and validation rather than model complexity.

---

# 8. Baselines

Two simple baselines were included.

## 8.1 Always-off baseline

The first baseline predicts:

```text
Washing-machine power = 0 W
```

for every timestamp.

This is important because the washing machine is inactive for most observations.

A model can therefore achieve deceptively low MAE simply by predicting zero almost everywhere.

---

## 8.2 Hour-of-day profile

The second baseline predicts washing-machine power using the average power associated with each hour of day in the training households.

This provides a simple behavioural baseline without using the aggregate power signature.

---

# 9. Final validation design

The final evaluation used a strict household-level split.

| Role | Houses |
|---|---|
| Training | 2, 5, 15 |
| Validation | 6 |
| Final untouched test | 19 |

This design prevents observations from the same household appearing in both training and final evaluation.

House 19 was not used for:

- model fitting
- feature selection
- hyperparameter selection
- prediction-threshold selection

The model configuration was frozen before evaluating House 19.

This makes House 19 the final estimate of cross-house generalisation.

---

# 10. Prediction-threshold selection

Ground-truth washing-machine activity was defined as:

```text
True washer power > 20 W
```

A separate threshold was used to convert predicted power into predicted on/off state.

The threshold was selected using validation House 6 only.

The following candidate thresholds were evaluated:

```text
10 W
20 W
30 W
40 W
50 W
...
200 W
```

The best validation F1 was obtained at:

**30 W**

with validation F1:

**0.262**

The 30 W threshold was then frozen before final testing on House 19.

---

# 11. Final untouched test — House 19

House 19 contained approximately:

**612,151 usable one-minute observations**

with approximately:

**23,990 active washing-machine minutes**

after feature preparation.

This means washing-machine activity represents only a small proportion of the full timeline.

---

## 11.1 Final test metrics

| Metric | Always off | Hour profile | Gradient boosting |
|---|---:|---:|---:|
| MAE (W) | **5.74** | 23.24 | 10.18 |
| RMSE (W) | **57.88** | 60.64 | 61.55 |
| Active-state MAE (W) | 145.42 | 135.04 | **109.88** |
| Precision | 0.000 | 0.019 | **0.359** |
| Recall | 0.000 | 0.223 | **0.497** |
| F1 | 0.000 | 0.036 | **0.417** |
| True energy | 58.52 kWh | 58.52 kWh | 58.52 kWh |
| Predicted energy | 0.00 kWh | 187.61 kWh | **77.29 kWh** |
| Energy error | -100.0% | +220.6% | **+32.1%** |

---

# 12. Interpretation of final results

The always-off baseline has the lowest global MAE and RMSE.

At first this may appear to make it the best model.

However, this result is caused by severe class imbalance.

The washing machine is off for the overwhelming majority of one-minute observations.

Therefore, predicting zero continuously produces a low average point-level error despite providing no useful washing-machine information.

The always-off baseline has:

- Precision = 0
- Recall = 0
- F1 = 0
- Energy error = -100%

It therefore completely fails at the actual appliance-disaggregation task.

---

# 13. Gradient-boosting performance

The gradient-boosting model produces a more useful appliance-level result.

Compared with always-off, active-state MAE improves from:

```text
145.42 W
```

to:

```text
109.88 W
```

This is approximately a **24% reduction in error during true washing-machine activity**.

The final model achieves:

- Precision: **0.359**
- Recall: **0.497**
- F1: **0.417**

This means the model recovers a meaningful portion of washing-machine activity in a household that was never used during model development.

---

# 14. Energy estimation

Actual washing-machine energy in House 19 was:

```text
58.52 kWh
```

The gradient-boosting model predicted:

```text
77.29 kWh
```

giving an energy error of:

```text
+32.1%
```

This is substantially better than:

### Always-off

```text
-100%
```

and the hour-profile baseline:

```text
+220.6%
```

The energy estimate is still not sufficiently accurate for billing or precise appliance-level accounting.

However, it is useful as an approximate behavioural or demand-flexibility signal.

---

# 15. Why MAE and RMSE alone are misleading

Sparse appliance loads require careful metric selection.

If the washing machine is inactive most of the time, a model predicting zero everywhere can obtain low MAE and RMSE.

This does not mean it performs useful NILM.

For this reason, the following metrics were reported.

## Global regression metrics

- MAE
- RMSE

These measure overall point-level power error.

---

## Active-state MAE

This calculates error only when the washing machine is genuinely active.

It better reflects model behaviour during periods relevant to the NILM task.

---

## Classification metrics

- Precision
- Recall
- F1

These evaluate whether the model correctly identifies appliance activity.

---

## Energy error

This measures whether predicted power produces a reasonable estimate of total washing-machine consumption.

No single metric is sufficient by itself.

---

# 16. Final actual-vs-predicted plot

File:

```text
figures/final_house19_actual_vs_predicted.png
```

This plot compares actual and predicted washing-machine power for the untouched House 19.

The model captures some genuine washing-machine activity but does not perfectly reproduce every power state within a physical cycle.

The plot supports the numerical results:

- useful activity detection
- incomplete recall
- imperfect power calibration

---

# 17. Failure analysis

Two final failure examples were generated from House 19.

Files:

```text
figures/final_house19_false_positive.png
figures/final_house19_false_negative.png
```

---

## 17.1 False positive

A false positive occurs when the model predicts washing-machine activity while the true washing-machine signal is inactive.

A likely reason is overlapping appliance signatures.

Other household appliances can create power changes in the aggregate signal that resemble portions of a washing-machine cycle.

Examples may include:

- kettles
- heaters
- dishwashers
- cooking equipment
- multiple simultaneous appliances

The model only sees whole-home aggregate demand and therefore cannot always determine which appliance generated a particular change.

---

## 17.2 False negative

A false negative occurs when the washing machine is active but the model predicts the appliance as inactive.

Some washing-machine stages operate at relatively low power.

These stages may become difficult to distinguish from normal background household demand.

The model may therefore detect high-power portions of a wash but miss lower-power phases.

---

# 18. Smart-meter resolution experiment

A separate sensitivity experiment tested the effect of reducing smart-meter resolution.

The original one-minute data was resampled to:

- 1 minute
- 5 minutes
- 15 minutes
- 30 minutes

The same general modelling approach was then evaluated.

---

## 18.1 Resolution results

| Resolution | Precision | Recall | F1 | Energy error |
|---:|---:|---:|---:|---:|
| 1 minute | 0.589 | 0.306 | 0.403 | -59.2% |
| 5 minutes | 0.443 | 0.284 | 0.346 | -55.3% |
| 15 minutes | 0.588 | 0.326 | 0.419 | -62.1% |
| 30 minutes | 0.668 | 0.391 | 0.493 | -66.6% |

Figures:

```text
figures/resolution_f1.png
figures/resolution_energy_error.png
```

---

# 19. Interpreting the resolution experiment

The results do not show a simple monotonic decline in F1 as resolution becomes coarser.

This does not mean 30-minute data provides better appliance disaggregation.

At coarser resolutions, the prediction task changes.

A 30-minute interval may contain multiple appliance states averaged into one observation.

Classification therefore becomes more like:

> "Did washing-machine activity occur somewhere within this broad interval?"

rather than:

> "Is the washing machine active at this exact minute?"

This can make broad interval classification appear easier while simultaneously removing important temporal information.

At coarser resolution it becomes harder to estimate:

- exact cycle start time
- exact cycle end time
- short heating periods
- transient power changes
- low-power cycle stages
- overlapping appliance events
- detailed cycle duration

Energy estimates also remained substantially biased.

Therefore, 15- and 30-minute data may still support broad behavioural insights, but detailed event-level NILM becomes substantially less precise.

---

# 20. Comparison between development and final holdout results

During development, House 15 was initially used as an evaluation household.

That experiment produced stronger event-level performance than the final House 19 result.

However, House 15 was subsequently involved in model-development decisions.

It was therefore moved into the final training set.

House 19 was introduced only after the modelling approach was fixed and was used as a genuinely untouched final holdout.

For this reason:

> **House 19 is the official final test result reported in this project.**

This provides a more credible estimate of real-world cross-house generalisation.

---

# 21. Main findings

The project produced five main findings.

## 1. Raw smart-meter data requires substantial quality control

The House 1 raw data contained:

- repeated timestamps
- conflicting duplicate observations
- daylight-saving discontinuity
- missing periods
- irregular sampling
- implausible appliance spikes

A documented cleaning pipeline was therefore essential before analysis.

---

## 2. Washing-machine behaviour varies strongly across households

Cycle duration and energy differed substantially between homes.

House 5 was especially different from Houses 2, 6, and 15.

This supports household-level validation rather than random row-level splitting.

---

## 3. Always-off baselines can appear deceptively strong

Because washing machines are inactive most of the time, always predicting zero can produce low global MAE.

This makes MAE alone inappropriate as the primary NILM metric.

---

## 4. Aggregate demand contains useful appliance information

The final gradient-boosting model achieved:

- F1 = **0.417**
- Recall = **0.497**
- Precision = **0.359**

on an untouched household.

This demonstrates that useful washing-machine activity information can be recovered from aggregate measurements.

---

## 5. Cross-house energy estimation remains difficult

Although the model produced useful activity predictions, appliance-energy estimation remained imperfect.

The final House 19 energy error was:

**+32.1%**

This is substantially better than the baselines but is not accurate enough for billing or precise appliance-level accounting.

---

# 22. Practical interpretation

The model is most suitable for:

- approximate appliance activity detection
- behavioural segmentation
- demand-response targeting
- peak-period appliance analysis
- customer energy insights

It should not currently be used for:

- appliance-level billing
- exact cycle-level energy accounting
- safety-critical decisions
- guaranteed appliance identification

---

# 23. Limitations

Several limitations remain.

## Overlapping appliance signatures

Different appliance combinations can produce similar aggregate power patterns.

This creates ambiguity that cannot always be resolved using aggregate power alone.

---

## Missing and forward-filled data

REFIT contains missing periods.

The official cleaned dataset also forward-fills some missing observations, which can hide the original outage structure.

---

## Household variation

Different washing-machine models, programmes, loads, and user behaviours produce different signatures.

Cross-house generalisation is therefore substantially harder than within-house prediction.

---

## Limited number of training homes

The final model was trained on only three households.

A larger and more varied training population would likely improve generalisation.

---

## UK-to-India transfer

REFIT contains UK households.

Direct application in India would require local validation because of differences in:

- washing-machine types
- appliance brands
- household size
- wash behaviour
- appliance ownership
- tariff structures
- voltage conditions
- time-of-day electricity use

The current results demonstrate methodology rather than production readiness for India.

---

# 24. Possible improvements

With additional time, the following extensions would be valuable:

1. leave-one-house-out evaluation across more REFIT households
2. train on a larger number of washing-machine homes
3. compare gradient boosting with Seq2Point or a lightweight neural NILM model
4. improve appliance-energy calibration
5. add uncertainty estimates
6. experiment with cycle-level loss functions
7. use richer aggregate-window features
8. evaluate event-level cycle precision and recall
9. test locally representative Indian smart-meter data
10. repeat the resolution experiment using the exact final modelling configuration

---

# 25. Final conclusion

The analysis demonstrates that washing-machine activity can be estimated to a useful degree from whole-home smart-meter data without dedicated appliance metering.

The final model was evaluated on a completely untouched household and achieved:

- **Precision: 0.359**
- **Recall: 0.497**
- **F1: 0.417**
- **Active-state MAE: 109.88 W**
- **Energy error: +32.1%**

The result is not accurate enough to replace direct appliance metering.

However, it is sufficiently informative to support further investigation of:

- behavioural insights
- flexible-load identification
- demand-response targeting
- customer energy recommendations

The most important conclusion is that **event-level behavioural information is more reliable than precise cross-house appliance-energy estimation** under the current modelling setup.