"""Command-line interface for SeismoAlert."""

from __future__ import annotations

import csv
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import click

from seismoalert import __version__
from seismoalert.alerts import (
    AlertManager,
    AlertRule,
    high_rate_condition,
    large_earthquake_condition,
)
from seismoalert.analyzer import detect_anomalies, gutenberg_richter
from seismoalert.client import USGSClient, USGSClientError
from seismoalert.models import EarthquakeCatalog
from seismoalert.visualizer import create_earthquake_map


@click.group()
@click.version_option(version=__version__, prog_name="seismoalert")
def main():
    """SeismoAlert - Real-time earthquake monitor and anomaly detector."""


def _write_catalog_csv(catalog: EarthquakeCatalog, output_csv: str) -> Path:
    """Write fetched events to a CSV file and return the saved path."""
    output_path = Path(output_csv).expanduser()
    if str(output_path.parent) not in {"", "."}:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "id",
                "time_utc",
                "latitude",
                "longitude",
                "depth_km",
                "magnitude",
                "place",
                "url",
            ],
        )
        writer.writeheader()
        for eq in catalog:
            writer.writerow(
                {
                    "id": eq.id,
                    "time_utc": eq.time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "latitude": eq.latitude,
                    "longitude": eq.longitude,
                    "depth_km": eq.depth,
                    "magnitude": eq.magnitude,
                    "place": eq.place,
                    "url": eq.url,
                }
            )

    return output_path.resolve()


@main.command()
@click.option(
    "--days", default=1, help="Days to look back.", show_default=True
)
@click.option(
    "--min-magnitude", default=2.5, help="Minimum magnitude.", show_default=True
)
@click.option(
    "--limit", default=100, help="Max number of events.", show_default=True
)
@click.option(
    "--output-csv",
    default="earthquakes.csv",
    help="Output CSV file for fetched events.",
    show_default=True,
)
def fetch(days: int, min_magnitude: float, limit: int, output_csv: str):
    """Fetch recent earthquakes from the USGS API."""
    client = USGSClient()
    endtime = datetime.now(UTC)
    starttime = endtime - timedelta(days=days)

    try:
        catalog = client.fetch_earthquakes(
            starttime=starttime,
            endtime=endtime,
            min_magnitude=min_magnitude,
            limit=limit,
        )
    except USGSClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    msg = f"Fetched {len(catalog)} earthquakes "
    msg += f"(M>={min_magnitude}, last {days} day(s))"
    click.echo(msg)
    try:
        output_path = _write_catalog_csv(catalog, output_csv=output_csv)
    except OSError as exc:
        click.echo(f"Error writing CSV: {exc}", err=True)
        sys.exit(1)
    click.echo(f"Saved {len(catalog)} events to {output_path}")

    if len(catalog) > 0:
        click.echo(f"Largest event: M{catalog.max_magnitude:.1f}")
        sorted_cat = catalog.sort_by_magnitude()
        click.echo("\nTop events:")
        for eq in list(sorted_cat)[:5]:
            click.echo(
                f"  M{eq.magnitude:.1f}  {eq.place}  "
                f"({eq.time.strftime('%Y-%m-%d %H:%M UTC')})"
            )


@main.command()
@click.option(
    "--days", default=30, help="Days to analyze.", show_default=True
)
@click.option(
    "--min-magnitude", default=1.0, help="Minimum magnitude.", show_default=True
)
@click.option(
    "--window-days", default=7, help="Anomaly window (days).", show_default=True
)
def analyze(days: int, min_magnitude: float, window_days: int):
    """Run statistical analysis on earthquake data."""
    client = USGSClient()
    endtime = datetime.now(UTC)
    starttime = endtime - timedelta(days=days)

    try:
        catalog = client.fetch_earthquakes(
            starttime=starttime,
            endtime=endtime,
            min_magnitude=min_magnitude,
        )
    except USGSClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Analyzing {len(catalog)} earthquakes over {days} days...")

    if len(catalog) < 2:
        click.echo("Insufficient data for analysis.")
        return

    try:
        gr = gutenberg_richter(catalog)
        click.echo("\nGutenberg-Richter fit:")
        click.echo(f"  Magnitude of completeness (Mc): {gr.mc}")
        click.echo(f"  a-value: {gr.a_value}")
        click.echo(f"  b-value: {gr.b_value}")
    except ValueError as exc:
        click.echo(f"\nG-R fit failed: {exc}")

    anomalies = detect_anomalies(catalog, window_days=window_days)
    if anomalies:
        click.echo(f"\nDetected {len(anomalies)} anomalous period(s):")
        for a in anomalies[:5]:
            click.echo(
                f"  Events {a.start_index}-{a.end_index}: "
                f"{a.event_count} events ({a.sigma_deviation:.1f}σ above mean)"
            )
    else:
        click.echo("\nNo anomalous periods detected.")


@main.command(name="map")
@click.option(
    "--days", default=7, help="Days to look back.", show_default=True
)
@click.option(
    "--min-magnitude", default=2.5, help="Minimum magnitude.", show_default=True
)
@click.option(
    "--output", default="earthquakes.html", help="Output HTML file.",
    show_default=True,
)
def map_cmd(days: int, min_magnitude: float, output: str):
    """Generate an interactive earthquake map."""
    client = USGSClient()
    endtime = datetime.now(UTC)
    starttime = endtime - timedelta(days=days)

    try:
        catalog = client.fetch_earthquakes(
            starttime=starttime,
            endtime=endtime,
            min_magnitude=min_magnitude,
        )
    except USGSClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"Generating map with {len(catalog)} earthquakes...")
    path = create_earthquake_map(catalog, output_path=output)
    click.echo(f"Map saved to {path}")


@main.command()
@click.option(
    "--days", default=1, help="Days to look back.", show_default=True
)
@click.option(
    "--min-magnitude", default=4.0, help="Minimum magnitude.", show_default=True
)
@click.option(
    "--alert-magnitude",
    default=6.0,
    help="Magnitude threshold for alerts.",
    show_default=True,
)
@click.option(
    "--alert-count",
    default=50,
    help="Event count threshold for alerts.",
    show_default=True,
)
def monitor(days: int, min_magnitude: float, alert_magnitude: float, alert_count: int):
    """One-shot monitor: fetch, analyze, and check alert rules."""
    client = USGSClient()
    endtime = datetime.now(UTC)
    starttime = endtime - timedelta(days=days)

    try:
        catalog = client.fetch_earthquakes(
            starttime=starttime,
            endtime=endtime,
            min_magnitude=min_magnitude,
        )
    except USGSClientError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    msg = f"Monitoring: {len(catalog)} events "
    msg += f"(M>={min_magnitude}, last {days} day(s))"
    click.echo(msg)

    # Set up alert rules
    manager = AlertManager()
    manager.add_rule(
        AlertRule(
            name="Large Earthquake",
            condition=large_earthquake_condition(alert_magnitude),
            message_template="Large earthquake detected! Max magnitude: M{max_mag}",
        )
    )
    manager.add_rule(
        AlertRule(
            name="High Seismicity Rate",
            condition=high_rate_condition(alert_count),
            message_template="High seismicity rate: {count} events detected",
        )
    )

    alerts = manager.evaluate(catalog)
    if alerts:
        click.echo(f"\n{len(alerts)} alert(s) triggered:")
        for alert in alerts:
            click.echo(f"  [{alert.rule_name}] {alert.message}")
    else:
        click.echo("\nNo alerts triggered. All clear.")
