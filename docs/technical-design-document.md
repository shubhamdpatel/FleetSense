# FleetSense – Phase 1 Technical Design Document

**Project:** FleetSense – Data Foundation and Operations Analytics  
**Phase:** Phase 1  
**Version:** 1.0 – Draft for Mentor Review  
**Prepared by:** FleetSense Team  
**Technology:** Python, DuckDB, Parquet, Pandas, SQL, Streamlit

> **Document status:** Draft for mentor review. The assigned client-specific business question, any client-specific operating rules, and the final revenue calculation must be checked against the Team Workspace and confirmed with the mentor before they are treated as final.

---

## 1. Project Overview

The objective of FleetSense Phase 1 is to build a reliable data foundation for taxi trip analysis and operations reporting.

The project will use NYC Yellow Taxi trip records to create a structured data warehouse, validate and clean trip records, define consistent business metrics, and analyze demand and revenue patterns by time and pickup zone.

The expected outputs include a reproducible data pipeline, cleaned and structured warehouse tables, exploratory analysis, an interactive Streamlit dashboard, and a findings report for a non-technical operations audience.

## 2. Data Sources

### 2.1 Source datasets

The project uses the following datasets:

1. **NYC TLC Yellow Taxi Trip Records**
   - Monthly Parquet files.
   - At least 12 consecutive months are required for Phase 1.
   - Contains trip timestamps, pickup and drop-off locations, passenger details, distance, and fare information.

2. **NYC TLC Trip Record Data Dictionary**
   - Used to understand the meaning of source fields and support validation and metric definitions.

3. **NYC Taxi Zone Lookup**
   - Used to map location IDs to boroughs, zone names, and service zones.

### 2.2 Parquet Dataset Schema

The project uses 12 consecutive months of NYC Yellow Taxi trip records in Parquet format. The following 20 columns represent the common schema identified during the initial inspection of the monthly files.

| Category       | Columns                                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Trip details   | `VendorID`, `passenger_count`, `trip_distance`                                                                                         |
| Timestamps     | `tpep_pickup_datetime`, `tpep_dropoff_datetime`                                                                                        |
| Locations      | `PULocationID`, `DOLocationID`                                                                                                         |
| Fare and total | `fare_amount`, `total_amount`                                                                                                          |
| Charges        | `extra`, `mta_tax`, `tip_amount`, `tolls_amount`, `improvement_surcharge`, `congestion_surcharge`, `Airport_fee`, `cbd_congestion_fee` |
| Other details  | `RatecodeID`, `store_and_fwd_flag`, `payment_type`                                                                                     |

**Schema details:**

- Total columns in the identified schema: 20.
- The ingestion pipeline will validate the schema of all 12 monthly files before combining and processing them.
- Any missing, additional, or changed columns will be identified and handled through documented schema validation rules.


### 2.3 Data ingestion approach

- Provide a Python script to download the required monthly Yellow Taxi Parquet files.
- Store original files in the raw data directory.
- Read and process Parquet files using DuckDB.
- Support incremental ingestion so rerunning the pipeline does not create duplicate records.
- Verify downloaded file integrity and record counts.
- Load the Taxi Zone Lookup for location mapping.
- Keep raw data files out of the Git repository.

## 3. Data Validation and Cleaning

Data validation will run before records are used in downstream warehouse models and analysis.

The validation process will check:

- Required pickup and drop-off timestamps are present.
- Drop-off timestamp is later than pickup timestamp.
- Fare values are checked for invalid negative amounts according to documented business rules.
- Trip distance and passenger values are checked against documented validation rules.
- Pickup and drop-off location IDs are checked against the Taxi Zone Lookup.
- Monthly file schemas are checked for missing, additional, or type-changed columns.
- Duplicate records are identified and handled consistently.

Invalid records will be kept separately in a quarantine dataset with a reason code describing the validation failure. The team will document which records are rejected, retained, or handled as exceptions.

## 4. Warehouse Model

The warehouse will use DuckDB for analytical queries and Parquet for columnar data storage.

### 4.1 `fact_trips`

Stores validated individual trip records.

Proposed fields:

- Trip identifier or documented deduplication key.
- `VendorID`.
- Pickup and drop-off timestamps.
- Pickup and drop-off location IDs.
- Passenger count.
- Trip distance.
- Fare amount.
- Extra charge.
- MTA tax.
- Tip amount.
- Tolls amount.
- Improvement surcharge.
- Congestion surcharge.
- Airport fee.
- CBD congestion fee.
- Total amount.
- Trip duration in minutes.

The individual fare and charge components will be retained so that revenue calculations can be defined transparently and recalculated if the approved business definition changes.

### 4.2 `dim_zones`

Stores taxi zone reference information.

Proposed fields:

- Location ID.
- Borough.
- Zone name.
- Service zone.

This dimension will support pickup- and drop-off-zone analysis.

### 4.3 `dim_calendar`

Stores calendar-date attributes.

Proposed fields:

- Date.
- Day of month.
- Weekday.
- Month.
- Year.

Hour-of-day and any shift classification will be derived from the trip pickup timestamp. They will not be treated as date-level attributes.

### 4.4 `hourly_zone_demand`

Stores aggregated demand by date, pickup zone, and hour.

Proposed fields:

- Date.
- Hour.
- Pickup zone ID.
- Total trips.

Revenue measures may also be included once the revenue definition is approved and consistently implemented.

### 4.5 Data flow

**Raw monthly Parquet files → Schema and data validation → Clean trip data → DuckDB warehouse tables → Metrics and aggregations → EDA, dashboard, and findings report**

## 5. Metric Definitions

