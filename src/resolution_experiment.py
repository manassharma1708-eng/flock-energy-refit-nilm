from pathlib import Path

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

RESOLUTIONS = [1, 5, 15, 30]
ON_THRESHOLD_W = 20
RANDOM_STATE = 42


def load_house(house):
    return pd.read_parquet(
        DATA_DIR / f"house{house}_clean_1min.parquet"
    )[["Aggregate", "washer"]].copy()


def resample_house(df, minutes):
    if minutes == 1:
        return df.copy()

    return df.resample(f"{minutes}min").mean()


def make_features(df):
    out = pd.DataFrame(index=df.index)

    a = df["Aggregate"]

    out["aggregate"] = a
    out["lag_1"] = a.shift(1)
    out["lag_2"] = a.shift(2)
    out["lag_5"] = a.shift(5)

    out["mean_3"] = a.rolling(3, min_periods=3).mean()
    out["mean_5"] = a.rolling(5, min_periods=5).mean()

    out["std_3"] = a.rolling(3, min_periods=3).std()
    out["diff_1"] = a.diff()

    out["hour"] = df.index.hour
    out["weekday"] = df.index.day_of_week

    out["washer"] = df["washer"]

    return out.dropna()


def prepare_house(house, resolution):
    df = load_house(house)
    df = resample_house(df, resolution)

    return make_features(df)


def evaluate(y, pred):
    pred = np.clip(pred, 0, None)

    true_on = y > ON_THRESHOLD_W
    pred_on = pred > ON_THRESHOLD_W

    mae = mean_absolute_error(y, pred)
    rmse = np.sqrt(mean_squared_error(y, pred))

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

    # Each sample represents resolution minutes.
    # Energy = sum(W * hours) / 1000.
    return mae, rmse, precision, recall, f1


results = []

for resolution in RESOLUTIONS:

    print("\n" + "=" * 80)
    print(f"{resolution}-MINUTE RESOLUTION")
    print("=" * 80)

    train_parts = [
        prepare_house(h, resolution)
        for h in TRAIN_HOUSES
    ]

    train = pd.concat(train_parts)

    validation = prepare_house(
        VAL_HOUSE,
        resolution
    )

    test = prepare_house(
        TEST_HOUSE,
        resolution
    )

    features = [
        c for c in train.columns
        if c != "washer"
    ]

    model = HistGradientBoostingRegressor(
        learning_rate=0.08,
        max_iter=180,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        random_state=RANDOM_STATE,
    )

    model.fit(
        train[features],
        train["washer"]
    )

    # --------------------------------------------------
    # Select prediction threshold using validation house
    # --------------------------------------------------

    val_pred = np.clip(
        model.predict(validation[features]),
        0,
        None
    )

    thresholds = [
        10, 20, 30, 40, 50,
        75, 100, 150, 200
    ]

    best_threshold = 20
    best_f1 = -1

    val_true = (
        validation["washer"].to_numpy()
        > ON_THRESHOLD_W
    )

    for threshold in thresholds:

        val_state = val_pred > threshold

        score = f1_score(
            val_true,
            val_state,
            zero_division=0
        )

        if score > best_f1:
            best_f1 = score
            best_threshold = threshold

    print(
        f"Validation-selected prediction threshold: "
        f"{best_threshold} W"
    )

    # --------------------------------------------------
    # Final test
    # --------------------------------------------------

    y = test["washer"].to_numpy()

    pred = np.clip(
        model.predict(test[features]),
        0,
        None
    )

    mae = mean_absolute_error(y, pred)
    rmse = np.sqrt(mean_squared_error(y, pred))

    true_on = y > ON_THRESHOLD_W
    pred_on = pred > best_threshold

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

    true_energy = (
        y.sum()
        * resolution
        / 60
        / 1000
    )

    pred_energy = (
        pred.sum()
        * resolution
        / 60
        / 1000
    )

    energy_error = (
        100
        * (pred_energy - true_energy)
        / true_energy
    )

    print(f"MAE: {mae:.3f} W")
    print(f"RMSE: {rmse:.3f} W")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")
    print(f"F1: {f1:.3f}")
    print(
        f"Energy error: "
        f"{energy_error:.2f}%"
    )

    results.append({
        "resolution_min": resolution,
        "prediction_threshold_w": best_threshold,
        "MAE_W": mae,
        "RMSE_W": rmse,
        "Precision": precision,
        "Recall": recall,
        "F1": f1,
        "True_Energy_kWh": true_energy,
        "Pred_Energy_kWh": pred_energy,
        "Energy_Error_pct": energy_error,
    })


results = pd.DataFrame(results)

print("\nFINAL RESOLUTION COMPARISON")
print(results.to_string(index=False))

results.to_csv(
    "resolution_results.csv",
    index=False
)

# --------------------------------------------------
# F1 degradation plot
# --------------------------------------------------

plt.figure(figsize=(8, 5))

plt.plot(
    results["resolution_min"],
    results["F1"],
    marker="o"
)

plt.xlabel("Smart-meter resolution (minutes)")
plt.ylabel("F1 score")
plt.title(
    "Washing-machine detection vs meter resolution"
)

plt.xticks(RESOLUTIONS)

plt.tight_layout()

plt.savefig(
    FIG_DIR / "resolution_f1.png",
    dpi=160
)

plt.close()

# --------------------------------------------------
# Energy error plot
# --------------------------------------------------

plt.figure(figsize=(8, 5))

plt.plot(
    results["resolution_min"],
    results["Energy_Error_pct"],
    marker="o"
)

plt.axhline(
    0,
    linewidth=1
)

plt.xlabel("Smart-meter resolution (minutes)")
plt.ylabel("Energy error (%)")
plt.title(
    "Washing-machine energy error vs meter resolution"
)

plt.xticks(RESOLUTIONS)

plt.tight_layout()

plt.savefig(
    FIG_DIR / "resolution_energy_error.png",
    dpi=160
)

plt.close()

print("\nSaved:")
print("resolution_results.csv")
print("figures/resolution_f1.png")
print("figures/resolution_energy_error.png")
