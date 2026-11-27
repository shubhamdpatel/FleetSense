
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd

from metrics.metrics import (
    get_hourly_seasonality,
    get_weekday_seasonality,
    get_monthly_seasonality,
    get_zone_demand,
    get_daily_demand_anomaly_candidates,
    get_zone_revenue_comparison,
)


PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "warehouse" / "fleetsense.duckdb"
CHART_DIR = PROJECT_ROOT / "charts"

CHART_DIR.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.figsize": (12, 6),
    "axes.titlesize": 14,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
})


def save_chart(filename):
    """Save the current chart as a PNG image."""
    output_path = CHART_DIR / filename
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def plot_hourly_seasonality(hourly):
    plt.figure()

    for shift in ["Day", "Night"]:
        data = hourly[hourly["shift"] == shift].sort_values("trip_hour")

        plt.plot(
            data["trip_hour"],
            data["average_trips_per_day"],
            marker="o",
            linewidth=2,
            label=shift,
        )

    plt.title("Average Hourly Taxi Demand - Day vs Night")
    plt.xlabel("Pickup Hour (24-hour format)")
    plt.ylabel("Average Trips per Day")
    plt.xticks(range(24))
    plt.grid(True, alpha=0.3)
    plt.legend(title="Shift")

    save_chart("hourly_seasonality.png")


def plot_weekday_seasonality(weekday):
    plt.figure()

    pivot = weekday.pivot(
        index="weekday_number",
        columns="shift",
        values="average_trips_per_day",
    ).sort_index()

    pivot.plot(kind="bar", ax=plt.gca(), width=0.8)

    plt.title("Average Daily Taxi Demand by Weekday")
    plt.xlabel("Weekday")
    plt.ylabel("Average Trips per Calendar Day")
    plt.xticks(
        range(len(pivot)),
        weekday.drop_duplicates("weekday_number")
        .sort_values("weekday_number")["weekday"],
        rotation=30,
    )
    plt.grid(axis="y", alpha=0.3)
    plt.legend(title="Shift")

    save_chart("weekday_seasonality.png")


def plot_monthly_seasonality(monthly):
    plt.figure()

    pivot = monthly.pivot(
        index="month_number",
        columns="shift",
        values="average_trips_per_day",
    ).sort_index()

    pivot.plot(kind="bar", ax=plt.gca(), width=0.8)

    month_labels = (
        monthly.drop_duplicates("month_number")
        .sort_values("month_number")["month"]
    )

    plt.title("Average Daily Taxi Demand by Month")
    plt.xlabel("Month")
    plt.ylabel("Average Trips per Calendar Day")
    plt.xticks(range(len(pivot)), month_labels, rotation=45)
    plt.grid(axis="y", alpha=0.3)
    plt.legend(title="Shift")

    save_chart("monthly_seasonality.png")


def plot_zone_demand(zones, shift):
    data = zones[zones["shift"] == shift].copy()

    top = data[data["category"] == "Top"].sort_values(
        "total_trips", ascending=True
    )

    bottom = data[data["category"] == "Bottom"].sort_values(
        "total_trips", ascending=False
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    axes[0].barh(top["zone"], top["total_trips"])
    axes[0].set_title(f"Top 10 Pickup Zones - {shift}")
    axes[0].set_xlabel("Total Trips")

    axes[1].barh(bottom["zone"], bottom["total_trips"])
    axes[1].set_title(f"Bottom 10 Pickup Zones - {shift}")
    axes[1].set_xlabel("Total Trips")

    fig.suptitle(
        f"Pickup Zone Demand - {shift} Shift",
        fontsize=16,
    )

    for axis in axes:
        axis.grid(axis="x", alpha=0.3)
        axis.tick_params(axis="y", labelsize=8)

    plt.tight_layout()
    output_path = CHART_DIR / f"top_bottom_zones_{shift.lower()}.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")


def plot_daily_anomalies(anomalies):
    candidates = anomalies[
        anomalies["is_anomaly_candidate"]
    ].copy()

    candidates["trip_date"] = pd.to_datetime(
        candidates["trip_date"]
    )

    fig, axes = plt.subplots(2, 1, figsize=(15, 10))

    for axis, shift in zip(axes, ["Day", "Night"]):
        data = candidates[
            candidates["shift"] == shift
        ].sort_values("trip_date")

        axis.bar(
            data["trip_date"].dt.strftime("%Y-%m-%d"),
            data["total_trips"],
        )

        axis.set_title(f"{shift} Shift - Daily Anomaly Candidates")
        axis.set_ylabel("Total Trips")
        axis.tick_params(axis="x", rotation=60)
        axis.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "Unusual Daily Taxi Demand - 2025",
        fontsize=16,
    )

    plt.tight_layout()
    output_path = CHART_DIR / "daily_demand_anomalies.png"
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_path}")

def plot_zone_revenue_comparison(revenue):
    data = revenue.nlargest(
        10,
        "revenue_difference"
    ).sort_values("revenue_difference")

    data = data.copy()
    data["additional_revenue_millions"] = (
        data["revenue_difference"] / 1_000_000
    )

    plt.figure(figsize=(12, 7))

    bars = plt.barh(
        data["zone"],
        data["additional_revenue_millions"],
    )

    for bar, value in zip(
        bars,
        data["additional_revenue_millions"]
    ):
        plt.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" ${value:.2f}M",
            va="center",
            fontsize=9,
        )

    plt.title("Top 10 Pickup Zones by Additional Revenue - 2025")
    plt.xlabel("Additional Revenue (USD Million)")
    plt.ylabel("Pickup Zone")
    plt.grid(axis="x", alpha=0.3)

    save_chart("zone_revenue_comparison.png")

def main():
    print("Connecting to FleetSense warehouse...")

    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        print("Loading seasonality and anomaly data...")

        hourly = get_hourly_seasonality(con)
        weekday = get_weekday_seasonality(con)
        monthly = get_monthly_seasonality(con)
        zones = get_zone_demand(con, limit=10)
        anomalies = get_daily_demand_anomaly_candidates(con)
        revenue = get_zone_revenue_comparison(con)

        print("Generating charts...")

        plot_hourly_seasonality(hourly)
        plot_weekday_seasonality(weekday)
        plot_monthly_seasonality(monthly)
        plot_zone_demand(zones, "Day")
        plot_zone_demand(zones, "Night")
        plot_daily_anomalies(anomalies)
        plot_zone_revenue_comparison(revenue)

        print("\nAll seven charts generated successfully.")

    finally:
        con.close()


if __name__ == "__main__":
    main()
