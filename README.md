# REFIT Appliance Disaggregation — Flock Energy Take-Home

This project builds a reproducible pipeline to clean REFIT smart-meter data, analyse washing-machine usage across households, and estimate washing-machine power from whole-home aggregate electricity demand.

The goal is not to build the most complex NILM model, but to demonstrate careful data handling, sensible validation, reproducibility, and clear interpretation.

---

## Headline results

### Held-out test household: House 15

| Metric | Always off | Hour profile | Gradient boosting |
|---|---:|---:|---:|
| MAE (W) | 16.67 | 34.68 | **14.84** |
| RMSE (W) | 169.84 | 169.06 | **127.66** |
| Active-state MAE (W) | 586.09 | 562.27 | **435.52** |
| Precision | 0.000 | 0.039 | **0.567** |
| Recall | 0.000 | 0.744 | 0.575 |
| F1 | 0.000 | 0.074 | **0.571** |
| Energy error | -100% | +16.8% | -58.7% |

The gradient-boosting model improves MAE, RMSE, active-state MAE and event-state F1 on a completely unseen household.

However, total appliance-energy estimation remains poorly calibrated across households.

The main conclusion is:

> Aggregate smart-meter data can recover useful washing-machine activity signals, but cross-house appliance-energy estimation remains difficult without household-specific calibration.

---

## Project structure

```text
flock-energy-refit-nilm/
├── README.md
├── DATA.md
├── RESULTS.md
├── Recommendation.md
├── requirements.txt
├── requirements-lock.txt
├── model_metrics.json
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
│   ├── model_actual_vs_predicted.png
│   ├── failure_false_positive.png
│   └── failure_false_negative.png
│
├── src/
│   ├── audit_house1.py
│   ├── investigate_house1.py
│   ├── check_house1_duplicates.py
│   ├── clean_house1.py
│   ├── washer_eda.py
│   └── train_model.py
│
└── tests/
```

Large REFIT datasets and generated processed datasets are intentionally excluded from Git.

---

# 1. Dataset

This project uses the REFIT Electrical Load Measurements dataset from the University of Strathclyde.

REFIT contains whole-home aggregate power and appliance-level measurements from