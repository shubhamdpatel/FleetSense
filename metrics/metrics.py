
"""Centralized business metrics for FleetSense.

Metrics use clean_trips so quarantined records are excluded.

All analytics cover January to December 2025 and are
reported separately for Day and Night shifts.

Day:   06:00 to 21:59
Night: 22:00 to 05:59
"""

from typing import Any

import duckdb


SOURCE_TABLE = "clean_trips"

START_DATE = "2025-01-01"
END_DATE = "2026-01-01"

SHIFTS = ("Day", "Night")


def get_metrics_sql(
    con: duckdb.DuckDBPyConnection,
) -> dict[str, dict[str, Any]]:
    """Calculate 2025 core business metrics separately by shift."""

    rows = con.execute(f"""
        WITH trips_with_shift AS (
            SELECT
                pickup_datetime,
                dropoff_datetime,
                fare_amount,

                CASE
                    WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
                      OR EXTRACT(HOUR FROM pickup_datetime) < 6
                    THEN 'Night'
                    ELSE 'Day'
                END AS shift

            FROM {SOURCE_TABLE}

            WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
              AND pickup_datetime < TIMESTAMP '{END_DATE}'
        )

        SELECT
            shift,

            COUNT(*) AS total_trips,

            COALESCE(SUM(fare_amount), 0)
                AS base_fare_revenue,

            AVG(fare_amount) AS average_fare,

            AVG(
                CASE
                    WHEN dropoff_datetime > pickup_datetime
                    THEN DATE_DIFF(
                        'second',
                        pickup_datetime,
                        dropoff_datetime
                    ) / 60.0
                END
            ) AS average_trip_duration_minutes,

            COALESCE(
                SUM(
                    CASE
                        WHEN dropoff_datetime > pickup_datetime
                        THEN DATE_DIFF(
                            'second',
                            pickup_datetime,
                            dropoff_datetime
                        ) / 60.0
                        ELSE 0
                    END
                ),
                0
            ) AS total_trip_duration_minutes

        FROM trips_with_shift

        GROUP BY shift
        ORDER BY shift
    """).fetchall()

    results = {
        shift: {
            "total_trips": 0,
            "base_fare_revenue": 0.0,
            "average_fare": 0.0,
            "average_trip_duration_minutes": 0.0,
            "total_trip_duration_minutes": 0.0,
        }
        for shift in SHIFTS
    }

    for row in rows:
        shift = row[0]

        results[shift] = {
            "total_trips": int(row[1]),
            "base_fare_revenue": float(row[2]),
            "average_fare": (
                float(row[3]) if row[3] is not None else 0.0
            ),
            "average_trip_duration_minutes": (
                float(row[4]) if row[4] is not None else 0.0
            ),
            "total_trip_duration_minutes": float(row[5]),
        }

    return results


def get_metrics_python(
    con: duckdb.DuckDBPyConnection,
) -> dict[str, dict[str, Any]]:
    """Calculate 2025 metrics in Python for SQL cross-checking.

    Fetches records in batches to avoid loading the entire dataset
    into memory.
    """

    cursor = con.execute(f"""
        SELECT
            pickup_datetime,
            dropoff_datetime,
            fare_amount

        FROM {SOURCE_TABLE}

        WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
          AND pickup_datetime < TIMESTAMP '{END_DATE}'
    """)

    results = {
        shift: {
            "total_trips": 0,
            "base_fare_revenue": 0.0,
            "fare_count": 0,
            "total_duration_minutes": 0.0,
            "duration_count": 0,
        }
        for shift in SHIFTS
    }

    batch_size = 100_000

    while True:
        rows = cursor.fetchmany(batch_size)

        if not rows:
            break

        for pickup, dropoff, fare in rows:
            if pickup is None:
                continue

            # Determine shift from the actual pickup hour.
            shift = (
                "Night"
                if pickup.hour >= 22 or pickup.hour < 6
                else "Day"
            )

            results[shift]["total_trips"] += 1

            if fare is not None:
                results[shift]["base_fare_revenue"] += float(fare)
                results[shift]["fare_count"] += 1

            if (
                dropoff is not None
                and dropoff > pickup
            ):
                duration_minutes = (
                    dropoff - pickup
                ).total_seconds() / 60.0

                results[shift]["total_duration_minutes"] += (
                    duration_minutes
                )
                results[shift]["duration_count"] += 1

    final_results = {}

    for shift in SHIFTS:
        data = results[shift]

        final_results[shift] = {
            "total_trips": data["total_trips"],

            "base_fare_revenue": data["base_fare_revenue"],

            "average_fare": (
                data["base_fare_revenue"] / data["fare_count"]
                if data["fare_count"] else 0.0
            ),

            "average_trip_duration_minutes": (
                data["total_duration_minutes"] / data["duration_count"]
                if data["duration_count"] else 0.0
            ),

            "total_trip_duration_minutes": (
                data["total_duration_minutes"]
            ),
        }

    return final_results


