
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
