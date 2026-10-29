from pathlib import Path
import pandas as pd
import numpy as np

FILES = [
    Path("data/raw/RAW_House1_Part1.csv"),
    Path("data/raw/RAW_House1_Part2.csv"),
]

POWER_COLS = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]

for path in FILES:
    print("\n" + "=" * 100)
    print(path.name)
    print("=" * 100)

    # Load timestamp columns only first
    ts = pd.read_csv(path, usecols=["Time", "Unix"])

    ts["Time"] = pd.to_datetime(ts["Time"], errors="coerce")
    ts["Unix"] = pd.to_numeric(ts["Unix"], errors="coerce")

    diff = ts["Unix"].diff()

    print("\nTIMESTAMP STRUCTURE")
    print("-------------------")
    print(f"Rows:                  {len(ts):,}")
    print(f"Unique UNIX timestamps:{ts['Unix'].nunique():,}")
    print(f"Repeated timestamp rows:{ts['Unix'].duplicated().sum():,}")
    print(f"Consecutive duplicates:{diff.eq(0).sum():,}")
    print(f"Backward jumps:        {(diff < 0).sum():,}")

    positive = diff[diff > 0]

    print("\nPositive interval quantiles (seconds):")
    print(
        positive.quantile(
            [0.01, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
        ).to_string()
    )

    # Show backward jumps
    bad_idx = np.flatnonzero((diff < 0).to_numpy())

    print("\nFIRST BACKWARD-JUMP EXAMPLES")
    print("----------------------------")

    if len(bad_idx) == 0:
        print("None")
    else:
        for idx in bad_idx[:10]:
            start = max(0, idx - 2)
            end = min(len(ts), idx + 3)
            print(ts.iloc[start:end].to_string(index=False))
            print()

    del ts

    # Power-value investigation
    print("\nPOWER VALUE INVESTIGATION")
    print("-------------------------")

    counts_gt_4000 = {c: 0 for c in POWER_COLS}
    counts_gt_10000 = {c: 0 for c in POWER_COLS}

    quantile_samples = []

    for chunk in pd.read_csv(
        path,
        usecols=POWER_COLS,
        chunksize=250_000
    ):
        for col in POWER_COLS:
            values = pd.to_numeric(chunk[col], errors="coerce")

            counts_gt_4000[col] += (values > 4000).sum()
            counts_gt_10000[col] += (values > 10000).sum()

        # small random sample for approximate distribution
        sample = chunk.sample(
            n=min(5000, len(chunk)),
            random_state=42
        )
        quantile_samples.append(sample)

    sample_df = pd.concat(quantile_samples, ignore_index=True)

    summary = []

    for col in POWER_COLS:
        values = pd.to_numeric(sample_df[col], errors="coerce")

        summary.append({
            "column": col,
            "p50": values.quantile(0.50),
            "p95": values.quantile(0.95),
            "p99": values.quantile(0.99),
            "p999": values.quantile(0.999),
            ">4000W": counts_gt_4000[col],
            ">10000W": counts_gt_10000[col],
        })

    summary = pd.DataFrame(summary)

    print(summary.to_string(index=False))