def get_hourly_demand(
    con: duckdb.DuckDBPyConnection,
):
    """Return 2025 trip demand by date, shift, hour, and pickup zone."""

    return con.execute(f"""
        SELECT
            CAST(pickup_datetime AS DATE) AS trip_date,

            CASE
                WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
                  OR EXTRACT(HOUR FROM pickup_datetime) < 6
                THEN 'Night'
                ELSE 'Day'
            END AS shift,

            EXTRACT(HOUR FROM pickup_datetime) AS trip_hour,

            pickup_location_id AS zone_id,

            COUNT(*) AS total_trips

        FROM {SOURCE_TABLE}

        WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
          AND pickup_datetime < TIMESTAMP '{END_DATE}'
          AND pickup_location_id IS NOT NULL

        GROUP BY
            CAST(pickup_datetime AS DATE),
            shift,
            EXTRACT(HOUR FROM pickup_datetime),
            pickup_location_id

        ORDER BY
            trip_date,
            shift,
            trip_hour,
            zone_id
    """).fetchdf()


def get_utilization_proxy(
    con: duckdb.DuckDBPyConnection,
):
    """Return 2025 trip activity by zone, hour, and shift.

    This is a demand/activity proxy, not actual fleet utilization.
    Vehicle availability and active fleet time are not present
    in the available dataset.
    """

    return con.execute(f"""
        SELECT
            pickup_location_id AS zone_id,

            CASE
                WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
                  OR EXTRACT(HOUR FROM pickup_datetime) < 6
                THEN 'Night'
                ELSE 'Day'
            END AS shift,

            EXTRACT(HOUR FROM pickup_datetime) AS trip_hour,

            COUNT(*) AS total_trips

        FROM {SOURCE_TABLE}

        WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
          AND pickup_datetime < TIMESTAMP '{END_DATE}'
          AND pickup_location_id IS NOT NULL

        GROUP BY
            pickup_location_id,
            shift,
            EXTRACT(HOUR FROM pickup_datetime)

        ORDER BY
            zone_id,
            shift,
            trip_hour
    """).fetchdf()

def get_hourly_seasonality(
    con: duckdb.DuckDBPyConnection,
):
    """Return 2025 hourly demand separately for Day and Night.

    Includes all valid trips, even when pickup_location_id is null.
    Average daily trips makes hourly demand easier to compare.
    """

    return con.execute(f"""
        WITH hours AS (
            SELECT
                UNNEST(GENERATE_SERIES(0, 23)) AS trip_hour
        ),

        hourly_totals AS (
            SELECT
                EXTRACT(HOUR FROM pickup_datetime) AS trip_hour,
                COUNT(*) AS total_trips

            FROM {SOURCE_TABLE}

            WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
              AND pickup_datetime < TIMESTAMP '{END_DATE}'

            GROUP BY EXTRACT(HOUR FROM pickup_datetime)
        )

        SELECT
            hours.trip_hour,

            CASE
                WHEN hours.trip_hour >= 22
                  OR hours.trip_hour < 6
                THEN 'Night'
                ELSE 'Day'
            END AS shift,

            COALESCE(hourly_totals.total_trips, 0)
                AS total_trips,

            ROUND(
                COALESCE(hourly_totals.total_trips, 0) / 365.0,
                2
            ) AS average_trips_per_day

        FROM hours

        LEFT JOIN hourly_totals
            ON hours.trip_hour = hourly_totals.trip_hour

        ORDER BY hours.trip_hour
    """).fetchdf()

