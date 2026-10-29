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

TRAIN_HOUSES = [2, 5]
VAL_HOUSE = 6
TEST_HOUSE = 15

ON_THRESHOLD_W = 20
RANDOM_STATE = 42


def load_house(house):
    path = DATA_DIR / f"house{house}_clean_1min.parquet"

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_parquet(path).copy()

    return df


def make_features(df):
    out = pd.DataFrame(index=df.index)

    a = df["Aggregate"]

    # Current household aggregate
    out["aggregate"] = a

    # Past-only lag features to avoid future leakage
    out["lag_1"] = a.shift(1)
    out["lag_2"] = a.shift(2)
    out["lag_5"] = a.shift(5)
    out["lag_10"] = a.shift(10)

    # Backward-looking rolling features
    out["mean_3"] = a.rolling(3, min_periods=3).mean()
    out["mean_5"] = a.rolling(5, min_periods=5).mean()
    out["mean_15"] = a.rolling(15, min_periods=15).mean()

    out["std_5"] = a.rolling(5, min_periods=5).std()

    out["diff_1"] = a.diff(1)

    # Calendar features
    out["hour"] = df.index.hour
    out["weekday"] = df.index.day_of_week

    out["washer"] = df["washer"]

    # Keep only rows where target and all features are known
    out = out.dropna()

    return out


def prepare_house(house):
    print(f"Preparing House {house}...")

    raw = load_house(house)
    prepared = make_features(raw)

    print(f"  usable rows: {len(prepared):,}")
    print(
        f"  active washer minutes: "
        f"{(prepared['washer'] > ON_THRESHOLD_W).sum():,}"
    )

    return prepared


def training_sample(df, max_off_rows=300_000):
    """
    Keep every active washer minute, but sample the much larger
    off-state population for faster and less imbalanced training.
    Evaluation remains on the complete held-out households.
    """

    active = df[df["washer"] > ON_THRESHOLD_W]
    inactive = df[df["washer"] <= ON_THRESHOLD_W]

    if len(inactive) > max_off_rows:
        inactive = inactive.sample(
            max_off_rows,
            random_state=RANDOM_STATE
        )

    sampled = pd.concat([active, inactive])

    return sampled.sample(
        frac=1,
        random_state=RANDOM_STATE
    )


def evaluate(name, df, model, hour_profile):
    features = [
        c for c in df.columns
        if c != "washer"
    ]

    X = df[features]
    y = df["washer"].to_numpy()

    pred = model.predict(X)
    pred = np.clip(pred, 0, None)

    # Baseline 1: always off
    pred_off = np.zeros_like(y)

    # Baseline 2: average washer power by hour of day
    pred_hour = (
        pd.Series(df.index.hour, index=df.index)
        .map(hour_profile)
        .fillna(0)
        .to_numpy()
    )

    def metrics(prediction):
        mae = mean_absolute_error(y, prediction)
        rmse = np.sqrt(mean_squared_error(y, prediction))

        true_on = y > ON_THRESHOLD_W
        pred_on = prediction > ON_THRESHOLD_W

        precision = precision_score(
            true_on,
            pred_on,
            zero_division=0
        )

        recall = recall_score(
            true_on,
            pred_on,
            zero_division=0
        )

        f1 = f1_score(
            true_on,
            pred_on,
            zero_division=0
        )

        true_energy = y.sum() / 60 / 1000
        pred_energy = prediction.sum() / 60 / 1000

        if true_energy > 0:
            energy_error_pct = (
                100 * (pred_energy - true_energy) / true_energy
            )
        else:
            energy_error_pct = np.nan

        active_mask = true_on

        active_mae = (
            mean_absolute_error(
                y[active_mask],
                prediction[active_mask]
            )
            if active_mask.any()
            else np.nan
        )

        return {
            "MAE_W": mae,
            "RMSE_W": rmse,
            "Active_MAE_W": active_mae,
            "Precision": precision,
            "Recall": recall,
            "F1": f1,
            "True_Energy_kWh": true_energy,
            "Pred_Energy_kWh": pred_energy,
            "Energy_Error_pct": energy_error_pct,
        }

    results = {
        "always_off": metrics(pred_off),
        "hour_profile": metrics(pred_hour),
        "gradient_boosting": metrics(pred),
    }

    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

    for model_name, result in results.items():
        print(f"\n{model_name}")

        for key, value in result.items():
            print(f"  {key}: {value:.4f}")

    return pred, results


