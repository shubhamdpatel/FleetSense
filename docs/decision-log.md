# FleetSense – Decision Log

## Decision 001: Hourly Seasonality Analysis

**Date:** 27 November 2026  
**Analysis period:** 1 January – 31 December 2025  
**Data source:** `clean_trips`  
**Status:** Initial analysis completed

### Client requirements

Day and Night demand must be reported separately.

- Day: 06:00–21:59
- Night: 22:00–05:59
- Shift is determined by pickup time.
- Do not use blended daily totals for operational reporting.

### Findings

**Day Shift**
- Busiest hour: 18:00 – 6,904.22 average trips per day.
- Quietest hour: 06:00 – 1,221.95 average trips per day.
- Demand generally increases through the day and peaks in the evening.

**Night Shift**
- Busiest hour: 22:00 – 4,927.52 average trips per day.
- Quietest hour: 04:00 – 450.02 average trips per day.
- Demand generally declines after 22:00, with a small recovery at 05:00.

### Validation

- Total hourly trips: 35,083,335.
- Previously verified 2025 trip count: 35,083,335.
- The two totals match.

### Anomaly investigation and handling

The lowest annual average at 04:00 is treated as an observed seasonal demand pattern, not a confirmed anomaly.

Annual hourly averages alone are insufficient to identify individual unusual dates. Daily demand observations must be investigated before an anomaly is confirmed or excluded.

No records have been removed or modified as part of this analysis.

### Decision

- Keep Day and Night reporting separate.
- Use hourly demand profiles to support shift-specific planning.
- Investigate unusual daily demand patterns separately by shift.
- Do not classify normal recurring seasonal patterns as anomalies without further investigation.

### Next steps

- Analyze weekday seasonality separately for Day and Night.
- Analyze monthly seasonality separately for Day and Night.
- Identify top and bottom pickup zones separately for Day and Night.
- Investigate and document confirmed anomalies.

## Decision 002: Weekday Seasonality Analysis

**Analysis period:** 1 January – 31 December 2025  
**Data source:** `clean_trips`  
**Status:** Analysis completed

### Client requirements

Day and Night demand must remain separate.

- Day: 06:00–21:59
- Night: 22:00–05:59

### Findings

**Day Shift**
- Busiest weekday: Thursday – 91,159.87 average trips per calendar day.
- Quietest weekday: Sunday – 63,137.19 average trips per calendar day.
- Demand is strongest during the middle of the working week and declines over the weekend.

**Night Shift**
- Busiest weekday: Saturday – 23,996.81 average trips per calendar day.
- Quietest weekday: Monday – 9,210.67 average trips per calendar day.
- Night demand increases toward the weekend, reaching its highest level on Saturday.

### Validation

- Seven weekdays analyzed for each shift.
- Total result rows: 14.
- Total trips: 35,083,335.
- Day and Night results remain separate.
- Weekday averages use the actual number of calendar occurrences in 2025 (52 or 53 days).

### Anomaly investigation and handling

No individual anomalies are confirmed by weekday averages alone. Differences between weekdays are treated as observed seasonality, not automatically as anomalies.

Daily observations should be investigated before unusual demand is classified as an anomaly. No records were removed or modified.

### Decision

- Maintain separate weekday demand reporting for Day and Night.
- Consider Saturday Night demand separately in operational planning.
- Do not use blended weekday totals for shift planning.

## Decision 003: Monthly Seasonality by Shift

**Date:** 2026-11-27

**Analysis:** Monthly demand patterns were calculated for 2025, separately for Day and Night shifts. Average trips per calendar day were used to account for differences in month length.

**Findings:**
- Day demand peaked in October at approximately 88,062 trips per day.
- Day demand was lowest in August at approximately 67,733 trips per day.
- Night demand peaked in May at approximately 17,135 trips per day.
- Night demand was lowest in August at approximately 13,301 trips per day.
- Both shifts experienced a slowdown during July and August, followed by recovery in September.

**Decision:**
- Keep monthly Day and Night demand separate in all reports and dashboard charts.
- Use average trips per calendar day when comparing months.
- Consider the July–August slowdown when planning driver capacity.
- Do not classify seasonal changes alone as anomalies. Investigate unusual daily or hourly deviations separately.

**Validation:**
- 24 result rows (12 months × 2 shifts).
- Total trips: 35,083,335.
- Reporting period: January–December 2025.
- No blended Day/Night metrics used.

## Decision 004: Pickup Zone Demand by Shift

**Date:** 2026-11-27

**Analysis:** Ranked the top 10 and bottom 10 pickup zones for 2025 separately for Day and Night shifts. Zone IDs were matched with `dim_zones` to display borough, zone name, and service zone.

**Findings:**