def get_weekday_seasonality(
    con: duckdb.DuckDBPyConnection,
):
    """Return 2025 weekday demand separately for Day and Night.

    Includes all calendar dates, including dates with zero trips,
    so average daily demand is calculated consistently.
    """

    return con.execute(f"""
        WITH calendar AS (
            SELECT
                CAST(calendar_date AS DATE) AS trip_date,
                EXTRACT(ISODOW FROM calendar_date) AS weekday_number,
                STRFTIME(calendar_date, '%A') AS weekday

            FROM (
                SELECT UNNEST(
                    GENERATE_SERIES(
                        DATE '2025-01-01',
                        DATE '2025-12-31',
                        INTERVAL 1 DAY
                    )
                ) AS calendar_date
            )
        ),

        shifts AS (
            SELECT UNNEST(['Day', 'Night']) AS shift
        ),

        daily_demand AS (
            SELECT
                CAST(pickup_datetime AS DATE) AS trip_date,

                CASE
                    WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
                      OR EXTRACT(HOUR FROM pickup_datetime) < 6
                    THEN 'Night'
                    ELSE 'Day'
                END AS shift,

                COUNT(*) AS total_trips

            FROM {SOURCE_TABLE}

            WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
              AND pickup_datetime < TIMESTAMP '{END_DATE}'

            GROUP BY
                CAST(pickup_datetime AS DATE),
                shift
        ),

        calendar_demand AS (
            SELECT
                calendar.trip_date,
                calendar.weekday_number,
                calendar.weekday,
                shifts.shift,
                COALESCE(daily_demand.total_trips, 0)
                    AS total_trips

            FROM calendar

            CROSS JOIN shifts

            LEFT JOIN daily_demand
                ON calendar.trip_date = daily_demand.trip_date
                AND shifts.shift = daily_demand.shift
        )

        SELECT
            weekday_number,
            weekday,
            shift,
            SUM(total_trips) AS total_trips,
            COUNT(*) AS calendar_days,

            ROUND(
                AVG(total_trips),
                2
            ) AS average_trips_per_day

        FROM calendar_demand

        GROUP BY
            weekday_number,
            weekday,
            shift

        ORDER BY
            weekday_number,
            CASE WHEN shift = 'Day' THEN 1 ELSE 2 END
    """).fetchdf()

def get_monthly_seasonality(
    con: duckdb.DuckDBPyConnection,
):
    """Return 2025 monthly demand separately for Day and Night."""

    return con.execute(f"""
        WITH calendar AS (
            SELECT
                CAST(calendar_date AS DATE) AS trip_date,
                EXTRACT(MONTH FROM calendar_date) AS month_number,
                STRFTIME(calendar_date, '%B') AS month

            FROM (
                SELECT UNNEST(
                    GENERATE_SERIES(
                        DATE '2025-01-01',
                        DATE '2025-12-31',
                        INTERVAL 1 DAY
                    )
                ) AS calendar_date
            )
        ),

        shifts AS (
            SELECT UNNEST(['Day', 'Night']) AS shift
        ),

        daily_demand AS (
            SELECT
                CAST(pickup_datetime AS DATE) AS trip_date,

                CASE
                    WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
                      OR EXTRACT(HOUR FROM pickup_datetime) < 6
                    THEN 'Night'
                    ELSE 'Day'
                END AS shift,

                COUNT(*) AS total_trips

            FROM {SOURCE_TABLE}

            WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
              AND pickup_datetime < TIMESTAMP '{END_DATE}'

            GROUP BY
                CAST(pickup_datetime AS DATE),
                shift
        ),

        calendar_demand AS (
            SELECT
                calendar.trip_date,
                calendar.month_number,
                calendar.month,
                shifts.shift,

                COALESCE(daily_demand.total_trips, 0)
                    AS total_trips

            FROM calendar

            CROSS JOIN shifts

            LEFT JOIN daily_demand
                ON calendar.trip_date = daily_demand.trip_date
                AND shifts.shift = daily_demand.shift
        )

        SELECT
            month_number,
            month,
            shift,
            SUM(total_trips) AS total_trips,
            COUNT(*) AS calendar_days,

            ROUND(
                AVG(total_trips),
                2
            ) AS average_trips_per_day

        FROM calendar_demand

        GROUP BY
            month_number,
            month,
            shift

        ORDER BY
            month_number,
            CASE WHEN shift = 'Day' THEN 1 ELSE 2 END
    """).fetchdf()

