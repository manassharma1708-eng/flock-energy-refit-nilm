# Results

## 1. Washing-machine exploratory analysis

Four households were analysed using the official cleaned REFIT data at one-minute resolution.

The active washing-machine rule was:

- washing-machine power above 20 W indicates activity
- inactive gaps of up to 5 minutes inside an event are merged
- detected events shorter than 15 minutes are discarded
- detected events must reach at least 100 W peak power

This rule allows short low-power phases within a wash programme without incorrectly splitting one physical wash into several events.

### Household summary

| House | Missing aggregate | Off time | Detected cycles | Median duration | Median energy |
|---:|---:|---:|---:|---:|---:|
| 2 | 24.70% | 96.53% | 345 | 95 min | 0.600 kWh |
| 5 | 13.25% | 94.18% | 800 | 41 min | 0.247 kWh |
| 6 | 15.35% | 98.43% | 136 | 95.5 min | 0.640 kWh |
| 15 | 13.70% | 97.55% | 255 | 90 min | 0.672 kWh |

A total of 1,536 washing-machine cycles were detected.

House 5 differs substantially from the other homes, with shorter and lower-energy cycles. This is an important reminder that appliance signatures and user behaviour vary meaningfully between households.

---

## 2. Usage patterns

The repository contains:

- `figures/washer_24h_trace.png`
- `figures/detected_washer_cycles.png`
- `figures/washer_energy_cross_house.png`
- `figures/washer_cycle_starts_hour.png`
- `figures/washer_cycle_starts_weekday.png`

The 24-hour trace shows that washing-machine demand forms only a small portion of the total household signal and is often surrounded by unrelated appliance activity.

The detected-cycle plot illustrates substantial variation in power shape between cycles.

The cross-house comparison shows that energy-per-cycle distributions differ materially between homes, which makes unseen-house disaggregation harder than within-house prediction.

---

## 3. Modelling approach

The goal was to estimate washing-machine power from household aggregate power at one-minute resolution.

The split was household-based:

- Training: Houses 2 and 5
- Validation: House 6
- Test: House 15

This prevents overlapping time windows from the same household appearing in both training and evaluation data.

House 15 therefore represents a genuinely unseen household.

### Features

The model uses only information available from the household aggregate signal and calendar:

- current aggregate power
- 1-minute lag
- 2-minute lag
- 5-minute lag
- 10-minute lag
- 3-minute rolling mean
- 5-minute rolling mean
- 15-minute rolling mean
- 5-minute rolling standard deviation
- one-minute power difference
- hour of day
- day of week

All rolling and lagged features use current or past measurements only.

### Models

Three approaches were compared:

1. Always-off baseline
2. Hour-of-day usage-profile baseline
3. Histogram Gradient Boosting regression

Gradient boosting was selected because the task primarily requires a reliable, explainable baseline model rather than maximum model complexity.

---

## 4. Validation results — House 6

| Metric | Always off | Hour profile | Gradient boosting |
|---|---:|---:|---:|
| MAE (W) | 6.99 | 25.25 | 15.53 |
| RMSE (W) | 102.52 | 102.88 | **86.94** |
| Active-state MAE (W) | 376.08 | 344.87 | **273.83** |
| Precision | 0.000 | 0.034 | **0.153** |
| Recall | 0.000 | 0.998 | 0.807 |
| F1 | 0.000 | 0.066 | **0.257** |
| True energy | 80.05 kWh | 80.05 kWh | 80.05 kWh |
| Predicted energy | 0 | 222.55 kWh | 144.16 kWh |
| Energy error | -100% | +178.0% | +80.1% |

The always-off model achieves low MAE because washing machines are inactive for most minutes, but it completely fails to identify usage.

Gradient boosting improves RMSE, active-state MAE and event-state F1, but still overestimates total energy on this validation household.

---

## 5. Final test results — unseen House 15

| Metric | Always off | Hour profile | Gradient boosting |
|---|---:|---:|---:|
| MAE (W) | 16.67 | 34.68 | **14.84** |
| RMSE (W) | 169.84 | 169.06 | **127.66** |
| Active-state MAE (W) | 586.09 | 562.27 | **435.52** |
| Precision | 0.000 | 0.039 | **0.567** |
| Recall | 0.000 | 0.744 | 0.575 |
| F1 | 0.000 | 0.074 | **0.571** |
| True energy | 193.57 kWh | 193.57 kWh | 193.57 kWh |
| Predicted energy | 0 | 226.14 kWh | 79.96 kWh |
| Energy error | -100% | +16.8% | -58.7% |

The gradient-boosting model improves test MAE, RMSE and active-state MAE relative to always-off.

More importantly, it achieves an F1 score of 0.571 on a completely unseen household, showing that meaningful appliance activity can be recovered from aggregate demand.

However, energy estimation remains poorly calibrated across households.

---

## 6. Why MAE alone is misleading

House 15's washing machine is inactive for approximately 97.5% of one-minute observations.

Therefore an always-off model receives a deceptively competitive MAE despite being useless for actual appliance detection.

For this reason, model assessment includes:

- MAE
- RMSE
- active-state MAE
- precision
- recall
- F1
- total energy error

The combined metrics provide a more realistic view of whether the model is useful.

---

## 7. Actual vs predicted

`figures/model_actual_vs_predicted.png` compares predicted and true washing-machine power over an evaluation window from the unseen House 15.

The model captures some periods of genuine washing-machine activity but does not reproduce the full power profile accurately.

This is consistent with the numerical results: event detection is substantially better than the baselines, while absolute energy prediction remains difficult.

---

## 8. Failure cases

Two failure examples are included:

- `figures/failure_false_positive.png`
- `figures/failure_false_negative.png`

### False positive

Large changes in whole-house demand can resemble washing-machine activity even when the washer is inactive.

This is expected because several appliances can produce overlapping signatures in aggregate power.

### False negative

Some low-power phases within a washing-machine cycle are difficult to distinguish from background household demand.

The model can therefore detect part of a cycle while missing lower-power sections.

---

## 9. Main interpretation

The experiment suggests that aggregate smart-meter data can support approximate washing-machine activity detection without dedicated appliance metering.

However, generalisation across households remains challenging.

The model performs reasonably for identifying whether washing-machine activity is occurring, but appliance-level energy estimates vary considerably between unseen households.

Therefore the current approach is more suitable for behavioural or demand-flexibility insights than for precise appliance-level billing or high-accuracy energy accounting.