"""Visualization utilities for earthquake data."""

from __future__ import annotations

from pathlib import Path

import folium
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from seismoalert.models import EarthquakeCatalog

matplotlib.use("Agg")


def _magnitude_to_color(mag: float) -> str:
    """Map magnitude to a color string."""
    if mag >= 7.0:
        return "red"
    if mag >= 5.0:
        return "orange"
    if mag >= 3.0:
        return "yellow"
    return "green"


def _magnitude_to_radius(mag: float) -> float:
    """Map magnitude to a circle radius in pixels."""
    return max(3.0, mag ** 2)


def create_earthquake_map(
    catalog: EarthquakeCatalog,
    output_path: str | Path = "earthquakes.html",
) -> Path:
    """Create an interactive Folium map of earthquake locations.

    Each earthquake is represented as a circle marker with size proportional
    to magnitude and color indicating severity.

    Args:
        catalog: Earthquake catalog to visualize.
        output_path: Path for the output HTML file.

    Returns:
        Path to the saved HTML file.
    """
    output_path = Path(output_path)

    # Center map on mean coordinates, or world center if empty
    if len(catalog) > 0:
        center_lat = np.mean([eq.latitude for eq in catalog])
        center_lon = np.mean([eq.longitude for eq in catalog])
        zoom = 3
    else:
        center_lat, center_lon = 0.0, 0.0
        zoom = 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom)

    for eq in catalog:
        popup_text = (
            f"<b>M{eq.magnitude:.1f}</b> - {eq.place}<br>"
            f"Depth: {eq.depth:.1f} km<br>"
            f"Time: {eq.time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        folium.CircleMarker(
            location=[eq.latitude, eq.longitude],
            radius=_magnitude_to_radius(eq.magnitude),
            color=_magnitude_to_color(eq.magnitude),
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_text, max_width=300),
        ).add_to(m)

    m.save(str(output_path))
    return output_path


def plot_magnitude_time(
    catalog: EarthquakeCatalog,
    output_path: str | Path = "magnitude_time.png",
) -> Path:
    """Plot earthquake magnitude vs. time.

    Args:
        catalog: Earthquake catalog to plot.
        output_path: Path for the output image file.

    Returns:
        Path to the saved image file.
    """
    output_path = Path(output_path)
    sorted_cat = catalog.sort_by_time()

    times = [eq.time for eq in sorted_cat]
    mags = [eq.magnitude for eq in sorted_cat]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(times, mags, s=10, alpha=0.6, c=mags, cmap="YlOrRd", edgecolors="none")
    ax.set_xlabel("Time")
    ax.set_ylabel("Magnitude")
    ax.set_title("Earthquake Magnitude vs. Time")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)

    return output_path


def plot_gutenberg_richter(
    catalog: EarthquakeCatalog,
    a_value: float,
    b_value: float,
    output_path: str | Path = "gutenberg_richter.png",
    mc: float | None = None,
) -> Path:
    """Plot the Gutenberg-Richter frequency-magnitude distribution.

    Shows observed cumulative event counts, the fitted G-R line,
    and optionally the magnitude of completeness (Mc).

    Args:
        catalog: Earthquake catalog to plot.
        a_value: G-R a-value (productivity).
        b_value: G-R b-value (slope).
        output_path: Path for the output image file.
        mc: Magnitude of completeness. Drawn as a vertical
            dashed line if provided.

    Returns:
        Path to the saved image file.
    """
    output_path = Path(output_path)
    mags = sorted(catalog.magnitudes)

    # Cumulative counts (N >= M)
    unique_mags = sorted(set(mags))
    cum_counts = [
        sum(1 for m in mags if m >= mag) for mag in unique_mags
    ]

    # G-R fit line
    mag_range = np.linspace(min(mags), max(mags), 100)
    gr_line = 10 ** (a_value - b_value * mag_range)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.semilogy(
        unique_mags, cum_counts, "ko", markersize=5, label="Observed"
    )
    ax.semilogy(
        mag_range,
        gr_line,
        "r-",
        linewidth=2,
        label=f"G-R fit (a={a_value:.2f}, b={b_value:.2f})",
    )

    if mc is not None:
        ax.axvline(
            x=mc,
            color="blue",
            linestyle="--",
            linewidth=1.5,
            label=f"Mc = {mc:.1f}",
        )

    ax.set_xlabel("Magnitude")
    ax.set_ylabel("Cumulative Number (N ≥ M)")
    ax.set_title("Gutenberg-Richter Distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(output_path), dpi=150)
    plt.close(fig)

    return output_path