def get_zone_demand(con: duckdb.DuckDBPyConnection, limit: int = 10):
    """Return top and bottom pickup zones separately for Day and Night."""

    return con.execute(f"""
        WITH zone_totals AS (
            SELECT
                CASE
                    WHEN EXTRACT(HOUR FROM t.pickup_datetime) >= 22
                      OR EXTRACT(HOUR FROM t.pickup_datetime) < 6
                    THEN 'Night'
                    ELSE 'Day'
                END AS shift,
                z.LocationID AS zone_id,
                z.Borough AS borough,
                z.Zone AS zone,
                z.service_zone,
                COUNT(*) AS total_trips
            FROM {SOURCE_TABLE} t
            INNER JOIN dim_zones z
                ON t.pickup_location_id = z.LocationID
            WHERE t.pickup_datetime >= TIMESTAMP '{START_DATE}'
              AND t.pickup_datetime < TIMESTAMP '{END_DATE}'
            GROUP BY
                shift,
                z.LocationID,
                z.Borough,
                z.Zone,
                z.service_zone
        ),
        ranked_zones AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY shift
                    ORDER BY total_trips DESC, zone_id
                ) AS top_rank,
                ROW_NUMBER() OVER (
                    PARTITION BY shift
                    ORDER BY total_trips ASC, zone_id
                ) AS bottom_rank
            FROM zone_totals
        ),
        top_zones AS (
            SELECT
                shift,
                'Top' AS category,
                top_rank AS rank,
                zone_id,
                borough,
                zone,
                service_zone,
                total_trips
            FROM ranked_zones
            WHERE top_rank <= {limit}
        ),
        bottom_zones AS (
            SELECT
                shift,
                'Bottom' AS category,
                bottom_rank AS rank,
                zone_id,
                borough,
                zone,
                service_zone,
                total_trips
            FROM ranked_zones
            WHERE bottom_rank <= {limit}
        )
        SELECT * FROM top_zones
        UNION ALL
        SELECT * FROM bottom_zones
        ORDER BY
            CASE WHEN shift = 'Day' THEN 1 ELSE 2 END,
            CASE WHEN category = 'Top' THEN 1 ELSE 2 END,
            rank
    """).fetchdf()

def get_daily_demand_by_shift(
    con: duckdb.DuckDBPyConnection,
):
    """Return daily 2025 trip demand for Day and Night shifts.

    Includes every calendar date and both shifts, even when
    a date/shift has zero trips.
    """

    return con.execute(f"""
        WITH calendar AS (
            SELECT
                CAST(calendar_date AS DATE) AS trip_date,
                STRFTIME(calendar_date, '%A') AS weekday,
                EXTRACT(ISODOW FROM calendar_date) AS weekday_number
            FROM (
                SELECT UNNEST(
                    GENERATE_SERIES(
                        DATE '2025-01-01',
                        DATE '2025-12-31',
                        INTERVAL 1 DAY
                    )
                ) AS calendar_date
            )
        ),

        shifts AS (
            SELECT UNNEST(['Day', 'Night']) AS shift
        ),

        daily_demand AS (
            SELECT
                CAST(pickup_datetime AS DATE) AS trip_date,
                CASE
                    WHEN EXTRACT(HOUR FROM pickup_datetime) >= 22
                      OR EXTRACT(HOUR FROM pickup_datetime) < 6
                    THEN 'Night'
                    ELSE 'Day'
                END AS shift,
                COUNT(*) AS total_trips
            FROM {SOURCE_TABLE}
            WHERE pickup_datetime >= TIMESTAMP '{START_DATE}'
              AND pickup_datetime < TIMESTAMP '{END_DATE}'
            GROUP BY
                CAST(pickup_datetime AS DATE),
                shift
        )

        SELECT
            calendar.trip_date,
            calendar.weekday,
            calendar.weekday_number,
            shifts.shift,
            COALESCE(daily_demand.total_trips, 0) AS total_trips
        FROM calendar
        CROSS JOIN shifts
        LEFT JOIN daily_demand
            ON calendar.trip_date = daily_demand.trip_date
            AND shifts.shift = daily_demand.shift
        ORDER BY
            calendar.trip_date,
            CASE WHEN shifts.shift = 'Day' THEN 1 ELSE 2 END
    """).fetchdf()

