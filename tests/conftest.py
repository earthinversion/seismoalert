"""Shared fixtures and configuration for tests."""

from datetime import UTC, datetime

import pytest

from seismoalert.models import Earthquake, EarthquakeCatalog


def _make_feature(
    eq_id: str,
    time_ms: int,
    lat: float,
    lon: float,
    depth: float,
    mag: float,
    place: str,
) -> dict:
    """Helper to create a USGS GeoJSON feature dict."""
    return {
        "type": "Feature",
        "id": eq_id,
        "properties": {
            "mag": mag,
            "place": place,
            "time": time_ms,
            "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{eq_id}",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [lon, lat, depth],
        },
    }


@pytest.fixture
def sample_geojson() -> dict:
    """A realistic USGS GeoJSON FeatureCollection with diverse events."""
    return {
        "type": "FeatureCollection",
        "metadata": {"generated": 1700000000000, "count": 10},
        "features": [
            _make_feature(
                "eq001", 1700000000000, 35.0, -118.0,
                10.0, 5.2, "10km NE of Los Angeles, CA",
            ),
            _make_feature(
                "eq002", 1700003600000, 36.5, -121.5,
                8.0, 3.1, "15km S of Hollister, CA",
            ),
            _make_feature(
                "eq003", 1700007200000, 34.0, -117.5,
                12.0, 2.5, "5km W of Riverside, CA",
            ),
            _make_feature(
                "eq004", 1700010800000, 37.8, -122.4,
                5.0, 4.0, "Near San Francisco, CA",
            ),
            _make_feature(
                "eq005", 1700014400000, 33.5, -116.5,
                15.0, 6.1, "20km S of Palm Springs, CA",
            ),
            _make_feature(
                "eq006", 1700018000000, 38.0, -122.0,
                7.0, 1.8, "10km E of Napa, CA",
            ),
            _make_feature(
                "eq007", 1700021600000, 35.5, -119.0,
                9.0, 2.0, "Near Bakersfield, CA",
            ),
            _make_feature(
                "eq008", 1700025200000, 36.0, -120.0,
                11.0, 3.5, "Central California",
            ),
            _make_feature(
                "eq009", 1700028800000, 34.5, -118.5,
                6.0, 7.2, "Near Los Angeles, CA",
            ),
            _make_feature(
                "eq010", 1700032400000, 37.0, -121.0,
                8.0, 2.8, "Near San Jose, CA",
            ),
        ],
    }


@pytest.fixture
def sample_catalog(sample_geojson) -> EarthquakeCatalog:
    """A pre-built EarthquakeCatalog from the sample GeoJSON."""
    return EarthquakeCatalog.from_geojson(sample_geojson)


@pytest.fixture
def sample_earthquake() -> Earthquake:
    """A single sample Earthquake instance."""
    return Earthquake(
        id="eq001",
        time=datetime(2023, 11, 14, 22, 13, 20, tzinfo=UTC),
        latitude=35.0,
        longitude=-118.0,
        depth=10.0,
        magnitude=5.2,
        place="10km NE of Los Angeles, CA",
        url="https://earthquake.usgs.gov/earthquakes/eventpage/eq001",
    )


@pytest.fixture
def mock_usgs_response(sample_geojson):
    """Set up a mocked USGS API response using the responses library."""
    import responses

    responses.add(
        responses.GET,
        "https://earthquake.usgs.gov/fdsnws/event/1/query",
        json=sample_geojson,
        status=200,
    )
    return sample_geojson