# -------------------------------------------------------
# Load data
# -------------------------------------------------------

train_parts = [
    prepare_house(h)
    for h in TRAIN_HOUSES
]

train_full = pd.concat(train_parts).sort_index()

val = prepare_house(VAL_HOUSE)
test = prepare_house(TEST_HOUSE)

# -------------------------------------------------------
# Hour-of-day baseline learned ONLY from training homes
# -------------------------------------------------------

hour_profile = (
    train_full
    .assign(hour=train_full.index.hour)
    .groupby("hour")["washer"]
    .mean()
)

# -------------------------------------------------------
# Downsample off-state rows for manageable training
# -------------------------------------------------------

train = train_full.copy()

print("\nTRAINING SET")
print(f"Rows used: {len(train):,}")
print(
    f"Active rows: "
    f"{(train['washer'] > ON_THRESHOLD_W).sum():,}"
)

features = [
    c for c in train.columns
    if c != "washer"
]

X_train = train[features]
y_train = train["washer"]

# Give active washer periods more influence during fitting.


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

print("\nTraining gradient boosting model...")

model.fit(
    X_train,
    y_train
)

print("Training complete.")

# -------------------------------------------------------
# Validation
# -------------------------------------------------------

val_pred, val_results = evaluate(
    "VALIDATION — House 6",
    val,
    model,
    hour_profile
)

# -------------------------------------------------------
# Final unseen-house test
# -------------------------------------------------------

test_pred, test_results = evaluate(
    "TEST — House 15",
    test,
    model,
    hour_profile
)

# -------------------------------------------------------
# Save metrics
# -------------------------------------------------------

metrics = {
    "split": {
        "train_houses": TRAIN_HOUSES,
        "validation_house": VAL_HOUSE,
        "test_house": TEST_HOUSE,
    },
    "validation": val_results,
    "test": test_results,
}

with open(
    "model_metrics.json",
    "w"
) as f:
    json.dump(metrics, f, indent=2)

# -------------------------------------------------------
# Actual vs predicted plot
# Choose a 48-hour window containing strong washer activity
# -------------------------------------------------------

plot_df = test.copy()
plot_df["prediction"] = test_pred

daily_energy = (
    plot_df["washer"]
    .resample("1D")
    .sum()
)

active_days = daily_energy[daily_energy > 0]

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
    "House 15: actual vs predicted washing-machine power"
)
plt.legend()
plt.tight_layout()

plt.savefig(
    FIG_DIR / "model_actual_vs_predicted.png",
    dpi=160
)

plt.close()

# -------------------------------------------------------
# Failure-case plots
# -------------------------------------------------------

plot_df["abs_error"] = np.abs(
    plot_df["washer"] -
    plot_df["prediction"]
)

# Largest false positive
false_positive = plot_df[
    (plot_df["washer"] <= ON_THRESHOLD_W)
    &
    (plot_df["prediction"] > ON_THRESHOLD_W)
]

# Largest false negative
false_negative = plot_df[
    (plot_df["washer"] > ON_THRESHOLD_W)
    &
    (plot_df["prediction"] <= ON_THRESHOLD_W)
]


def plot_failure(rows, filename, title):
    if rows.empty:
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

    plt.ylabel("Power (W)")
    plt.xlabel("Time")
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
    "failure_false_positive.png",
    "Failure case: false-positive washer detection"
)

plot_failure(
    false_negative,
    "failure_false_negative.png",
    "Failure case: missed washing-machine activity"
)

# Save predictions locally; data/processed is gitignored.
prediction_output = test[["washer", "aggregate"]].copy()
prediction_output["prediction"] = test_pred

prediction_output.to_parquet(
    DATA_DIR / "house15_model_predictions.parquet"
)

print("\nSaved:")
print("model_metrics.json")
print("figures/model_actual_vs_predicted.png")
print("figures/failure_false_positive.png")
print("figures/failure_false_negative.png")
print("data/processed/house15_model_predictions.parquet")
