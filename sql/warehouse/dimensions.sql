-- Purpose: Create a 2025 calendar dimension with Day and Night shifts.
-- Grain: One row per calendar date per shift.

CREATE OR REPLACE TABLE dim_calendar AS
SELECT
    CAST(calendar_date AS DATE) AS date,
    EXTRACT(YEAR FROM calendar_date) AS year,
    EXTRACT(MONTH FROM calendar_date) AS month,
    EXTRACT(DAY FROM calendar_date) AS day,
    EXTRACT(DOW FROM calendar_date) AS day_of_week,
    STRFTIME(calendar_date, '%A') AS day_name,
    STRFTIME(calendar_date, '%B') AS month_name,
    shifts.shift
FROM (
    SELECT UNNEST(
        GENERATE_SERIES(
            DATE '2025-01-01',
            DATE '2025-12-31',
            INTERVAL 1 DAY
        )
    ) AS calendar_date
)
CROSS JOIN (
    SELECT UNNEST(['Day', 'Night']) AS shift
) AS shifts;
