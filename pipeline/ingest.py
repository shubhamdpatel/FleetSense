
from pathlib import Path

import duckdb


# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "yellow_taxi"
REFERENCE_FILE = PROJECT_ROOT / "data" / "reference" / "taxi_zone_lookup.csv"

DB_DIR = PROJECT_ROOT / "data" / "warehouse"
DB_PATH = DB_DIR / "fleetsense.duckdb"


# --------------------------------------------------
# 2. DATABASE SETUP
# --------------------------------------------------

def create_database():
    """Create the DuckDB database and required tables."""

    DB_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    con.execute("""
        CREATE TABLE IF NOT EXISTS fact_trips (
            trip_hash VARCHAR PRIMARY KEY,
            pickup_datetime TIMESTAMP,
            dropoff_datetime TIMESTAMP,
            passenger_count DOUBLE,
            trip_distance DOUBLE,
            pickup_location_id INTEGER,
            dropoff_location_id INTEGER,
            fare_amount DOUBLE,
            tip_amount DOUBLE,
            tolls_amount DOUBLE,
            total_amount DOUBLE,
            extra DOUBLE,
            mta_tax DOUBLE,
            improvement_surcharge DOUBLE,
            congestion_surcharge DOUBLE,
            airport_fee DOUBLE,
            cbd_congestion_fee DOUBLE,
            source_file VARCHAR
        )
    """)

    # Migrate existing databases by adding missing columns.
    financial_columns = [
        ("extra", "DOUBLE"),
        ("mta_tax", "DOUBLE"),
        ("improvement_surcharge", "DOUBLE"),
        ("congestion_surcharge", "DOUBLE"),
        ("airport_fee", "DOUBLE"),
        ("cbd_congestion_fee", "DOUBLE"),
    ]

    for column_name, column_type in financial_columns:
        con.execute(
            f"ALTER TABLE fact_trips "
            f"ADD COLUMN IF NOT EXISTS {column_name} {column_type}"
        )

    con.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_log (
            source_file VARCHAR,
            rows_in BIGINT,
            rows_loaded BIGINT,
            rows_skipped BIGINT,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    return con


# --------------------------------------------------
# 3. MONTHLY DATA INGESTION
# --------------------------------------------------

def load_monthly_data(con, file_path):
    """Load monthly trips and update existing records without duplicates."""

    print(f"\nProcessing: {file_path.name}")

    # Read monthly Parquet data into a temporary DuckDB table.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE monthly_data AS
        SELECT
            sha256(concat_ws('|',
                coalesce(CAST(tpep_pickup_datetime AS VARCHAR), '<NULL>'),
                coalesce(CAST(tpep_dropoff_datetime AS VARCHAR), '<NULL>'),
                coalesce(CAST(passenger_count AS VARCHAR), '<NULL>'),
                coalesce(CAST(trip_distance AS VARCHAR), '<NULL>'),
                coalesce(CAST(PULocationID AS VARCHAR), '<NULL>'),
                coalesce(CAST(DOLocationID AS VARCHAR), '<NULL>'),
                coalesce(CAST(fare_amount AS VARCHAR), '<NULL>'),
                coalesce(CAST(tip_amount AS VARCHAR), '<NULL>'),
                coalesce(CAST(tolls_amount AS VARCHAR), '<NULL>'),
                coalesce(CAST(total_amount AS VARCHAR), '<NULL>')
            )) AS trip_hash,

            CAST(tpep_pickup_datetime AS TIMESTAMP) AS pickup_datetime,
            CAST(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_datetime,
            CAST(passenger_count AS DOUBLE) AS passenger_count,
            CAST(trip_distance AS DOUBLE) AS trip_distance,
            CAST(PULocationID AS INTEGER) AS pickup_location_id,
            CAST(DOLocationID AS INTEGER) AS dropoff_location_id,
            CAST(fare_amount AS DOUBLE) AS fare_amount,
            CAST(tip_amount AS DOUBLE) AS tip_amount,
            CAST(tolls_amount AS DOUBLE) AS tolls_amount,
            CAST(total_amount AS DOUBLE) AS total_amount,

            CAST(extra AS DOUBLE) AS extra,
            CAST(mta_tax AS DOUBLE) AS mta_tax,
            CAST(improvement_surcharge AS DOUBLE) AS improvement_surcharge,
            CAST(congestion_surcharge AS DOUBLE) AS congestion_surcharge,
            CAST(Airport_fee AS DOUBLE) AS airport_fee,
            CAST(cbd_congestion_fee AS DOUBLE) AS cbd_congestion_fee,

            ? AS source_file

        FROM read_parquet(?)
    """, [file_path.name, str(file_path)])

    # Count original source rows.
    rows_in = con.execute("""
        SELECT COUNT(*) FROM monthly_data
    """).fetchone()[0]

    # Remove duplicate records within this file.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE deduplicated_data AS
        SELECT *
        FROM monthly_data
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY trip_hash
            ORDER BY pickup_datetime
        ) = 1
    """)

    # Count records before insertion.
    before_count = con.execute("""
        SELECT COUNT(*) FROM fact_trips
    """).fetchone()[0]

    # Insert new records and update existing records.
    # The original trip_hash formula is preserved to avoid
    # generating new hashes for previously ingested trips.
    con.execute("""
        INSERT INTO fact_trips (
            trip_hash,
            pickup_datetime,
            dropoff_datetime,
            passenger_count,
            trip_distance,
            pickup_location_id,
            dropoff_location_id,
            fare_amount,
            tip_amount,
            tolls_amount,
            total_amount,
            extra,
            mta_tax,
            improvement_surcharge,
            congestion_surcharge,
            airport_fee,
            cbd_congestion_fee,
            source_file
        )
        SELECT
            trip_hash,
            pickup_datetime,
            dropoff_datetime,
            passenger_count,
            trip_distance,
            pickup_location_id,
            dropoff_location_id,
            fare_amount,
            tip_amount,
            tolls_amount,
            total_amount,
            extra,
            mta_tax,
            improvement_surcharge,
            congestion_surcharge,
            airport_fee,
            cbd_congestion_fee,
            source_file
        FROM deduplicated_data

        ON CONFLICT (trip_hash) DO UPDATE SET
            extra = EXCLUDED.extra,
            mta_tax = EXCLUDED.mta_tax,
            improvement_surcharge = EXCLUDED.improvement_surcharge,
            congestion_surcharge = EXCLUDED.congestion_surcharge,
            airport_fee = EXCLUDED.airport_fee,
            cbd_congestion_fee = EXCLUDED.cbd_congestion_fee,
            source_file = EXCLUDED.source_file
    """)

    # Count records after insertion.
    after_count = con.execute("""
        SELECT COUNT(*) FROM fact_trips
    """).fetchone()[0]

    rows_loaded = after_count - before_count
    rows_skipped = rows_in - rows_loaded

    # Save monthly ingestion statistics.
    con.execute("""
        INSERT INTO ingestion_log (
            source_file,
            rows_in,
            rows_loaded,
            rows_skipped
        )
        VALUES (?, ?, ?, ?)
    """, [
        file_path.name,
        rows_in,
        rows_loaded,
        rows_skipped
    ])

    # Clean up temporary tables.
    con.execute("DROP TABLE IF EXISTS monthly_data")
    con.execute("DROP TABLE IF EXISTS deduplicated_data")

    print(f"Rows in source file: {rows_in:,}")
    print(f"New rows inserted:   {rows_loaded:,}")
    print(f"Rows skipped:        {rows_skipped:,}")

    return rows_in, rows_loaded, rows_skipped


# --------------------------------------------------
# 4. ZONE LOOKUP INGESTION
# --------------------------------------------------

def load_zone_lookup(con):
    """Load NYC taxi zone reference data."""

    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Zone lookup file not found: {REFERENCE_FILE}"
        )

    con.execute("""
        CREATE OR REPLACE TABLE dim_zones AS
        SELECT *
        FROM read_csv_auto(?)
    """, [str(REFERENCE_FILE)])

    zone_count = con.execute("""
        SELECT COUNT(*) FROM dim_zones
    """).fetchone()[0]

    print(f"\nZone lookup records loaded: {zone_count:,}")


