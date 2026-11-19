# FleetSense – Team Roles & Responsibilities

## 1. Team Members

| Team Member | Role | Responsibilities |
|---|---|---|
| Shubham Patel | Data Engineer & Platform Owner | Data ingestion, validation, quarantine, DuckDB warehouse, GitHub, CI, testing, Docker and deployment |
| Shravani Mamile | Data Analyst | Metric definitions, exploratory data analysis (EDA), Streamlit dashboard and findings report |
| Priyanka | Machine Learning Engineer | Feature engineering, baseline model development, model evaluation and experiment tracking |

## 2. Task Ownership & Acceptance Criteria

### 2.1 Data Ingestion & Validation
**Owner:** Shubham Patel

**Responsibilities:**
- Ingest 12 consecutive months of NYC Yellow Taxi data.
- Validate schema, data ranges and business rules.
- Quarantine invalid records with reason codes.
- Support incremental ingestion without duplicate records.

**Acceptance Criteria:**
- All valid records are loaded successfully.
- Invalid records are quarantined with reasons.
- Re-running ingestion does not create duplicate records.

**Testing:**
- Test schema and data validation.
- Test duplicate prevention during repeated ingestion.
- Verify loaded rows + quarantined rows = input rows.

### 2.2 Warehouse & Data Models
**Owner:** Shubham Patel

**Responsibilities:**
- Build warehouse tables using DuckDB.
- Create fact and dimension tables.
- Create hourly demand aggregations by zone.

**Acceptance Criteria:**
- Required warehouse tables are created.
- Data relationships and aggregations are correct.

**Testing:**
- Test table creation and data transformations.
- Verify hourly demand results against source data.

### 2.3 Metrics & Exploratory Data Analysis
**Owner:** Shravani Mamile

**Responsibilities:**
- Define trips, revenue, average fare, trip duration and utilization proxy metrics.
- Analyze hourly, weekday and monthly trends.
- Identify top/bottom zones and unusual patterns.

**Acceptance Criteria:**
- All required metrics are documented.
- EDA covers the required trends and anomalies.
- Metric definitions are consistent and reproducible.

**Testing:**
- Validate metric calculations using SQL queries.
- Cross-check dashboard figures against SQL results.

### 2.4 Operations Dashboard & Findings
**Owner:** Shravani Mamile

**Responsibilities:**
- Build the dashboard using Streamlit.
- Add date and zone filters.
- Display zone rankings and hourly demand profiles.
- Prepare the findings report with up to 6 charts and 3 recommendations.

**Acceptance Criteria:**
- Dashboard is accessible and filters work correctly.
- Required visualizations display accurate data.
- Findings report includes key insights and recommendations.

**Testing:**
- Test dashboard filters.
- Verify displayed figures against warehouse SQL queries.

### 2.5 Machine Learning & Model Evaluation
**Owner:** Priyanka

**Responsibilities:**
- Prepare relevant features.
- Develop baseline models if required for the agreed Phase 1 scope.
- Evaluate model performance and document experiments.

**Acceptance Criteria:**
- Features and model approach are documented.
- Evaluation results are reproducible.
- Model performance is compared with an appropriate baseline.

**Testing:**
- Test feature transformations.
- Verify evaluation calculations and experiment results.

### 2.6 Platform, CI & Deployment
**Primary Owner:** Shubham Patel  
**Shared Responsibility:** All team members

**Responsibilities:**
- Maintain GitHub repository and branch workflow.
- Configure GitHub Actions for continuous integration.
- Set up automated testing using pytest.
- Create Docker configuration.
- Coordinate application deployment and run logging.

**Acceptance Criteria:**
- Code changes trigger automated tests.
- Docker configuration runs the application.
- Deployment and execution instructions are documented.

**Testing:**
- Verify GitHub Actions workflow.
- Run project tests before merging changes.
- Verify the Docker build and application startup.

## 3. Shared Responsibility – Reproducibility

**Owner:** Shubham Patel

All team members must support reproducibility.

**Responsibilities:**
- Maintain a documented command to rebuild the pipeline and results from raw data.
- Ensure transformations and feature functions have tests.
- Maintain project documentation and execution instructions.

**Acceptance Criteria:**
- The project can be rebuilt using one documented command.
- Re-running the pipeline does not create duplicate records.
- Run logs include relevant row counts and execution information.

**Testing:**
- Execute the complete pipeline from raw data.
- Run it again to verify duplicate prevention.
- Verify the final output and row counts.

## 4. Team Collaboration

- Each owner is responsible for completing and testing their assigned tasks.
- All code changes should be committed through GitHub.
- Team members should review and test changes before integration.
- Blockers and progress should be communicated regularly.
- All members share responsibility for delivering the Phase 1 requirements.

---

**Project:** FleetSense – Phase 1: Data Foundation & Operations Analytics  
**Project Duration:** 7 November – 7 December 2026