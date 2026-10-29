from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = Path("data/cleaned")
OUT_DIR = Path("data/processed")
FIG_DIR = Path("figures")

OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

HOUSES = {
    2: "Appliance2",
    5: "Appliance3",
    6: "Appliance2",
    15: "Appliance3",
    19: "Appliance2",
}

THRESHOLD_W = 20
MAX_INTERNAL_GAP_MIN = 5
MIN_CYCLE_MIN = 15
MIN_PEAK_W = 100


def find_file(house):
    matches = list(DATA_DIR.glob(f"*House{house}*.csv"))

    if not matches:
        matches = list(DATA_DIR.glob(f"*House_{house}*.csv"))

    if not matches:
        raise FileNotFoundError(f"No cleaned CSV found for House {house}")

    return matches[0]


def merge_short_off_gaps(active, max_gap=5):
    active = active.copy()

    groups = active.ne(active.shift()).cumsum()

    for _, idx in active.groupby(groups).groups.items():
        idx = list(idx)

        if not active.loc[idx[0]] and len(idx) <= max_gap:
            first = idx[0]
            last = idx[-1]

            pos_first = active.index.get_loc(first)
            pos_last = active.index.get_loc(last)

            has_before = pos_first > 0
            has_after = pos_last < len(active) - 1

            if has_before and has_after:
                before = active.iloc[pos_first - 1]
                after = active.iloc[pos_last + 1]

                if before and after:
                    active.loc[idx] = True

    return active


def detect_cycles(df):
    active = df["washer"] > THRESHOLD_W
    active = merge_short_off_gaps(active, MAX_INTERNAL_GAP_MIN)

    event_start = active & ~active.shift(fill_value=False)
    event_id = event_start.cumsum()

    cycles = []

    for event, grp in df[active].groupby(event_id[active]):
        if len(grp) < MIN_CYCLE_MIN:
            continue

        peak = grp["washer"].max()

        if peak < MIN_PEAK_W:
            continue

        cycles.append({
            "cycle_id": int(event),
            "start": grp.index.min(),
            "end": grp.index.max(),
            "duration_min": len(grp),
            "peak_w": peak,
            "energy_kwh": grp["washer"].sum() / 60 / 1000,
        })

    return pd.DataFrame(cycles)


all_cycles = []
summaries = []
processed = {}

for house, washer_col in HOUSES.items():

    path = find_file(house)

    print("\n" + "=" * 80)
    print(f"HOUSE {house}: {path.name}")
    print("=" * 80)

    header = pd.read_csv(path, nrows=0).columns.tolist()

    usecols = ["Unix", "Aggregate", washer_col]

    if "Issues" in header:
        usecols.append("Issues")

    df = pd.read_csv(path, usecols=usecols)

    df["Unix"] = pd.to_numeric(df["Unix"], errors="coerce")
    df = df.dropna(subset=["Unix"])

    df["timestamp"] = pd.to_datetime(
        df["Unix"],
        unit="s",
        utc=True
    )

    df = df.sort_values("timestamp")

    # Average repeated observations at each timestamp.
    agg_dict = {
        "Aggregate": "mean",
        washer_col: "mean",
    }

    if "Issues" in df.columns:
        agg_dict["Issues"] = "max"

    df = (
        df.groupby("timestamp")
        .agg(agg_dict)
        .sort_index()
    )

    df = df.rename(columns={washer_col: "washer"})

    # Known discrepancy rows should not be used as reliable ground truth.
    if "Issues" in df.columns:
        issue_rate = 100 * df["Issues"].eq(1).mean()

        bad = df["Issues"].eq(1)
        df.loc[bad, ["Aggregate", "washer"]] = np.nan
    else:
        issue_rate = np.nan

    minute = df[["Aggregate", "washer"]].resample("1min").mean()

    expected_minutes = len(minute)
    missing_minutes = minute["Aggregate"].isna().sum()

    off_pct = 100 * (minute["washer"].fillna(0) <= THRESHOLD_W).mean()

    cycles = detect_cycles(minute)

    if len(cycles):
        cycles["house"] = house
        cycles["start_hour"] = cycles["start"].dt.hour
        cycles["weekday"] = cycles["start"].dt.day_name()

        all_cycles.append(cycles)

    summaries.append({
        "house": house,
        "start": minute.index.min(),
        "end": minute.index.max(),
        "minutes": expected_minutes,
        "missing_minutes": int(missing_minutes),
        "missing_pct": 100 * missing_minutes / expected_minutes,
        "issues_pct": issue_rate,
        "off_pct": off_pct,
        "cycles": len(cycles),
        "median_duration_min": (
            cycles["duration_min"].median()
            if len(cycles) else np.nan
        ),
        "median_energy_kwh": (
            cycles["energy_kwh"].median()
            if len(cycles) else np.nan
        ),
    })

    minute.to_parquet(
        OUT_DIR / f"house{house}_clean_1min.parquet"
    )

    processed[house] = minute

