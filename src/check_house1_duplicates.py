from pathlib import Path
import pandas as pd

FILES = [
    Path("data/raw/RAW_House1_Part1.csv"),
    Path("data/raw/RAW_House1_Part2.csv"),
]

POWER_COLS = ["Aggregate"] + [f"Appliance{i}" for i in range(1, 10)]
COLS = ["Time", "Unix"] + POWER_COLS
CHUNK_SIZE = 250_000


def scan_duplicates(path):
    exact_duplicates = 0
    conflicting_duplicates = 0
    examples = []
    previous = None

    for chunk in pd.read_csv(path, usecols=COLS, chunksize=CHUNK_SIZE):

        if previous is not None:
            chunk = pd.concat(
                [previous.to_frame().T, chunk],
                ignore_index=True
            )

        same_timestamp = chunk["Unix"].eq(chunk["Unix"].shift())

        current_values = chunk[POWER_COLS]
        previous_values = current_values.shift()

        same_values = (
            current_values.eq(previous_values)
            |
            (current_values.isna() & previous_values.isna())
        ).all(axis=1)

        exact_mask = same_timestamp & same_values
        conflict_mask = same_timestamp & ~same_values

        exact_duplicates += int(exact_mask.sum())
        conflicting_duplicates += int(conflict_mask.sum())

        if len(examples) < 10:
            conflict_positions = chunk.index[conflict_mask].tolist()

            for idx in conflict_positions:
                if len(examples) >= 10:
                    break

                examples.append(
                    chunk.iloc[max(0, idx - 1):idx + 1].copy()
                )

        previous = chunk.iloc[-1][COLS]

    print("\n" + "=" * 90)
    print(path.name)
    print("=" * 90)

    print(f"Exact consecutive duplicates:       {exact_duplicates:,}")
    print(f"Conflicting consecutive duplicates: {conflicting_duplicates:,}")

    if examples:
        print("\nCONFLICT EXAMPLES")
        print("-----------------")

        for example in examples:
            print(example.to_string(index=False))
            print()
    else:
        print("\nNo conflicting duplicate examples found.")


for file in FILES:
    scan_duplicates(file)
