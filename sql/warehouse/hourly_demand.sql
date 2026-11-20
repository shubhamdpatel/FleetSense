-- Purpose: Calculate hourly taxi trip demand for each pickup zone.
-- Each row represents the number of valid trips for a specific date,
-- hour, and pickup zone.

CREATE OR REPLACE TABLE hourly_demand AS
SELECT
    CAST(pickup_datetime AS DATE) AS trip_date,
    EXTRACT(HOUR FROM pickup_datetime) AS trip_hour,
    pickup_location_id AS zone_id,
    COUNT(*) AS total_trips
FROM clean_trips
WHERE pickup_datetime >= TIMESTAMP '2025-01-01 00:00:00'
  AND pickup_datetime < TIMESTAMP '2026-01-01 00:00:00'
GROUP BY
    CAST(pickup_datetime AS DATE),
    EXTRACT(HOUR FROM pickup_datetime),
    pickup_location_id;