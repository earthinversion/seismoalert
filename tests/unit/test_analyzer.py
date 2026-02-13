"""Unit tests for statistical analysis."""

from datetime import UTC

import numpy as np
import pytest

from seismoalert.analyzer import (
    AnomalyPeriod,
    GutenbergRichterResult,
    clustering_coefficient,
    detect_anomalies,
    gutenberg_richter,
    interevent_times,
    magnitude_of_completeness,
)
from seismoalert.models import EarthquakeCatalog

pytestmark = pytest.mark.unit


class TestMagnitudeOfCompleteness:
    def test_basic(self, sample_catalog):
        mc = magnitude_of_completeness(sample_catalog)
        assert isinstance(mc, float)
        assert 1.0 <= mc <= 8.0

    def test_empty_catalog(self):
        catalog = EarthquakeCatalog()
        with pytest.raises(ValueError, match="empty catalog"):
            magnitude_of_completeness(catalog)


class TestGutenbergRichter:
    def test_basic_fit(self, sample_catalog):
        result = gutenberg_richter(sample_catalog)
        assert isinstance(result, GutenbergRichterResult)
        assert result.b_value > 0
        assert result.a_value > 0
        assert result.mc > 0

    def test_with_explicit_mc(self, sample_catalog):
        result = gutenberg_richter(sample_catalog, mc=2.0)
        assert result.mc == 2.0
        assert result.b_value > 0

    def test_empty_catalog(self):
        catalog = EarthquakeCatalog()
        with pytest.raises(ValueError, match="empty catalog"):
            gutenberg_richter(catalog)

    def test_insufficient_data(self, sample_catalog):
        # Filter to very high magnitudes where few events exist
        with pytest.raises(ValueError, match="Insufficient events"):
            gutenberg_richter(sample_catalog, mc=8.0)


class TestIntereventTimes:
    def test_basic(self, sample_catalog):
        deltas = interevent_times(sample_catalog)
        assert isinstance(deltas, np.ndarray)
        assert len(deltas) == len(sample_catalog) - 1
        assert all(d >= 0 for d in deltas)

    def test_sorted_output(self, sample_catalog):
        """Inter-event times should be for consecutive sorted events."""
        deltas = interevent_times(sample_catalog)
        # All deltas should be non-negative since events are sorted by time
        assert all(d >= 0 for d in deltas)

    def test_too_few_events(self):
        from datetime import datetime

        from seismoalert.models import Earthquake

        eq = Earthquake(
            id="single",
            time=datetime(2023, 1, 1, tzinfo=UTC),
            latitude=0,
            longitude=0,
            depth=5,
            magnitude=3.0,
            place="Test",
            url="",
        )
        catalog = EarthquakeCatalog(earthquakes=[eq])
        with pytest.raises(ValueError, match="at least 2"):
            interevent_times(catalog)


class TestDetectAnomalies:
    def test_returns_list(self, sample_catalog):
        anomalies = detect_anomalies(sample_catalog)
        assert isinstance(anomalies, list)

    def test_anomaly_structure(self, sample_catalog):
        anomalies = detect_anomalies(sample_catalog, threshold_sigma=0.5)
        if anomalies:
            a = anomalies[0]
            assert isinstance(a, AnomalyPeriod)
            assert a.event_count > 0
            assert a.sigma_deviation >= 0.5

    def test_empty_catalog(self):
        catalog = EarthquakeCatalog()
        anomalies = detect_anomalies(catalog)
        assert anomalies == []

    def test_single_event(self):
        from datetime import datetime

        from seismoalert.models import Earthquake

        eq = Earthquake(
            id="single",
            time=datetime(2023, 1, 1, tzinfo=UTC),
            latitude=0,
            longitude=0,
            depth=5,
            magnitude=3.0,
            place="Test",
            url="",
        )
        catalog = EarthquakeCatalog(earthquakes=[eq])
        assert detect_anomalies(catalog) == []


class TestClusteringCoefficient:
    def test_basic(self, sample_catalog):
        cc = clustering_coefficient(sample_catalog)
        assert isinstance(cc, float)
        assert 0.0 <= cc <= 1.0

    def test_empty_catalog(self):
        catalog = EarthquakeCatalog()
        assert clustering_coefficient(catalog) == 0.0

    def test_single_event(self):
        from datetime import datetime

        from seismoalert.models import Earthquake

        eq = Earthquake(
            id="single",
            time=datetime(2023, 1, 1, tzinfo=UTC),
            latitude=0,
            longitude=0,
            depth=5,
            magnitude=3.0,
            place="Test",
            url="",
        )
        catalog = EarthquakeCatalog(earthquakes=[eq])
        assert clustering_coefficient(catalog) == 0.0
