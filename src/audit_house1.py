from pathlib import Path
import pandas as pd
import numpy as np

FILES = [
    Path("data/raw/RAW_House1_Part1.csv"),
    Path("data/raw/RAW_House1_Part2.csv"),
]

CHUNK_SIZE = 250_000


def audit_file(path):
    print("\n" + "=" * 90)
    print(f"AUDITING: {path.name}")
    print("=" * 90)

    total_rows = 0
    invalid_time = 0
    duplicate_unix = 0

    first_time = None
    last_time = None
    previous_last_unix = None

    missing_counts = None
    negative_counts = None
    min_values = None
    max_values = None

    interval_count = 0
    interval_sum = 0
    interval_min = None
    interval_max = None

    gap_gt_15 = 0
    gap_gt_30 = 0
    gap_gt_60 = 0
    gap_gt_300 = 0

    for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE):
        total_rows += len(chunk)

        # Parse timestamp
        parsed_time = pd.to_datetime(chunk["Time"], errors="coerce")
        invalid_time += parsed_time.isna().sum()

        if first_time is None and parsed_time.notna().any():
            first_time = parsed_time.dropna().iloc[0]

        if parsed_time.notna().any():
            last_time = parsed_time.dropna().iloc[-1]

        # Missing values
        chunk_missing = chunk.isna().sum()
        missing_counts = (
            chunk_missing
            if missing_counts is None
            else missing_counts.add(chunk_missing, fill_value=0)
        )

        # Numerical checks
        numeric_cols = [
            c for c in chunk.columns
            if c not in ["Time", "Unix"]
        ]

        numeric = chunk[numeric_cols]

        chunk_negative = (numeric < 0).sum()
        negative_counts = (
            chunk_negative
            if negative_counts is None
            else negative_counts.add(chunk_negative, fill_value=0)
        )

        chunk_min = numeric.min()
        chunk_max = numeric.max()

        min_values = (
            chunk_min
            if min_values is None
            else pd.concat([min_values, chunk_min], axis=1).min(axis=1)
        )

        max_values = (
            chunk_max
            if max_values is None
            else pd.concat([max_values, chunk_max], axis=1).max(axis=1)
        )

        # UNIX timestamp checks
        unix = pd.to_numeric(chunk["Unix"], errors="coerce")

        duplicate_unix += unix.duplicated().sum()

        # Catch duplicate across chunk boundary
        if previous_last_unix is not None and len(unix):
            if unix.iloc[0] == previous_last_unix:
                duplicate_unix += 1

        # Sampling intervals
        if previous_last_unix is not None and len(unix):
            unix_for_diff = pd.concat([
                pd.Series([previous_last_unix]),
                unix.reset_index(drop=True)
            ], ignore_index=True)
        else:
            unix_for_diff = unix.reset_index(drop=True)

        diffs = unix_for_diff.diff().dropna()
        diffs = diffs[np.isfinite(diffs)]

        if len(diffs):
            interval_count += len(diffs)
            interval_sum += diffs.sum()

            current_min = diffs.min()
            current_max = diffs.max()

            interval_min = (
                current_min if interval_min is None
                else min(interval_min, current_min)
            )
            interval_max = (
                current_max if interval_max is None
                else max(interval_max, current_max)
            )

            gap_gt_15 += (diffs > 15).sum()
            gap_gt_30 += (diffs > 30).sum()
            gap_gt_60 += (diffs > 60).sum()
            gap_gt_300 += (diffs > 300).sum()

        if len(unix):
            previous_last_unix = unix.iloc[-1]

    mean_interval = (
        interval_sum / interval_count if interval_count else np.nan
    )

    print(f"\nRows: {total_rows:,}")
    print(f"Start: {first_time}")
    print(f"End:   {last_time}")
    print(f"Invalid Time values: {invalid_time:,}")
    print(f"Duplicate UNIX timestamps: {duplicate_unix:,}")

    print("\nSampling intervals:")
    print(f"Mean interval: {mean_interval:.2f} sec")
    print(f"Minimum interval: {interval_min}")
    print(f"Maximum interval: {interval_max}")
    print(f"Gaps > 15 sec:  {gap_gt_15:,}")
    print(f"Gaps > 30 sec:  {gap_gt_30:,}")
    print(f"Gaps > 60 sec:  {gap_gt_60:,}")
    print(f"Gaps > 5 min:   {gap_gt_300:,}")

    print("\nMissing values:")
    print(missing_counts.astype("int64").to_string())

    print("\nNegative values:")
    print(negative_counts.astype("int64").to_string())

    print("\nMinimum values:")
    print(min_values.to_string())

    print("\nMaximum values:")
    print(max_values.to_string())


for file in FILES:
    audit_file(file)