- Day Shift's highest-demand pickup zone was Upper East Side South, with 1,689,306 trips.
- Night Shift's highest-demand pickup zone was JFK Airport, with 418,104 trips.
- Day demand was concentrated in Manhattan and major airports.
- Night demand was strong around JFK Airport, East Village, West Village, Times Square, and other Manhattan locations.
- The lowest-demand zones had between 1 and 6 trips in Day and between 1 and 3 trips in Night.

**Decision:**

- Keep Day and Night zone rankings separate in the dashboard and reports.
- Highlight JFK Airport for Night Shift demand planning.
- Consider major Manhattan pickup areas when planning Day Shift coverage.
- Investigate extremely low-demand zones before making driver allocation decisions.
- Do not automatically classify low trip counts as data errors.

**Validation:**

- 40 ranked results: 10 top and 10 bottom zones for each shift.
- Reporting period: January–December 2025.
- Zone names joined using `pickup_location_id = LocationID`.
- Only zones with at least one matched pickup were included.
- Day and Night metrics were not blended.
- Pickup-zone coverage validation:
  - Total 2025 trips: 35,083,335.
  - Matched pickup zones: 35,083,335.
  - Null pickup IDs: 0.
  - Unmatched pickup IDs: 0.
  - Zone matching coverage: 100%.
- No 2025 trips were excluded by the pickup-zone dimension join.

## Decision 005: Daily and Hourly Demand Anomaly Investigation

**Date:** 27 November 2026  
**Status:** Initial investigation completed; selected dates require further review

### Objective

Identify unusual daily and hourly demand patterns while keeping Day and Night Shift metrics separate, as required by the client.

### Method

1. Generated daily demand observations for all 365 calendar dates and both shifts (730 observations).
2. Calculated robust Z-scores using the median and median absolute deviation (MAD), grouped by shift and weekday.
3. Used an absolute robust Z-score threshold of 3.0 to identify daily anomaly candidates.
4. Investigated hourly demand on the candidate dates against the typical demand for the same weekday, hour, and shift.
5. Used hourly robust Z-scores to identify unusual hourly observations.

### Results

- Total daily observations: 730
- Daily anomaly candidates: 20
- Hourly observations investigated: 248
- Hourly observations with absolute robust Z-score >= 3: 11

### Key Findings

**1. New Year's Day – January 1**

Day Shift demand was substantially below its normal Wednesday pattern throughout much of the day. Night Shift demand was unusually high. This may reflect New Year's Eve and New Year's Day activity.

**2. Independence Day period – July 2 to July 5**

July 2 showed elevated Day Shift demand across multiple hours. July 4 and the surrounding dates also showed unusual daily demand. These patterns require further investigation and should not automatically be classified as data-quality issues.

**3. Thanksgiving period – November 27 to November 29**

Reduced demand was observed around Thanksgiving, particularly during Night Shift.

**4. Christmas period – December 24 to December 28**

Demand was substantially lower around Christmas. December 27 Night Shift showed particularly low demand between midnight and 05:59, while its 22:00 and 23:00 demand was closer to the normal Saturday pattern.

### Decisions and Handling

- Retain all flagged observations in the warehouse.
- Do not delete or modify records based only on anomaly scores.
- Treat holiday-related demand changes as potential calendar effects.
- Investigate July 2 elevated demand and December 27 early-morning Night Shift demand further.
- Keep Day and Night Shift results separate in all reporting.
- Use actual pickup calendar dates for reporting, consistent with the agreed shift definition.
- Treat anomaly scores as investigation indicators, not confirmed data-quality failures.

### Limitations

- The analysis covers one calendar year (2025), so recurring holiday patterns cannot be confirmed across multiple years.
- Weekday-based baselines do not explicitly account for holidays or special events.
- Very small MAD values can produce unusually large robust Z-scores.
- No records have been classified as confirmed data errors based on this analysis alone.

### Implementation

- `metrics/metrics.py`
- `get_daily_demand_by_shift()`
- `get_daily_demand_anomaly_candidates()`
- `get_hourly_anomaly_investigation()`

**Outcome:** Initial anomaly screening and hourly investigation completed. Selected observations remain flagged for further review; no data corrections or deletions were performed.

## Week 3 – Task 2: Chart Outputs

The following charts were generated using the existing metrics functions
and 2025 clean trip data.

1. [Hourly Seasonality](../charts/hourly_seasonality.png)
2. [Weekday Seasonality](../charts/weekday_seasonality.png)
3. [Monthly Seasonality](../charts/monthly_seasonality.png)
4. [Day Shift Top and Bottom Zones](../charts/top_bottom_zones_day.png)
5. [Night Shift Top and Bottom Zones](../charts/top_bottom_zones_night.png)
6. [Daily Demand Anomalies](../charts/daily_demand_anomalies.png)