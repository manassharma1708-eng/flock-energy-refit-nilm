# REFIT Appliance Disaggregation — Flock Energy 

A reproducible data-science pipeline for cleaning REFIT smart-meter data, analysing washing-machine usage across households, and estimating washing-machine power from whole-home aggregate electricity demand.

The project prioritises:

- careful data handling
- leakage-safe validation
- interpretable modelling
- reproducibility
- realistic utility-facing conclusions

rather than unnecessary model complexity.

---

# Headline result

## Final untouched household: House 19

The final evaluation used:

- **Training:** Houses 2, 5, and 15
- **Validation:** House 6
- **Final untouched test:** House 19

The prediction threshold was selected using **House 6 only**.

After the model configuration and prediction threshold were fixed, House 19 was evaluated as the final holdout household.

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

The always-off baseline has the lowest global MAE because the washing machine is inactive for most one-minute observations.

However, it detects no appliance activity and has -100% energy error.

The gradient-boosting model instead:

- reduces active-state MAE by about 24% relative to always-off
- recovers nearly half of true active washing-machine minutes
- achieves F1 = **0.417**
- reduces total appliance-energy error to **+32.1%**

The main conclusion is:

> **Aggregate smart-meter data can recover useful washing-machine activity signals on an unseen household, but cross-house appliance-energy estimation remains substantially harder than direct appliance metering.**

---

# Project structure

```text
flock-energy-refit-nilm/
│
├── README.md
├── DATA.md
├── RESULTS.md
├── Recommendation.md
│
├── requirements.txt
├── requirements-lock.txt
│
├── model_metrics.json
├── final_holdout_metrics.json
├── resolution_results.csv
│
├── data/
│   ├── README.md
│   ├── raw/
│   ├── cleaned/
│   └── processed/
│
├── figures/
│   ├── house1_before_cleaning.png
│   ├── house1_after_cleaning.png
│   ├── washer_24h_trace.png
│   ├── detected_washer_cycles.png
│   ├── washer_energy_cross_house.png
│   ├── washer_cycle_starts_hour.png
│   ├── washer_cycle_starts_weekday.png
│   ├── final_house19_actual_vs_predicted.png
│   ├── final_house19_false_positive.png
│   ├── final_house19_false_negative.png
│   ├── resolution_f1.png
│   └── resolution_energy_error.png
│
├── src/
│   ├── audit_house1.py
│   ├── investigate_house1.py
│   ├── check_house1_duplicates.py
│   ├── clean_house1.py
│   ├── washer_eda.py
│   ├── train_model.py
│   ├── final_holdout_model.py
│   └── resolution_experiment.py
│
└── tests/
```

Large raw and cleaned REFIT datasets are intentionally excluded from Git.

---

# 1. Problem

Flock Energy works with electricity-distribution utilities and smart-meter data.

A recurring challenge is estimating how much electricity individual appliances use when only whole-home electricity measurements are available.

This project focuses on one appliance:

**washing machine**

The modelling task is:

```text
Whole-home aggregate power
            ↓
   Disaggregation model
            ↓
Estimated washing-machine power
```

This is a Non-Intrusive Load Monitoring (NILM) problem.

---

# 2. Dataset

The project uses the REFIT Electrical Load Measurements dataset from the University of Strathclyde.

REFIT contains:

- whole-home aggregate power
- individual appliance measurements
- 20 UK households
- active power measurements in watts
- original sampling at approximately 8-second intervals

The project uses:

- raw House 1 data for the cleaning exercise
- official cleaned REFIT data for washing-machine EDA and modelling

All modelling is performed at one-minute resolution.

---

# 3. Raw House 1 cleaning

Two raw House 1 files were analysed:

| File | Rows | Start | End |
|---|---:|---|---|
| Part 1 | 4,377,877 | 2013-10-09 | 2014-10-01 |
| Part 2 | 4,140,886 | 2014-06-27 | 2015-07-10 |

The files overlap between June and October 2014.

Several important data-quality issues were found.

---

## 3.1 Duplicate timestamps

Part 1 contained more than one million repeated UNIX timestamps.

Detailed inspection found approximately:

- 883,358 exact consecutive duplicates
- 120,592 conflicting consecutive duplicates

Part 2 contained:

- 393 exact consecutive duplicates
- 14,362 conflicting consecutive duplicates

Because duplicated timestamps sometimes contained different or complementary readings, duplicates were collapsed by averaging available readings at the same UNIX timestamp rather than blindly keeping the first or final row.

---

## 3.2 Daylight-saving discontinuity

A backwards local-time jump was observed around the UK daylight-saving transition on 27 October 2013.

UNIX timestamps were therefore treated as the authoritative chronological field.

---

## 3.3 Part 1 versus Part 2

Part 1 represents unavailable sensors as zero.

Part 2 preserves unavailable measurements as missing values.

