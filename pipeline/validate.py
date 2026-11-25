
import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "warehouse" / "fleetsense.duckdb"


def create_validation_tables(con):
    """Create clean, quarantine, and validation summary tables."""

    con.execute("""
        CREATE TABLE IF NOT EXISTS clean_trips AS
        SELECT *, CAST(NULL AS VARCHAR) AS reason_codes
        FROM fact_trips
        WHERE FALSE
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS quarantine_trips AS
        SELECT *, CAST(NULL AS VARCHAR) AS reason_codes
        FROM fact_trips
        WHERE FALSE
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS validation_log (
            month VARCHAR,
            rows_in BIGINT,
            rows_loaded BIGINT,
            rows_quarantined BIGINT,
            run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Store rejection counts and revenue impact for each validation rule.
    con.execute("""
        CREATE TABLE IF NOT EXISTS validation_rule_summary (
            rule_code VARCHAR,
            rejected_rows BIGINT,
            rejection_percentage DOUBLE,
            excluded_revenue DOUBLE,
            revenue_impact_percentage DOUBLE,
            run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def validate_trips(con):
    """Validate trips and separate clean and invalid records."""

    print("Starting data validation...")

    con.execute("""
        CREATE OR REPLACE TEMP TABLE validation_results AS
        SELECT
            *,
            NULLIF(
                CONCAT_WS(',',
                    CASE
                        WHEN pickup_datetime IS NULL
                        THEN 'MISSING_PICKUP_TIME'
                    END,
                    CASE
                        WHEN dropoff_datetime IS NULL
                        THEN 'MISSING_DROPOFF_TIME'
                    END,
                    CASE
                        WHEN pickup_datetime IS NOT NULL
                         AND dropoff_datetime IS NOT NULL
                         AND dropoff_datetime <= pickup_datetime
                        THEN 'INVALID_TRIP_TIME'
                    END,
                    CASE
                        WHEN passenger_count IS NULL OR passenger_count <= 0
                        THEN 'INVALID_PASSENGER_COUNT'
                    END,
                    CASE
                        WHEN trip_distance IS NULL OR trip_distance <= 0
                        THEN 'INVALID_TRIP_DISTANCE'
                    END,
                    CASE
                        WHEN fare_amount IS NULL OR fare_amount < 0
                        THEN 'INVALID_FARE_AMOUNT'
                    END,
                    CASE
                        WHEN total_amount IS NULL OR total_amount < 0
                        THEN 'INVALID_TOTAL_AMOUNT'
                    END
                ),
                ''
            ) AS reason_codes
        FROM fact_trips
    """)

    print("Validation rules applied.")

    # Calculate overall input and revenue totals for rule-wise reporting.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE validation_totals AS
        SELECT
            COUNT(*) AS total_rows,
            COALESCE(
                SUM(CASE WHEN total_amount > 0 THEN total_amount ELSE 0 END),
                0
            ) AS total_revenue
        FROM validation_results
    """)

    # Expand multiple reason codes into individual rule records.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE rule_failures AS
        SELECT
            UNNEST(STRING_SPLIT(reason_codes, ',')) AS rule_code,
            trip_hash,
            total_amount
        FROM validation_results
        WHERE reason_codes IS NOT NULL
    """)

    # Replace previous validation results safely in one transaction.
    con.execute("BEGIN TRANSACTION")

    try:
        # Clear previous validation results.
        con.execute("DELETE FROM clean_trips")
        con.execute("DELETE FROM quarantine_trips")
        con.execute("DELETE FROM validation_log")
        con.execute("DELETE FROM validation_rule_summary")

        # Store valid trips.
        con.execute("""
            INSERT INTO clean_trips
            SELECT *
            FROM validation_results
            WHERE reason_codes IS NULL
        """)

        # Store invalid trips with their reason codes.
        con.execute("""
            INSERT INTO quarantine_trips
            SELECT *
            FROM validation_results
            WHERE reason_codes IS NOT NULL
        """)

        # Generate monthly validation logs.
        con.execute("""
            INSERT INTO validation_log (
                month,
                rows_in,
                rows_loaded,
                rows_quarantined
            )
            SELECT
                REGEXP_EXTRACT(
                    source_file,
                    'yellow_tripdata_([0-9]{4}-[0-9]{2})',
                    1
                ) AS month,
                COUNT(*) AS rows_in,
                SUM(CASE WHEN reason_codes IS NULL THEN 1 ELSE 0 END)
                    AS rows_loaded,
                SUM(CASE WHEN reason_codes IS NOT NULL THEN 1 ELSE 0 END)
                    AS rows_quarantined
            FROM validation_results
            GROUP BY month
            ORDER BY month
        """)

        # Generate rejection counts and excluded revenue per rule.
        # A trip failing multiple rules is counted once under each failed rule.
        # Revenue impact considers only positive total_amount values.

        con.execute("""
            WITH all_rules(rule_code) AS (
                VALUES
                    ('MISSING_PICKUP_TIME'),
                    ('MISSING_DROPOFF_TIME'),
                    ('INVALID_TRIP_TIME'),
                    ('INVALID_PASSENGER_COUNT'),
                    ('INVALID_TRIP_DISTANCE'),
                    ('INVALID_FARE_AMOUNT'),
                    ('INVALID_TOTAL_AMOUNT')
            ),
            rule_stats AS (
                SELECT
                    rule_code,
                    COUNT(DISTINCT trip_hash) AS rejected_rows,
                    SUM(
                        CASE
                            WHEN total_amount > 0 THEN total_amount
                            ELSE 0
                        END
                    ) AS excluded_revenue
                FROM rule_failures
                GROUP BY rule_code
            )
            INSERT INTO validation_rule_summary (
                rule_code,
                rejected_rows,
                rejection_percentage,
                excluded_revenue,
                revenue_impact_percentage
            )
            SELECT
                r.rule_code,

                COALESCE(s.rejected_rows, 0) AS rejected_rows,

                ROUND(
                    COALESCE(s.rejected_rows, 0) * 100.0
                    / NULLIF(v.total_rows, 0),
                    2
                ) AS rejection_percentage,

                COALESCE(s.excluded_revenue, 0) AS excluded_revenue,

                ROUND(
                    COALESCE(s.excluded_revenue, 0) * 100.0
                    / NULLIF(v.total_revenue, 0),
                    2
                ) AS revenue_impact_percentage

            FROM all_rules r
            LEFT JOIN rule_stats s
                ON r.rule_code = s.rule_code
            CROSS JOIN validation_totals v
            ORDER BY r.rule_code
        """)

        con.execute("COMMIT")
        print("Validation results committed successfully.")

    except Exception:
        con.execute("ROLLBACK")
        raise

    print("Clean and quarantine tables populated.")
    print("Monthly validation logs generated.")
    print("Per-rule rejection and revenue summaries generated.")


def main():
    con = duckdb.connect(str(DB_PATH))

    try:
        create_validation_tables(con)
        validate_trips(con)

        print("\nData validation completed successfully.")

    finally:
        con.close()


if __name__ == "__main__":
    main()