Business metrics will be defined centrally and reused across SQL transformations, analysis, tests, and dashboard components.

| Metric | Proposed definition |
|---|---|
| Total Trips | Count of valid trip records. |
| Base Fare Revenue | Sum of `fare_amount` for valid trips. |
| Average Fare | Sum of `fare_amount` divided by the number of valid trips included in the calculation. |
| Trip Duration | Difference between drop-off and pickup timestamps, expressed in minutes. |
| Hourly Demand | Count of valid trips grouped by pickup zone and pickup hour. |
| Utilization Proxy | Trip activity by zone and time period, used as an indicator of demand. |

**Utilization limitation:** The available trip records do not establish how many vehicles were available or the total time each vehicle was available for service. Therefore, trip activity will be described as a demand or activity proxy, not as actual fleet utilization.

### 5.1 Client-specific analysis

The team must include the business question assigned to its client in the Team Workspace. The exact requirement and its acceptance criteria must be copied into this section after verification.

If the assigned requirement includes a day/night or shift comparison, the team will document the approved time boundaries and classify trips consistently using pickup time. No shift definition is considered final until it is confirmed against the assigned requirement.

### 5.2 CR-1: Revenue with and without tolls and surcharges

CR-1 requires the team to report revenue with and without tolls and surcharges and analyze the difference by zone.

The inspected source schema contains these potentially relevant fields:

- `fare_amount`
- `extra`
- `mta_tax`
- `tip_amount`
- `tolls_amount`
- `improvement_surcharge`
- `total_amount`
- `congestion_surcharge`
- `Airport_fee`
- `cbd_congestion_fee`

The team will retain the individual components and confirm the exact calculation with the TLC data dictionary and mentor before implementation.

The final metric specification must state:
- Which amount is treated as the base revenue.
- Which tolls and surcharge fields are included in the inclusive calculation.
- Whether tips and taxes are included or excluded.
- How null values are handled.
- How the difference is calculated and grouped by pickup zone.

The inclusive and exclusive calculations must use the same valid trip population so that the comparison is consistent. `total_amount` will not automatically be treated as the approved CR-1 revenue measure without confirming its composition and the required business definition.

## 6. Exploratory Data Analysis

Exploratory Data Analysis (EDA) will be performed on validated trip data.

The analysis will cover:

1. Trip demand by hour, weekday, and month.
2. Highest- and lowest-demand pickup zones.
3. Revenue patterns across zones and time periods.
4. Trip duration and fare distributions.
5. Unusual values and anomalies in the data.
6. Relevant comparisons required by the assigned client question.

Anomalies will be investigated. Any exclusion, correction, or retention decision will be documented with its reason.

## 7. Dashboard Design

An interactive dashboard will be developed using Streamlit.

The planned dashboard features are:

- Date-range filter.
- Pickup-zone filter.
- Summary metrics such as total trips and approved revenue measures.
- Zone-wise demand shown through a map or ranked table.
- Hourly demand profiles.
- CR-1 revenue comparison once the calculation is approved.
- Client-specific views required by the assigned business question.

Dashboard queries should meet the Phase 1 performance target of under two seconds for normal dashboard interactions.

## 8. Risks and Mitigation

| Risk | Mitigation |
|---|---|
| Large monthly datasets | Use Parquet and DuckDB for efficient analytical processing. |
| Missing or invalid values | Apply documented validation rules and quarantine invalid records with reason codes. |
| Duplicate records | Implement incremental ingestion and a documented duplicate-handling strategy. |
| Invalid trip duration | Validate pickup and drop-off timestamps and investigate invalid durations. |
| Unknown zone IDs | Validate location IDs against the Taxi Zone Lookup. |
| Monthly schema differences | Inspect every monthly file and validate its schema before combining data. |
| Incorrect revenue calculation | Retain individual fare components and obtain agreement on metric definitions before implementation. |
| Incorrect client-specific logic | Verify the assigned business question and acceptance criteria in Team Workspace. |
| Pipeline failures | Add logging, error handling, automated tests, and a documented rebuild command. |
| Slow processing or dashboard queries | Use efficient Parquet/DuckDB queries and test against the Phase 1 performance targets. |

## 9. Technology Stack

| Area | Proposed technology |
|---|---|
| Programming language | Python 3.11+ |
| Data processing | Pandas |
| Data storage | Parquet |
| Query engine | DuckDB |
| Transformations | SQL and Python |
| Data validation | Pandera or another mentor-approved validation approach |
| Dashboard | Streamlit |
| Testing | Pytest |
| Version control | Git and GitHub |
| Continuous integration | GitHub Actions |
| Containerization | Docker |

Dependency versions will be maintained in the project's dependency file. Any change to the proposed stack will be documented.

## 10. Items for Mentor Review and Approval

Please review and confirm the following before the team finalizes implementation:

1. **Client requirement:** Is the client-specific business question in this document aligned with the team's assigned requirement in Team Workspace? The team will insert the exact wording and acceptance criteria.
2. **Data coverage:** Are the selected 12 consecutive months appropriate? January, February, and March schemas have been compared and match; the remaining months still need schema checks.
3. **Warehouse model:** Is the proposed fact and dimension structure suitable for the required Phase 1 analysis?
4. **Metric definitions:** Are the proposed trip, fare, duration, demand, and utilization-proxy definitions appropriate?
5. **CR-1 revenue:** Which fare, toll, surcharge, tax, and tip components should be included or excluded in each calculation?
6. **Validation:** Are the proposed validation and quarantine rules appropriate?
7. **Technology:** Is the proposed stack acceptable for the team's implementation?

**Approval status:** Pending mentor review and approval.
