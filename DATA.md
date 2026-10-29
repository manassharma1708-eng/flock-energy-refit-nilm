# REFIT Data Quality and Cleaning

## 1. Raw House 1 inspection

House 1 was analysed using the two raw REFIT files before any
cleaning or resampling.

### Initial coverage

| File | Rows | Start | End |
|---|---:|---|---|
| Part 1 | 4,377,877 | 2013-10-09 14:06:17 | 2014-10-01 01:27:07 |
| Part 2 | 4,140,886 | 2014-06-27 21:57:50 | 2015-07-10 11:56:32 |

The files overlap from 27 June 2014 to 1 October 2014, so they
cannot be concatenated blindly.

### Initial timestamp findings

Part 1 contained 1,004,253 repeated UNIX timestamps, compared with
14,755 in Part 2. Part 1 also contained at least one backwards time
jump, with a minimum observed interval of -3,597 seconds.

Long gaps were present in both files. The maximum observed gap was
approximately 41.6 days in Part 1 and 8.65 days in Part 2.

These anomalies are investigated before defining the final
deduplication and outage-handling rules.

### Missing values

Part 1 contained no explicit NaN values. This is consistent with the
REFIT raw-data documentation, which states that unavailable sensors
in Part 1 were represented as zero.

Part 2 explicitly represents unavailable sensor readings as NaN.
Missingness varies substantially between channels. Aggregate power
is missing in approximately 4.6% of rows, while the House 1 washing
machine channel (Appliance5) is missing in approximately 12.0%.

### Initial power-value findings

No negative power readings were detected.

However, several appliance channels contain extreme values far above
typical domestic appliance loads, including readings above 30 kW and
values approaching 100 kW. These readings are treated as candidates
for sensor errors or spikes and are investigated before a cleaning
threshold is chosen.