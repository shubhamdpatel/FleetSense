-- Purpose: Create a calendar dimension containing each valid trip date in 2025.

CREATE OR REPLACE TABLE dim_calendar AS
SELECT
    CAST(calendar_date AS DATE) AS date,
    EXTRACT(YEAR FROM calendar_date) AS year,
    EXTRACT(MONTH FROM calendar_date) AS month,
    EXTRACT(DAY FROM calendar_date) AS day,
    EXTRACT(DOW FROM calendar_date) AS day_of_week,
    STRFTIME(calendar_date, '%A') AS day_name,
    STRFTIME(calendar_date, '%B') AS month_name
FROM (
    SELECT DISTINCT CAST(pickup_datetime AS DATE) AS calendar_date
    FROM clean_trips
    WHERE pickup_datetime >= TIMESTAMP '2025-01-01 00:00:00'
      AND pickup_datetime < TIMESTAMP '2026-01-01 00:00:00'
);