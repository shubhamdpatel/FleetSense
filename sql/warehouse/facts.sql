-- Purpose: Define the fact_trips table structure for NYC yellow taxi trip records.
-- The ingestion pipeline (pipeline/ingest.py) creates and populates this table.
-- trip_hash is the primary key used for duplicate prevention.

-- Columns:
-- trip_hash, pickup_datetime, dropoff_datetime,
-- passenger_count, trip_distance, pickup_location_id,
-- dropoff_location_id, fare_amount, tip_amount,
-- tolls_amount, total_amount, source_file.

SELECT COUNT(*) AS total_trips
FROM fact_trips;