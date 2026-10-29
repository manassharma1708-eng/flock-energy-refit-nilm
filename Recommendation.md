# Utility Recommendation

## Executive summary

This project tested whether household smart-meter readings can be used to infer washing-machine activity without installing appliance-level meters.

Using REFIT data, a gradient-boosting model was trained on Houses 2 and 5, validated on House 6, and tested on the completely unseen House 15.

On House 15, the model achieved:

- F1 score: 0.571
- MAE: 14.84 W
- RMSE: 127.66 W
- washing-machine recall: 0.575
- washing-machine precision: 0.567

The model therefore shows useful ability to detect appliance activity from household-level data, but its appliance-energy estimate was not sufficiently accurate for billing or precise consumption attribution.

## Recommended use

A realistic utility use case is **identifying households that frequently operate flexible appliances during peak-demand periods**.

For example, estimated washing-machine activity could be used to identify customers who frequently run laundry during evening peaks and offer them incentives or personalised messages encouraging off-peak operation.

The model should be used as a behavioural segmentation signal rather than an exact appliance meter.

## How to measure success

A utility could evaluate the intervention using a randomised control trial.

Customers identified as frequent peak-period washing-machine users would be split into:

- treatment group receiving an off-peak laundry nudge or tariff incentive
- control group receiving no intervention

The primary KPI would be:

**share of detected washing-machine cycles starting during the peak period**

Secondary measures could include:

- estimated peak-period washing-machine kWh
- change in total household peak demand
- customer engagement with the message
- persistence of behaviour change after several weeks

A pre/post comparison between treatment and control groups would help separate intervention effects from seasonal or household-level changes.

## Model limitations

### Overlapping appliance signatures

The household aggregate contains the combined demand of many devices.

Kettles, heaters, dishwashers and other high-power appliances can temporarily resemble parts of a washing-machine cycle.

This produces both false positives and false negatives.

### Missing data

The REFIT dataset contains outages and missing measurements.

The official cleaned dataset also forward-fills some missing readings, which can hide the original structure of outages.

Predictions during poor-quality periods should therefore be treated cautiously.

### Household differences

Washing machines differ by model, programme, load size and user behaviour.

This was visible in the EDA: House 5 had substantially shorter and lower-energy detected cycles than the other selected homes.

The model also showed different energy-estimation errors between validation House 6 and test House 15, demonstrating that cross-house calibration is difficult.

### UK to India transfer

REFIT contains UK households and appliances.

Direct transfer to Indian homes would be risky because of differences in:

- appliance brands and washing-machine types
- top-load versus front-load usage
- wash programmes
- household size
- water-heating behaviour
- voltage conditions
- appliance ownership
- electricity tariffs
- time-of-day usage patterns

REFIT is therefore useful for demonstrating the methodology, but deployment in India should include Indian household data for calibration and validation.

## Effect of 15-minute or 30-minute smart-meter data

The current analysis uses one-minute data.

At 15- or 30-minute resolution, short appliance states would be averaged together with other household demand.

This would make it harder to identify:

- cycle start and end times
- short heating phases
- transient power changes
- overlapping appliance events
- exact cycle duration

Energy estimation over longer periods may still be possible, but appliance-event detection would become substantially less precise.

## Recommendation

The current approach is suitable for:

- approximate appliance activity detection
- behavioural segmentation
- demand-response targeting
- peak-load flexibility analysis
- customer energy insights

It is not yet suitable for:

- appliance-level billing
- exact per-cycle energy accounting
- safety-critical decisions
- high-confidence appliance identification in every household

The most valuable next step would be to train and validate the model on a larger and more geographically representative set of households, including Indian smart-meter data, before production deployment.