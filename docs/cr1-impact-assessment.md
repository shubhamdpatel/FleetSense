# CR-1 – Revenue Reporting Change Impact Assessment

**Project:** FleetSense – Data Foundation and Operations Analytics  
**Change Request:** CR-1  
**Requested by:** Finance  
**Status:** Implemented

## 1. Change Requested

Finance requested revenue reporting with and without tolls and surcharges, with the difference reported for each pickup zone.

## 2. Impact Assessment

### What Changes

- Add a zone-level revenue comparison metric.
- Calculate revenue without tolls and surcharges using `fare_amount`.
- Calculate revenue with tolls and surcharges by including:
  - Tolls
  - Extra charges
  - Improvement surcharge
  - Congestion surcharge
  - Airport fee
  - CBD congestion fee
- Calculate the additional revenue contributed by these charges.
- Group results by pickup zone, borough, and zone ID.
- Add automated tests and a chart to communicate the results.

**Calculation decisions:**
- MTA tax is excluded from the surcharge calculation.
- Tips are excluded from both revenue calculations.
- NULL charge values are treated as zero.
- Only clean trips from January–December 2025 are included.

### Estimated Effort

| Activity | Estimated effort |
|---|---:|
| Impact assessment and calculation design | 30 minutes |
| Implement zone-level revenue metric | 1 hour |
| Add automated tests and validation | 45 minutes |
| Generate chart and document findings | 1 hour |
| **Total** | **3 hours 15 minutes** |

### Risks

- Incorrectly including taxes or tips could overstate surcharge revenue.
- Missing surcharge values could affect calculations if not handled.
- Incorrect joins between clean trips, fact trips, and zone dimensions could produce inaccurate results.

**Mitigation:**
- Use `COALESCE` for nullable charge fields.
- Join using `trip_hash` and pickup location ID.
- Validate aggregate totals against the zone-level results.
- Add automated tests for the calculation.

## 3. Implementation Result

The CR-1 revenue comparison function was implemented in `metrics/metrics.py` as:

`get_zone_revenue_comparison(con)`

Automated tests passed, and the function was verified against the actual DuckDB database.

## 4. Verified Results – 2025

| Metric | Revenue |
|---|---:|
| Revenue without tolls and surcharges | $694,361,198.46 |
| Revenue with tolls and surcharges | $910,191,487.79 |
| Additional revenue | $215,830,289.33 |

A total of 262 pickup zones had trips included in the comparison.

## 5. Chart and Visualization

Generated chart:

`charts/zone_revenue_comparison.png`

The chart displays the top 10 pickup zones ranked by additional revenue from tolls and surcharges.

## 6. Final Status

CR-1 has been implemented and verified.

- Zone-level revenue comparison function added.
- Automated tests passed.
- Actual database results verified across 262 zones.
- Revenue comparison chart generated successfully.
- Existing six charts remain available.

**Status: Completed**python -m pytest -v