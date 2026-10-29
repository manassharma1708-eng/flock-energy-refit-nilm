from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")
FIG_DIR = Path("figures")

OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

FILE1 = RAW_DIR / "RAW_House1_Part1.csv"
FILE2 = RAW_DIR / "RAW_House1_Part2.csv"

POWER_COLS = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
USECOLS = ["Unix"] + POWER_COLS

dtype = {"Unix": "int64"}
dtype.update({c: "float32" for c in POWER_COLS})


def load_and_dedupe(path):
    print(f"Loading {path.name}...")
    df = pd.read_csv(path, usecols=USECOLS, dtype=dtype)

    before = len(df)

    # Multiple sensor updates can share the same UNIX second.
    # Average available readings rather than arbitrarily choosing a row.
    df = (
        df.groupby("Unix", as_index=False, sort=True)[POWER_COLS]
        .mean()
    )

    print(f"  rows before dedupe: {before:,}")
    print(f"  unique timestamps:  {len(df):,}")

    return df


p1 = load_and_dedupe(FILE1)
p2 = load_and_dedupe(FILE2)

# Prefer Part 2 wherever the files overlap because Part 2 explicitly
# represents unavailable sensors as NaN rather than zero.
p2_start = p2["Unix"].min()

p1 = p1[p1["Unix"] < p2_start].copy()

df = pd.concat([p1, p2], ignore_index=True)
df = df.sort_values("Unix").reset_index(drop=True)

print("\nCombined coverage:")
print(pd.to_datetime(df["Unix"].min(), unit="s", utc=True))
print(pd.to_datetime(df["Unix"].max(), unit="s", utc=True))
print(f"Rows after merge: {len(df):,}")

# Use UNIX timestamps as the authoritative chronology.
df["timestamp"] = pd.to_datetime(df["Unix"], unit="s", utc=True)

# Save a pre-cleaning copy for plotting.
raw_for_plot = df[["timestamp", "Aggregate", "Appliance1", "Appliance5"]].copy()

# Individual appliance readings above 4 kW are treated as unreliable spikes.
# Aggregate is NOT thresholded because whole-home demand may legitimately exceed 4 kW.
outlier_counts = {}

for col in [f"Appliance{i}" for i in range(1, 10)]:
    mask = df[col] > 4000
    outlier_counts[col] = int(mask.sum())
    df.loc[mask, col] = np.nan

print("\nAppliance readings > 4000 W set to NaN:")
for col, count in outlier_counts.items():
    print(f"{col}: {count:,}")

df = df.set_index("timestamp")

# 1-minute mean
minute = df[POWER_COLS].resample("1min").mean()

# Identify long aggregate outages BEFORE filling.
missing = minute["Aggregate"].isna()
groups = missing.ne(missing.shift()).cumsum()
run_length = missing.groupby(groups).transform("sum")

minute["long_outage"] = missing & (run_length > 2)

# Fill only missing runs of <= 2 minutes.
for col in POWER_COLS:
    miss = minute[col].isna()
    grp = miss.ne(miss.shift()).cumsum()
    lengths = miss.groupby(grp).transform("sum")

    short_gap = miss & (lengths <= 2)

    interpolated = minute[col].interpolate(
        method="time",
        limit_area="inside"
    )

    minute.loc[short_gap, col] = interpolated.loc[short_gap]

print("\n1-minute output:")
print(f"Rows: {len(minute):,}")
print(f"Long-outage minutes: {minute['long_outage'].sum():,}")
print(f"Remaining Aggregate NaNs: {minute['Aggregate'].isna().sum():,}")

# Pick a representative day containing washing-machine activity.
daily_peak = minute["Appliance5"].resample("1D").max()
candidate_days = daily_peak[daily_peak > 100]

if len(candidate_days):
    selected_day = candidate_days.index[0]
else:
    selected_day = minute.index[0].normalize()

end_day = selected_day + pd.Timedelta(days=1)

# BEFORE CLEANING
raw_day = raw_for_plot[
    (raw_for_plot["timestamp"] >= selected_day) &
    (raw_for_plot["timestamp"] < end_day)
]

plt.figure(figsize=(14, 6))
plt.plot(raw_day["timestamp"], raw_day["Aggregate"], label="Aggregate", alpha=0.8)
plt.plot(raw_day["timestamp"], raw_day["Appliance1"], label="Fridge", alpha=0.8)
plt.plot(raw_day["timestamp"], raw_day["Appliance5"], label="Washing machine", alpha=0.8)
plt.ylabel("Power (W)")
plt.xlabel("Time")
plt.title("House 1 raw readings — representative 24 hours")
plt.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "house1_before_cleaning.png", dpi=160)
plt.close()

# AFTER CLEANING
clean_day = minute.loc[selected_day:end_day]

plt.figure(figsize=(14, 6))
plt.plot(clean_day.index, clean_day["Aggregate"], label="Aggregate", alpha=0.8)
plt.plot(clean_day.index, clean_day["Appliance1"], label="Fridge", alpha=0.8)
plt.plot(clean_day.index, clean_day["Appliance5"], label="Washing machine", alpha=0.8)
plt.ylabel("Power (W)")
plt.xlabel("Time")
plt.title("House 1 cleaned and resampled to 1 minute")
plt.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "house1_after_cleaning.png", dpi=160)
plt.close()

minute.to_parquet(OUT_DIR / "house1_1min.parquet")

print("\nSaved:")
print(OUT_DIR / "house1_1min.parquet")
print(FIG_DIR / "house1_before_cleaning.png")
print(FIG_DIR / "house1_after_cleaning.png")
