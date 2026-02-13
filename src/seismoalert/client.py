"""USGS Earthquake API client."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from seismoalert.models import EarthquakeCatalog

DEFAULT_BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
DEFAULT_TIMEOUT = 30


class USGSClientError(Exception):
    """Raised when the USGS API returns an error."""


class USGSClient:
    """Client for the USGS Earthquake Hazards Program API.

    Args:
        base_url: API endpoint URL.
        timeout: Request timeout in seconds.
        max_retries: Number of retries on transient failures.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=max_retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_earthquakes(
        self,
        starttime: datetime | None = None,
        endtime: datetime | None = None,
        min_magnitude: float | None = None,
        max_magnitude: float | None = None,
        min_depth: float | None = None,
        max_depth: float | None = None,
        limit: int = 1000,
    ) -> EarthquakeCatalog:
        """Fetch earthquake data from the USGS API.

        Args:
            starttime: Start of time window (defaults to 24 hours ago).
            endtime: End of time window (defaults to now).
            min_magnitude: Minimum magnitude filter.
            max_magnitude: Maximum magnitude filter.
            min_depth: Minimum depth in km.
            max_depth: Maximum depth in km.
            limit: Maximum number of events to return.

        Returns:
            EarthquakeCatalog with fetched events.

        Raises:
            USGSClientError: If the API returns an error response.
        """
        if endtime is None:
            endtime = datetime.now(UTC)
        if starttime is None:
            starttime = endtime - timedelta(days=1)

        params: dict = {
            "format": "geojson",
            "starttime": starttime.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": endtime.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": limit,
            "orderby": "time",
        }

        # Avoid sending unset params for cleaner API requests.
        if min_magnitude is not None:
            params["minmagnitude"] = min_magnitude
        if max_magnitude is not None:
            params["maxmagnitude"] = max_magnitude
        if min_depth is not None:
            params["mindepth"] = min_depth
        if max_depth is not None:
            params["maxdepth"] = max_depth

        try:
            response = self.session.get(
                self.base_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
        except (requests.exceptions.RequestException, ConnectionError) as exc:
            raise USGSClientError(
                f"Failed to fetch earthquake data: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise USGSClientError(f"Invalid JSON response: {exc}") from exc

        return EarthquakeCatalog.from_geojson(data)