# --------------------------------------------------
# 5. MAIN INGESTION PROCESS
# --------------------------------------------------

def main():

    print("========== FLEETSENSE DATA INGESTION ==========")

    con = create_database()

    try:
        files = sorted(
            RAW_DIR.glob("yellow_tripdata_*.parquet")
        )

        if not files:
            raise FileNotFoundError(
                f"No Parquet files found in {RAW_DIR}"
            )

        total_input = 0
        total_loaded = 0
        total_skipped = 0

        print(f"\nMonthly files found: {len(files)}")

        for file_path in files:

            rows_in, rows_loaded, rows_skipped = (
                load_monthly_data(con, file_path)
            )

            total_input += rows_in
            total_loaded += rows_loaded
            total_skipped += rows_skipped

        # Load zone reference data.
        load_zone_lookup(con)

        # Final database count.
        total_database_rows = con.execute("""
            SELECT COUNT(*) FROM fact_trips
        """).fetchone()[0]

        print("\n========== INGESTION SUMMARY ==========")

        print(f"Files processed:       {len(files)}")
        print(f"Total source rows:     {total_input:,}")
        print(f"New rows inserted:     {total_loaded:,}")
        print(f"Rows skipped:          {total_skipped:,}")
        print(f"Total database rows:   {total_database_rows:,}")

        print("\nIngestion completed successfully.")

    finally:
        con.close()


# --------------------------------------------------
# 6. SCRIPT ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    main()