"""Statistical analysis of earthquake catalogs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import numpy as np

from seismoalert.models import EarthquakeCatalog


@dataclass
class GutenbergRichterResult:
    """Result of a Gutenberg-Richter law fit.

    The G-R law states: log10(N) = a - b * M
    where N is the number of events >= magnitude M.

    Attributes:
        a_value: Productivity parameter (log10 of total event rate).
        b_value: Slope of the frequency-magnitude distribution.
        mc: Magnitude of completeness used for the fit.
    """

    a_value: float
    b_value: float
    mc: float


@dataclass
class AnomalyPeriod:
    """Represents a detected anomalous seismicity period.

    Attributes:
        start_index: Start index in the time-sorted catalog.
        end_index: End index in the time-sorted catalog.
        event_count: Number of events in the window.
        expected_count: Expected number of events based on the mean rate.
        sigma_deviation: Number of standard deviations above the mean.
    """

    start_index: int
    end_index: int
    event_count: int
    expected_count: float
    sigma_deviation: float


def magnitude_of_completeness(catalog: EarthquakeCatalog) -> float:
    """Estimate the magnitude of completeness (Mc) using the max-curvature method.

    The magnitude of completeness is the magnitude at which the frequency-magnitude
    distribution reaches its maximum, i.e., the most frequently occurring magnitude bin.

    Args:
        catalog: Earthquake catalog to analyze.

    Returns:
        Estimated magnitude of completeness.

    Raises:
        ValueError: If catalog is empty.
    """
    if len(catalog) == 0:
        raise ValueError("Cannot compute Mc for an empty catalog")

    mags = np.array(catalog.magnitudes)
    # Round to nearest 0.1 for binning
    bin_min = np.floor(mags.min() * 10) / 10
    bin_max = np.ceil(mags.max() * 10) / 10 + 0.1
    bins = np.arange(bin_min, bin_max, 0.1)
    counts, bin_edges = np.histogram(mags, bins=bins)
    max_idx = np.argmax(counts)
    mc = (bin_edges[max_idx] + bin_edges[max_idx + 1]) / 2
    return round(float(mc), 1)


def gutenberg_richter(
    catalog: EarthquakeCatalog, mc: float | None = None
) -> GutenbergRichterResult:
    """Fit the Gutenberg-Richter frequency-magnitude relation.

    Uses the maximum likelihood estimate for b-value:
        b = log10(e) / (M_mean - Mc)

    Args:
        catalog: Earthquake catalog to analyze.
        mc: Magnitude of completeness. If None, estimated automatically.

    Returns:
        GutenbergRichterResult with a-value, b-value, and mc.

    Raises:
        ValueError: If catalog has insufficient data above Mc.
    """
    if len(catalog) == 0:
        raise ValueError("Cannot fit G-R law to an empty catalog")

    if mc is None:
        mc = magnitude_of_completeness(catalog)

    filtered = catalog.filter_by_magnitude(min_mag=mc)
    if len(filtered) < 2:
        raise ValueError(f"Insufficient events (n={len(filtered)}) above Mc={mc}")

    mags = np.array(filtered.magnitudes)
    mean_mag = np.mean(mags)

    # Aki (1965) maximum likelihood b-value estimator
    # bin width correction: delta_m = 0.1
    delta_m = 0.1
    b_value = np.log10(np.e) / (mean_mag - (mc - delta_m / 2))

    # a-value: log10(N) = a - b * Mc
    a_value = np.log10(len(filtered)) + b_value * mc

    return GutenbergRichterResult(
        a_value=round(float(a_value), 3),
        b_value=round(float(b_value), 3),
        mc=mc,
    )


def interevent_times(catalog: EarthquakeCatalog) -> np.ndarray:
    """Compute inter-event time intervals in seconds.

    Args:
        catalog: Earthquake catalog (will be sorted by time).

    Returns:
        Array of time differences in seconds between consecutive events.

    Raises:
        ValueError: If catalog has fewer than 2 events.
    """
    if len(catalog) < 2:
        raise ValueError("Need at least 2 events to compute inter-event times")

    sorted_cat = catalog.sort_by_time()
    times = [eq.time for eq in sorted_cat]
    deltas = [(times[i + 1] - times[i]).total_seconds() for i in range(len(times) - 1)]
    return np.array(deltas)


def detect_anomalies(
    catalog: EarthquakeCatalog,
    window_days: int = 7,
    threshold_sigma: float = 2.0,
) -> list[AnomalyPeriod]:
    """Detect anomalous seismicity rate periods using a sliding window.

    Compares event counts in each window to the overall mean rate.
    Windows with counts exceeding mean + threshold_sigma * std are flagged.

    Args:
        catalog: Earthquake catalog to analyze.
        window_days: Sliding window size in days.
        threshold_sigma: Number of standard deviations for anomaly threshold.

    Returns:
        List of AnomalyPeriod objects for each detected anomaly.
    """
    if len(catalog) < 2:
        return []

    sorted_cat = catalog.sort_by_time()
    events = sorted_cat.earthquakes
    window = timedelta(days=window_days)

    # Count events in each sliding window
    window_counts = []
    window_indices = []
    for i, eq in enumerate(events):
        window_end = eq.time + window
        count = sum(1 for e in events[i:] if e.time <= window_end)
        window_counts.append(count)
        # Find end index
        end_idx = i
        for j in range(i, len(events)):
            if events[j].time <= window_end:
                end_idx = j
            else:
                break
        window_indices.append((i, end_idx))

    counts_arr = np.array(window_counts, dtype=float)
    mean_count = np.mean(counts_arr)
    std_count = np.std(counts_arr)

    if std_count == 0:
        return []

    anomalies = []
    for i, count in enumerate(window_counts):
        sigma_dev = (count - mean_count) / std_count
        if sigma_dev >= threshold_sigma:
            start_idx, end_idx = window_indices[i]
            anomalies.append(
                AnomalyPeriod(
                    start_index=start_idx,
                    end_index=end_idx,
                    event_count=count,
                    expected_count=round(mean_count, 1),
                    sigma_deviation=round(float(sigma_dev), 2),
                )
            )

    return anomalies


def clustering_coefficient(
    catalog: EarthquakeCatalog,
    radius_km: float = 50.0,
    time_window_hours: float = 72.0,
) -> float:
    """Compute a spatio-temporal clustering coefficient.

    Measures the fraction of event pairs that fall within a given
    spatial radius and time window.

    Args:
        catalog: Earthquake catalog to analyze.
        radius_km: Spatial clustering radius in kilometers.
        time_window_hours: Temporal clustering window in hours.

    Returns:
        Clustering coefficient between 0.0 and 1.0.
    """
    if len(catalog) < 2:
        return 0.0

    events = catalog.earthquakes
    n = len(events)
    total_pairs = n * (n - 1) / 2
    clustered_pairs = 0

    time_window = timedelta(hours=time_window_hours)

    for i in range(n):
        for j in range(i + 1, n):
            # Temporal check
            time_diff = abs(events[i].time - events[j].time)
            if time_diff > time_window:
                continue

            # Spatial check (approximate distance using Haversine)
            dist = _haversine_km(
                events[i].latitude,
                events[i].longitude,
                events[j].latitude,
                events[j].longitude,
            )
            if dist <= radius_km:
                clustered_pairs += 1

    return clustered_pairs / total_pairs


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the Haversine distance between two points in kilometers."""
    r = 6371.0  # Earth radius in km
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(
        np.radians(lat2)
    ) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return float(r * c)
