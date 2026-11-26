-- Purpose: Calculate 2025 hourly taxi demand by date, shift, and pickup zone.
-- Shift is determined by pickup time.

CREATE OR REPLACE TABLE hourly_demand AS
WITH trips_with_shift AS (
    SELECT
        CAST(pickup_datetime AS DATE) AS trip_date,

        EXTRACT(HOUR FROM pickup_datetime) AS trip_hour,

        CASE
            WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
              OR EXTRACT(HOUR FROM pickup_datetime) < 6
            THEN 'Night'
            ELSE 'Day'
        END AS shift,

        pickup_location_id AS zone_id

    FROM clean_trips

    WHERE pickup_datetime >= TIMESTAMP '2025-01-01 00:00:00'
      AND pickup_datetime < TIMESTAMP '2026-01-01 00:00:00'
      AND pickup_location_id IS NOT NULL
)

SELECT
    trip_date,
    shift,
    trip_hour,
    zone_id,
    COUNT(*) AS total_trips

FROM trips_with_shift

GROUP BY
    trip_date,
    shift,
    trip_hour,
    zone_id

ORDER BY
    trip_date,
    shift,
    trip_hour,
    zone_id;