def get_daily_demand_anomaly_candidates(
    con: duckdb.DuckDBPyConnection,
    threshold: float = 3.0,
):
    """Rank unusual daily demand observations by shift and weekday.

    Uses a median-based robust Z-score to reduce the influence
    of unusually high or low observations.

    A score at or above the threshold is an investigation
    candidate, not a confirmed anomaly.
    """

    import numpy as np

    df = get_daily_demand_by_shift(con)

    groups = df.groupby(["shift", "weekday_number"])

    df["weekday_median"] = groups["total_trips"].transform("median")

    df["absolute_deviation"] = abs(
        df["total_trips"] - df["weekday_median"]
    )

    df["weekday_mad"] = (
        df.groupby(["shift", "weekday_number"])[
            "absolute_deviation"
        ].transform("median")
    )

    scale = 1.4826 * df["weekday_mad"]

    df["robust_z_score"] = np.where(
        scale > 0,
        (df["total_trips"] - df["weekday_median"]) / scale,
        0.0,
    )

    df["is_anomaly_candidate"] = (
        df["robust_z_score"].abs() >= threshold
    )

    return df.sort_values(
        "robust_z_score",
        key=lambda values: values.abs(),
        ascending=False,
    )

def get_hourly_anomaly_investigation(con):
    """Compare hourly demand on daily anomaly candidates
    with the usual demand for the same weekday, hour and shift.
    """

    import numpy as np

    hourly = con.execute("""
        WITH calendar_hours AS (
            SELECT
                CAST(d.calendar_date AS DATE) AS trip_date,
                EXTRACT(DOW FROM d.calendar_date) AS weekday_number,
                STRFTIME(d.calendar_date, '%A') AS weekday,
                h.trip_hour,
                CASE
                    WHEN h.trip_hour >= 22 OR h.trip_hour < 6
                    THEN 'Night'
                    ELSE 'Day'
                END AS shift
            FROM GENERATE_SERIES(
                DATE '2025-01-01',
                DATE '2025-12-31',
                INTERVAL 1 DAY
            ) AS d(calendar_date)
            CROSS JOIN UNNEST(RANGE(0, 24)) AS h(trip_hour)
        ),
        hourly_counts AS (
            SELECT
                CAST(pickup_datetime AS DATE) AS trip_date,
                EXTRACT(HOUR FROM pickup_datetime) AS trip_hour,
                COUNT(*) AS total_trips
            FROM clean_trips
            WHERE pickup_datetime >= TIMESTAMP '2025-01-01 00:00:00'
              AND pickup_datetime < TIMESTAMP '2026-01-01 00:00:00'
            GROUP BY 1, 2
        )
        SELECT
            c.trip_date,
            c.weekday,
            c.weekday_number,
            c.shift,
            c.trip_hour,
            COALESCE(h.total_trips, 0) AS total_trips
        FROM calendar_hours c
        LEFT JOIN hourly_counts h
            ON c.trip_date = h.trip_date
           AND c.trip_hour = h.trip_hour
        ORDER BY c.trip_date, c.trip_hour
    """).fetchdf()

    daily_candidates = get_daily_demand_anomaly_candidates(con)
    candidates = daily_candidates[
        daily_candidates["is_anomaly_candidate"]
    ][["trip_date", "shift"]].copy()

    hourly = hourly.merge(
        candidates,
        on=["trip_date", "shift"],
        how="inner",
    )

    groups = hourly.groupby(
        ["weekday_number", "trip_hour", "shift"]
    )

    hourly["hourly_median"] = groups["total_trips"].transform("median")

    hourly["absolute_deviation"] = (
        hourly["total_trips"] - hourly["hourly_median"]
    ).abs()

    hourly["hourly_mad"] = (
        hourly.groupby(
            ["weekday_number", "trip_hour", "shift"]
        )["absolute_deviation"].transform("median")
    )

    scale = 1.4826 * hourly["hourly_mad"]

    hourly["hourly_robust_z"] = np.where(
        scale > 0,
        (hourly["total_trips"] - hourly["hourly_median"]) / scale,
        0.0,
    )

    return hourly.sort_values(
        "hourly_robust_z",
        key=lambda values: values.abs(),
        ascending=False,
    )