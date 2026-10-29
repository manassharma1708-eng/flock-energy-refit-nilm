from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    f1_score,
)

DATA_DIR = Path("data/processed")
FIG_DIR = Path("figures")
FIG_DIR.mkdir(exist_ok=True)

# FINAL LOCKED SPLIT
TRAIN_HOUSES = [2, 5, 15]
VAL_HOUSE = 6
TEST_HOUSE = 19

TRUE_ON_THRESHOLD_W = 20
RANDOM_STATE = 42


def load_house(house):
    path = DATA_DIR / f"house{house}_clean_1min.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    return pd.read_parquet(path).copy()


def make_features(df):
    out = pd.DataFrame(index=df.index)

    a = df["Aggregate"]

    out["aggregate"] = a

    # Past-only temporal features
    out["lag_1"] = a.shift(1)
    out["lag_2"] = a.shift(2)
    out["lag_5"] = a.shift(5)
    out["lag_10"] = a.shift(10)

    out["mean_3"] = a.rolling(3, min_periods=3).mean()
    out["mean_5"] = a.rolling(5, min_periods=5).mean()
    out["mean_15"] = a.rolling(15, min_periods=15).mean()

    out["std_5"] = a.rolling(5, min_periods=5).std()
    out["diff_1"] = a.diff(1)

    out["hour"] = df.index.hour
    out["weekday"] = df.index.day_of_week

    out["washer"] = df["washer"]

    return out.dropna()


def prepare_house(house):
    print(f"Preparing House {house}...")

    df = make_features(load_house(house))

    print(f"  usable rows: {len(df):,}")
    print(
        f"  active washer minutes: "
        f"{(df['washer'] > TRUE_ON_THRESHOLD_W).sum():,}"
    )

    return df


def regression_metrics(y, pred):
    pred = np.clip(pred, 0, None)

    mae = mean_absolute_error(y, pred)
    rmse = np.sqrt(mean_squared_error(y, pred))

    true_energy = y.sum() / 60 / 1000
    pred_energy = pred.sum() / 60 / 1000

    if true_energy > 0:
        energy_error = (
            100 * (pred_energy - true_energy) / true_energy
        )
    else:
        energy_error = np.nan

    active = y > TRUE_ON_THRESHOLD_W

    active_mae = (
        mean_absolute_error(y[active], pred[active])
        if active.any()
        else np.nan
    )

    return {
        "MAE_W": mae,
        "RMSE_W": rmse,
        "Active_MAE_W": active_mae,
        "True_Energy_kWh": true_energy,
        "Pred_Energy_kWh": pred_energy,
        "Energy_Error_pct": energy_error,
    }


def classification_metrics(y, pred, prediction_threshold):
    true_on = y > TRUE_ON_THRESHOLD_W
    pred_on = pred > prediction_threshold

    return {
        "Precision": precision_score(
            true_on, pred_on, zero_division=0
        ),
        "Recall": recall_score(
            true_on, pred_on, zero_division=0
        ),
        "F1": f1_score(
            true_on, pred_on, zero_division=0
        ),
    }


# -------------------------------------------------------
# Load final split
# -------------------------------------------------------

train_parts = [
    prepare_house(h)
    for h in TRAIN_HOUSES
]

train = pd.concat(train_parts).sort_index()

validation = prepare_house(VAL_HOUSE)
test = prepare_house(TEST_HOUSE)

features = [
    c for c in train.columns
    if c != "washer"
]

print("\nFINAL SPLIT")
print("Training:", TRAIN_HOUSES)
print("Validation:", VAL_HOUSE)
print("Untouched test:", TEST_HOUSE)

# -------------------------------------------------------
# Baselines learned only from training homes
# -------------------------------------------------------

hour_profile = (
    train
    .assign(hour=train.index.hour)
    .groupby("hour")["washer"]
    .mean()
)

# -------------------------------------------------------
# Model
# -------------------------------------------------------

model = HistGradientBoostingRegressor(
    learning_rate=0.08,
    max_iter=180,
    max_leaf_nodes=31,
    l2_regularization=1.0,
    random_state=RANDOM_STATE,
)

print("\nTraining final locked model...")

model.fit(
    train[features],
    train["washer"]
)

print("Training complete.")

# -------------------------------------------------------
# Validation threshold selection
# -------------------------------------------------------

val_y = validation["washer"].to_numpy()

val_pred = np.clip(
    model.predict(validation[features]),
    0,
    None
)

threshold_candidates = list(range(10, 210, 10))

threshold_results = []

for threshold in threshold_candidates:

    metrics = classification_metrics(
        val_y,
        val_pred,
        threshold
    )

    threshold_results.append({
        "threshold": threshold,
        **metrics,
    })

threshold_df = pd.DataFrame(threshold_results)

best_row = threshold_df.loc[
    threshold_df["F1"].idxmax()
]

best_threshold = float(best_row["threshold"])

print("\nVALIDATION THRESHOLD SEARCH — HOUSE 6")
print(threshold_df.to_string(index=False))

print(
    f"\nSelected prediction threshold: "
    f"{best_threshold:.0f} W"
)

print(
    f"Validation F1 at selected threshold: "
    f"{best_row['F1']:.4f}"
)

# -------------------------------------------------------
# FINAL TEST — House 19
# -------------------------------------------------------