Because Part 2 better distinguishes:

```text
real zero consumption
```

from:

```text
sensor unavailable
```

Part 2 was preferred wherever the files overlap.

---

## 3.4 Extreme values

Several appliance channels contained implausibly large readings, including values above 30 kW and some approaching 100 kW.

For individual appliance channels:

```text
power > 4000 W
```

was treated as an unreliable measurement and converted to missing.

The household Aggregate signal was not subjected to this threshold because total home demand can legitimately exceed 4 kW.

---

## 3.5 Missing periods

After deduplication and overlap handling:

```text
6,663,716 observations
```

remained.

The data was resampled to:

```text
1-minute mean power
```

producing:

```text
920,031 one-minute rows
```

Short missing runs of up to two minutes were interpolated.

Longer outages were left missing and explicitly flagged.

The final dataset contained:

```text
119,063 long-outage minutes
```

Long gaps were intentionally not filled because doing so would introduce unsupported synthetic consumption.

---

# 4. House 1 cleaning figures

Before cleaning:

```text
figures/house1_before_cleaning.png
```

After cleaning and one-minute resampling:

```text
figures/house1_after_cleaning.png
```

The plots include:

- household Aggregate
- refrigerator
- washing machine

over the same representative period.

See `DATA.md` for the full raw-data analysis.

---

# 5. Washing-machine exploratory analysis

The official cleaned REFIT dataset was used for washing-machine analysis.

The selected households were:

| House | Washing-machine channel |
|---:|---|
| 2 | Appliance2 |
| 5 | Appliance3 |
| 6 | Appliance2 |
| 15 | Appliance3 |
| 19 | Appliance2 |

Houses 2, 5, 6, and 15 were used during development and EDA.

House 19 was subsequently introduced as the final untouched test household.

---

# 6. Washing-machine cycle definition

A simple, interpretable cycle detector was used.

A minute was considered active when:

```text
washing-machine power > 20 W
```

To avoid splitting a single physical wash programme:

- inactive gaps up to 5 minutes were merged
- events shorter than 15 minutes were discarded
- a valid event had to reach at least 100 W peak power

This rule intentionally prioritises consistency and interpretability over manufacturer-specific cycle reconstruction.

---

# 7. EDA results

For the four development households:

| House | Missing aggregate | Off time | Cycles | Median duration | Median energy |
|---:|---:|---:|---:|---:|---:|
| 2 | 24.70% | 96.53% | 345 | 95 min | 0.600 kWh |
| 5 | 13.25% | 94.18% | 800 | 41 min | 0.247 kWh |
| 6 | 15.35% | 98.43% | 136 | 95.5 min | 0.640 kWh |
| 15 | 13.70% | 97.55% | 255 | 90 min | 0.672 kWh |

A total of:

```text
1,536 detected cycles
```

were identified across these four households.

---

# 8. Cross-house differences

House 5 differs substantially from Houses 2, 6, and 15.

Its detected cycles have:

- shorter median duration
- lower median energy

This demonstrates that washing-machine signatures are not constant across households.

Possible causes include:

- machine model
- wash programme
- load size
- user behaviour
- monitoring differences

This cross-house variation is one of the main reasons household-level validation is important.

---

# 9. EDA figures

Representative 24-hour trace:

```text
figures/washer_24h_trace.png
```

Detected cycles:

```text
figures/detected_washer_cycles.png
```

Cross-house cycle-energy comparison:

```text
figures/washer_energy_cross_house.png
```

Cycle starts by hour:

```text
figures/washer_cycle_starts_hour.png
```

Cycle starts by weekday:

```text
figures/washer_cycle_starts_weekday.png
```

---

# 10. Model

The main model is:

```text
HistGradientBoostingRegressor
```

Gradient boosting was chosen because it:

- handles nonlinear relationships
- trains efficiently
- works well with engineered time-series features
- does not require GPU resources
- remains easy to explain

The goal was to build a reliable and defensible model rather than maximise complexity.

---

# 11. Features

The model uses:

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

All lagged and rolling features use current or historical observations only.

No future aggregate measurements are used.

---

# 12. Baselines

Two baselines are included.

## Always-off baseline

```text
Predicted washer power = 0 W
```

This is important because the washing machine is inactive for most observations.

---

## Hour-of-day profile baseline

This baseline predicts washing-machine power using average washing-machine demand by hour of day learned from the training households.

It provides a simple behavioural comparison.

---

# 13. Final validation design

The final split is:

```text
Training
House 2
House 5
House 15

Validation
House 6

Final untouched test
House 19
```

This prevents household-level leakage.

House 19 was not used for:

- training
- model selection
- feature selection
- hyperparameter selection
- threshold selection

The model configuration was fixed before House 19 was evaluated.

---

# 14. Prediction-threshold selection

Ground-truth washing-machine activity is defined as:

