"""Unit tests for data models."""

import pytest

from seismoalert.models import Earthquake, EarthquakeCatalog

pytestmark = pytest.mark.unit


class TestEarthquake:
    def test_creation(self, sample_earthquake):
        assert sample_earthquake.id == "eq001"
        assert sample_earthquake.magnitude == 5.2
        assert sample_earthquake.latitude == 35.0
        assert sample_earthquake.longitude == -118.0
        assert sample_earthquake.depth == 10.0

    def test_from_geojson_feature(self):
        feature = {
            "type": "Feature",
            "id": "test123",
            "properties": {
                "mag": 4.5,
                "place": "Somewhere, Earth",
                "time": 1700000000000,
                "url": "https://example.com/eq",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [-120.0, 36.0, 8.0],
            },
        }
        eq = Earthquake.from_geojson_feature(feature)
        assert eq.id == "test123"
        assert eq.magnitude == 4.5
        assert eq.latitude == 36.0
        assert eq.longitude == -120.0
        assert eq.depth == 8.0
        assert eq.place == "Somewhere, Earth"

    def test_from_geojson_feature_missing_place(self):
        feature = {
            "type": "Feature",
            "id": "test456",
            "properties": {"mag": 3.0, "time": 1700000000000},
            "geometry": {"type": "Point", "coordinates": [0.0, 0.0, 5.0]},
        }
        eq = Earthquake.from_geojson_feature(feature)
        assert eq.place == "Unknown"

    def test_earthquake_is_frozen(self, sample_earthquake):
        with pytest.raises(AttributeError):
            sample_earthquake.magnitude = 9.0


class TestEarthquakeCatalog:
    def test_from_geojson(self, sample_geojson):
        catalog = EarthquakeCatalog.from_geojson(sample_geojson)
        assert len(catalog) == 10

    def test_from_geojson_skips_null_magnitudes(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "null_mag",
                    "properties": {"mag": None, "time": 1700000000000},
                    "geometry": {"type": "Point", "coordinates": [0, 0, 5]},
                },
                {
                    "type": "Feature",
                    "id": "valid",
                    "properties": {"mag": 3.0, "place": "Test", "time": 1700000000000},
                    "geometry": {"type": "Point", "coordinates": [0, 0, 5]},
                },
            ],
        }
        catalog = EarthquakeCatalog.from_geojson(geojson)
        assert len(catalog) == 1

    def test_from_geojson_empty(self):
        catalog = EarthquakeCatalog.from_geojson({"features": []})
        assert len(catalog) == 0

    def test_filter_by_magnitude(self, sample_catalog):
        filtered = sample_catalog.filter_by_magnitude(min_mag=4.0)
        assert all(eq.magnitude >= 4.0 for eq in filtered)
        assert len(filtered) > 0

    def test_filter_by_magnitude_max(self, sample_catalog):
        filtered = sample_catalog.filter_by_magnitude(max_mag=3.0)
        assert all(eq.magnitude <= 3.0 for eq in filtered)

    def test_filter_by_magnitude_range(self, sample_catalog):
        filtered = sample_catalog.filter_by_magnitude(min_mag=2.0, max_mag=4.0)
        assert all(2.0 <= eq.magnitude <= 4.0 for eq in filtered)

    def test_filter_by_depth(self, sample_catalog):
        filtered = sample_catalog.filter_by_depth(min_depth=10.0)
        assert all(eq.depth >= 10.0 for eq in filtered)

    def test_filter_by_depth_max(self, sample_catalog):
        filtered = sample_catalog.filter_by_depth(max_depth=8.0)
        assert all(eq.depth <= 8.0 for eq in filtered)

    def test_sort_by_time(self, sample_catalog):
        sorted_cat = sample_catalog.sort_by_time()
        times = [eq.time for eq in sorted_cat]
        assert times == sorted(times)

    def test_sort_by_time_reverse(self, sample_catalog):
        sorted_cat = sample_catalog.sort_by_time(reverse=True)
        times = [eq.time for eq in sorted_cat]
        assert times == sorted(times, reverse=True)

    def test_sort_by_magnitude(self, sample_catalog):
        sorted_cat = sample_catalog.sort_by_magnitude()
        mags = [eq.magnitude for eq in sorted_cat]
        assert mags == sorted(mags, reverse=True)

    def test_magnitudes_property(self, sample_catalog):
        mags = sample_catalog.magnitudes
        assert len(mags) == 10
        assert all(isinstance(m, float) for m in mags)

    def test_max_magnitude(self, sample_catalog):
        assert sample_catalog.max_magnitude == 7.2

    def test_max_magnitude_empty(self):
        catalog = EarthquakeCatalog()
        assert catalog.max_magnitude is None

    def test_iteration(self, sample_catalog):
        count = sum(1 for _ in sample_catalog)
        assert count == 10