test_y = test["washer"].to_numpy()

model_pred = np.clip(
    model.predict(test[features]),
    0,
    None
)

always_off_pred = np.zeros_like(test_y)

hour_pred = (
    pd.Series(
        test.index.hour,
        index=test.index
    )
    .map(hour_profile)
    .fillna(0)
    .to_numpy()
)


def full_metrics(y, pred, threshold):
    result = regression_metrics(y, pred)

    result.update(
        classification_metrics(
            y,
            pred,
            threshold
        )
    )

    return result


always_off_results = full_metrics(
    test_y,
    always_off_pred,
    TRUE_ON_THRESHOLD_W
)

hour_results = full_metrics(
    test_y,
    hour_pred,
    TRUE_ON_THRESHOLD_W
)

model_results = full_metrics(
    test_y,
    model_pred,
    best_threshold
)

print("\n" + "=" * 80)
print("FINAL UNTOUCHED TEST — HOUSE 19")
print("=" * 80)

for name, result in [
    ("always_off", always_off_results),
    ("hour_profile", hour_results),
    ("gradient_boosting", model_results),
]:

    print(f"\n{name}")

    for key, value in result.items():
        print(f"  {key}: {value:.4f}")

# -------------------------------------------------------
# Save metrics
# -------------------------------------------------------

output = {
    "split": {
        "train_houses": TRAIN_HOUSES,
        "validation_house": VAL_HOUSE,
        "final_test_house": TEST_HOUSE,
    },
    "true_active_threshold_w": TRUE_ON_THRESHOLD_W,
    "prediction_threshold_selected_on_validation_w": best_threshold,
    "validation_threshold_search": threshold_results,
    "final_test": {
        "always_off": always_off_results,
        "hour_profile": hour_results,
        "gradient_boosting": model_results,
    },
}

with open(
    "final_holdout_metrics.json",
    "w"
) as f:
    json.dump(output, f, indent=2)

# -------------------------------------------------------
# Predictions dataframe
# -------------------------------------------------------

plot_df = test.copy()

plot_df["prediction"] = model_pred

plot_df["abs_error"] = np.abs(
    plot_df["washer"]
    - plot_df["prediction"]
)

# -------------------------------------------------------
# Actual vs predicted plot
# -------------------------------------------------------

daily_energy = (
    plot_df["washer"]
    .resample("1D")
    .sum()
)

active_days = daily_energy[
    daily_energy > 0
]

if len(active_days):
    start = active_days.idxmax()
else:
    start = plot_df.index[0]

end = start + pd.Timedelta(hours=48)

window = plot_df.loc[
    (plot_df.index >= start)
    &
    (plot_df.index < end)
]

plt.figure(figsize=(14, 6))

plt.plot(
    window.index,
    window["washer"],
    label="Actual washer power",
    linewidth=1.4,
)

plt.plot(
    window.index,
    window["prediction"],
    label="Predicted washer power",
    linewidth=1.2,
)

plt.xlabel("Time")
plt.ylabel("Power (W)")

plt.title(
    "Final untouched House 19: actual vs predicted washer power"
)

plt.legend()
plt.tight_layout()

plt.savefig(
    FIG_DIR / "final_house19_actual_vs_predicted.png",
    dpi=160,
)

plt.close()

# -------------------------------------------------------
# Failure cases
# -------------------------------------------------------

false_positive = plot_df[
    (plot_df["washer"] <= TRUE_ON_THRESHOLD_W)
    &
    (plot_df["prediction"] > best_threshold)
]

false_negative = plot_df[
    (plot_df["washer"] > TRUE_ON_THRESHOLD_W)
    &
    (plot_df["prediction"] <= best_threshold)
]


def plot_failure(rows, filename, title):

    if rows.empty:
        print(f"No rows for {title}")
        return

    center = rows["abs_error"].idxmax()

    start = center - pd.Timedelta(minutes=90)
    end = center + pd.Timedelta(minutes=90)

    w = plot_df.loc[start:end]

    plt.figure(figsize=(12, 5))

    plt.plot(
        w.index,
        w["washer"],
        label="Actual washer"
    )

    plt.plot(
        w.index,
        w["prediction"],
        label="Prediction"
    )

    plt.plot(
        w.index,
        w["aggregate"],
        label="Aggregate",
        alpha=0.45
    )

    plt.xlabel("Time")
    plt.ylabel("Power (W)")
    plt.title(title)

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        FIG_DIR / filename,
        dpi=160
    )

    plt.close()


plot_failure(
    false_positive,
    "final_house19_false_positive.png",
    "Final House 19 failure case: false positive"
)

plot_failure(
    false_negative,
    "final_house19_false_negative.png",
    "Final House 19 failure case: false negative"
)

# -------------------------------------------------------
# Save predictions locally
# -------------------------------------------------------

prediction_output = test[
    ["washer", "aggregate"]
].copy()

prediction_output["prediction"] = model_pred

prediction_output.to_parquet(
    DATA_DIR / "house19_final_predictions.parquet"
)

print("\nSaved:")
print("final_holdout_metrics.json")
print("figures/final_house19_actual_vs_predicted.png")
print("figures/final_house19_false_positive.png")
print("figures/final_house19_false_negative.png")
print("data/processed/house19_final_predictions.parquet")
