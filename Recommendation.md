# Utility Recommendation

## Executive summary

This project evaluated whether washing-machine activity can be estimated from whole-home smart-meter measurements without dedicated appliance meters.

The final model used a strict household-level validation design:

- **Training:** Houses 2, 5, and 15
- **Validation:** House 6
- **Final untouched test:** House 19

The model configuration and prediction threshold were fixed before House 19 was evaluated.

On the final untouched household, the gradient-boosting model achieved:

- **Precision:** 0.359
- **Recall:** 0.497
- **F1:** 0.417
- **Active-state MAE:** 109.88 W
- **Actual washing-machine energy:** 58.52 kWh
- **Predicted washing-machine energy:** 77.29 kWh
- **Energy error:** +32.1%

The always-off baseline produced a lower overall MAE because the washing machine is inactive for most observations. However, it detected no appliance activity and had -100% energy error.

The gradient-boosting model therefore provides substantially more useful appliance-level information, despite not having the lowest global MAE.

## Recommended utility use case

The most realistic application is identifying customers who frequently operate flexible appliances during peak-demand periods.

For example, a utility could identify households whose estimated washing-machine activity regularly occurs during evening peaks and offer:

- off-peak tariff incentives
- personalised load-shifting recommendations
- demand-response notifications
- targeted energy-saving advice

The model should be treated as an approximate behavioural signal rather than an exact appliance meter.

## How to measure whether the intervention works

A utility could evaluate the intervention using a randomised controlled trial.

Eligible customers would be divided into:

- a treatment group receiving an off-peak laundry recommendation or incentive
- a control group receiving no intervention

The primary KPI would be the proportion of detected washing-machine activity occurring during peak-demand periods.

Secondary measures could include:

- estimated washing-machine kWh during peak periods
- total household peak demand
- customer engagement
- persistence of load shifting over time

A successful intervention would reduce peak-period appliance activity relative to the control group without materially reducing customer participation.

## Limitations

### Overlapping appliance signatures

Different appliances can create similar changes in whole-home aggregate demand.

A kettle, heater, dishwasher, cooking appliance, or several simultaneous loads may resemble parts of a washing-machine signature.

This creates unavoidable ambiguity when only aggregate power is available.

### Missing data

REFIT contains missing readings and outages.

Although the analysis excludes or flags unreliable periods, missing information can reduce the reliability of detected events.

### Household differences

Washing-machine behaviour varies substantially between households because of differences in:

- appliance model
- wash programme
- load size
- user behaviour
- background household demand

This is why performance on an unseen household is lower than performance seen during development.

### Energy calibration

The final House 19 energy error was **+32.1%**.

This is substantially better than the simple baselines but is not accurate enough for appliance billing or exact energy attribution.

## Applying UK results to India

REFIT contains UK households.

Direct deployment in India would require local validation because Indian households may differ in:

- top-load versus front-load washing-machine prevalence
- appliance brands and power profiles
- household size
- washing frequency
- appliance ownership
- electricity tariffs
- voltage conditions
- peak-demand periods
- time-of-day behaviour

The current work should therefore be treated as a methodological demonstration rather than evidence of production-ready performance in India.

A practical next step would be to validate the same pipeline using representative Indian smart-meter and appliance-level data.

## What becomes harder with 15- or 30-minute smart-meter data?

A separate sensitivity experiment tested 1-, 5-, 15-, and 30-minute resolution.

The classification F1 did not decrease monotonically because coarser intervals change the nature of the task. A 30-minute interval can average several appliance states together and may make broad activity classification appear easier.

However, lower temporal resolution removes information needed for detailed NILM.

At 15- or 30-minute resolution it becomes harder to identify:

- exact cycle start time
- exact cycle end time
- short heating stages
- low-power phases
- transient changes
- overlapping appliance events
- precise cycle duration

Energy estimates also remained materially biased.

Therefore 15- and 30-minute data may still support broad behavioural segmentation and demand-response targeting, but precise event reconstruction becomes substantially less reliable.

## Recommendation

The current model is suitable for further exploration in:

- behavioural segmentation
- flexible-load identification
- peak-demand analysis
- demand-response targeting
- customer energy insights

It is **not** suitable for:

- appliance-level billing
- exact cycle-level energy accounting
- safety-critical decisions
- guaranteed appliance identification

The strongest next step would be validation across more unseen households and on locally representative Indian smart-meter data.