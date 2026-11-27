
from datetime import datetime
from metrics.metrics import get_zone_revenue_comparison

import duckdb
import pytest

from metrics.metrics import (
    get_metrics_sql,
    get_metrics_python,
    get_hourly_demand,
    get_utilization_proxy,
)


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")

    connection.execute("""
        CREATE TABLE clean_trips (
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
            source_file VARCHAR,
            reason_codes VARCHAR
        )
    """)

    connection.execute("""
        INSERT INTO clean_trips VALUES

        -- Night: 05:59
        (
            '2025-01-01 05:59:00',
            '2025-01-01 06:29:00',
            1, 5.0, 100, 200, 5.0, 1.0, 0.0, 6.0,
            'test.parquet', NULL
        ),

        -- Day: 06:00
        (
            '2025-01-01 06:00:00',
            '2025-01-01 06:30:00',
            1, 5.0, 100, 200, 10.0, 2.0, 0.0, 12.0,
            'test.parquet', NULL
        ),

        -- Day: 21:59
        (
            '2025-01-01 21:59:00',
            '2025-01-01 22:29:00',
            2, 4.0, 101, 201, 15.0, 3.0, 0.0, 18.0,
            'test.parquet', NULL
        ),

        -- Night: 22:00
        (
            '2025-01-01 22:00:00',
            '2025-01-01 22:30:00',
            1, 3.0, 101, 200, 20.0, 4.0, 0.0, 24.0,
            'test.parquet', NULL
        ),

        -- Outside reporting period: must be excluded
        (
            '2024-12-31 12:00:00',
            '2024-12-31 12:30:00',
            1, 2.0, 100, 200, 100.0, 0.0, 0.0, 100.0,
            'test.parquet', NULL
        ),

        -- Outside reporting period: must be excluded
        (
            '2026-01-01 12:00:00',
            '2026-01-01 12:30:00',
            1, 2.0, 100, 200, 200.0, 0.0, 0.0, 200.0,
            'test.parquet', NULL
        )
    """)

    yield connection
    connection.close()


def test_core_metrics_by_shift(con):
    metrics = get_metrics_sql(con)

    assert metrics["Day"]["total_trips"] == 2
    assert metrics["Night"]["total_trips"] == 2

    assert metrics["Day"]["base_fare_revenue"] == pytest.approx(25.0)
    assert metrics["Night"]["base_fare_revenue"] == pytest.approx(25.0)

    assert metrics["Day"]["average_fare"] == pytest.approx(12.5)
    assert metrics["Night"]["average_fare"] == pytest.approx(12.5)

    assert (
        metrics["Day"]["average_trip_duration_minutes"]
        == pytest.approx(30.0)
    )

    assert (
        metrics["Night"]["average_trip_duration_minutes"]
        == pytest.approx(30.0)
    )

    assert (
        metrics["Day"]["total_trip_duration_minutes"]
        == pytest.approx(60.0)
    )

    assert (
        metrics["Night"]["total_trip_duration_minutes"]
        == pytest.approx(60.0)
    )


def test_python_and_sql_metrics_match(con):
    sql_metrics = get_metrics_sql(con)
    python_metrics = get_metrics_python(con)

    for shift in ("Day", "Night"):
        for metric in sql_metrics[shift]:
            assert python_metrics[shift][metric] == pytest.approx(
                sql_metrics[shift][metric]
            )


def test_total_trips_equal_both_shifts(con):
    metrics = get_metrics_sql(con)

    total_trips = (
        metrics["Day"]["total_trips"]
        + metrics["Night"]["total_trips"]
    )

    assert total_trips == 4


def test_hourly_demand_by_shift(con):
    demand = get_hourly_demand(con)

    assert "shift" in demand.columns
    assert "trip_hour" in demand.columns

    assert demand["total_trips"].sum() == 4

    shift_totals = demand.groupby("shift")["total_trips"].sum()

    assert shift_totals["Day"] == 2
    assert shift_totals["Night"] == 2

    assert set(demand["shift"]) == {"Day", "Night"}


def test_utilization_proxy_by_shift(con):
    proxy = get_utilization_proxy(con)

    assert "shift" in proxy.columns
    assert "trip_hour" in proxy.columns

    assert proxy["total_trips"].sum() == 4

    shift_totals = proxy.groupby("shift")["total_trips"].sum()

    assert shift_totals["Day"] == 2
    assert shift_totals["Night"] == 2


def test_zone_revenue_comparison(con):
    # Add trip_hash to the existing test data.
    con.execute("""
        ALTER TABLE clean_trips
        ADD COLUMN trip_hash VARCHAR
    """)

    con.execute("""
        UPDATE clean_trips
        SET trip_hash = CAST(pickup_datetime AS VARCHAR)
    """)

    # Create the financial fact table.
    con.execute("""
        CREATE TABLE fact_trips AS
        SELECT
            trip_hash,
            fare_amount,
            tolls_amount,
            0.0::DOUBLE AS extra,
            0.0::DOUBLE AS improvement_surcharge,
            0.0::DOUBLE AS congestion_surcharge,
            0.0::DOUBLE AS airport_fee,
            0.0::DOUBLE AS cbd_congestion_fee
        FROM clean_trips
    """)

    # Add test surcharge amounts to one trip.
    con.execute("""
        UPDATE fact_trips
        SET
            tolls_amount = 2.0,
            extra = 3.0
        WHERE trip_hash = (
            SELECT CAST(pickup_datetime AS VARCHAR)
            FROM clean_trips
            WHERE pickup_datetime = TIMESTAMP '2025-01-01 05:59:00'
        )
    """)

    # Create test zones.
    con.execute("""
        CREATE TABLE dim_zones (
            LocationID INTEGER,
            Borough VARCHAR,
            Zone VARCHAR,
            service_zone VARCHAR
        )
    """)

    con.execute("""
        INSERT INTO dim_zones VALUES
            (100, 'Manhattan', 'Test Zone A', 'Yellow Zone'),
            (101, 'Queens', 'Test Zone B', 'Boro Zone')
    """)

    result = get_zone_revenue_comparison(con)

    zone_100 = result[result["zone_id"] == 100].iloc[0]

    assert zone_100["total_trips"] == 2
    assert zone_100["revenue_without_charges"] == pytest.approx(15.0)
    assert zone_100["revenue_with_charges"] == pytest.approx(20.0)
    assert zone_100["revenue_difference"] == pytest.approx(5.0)

    # Trips outside 2025 must not be included.
    assert result["total_trips"].sum() == 4
