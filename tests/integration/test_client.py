"""Integration tests for the USGS API client."""

from datetime import UTC, datetime

import pytest
import responses

from seismoalert.client import USGSClient, USGSClientError

pytestmark = pytest.mark.integration


class TestUSGSClient:
    @responses.activate
    def test_fetch_earthquakes_success(self, mock_usgs_response):
        client = USGSClient()
        catalog = client.fetch_earthquakes(
            starttime=datetime(2023, 11, 14, tzinfo=UTC),
            endtime=datetime(2023, 11, 15, tzinfo=UTC),
            min_magnitude=1.0,
        )
        assert len(catalog) == 10
        assert catalog.max_magnitude == 7.2

    @responses.activate
    def test_fetch_earthquakes_default_times(self, mock_usgs_response):
        client = USGSClient()
        catalog = client.fetch_earthquakes()
        assert len(catalog) == 10

    @responses.activate
    def test_fetch_earthquakes_with_filters(self, mock_usgs_response):
        client = USGSClient()
        catalog = client.fetch_earthquakes(
            min_magnitude=2.0,
            max_magnitude=6.0,
            min_depth=5.0,
            max_depth=20.0,
            limit=50,
        )
        assert len(catalog) == 10  # Mock always returns the same data

    @responses.activate
    def test_fetch_earthquakes_empty_response(self):
        responses.add(
            responses.GET,
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            json={"type": "FeatureCollection", "features": []},
            status=200,
        )
        client = USGSClient()
        catalog = client.fetch_earthquakes()
        assert len(catalog) == 0

    @responses.activate
    def test_fetch_earthquakes_http_error(self):
        responses.add(
            responses.GET,
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            json={"error": "Bad request"},
            status=400,
        )
        client = USGSClient(max_retries=0)
        with pytest.raises(USGSClientError, match="Failed to fetch"):
            client.fetch_earthquakes()

    @responses.activate
    def test_fetch_earthquakes_server_error(self):
        responses.add(
            responses.GET,
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            json={"error": "Internal server error"},
            status=500,
        )
        client = USGSClient(max_retries=0)
        with pytest.raises(USGSClientError, match="Failed to fetch"):
            client.fetch_earthquakes()

    @responses.activate
    def test_fetch_earthquakes_invalid_json(self):
        responses.add(
            responses.GET,
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            body="not json",
            status=200,
            content_type="text/plain",
        )
        client = USGSClient()
        with pytest.raises(USGSClientError, match="Invalid JSON"):
            client.fetch_earthquakes()

    @responses.activate
    def test_fetch_earthquakes_connection_error(self):
        responses.add(
            responses.GET,
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            body=ConnectionError("Connection refused"),
        )
        client = USGSClient(max_retries=0)
        with pytest.raises(USGSClientError, match="Failed to fetch"):
            client.fetch_earthquakes()

    def test_custom_base_url(self):
        client = USGSClient(base_url="https://custom.api.example.com/query")
        assert client.base_url == "https://custom.api.example.com/query"

    def test_custom_timeout(self):
        client = USGSClient(timeout=60)
        assert client.timeout == 60