summary = pd.DataFrame(summaries)

cycles = (
    pd.concat(all_cycles, ignore_index=True)
    if all_cycles
    else pd.DataFrame()
)

print("\nHOUSE SUMMARY")
print(summary.to_string(index=False))

print("\nTOTAL DETECTED CYCLES:", len(cycles))

summary.to_csv(
    OUT_DIR / "washer_house_summary.csv",
    index=False
)

cycles.to_csv(
    OUT_DIR / "washer_cycles.csv",
    index=False
)

# ---------------------------------------------------------
# FIGURE 1: representative 24-hour aggregate + washer trace
# ---------------------------------------------------------

house = 2
m = processed[house]

daily_max = m["washer"].resample("1D").max()
candidate = daily_max[daily_max > 100]

if len(candidate):
    day = candidate.index[0]
else:
    day = m.index[0].normalize()

plot_day = m.loc[
    (m.index >= day) &
    (m.index < day + pd.Timedelta(days=1))
]

plt.figure(figsize=(14, 6))
plt.plot(
    plot_day.index,
    plot_day["Aggregate"],
    label="Aggregate",
    linewidth=1
)
plt.plot(
    plot_day.index,
    plot_day["washer"],
    label="Washing machine",
    linewidth=1.4
)

plt.ylabel("Power (W)")
plt.xlabel("Time")
plt.title("House 2: 24-hour aggregate and washing-machine load")
plt.legend()
plt.tight_layout()
plt.savefig(
    FIG_DIR / "washer_24h_trace.png",
    dpi=160
)
plt.close()

# ---------------------------------------------------------
# FIGURE 2: detected cycles
# ---------------------------------------------------------

if len(cycles):
    example = cycles.head(3)

    plt.figure(figsize=(12, 6))

    for _, cycle in example.iterrows():
        house = int(cycle["house"])
        m = processed[house]

        trace = m.loc[
            cycle["start"]:cycle["end"],
            "washer"
        ]

        elapsed = np.arange(len(trace))

        plt.plot(
            elapsed,
            trace.values,
            label=f"House {house}: {cycle['start'].date()}"
        )

    plt.xlabel("Minutes since detected cycle start")
    plt.ylabel("Washing-machine power (W)")
    plt.title("Example detected washing-machine cycles")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        FIG_DIR / "detected_washer_cycles.png",
        dpi=160
    )
    plt.close()

# ---------------------------------------------------------
# FIGURE 3: energy per cycle across households
# ---------------------------------------------------------

if len(cycles):
    houses = sorted(cycles["house"].unique())

    data = [
        cycles.loc[
            cycles["house"] == h,
            "energy_kwh"
        ].values
        for h in houses
    ]

    plt.figure(figsize=(9, 6))
    plt.boxplot(
        data,
        tick_labels=[str(h) for h in houses]
    )
    plt.xlabel("House")
    plt.ylabel("Energy per detected cycle (kWh)")
    plt.title("Washing-machine energy per cycle across households")
    plt.tight_layout()
    plt.savefig(
        FIG_DIR / "washer_energy_cross_house.png",
        dpi=160
    )
    plt.close()

# ---------------------------------------------------------
# Additional useful plots: cycle starts
# ---------------------------------------------------------

if len(cycles):

    hourly = (
        cycles.groupby("start_hour")
        .size()
        .reindex(range(24), fill_value=0)
    )

    plt.figure(figsize=(10, 5))
    hourly.plot(kind="bar")
    plt.xlabel("Hour of day")
    plt.ylabel("Detected cycle starts")
    plt.title("Washing-machine cycle starts by hour")
    plt.tight_layout()
    plt.savefig(
        FIG_DIR / "washer_cycle_starts_hour.png",
        dpi=160
    )
    plt.close()

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    weekdays = (
        cycles.groupby("weekday")
        .size()
        .reindex(weekday_order, fill_value=0)
    )

    plt.figure(figsize=(10, 5))
    weekdays.plot(kind="bar")
    plt.xlabel("Day of week")
    plt.ylabel("Detected cycle starts")
    plt.title("Washing-machine cycle starts by weekday")
    plt.tight_layout()
    plt.savefig(
        FIG_DIR / "washer_cycle_starts_weekday.png",
        dpi=160
    )
    plt.close()

print("\nSaved EDA outputs and figures.")