```text
True power > 20 W
```

The model produces a continuous power prediction.

A separate prediction threshold was selected using House 6.

Candidate thresholds from:

```text
10 W → 200 W
```

were compared.

The best validation F1 occurred at:

```text
30 W
```

with validation:

```text
F1 = 0.262
```

The 30 W prediction threshold was then frozen before evaluating House 19.

---

# 15. Final untouched test — House 19

House 19 contained approximately:

```text
612,151 usable one-minute observations
```

with:

```text
23,990 active washing-machine minutes
```

after feature preparation.

This means washing-machine activity is sparse relative to the full timeline.

---

## Final test metrics

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

# 16. Why the always-off baseline wins global MAE

The washing machine is inactive for most timestamps.

Therefore:

```text
predict zero everywhere
```

can achieve a surprisingly low global MAE.

However, the always-off baseline has:

```text
Precision = 0
Recall = 0
F1 = 0
Energy error = -100%
```

It provides no useful appliance-level information.

This is why global MAE or standard accuracy should not be used alone for sparse NILM problems.

---

# 17. Active-state performance

During true washing-machine activity:

Always-off active-state MAE:

```text
145.42 W
```

Gradient boosting:

```text
109.88 W
```

This is approximately a:

```text
24% reduction
```

in error during the periods that matter most for appliance detection.

---

# 18. Event-state performance

The final model achieved:

```text
Precision = 0.359
Recall    = 0.497
F1        = 0.417
```

on a completely untouched household.

This means the model recovers a meaningful proportion of real washing-machine activity despite substantial differences between homes.

---

# 19. Energy estimation

Actual House 19 washing-machine energy:

```text
58.52 kWh
```

Predicted:

```text
77.29 kWh
```

Energy error:

```text
+32.1%
```

This is substantially better than:

Always-off:

```text
-100%
```

Hour profile:

```text
+220.6%
```

The energy estimate is still not sufficiently accurate for billing.

It is more appropriate as an approximate behavioural or demand-flexibility signal.

---

# 20. Actual vs predicted

Final evaluation plot:

```text
figures/final_house19_actual_vs_predicted.png
```

The model captures some genuine washing-machine activity but does not reconstruct every internal power state accurately.

This is consistent with the numerical results:

- useful event detection
- incomplete recall
- imperfect energy calibration

---

# 21. Failure analysis

Final failure examples:

```text
figures/final_house19_false_positive.png
figures/final_house19_false_negative.png
```

## False positive

Other household appliances can create aggregate-power patterns that resemble washing-machine activity.

Possible sources include:

- kettles
- heaters
- dishwashers
- cooking appliances
- overlapping appliance operation

---

## False negative

Some washing-machine phases operate at relatively low power.

These stages can become difficult to distinguish from household background demand.

The model may therefore detect high-power portions of a wash while missing lower-power stages.

---

# 22. Smart-meter resolution experiment

A separate sensitivity experiment tested:

```text
1-minute
5-minute
15-minute
30-minute
```

smart-meter resolution.

Results:

| Resolution | Precision | Recall | F1 | Energy error |
|---:|---:|---:|---:|---:|
| 1 min | 0.589 | 0.306 | 0.403 | -59.2% |
| 5 min | 0.443 | 0.284 | 0.346 | -55.3% |
| 15 min | 0.588 | 0.326 | 0.419 | -62.1% |
| 30 min | 0.668 | 0.391 | 0.493 | -66.6% |

Figures:

```text
figures/resolution_f1.png
figures/resolution_energy_error.png
```

These results come from a separate sensitivity experiment and should not be compared directly with the final House 19 evaluation because the experiment uses its own fixed feature configuration.

---

# 23. What happens at 15- and 30-minute resolution?

Classification F1 does not decline monotonically as resolution becomes coarser.

This does not mean 30-minute data is better for appliance disaggregation.

At 30-minute resolution, many appliance states are averaged into one observation.

The question effectively changes from:

```text
Is the washer active at this exact minute?
```

to:

```text
Did washer activity occur somewhere within this broad interval?
```

This can make broad interval classification appear easier while destroying detailed temporal information.

At coarse resolution, it becomes harder to estimate:

- exact cycle start
- exact cycle end
- short heating periods
- transient states
- low-power phases
- overlapping appliances
- exact cycle duration

Therefore 15- and 30-minute data may still support broad behavioural analysis, but detailed event-level NILM becomes substantially harder.

---

# 24. Utility use case

The most realistic application is:

> **identifying households with flexible appliance activity during peak-demand periods**

For example, customers who frequently run washing machines during evening peaks could receive:

- off-peak tariff incentives
- load-shifting recommendations
- demand-response notifications
- personalised energy advice

The model should be treated as an approximate behavioural signal rather than an appliance meter.

---

# 25. Measuring utility impact

