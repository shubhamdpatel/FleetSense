
import duckdb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "warehouse" / "fleetsense.duckdb"


def create_validation_tables(con):
    """Create clean, quarantine, and validation log tables."""

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

    # Clear previous validation results for safe reruns.
    con.execute("DELETE FROM clean_trips")
    con.execute("DELETE FROM quarantine_trips")
    con.execute("DELETE FROM validation_log")

    # Store valid trips.
    con.execute("""
        INSERT INTO clean_trips
        SELECT * FROM validation_results
        WHERE reason_codes IS NULL
    """)

    # Store invalid trips with their reason codes.
    con.execute("""
        INSERT INTO quarantine_trips
        SELECT * FROM validation_results
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

    print("Clean and quarantine tables populated.")
    print("Monthly validation logs generated.")


def main():
    con = duckdb.connect(str(DB_PATH))

    try:
        create_validation_tables(con)
        validate_trips(con)

        print("\nData validation completed successfully.")

    except Exception:
        raise

    finally:
        con.close()


if __name__ == "__main__":
    main()
