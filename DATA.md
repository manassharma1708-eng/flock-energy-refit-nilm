# Data Quality and Cleaning

## Dataset

This project uses the REFIT Electrical Load Measurements dataset from the University of Strathclyde.

REFIT contains whole-home aggregate electricity demand together with individual appliance measurements for 20 UK households. Power is recorded in watts, with nominal sampling around 8 seconds.

For the raw-data cleaning task, House 1 was used as required by the assignment.

For washing-machine analysis and modelling, the official cleaned data from Houses 2, 5, 6, and 15 was used.

---

## 1. Raw House 1 inspection

Two raw House 1 files were analysed:

| File | Rows | Start | End |
|---|---:|---|---|
| RAW_House1_Part1.csv | 4,377,877 | 2013-10-09 14:06:17 | 2014-10-01 01:27:07 |
| RAW_House1_Part2.csv | 4,140,886 | 2014-06-27 21:57:50 | 2015-07-10 11:56:32 |

The two files overlap between 27 June 2014 and 1 October 2014 and therefore cannot be concatenated blindly.

### Timestamp quality

No timestamp parsing failures were found.

Part 1 contained:

- 1,004,404 repeated UNIX timestamps
- 1,003,950 consecutive duplicate timestamps
- one backwards timestamp jump
- median positive sampling interval of 7 seconds

The backwards jump occurred during the UK daylight-saving clock change on 27 October 2013. For chronology, UNIX timestamps were therefore treated as the authoritative time reference.

Part 2 was substantially cleaner:

- 14,755 repeated UNIX timestamps
- no backwards jumps
- median positive sampling interval of 7 seconds

### Duplicate timestamps

Duplicate timestamps were not always identical.

Part 1 contained approximately:

- 883,358 exact consecutive duplicates
- 120,592 conflicting consecutive duplicates

Part 2 contained:

- 393 exact consecutive duplicates
- 14,362 conflicting consecutive duplicates

Because multiple sensor updates may occur during the same UNIX second, duplicate timestamps were collapsed by averaging available measurements at each timestamp rather than arbitrarily retaining the first or last row.

---

## 2. Missing data

Part 1 contained no explicit NaN values.

Part 2 contained substantial missingness:

| Channel | Missing rows |
|---|---:|
| Aggregate | 188,973 |
| Appliance1 | 437,890 |
| Appliance2 | 459,468 |
| Appliance3 | 311,961 |
| Appliance4 | 510,963 |
| Appliance5 | 497,223 |
| Appliance6 | 342,337 |
| Appliance7 | 232,752 |
| Appliance8 | 390,705 |
| Appliance9 | 1,911,811 |

This difference is consistent with the REFIT raw-data format: unavailable sensors in Part 1 were represented as zero, while Part 2 used NaN.

Because Part 2 preserves the distinction between true zero consumption and unavailable measurements, Part 2 was preferred wherever the two files overlap.

---

## 3. Extreme values

No negative power readings were detected.

However, several individual appliance channels contained implausibly high values, including values above 30 kW and readings approaching 100 kW.

Examples of observed maxima included:

- Appliance1: above 69 kW
- Appliance2: above 98 kW
- Appliance4: above 98 kW
- Appliance8: above 98 kW

These values are not credible for the monitored domestic appliances.

The official REFIT cleaned dataset also treats individual-appliance measurements above 4,000 W as spikes.

For this project:

- appliance values above 4,000 W were treated as unreliable and converted to missing values
- the household Aggregate channel was not subjected to this threshold because whole-home demand can legitimately exceed 4 kW

---

## 4. Cleaning pipeline

The raw House 1 cleaning pipeline was:

1. Parse and validate timestamps.
2. Use UNIX time as the authoritative chronological field.
3. Group repeated UNIX timestamps and average available readings.
4. Prefer Part 2 during the Part 1 / Part 2 overlap.
5. Sort observations chronologically.
6. Flag individual-appliance values above 4,000 W as missing.
7. Resample the data to 1-minute mean power.
8. Interpolate only missing runs of two minutes or less.
9. Leave longer gaps missing and flag them as outages.

This produced:

- 6,663,716 observations after duplicate resolution and overlap handling
- 920,031 one-minute rows
- 119,063 minutes flagged as long outages

Long outages were intentionally not filled because doing so would introduce unsupported synthetic consumption.

---

## 5. Before and after cleaning

The repository contains:

- `figures/house1_before_cleaning.png`
- `figures/house1_after_cleaning.png`

Both show Aggregate, refrigerator, and washing-machine power over a representative period.

The cleaned version is easier to interpret because duplicate timestamps, extreme appliance spikes, irregular sampling, and short gaps have been handled before resampling to one-minute resolution.

---

## 6. Official cleaned REFIT data

Sections 2 and 3 use the official cleaned REFIT data rather than the custom House 1 output.

The selected homes and washing-machine channels are:

| House | Washing-machine channel |
|---:|---|
| 2 | Appliance2 |
| 5 | Appliance3 |
| 6 | Appliance2 |
| 15 | Appliance3 |

Known REFIT cleaned-data limitations were retained in the analysis:

- missing values were forward-filled during the official REFIT cleaning process
- individual appliance spikes above 4,000 W were replaced
- an `Issues` flag identifies observations where submeter totals exceed household aggregate

Rows flagged with `Issues = 1` were not treated as reliable ground truth during the processed analysis.

---

## 7. Remaining limitations

The raw data contains long outages and irregular sensor reporting.

The official cleaned data improves usability but does not eliminate all uncertainty. Forward filling can hide outage periods as long constant runs, and appliance monitors are not perfectly synchronized with the household aggregate.

The selected cleaning pipeline is intentionally simple and reproducible rather than attempting to reproduce the full specialised REFIT cleaning procedure.