A utility could evaluate the intervention using a randomised controlled design.

Treatment group:

```text
customers receiving an off-peak laundry intervention
```

Control group:

```text
customers receiving no intervention
```

Primary KPI:

```text
share of detected washing-machine cycles occurring during peak periods
```

Secondary KPIs:

- estimated peak-period washing-machine kWh
- total household peak demand
- engagement with the intervention
- persistence of behaviour change

---

# 26. UK-to-India transfer

REFIT contains UK households.

Direct deployment in India would require local validation because of differences in:

- top-load versus front-load machines
- appliance brands
- household size
- wash behaviour
- climate
- appliance ownership
- tariff structures
- voltage conditions
- time-of-day electricity use

REFIT therefore demonstrates the methodology but does not establish production performance in India.

---

# 27. Limitations

Important limitations include:

## Overlapping appliance signatures

Different appliance combinations can produce similar aggregate power patterns.

## Missing data

REFIT contains missing observations and outages.

## Forward-filled cleaned data

Some missing observations in the official cleaned REFIT dataset were forward-filled.

## Household variation

Different machines, programmes and users produce different appliance signatures.

## Small training population

The final model uses only three training households.

## Energy calibration

Cross-house energy estimation remains imperfect.

---

# 28. Reproducibility

The project includes:

- fixed random seeds
- household-level validation
- explicit preprocessing rules
- reproducible scripts
- pinned dependencies
- saved figures
- saved metric outputs
- raw and processed datasets excluded from Git

The main analytical pipeline can be rerun from the raw/cleaned REFIT files.

---

# 29. Setup

Clone:

```bash
git clone https://github.com/manassharma1708-eng/flock-energy-refit-nilm.git
cd flock-energy-refit-nilm
```

Create environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

For exact package versions:

```bash
pip install -r requirements-lock.txt
```

---

# 30. Data placement

Place raw House 1 files in:

```text
data/raw/RAW_House1_Part1.csv
data/raw/RAW_House1_Part2.csv
```

Place cleaned REFIT files in:

```text
data/cleaned/CLEAN_House2.csv
data/cleaned/CLEAN_House5.csv
data/cleaned/CLEAN_House6.csv
data/cleaned/CLEAN_House15.csv
data/cleaned/CLEAN_House19.csv
```

These files are intentionally excluded from Git.

---

# 31. Running the pipeline

## Raw-data audit

```bash
python src/audit_house1.py
python src/investigate_house1.py
python src/check_house1_duplicates.py
```

## House 1 cleaning

```bash
python src/clean_house1.py
```

## Washing-machine EDA

```bash
python src/washer_eda.py
```

## Development model

```bash
python src/train_model.py
```

## Final untouched holdout model

```bash
python src/final_holdout_model.py
```

## Resolution experiment

```bash
python src/resolution_experiment.py
```

---

# 32. Main outputs

Detailed raw-data findings:

```text
DATA.md
```

Full modelling and EDA results:

```text
RESULTS.md
```

Utility-facing recommendations:

```text
Recommendation.md
```

Final evaluation metrics:

```text
final_holdout_metrics.json
```

Resolution experiment:

```text
resolution_results.csv
```

---

# 33. AI tools used

AI assistance was used for:

- code-review support
- debugging
- structuring the analysis
- discussing modelling and validation choices
- documentation drafting

All reported statistics and model results come from the actual executed pipeline.

The outputs were checked against the generated files and terminal results.

No model metrics were fabricated.

---

# 34. Trade-offs

The project intentionally prioritises:

- correct data handling
- transparent assumptions
- household-level validation
- interpretable modelling
- reproducibility
- honest limitations

over:

- extensive hyperparameter search
- deep-learning architectures
- large ensembles
- household-specific calibration

This keeps the solution manageable and defensible.

---

# 35. Possible improvements

With more time, useful extensions would include:

1. leave-one-house-out validation across more REFIT homes
2. training on more washing-machine households
3. Seq2Point or another neural NILM comparison
4. better appliance-energy calibration
5. event-level cycle precision and recall
6. uncertainty estimates
7. richer temporal features
8. Indian smart-meter validation
9. exact-resolution comparison using the final model configuration
10. household-specific fine-tuning

---

# Final takeaway

The project demonstrates that useful washing-machine activity information can be recovered from whole-home smart-meter measurements.

On the final untouched House 19, the model achieved:

```text
Precision:         0.359
Recall:            0.497
F1:                0.417
Active-state MAE: 109.88 W
Energy error:     +32.1%
```

The result is not accurate enough to replace dedicated appliance metering.

However, it is potentially useful for:

- behavioural segmentation
- flexible-load identification
- peak-demand analysis
- demand-response targeting
- customer energy insights

The strongest conclusion is:

> **Event-level behavioural information is more reliable than precise cross-house appliance-energy estimation under the current modelling setup.**