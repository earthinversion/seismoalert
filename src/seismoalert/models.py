"""Data models for earthquake data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Earthquake:
    """Represents a single earthquake event.

    Attributes:
        id: Unique event identifier from USGS.
        time: Event timestamp (UTC).
        latitude: Epicenter latitude in degrees.
        longitude: Epicenter longitude in degrees.
        depth: Hypocentral depth in kilometers.
        magnitude: Event magnitude.
        place: Human-readable location description.
        url: USGS event detail URL.
    """

    id: str
    time: datetime
    latitude: float
    longitude: float
    depth: float
    magnitude: float
    place: str
    url: str

    @classmethod
    def from_geojson_feature(cls, feature: dict) -> Earthquake:
        """Create an Earthquake from a USGS GeoJSON feature.

        Args:
            feature: A single GeoJSON feature dict from USGS API response.

        Returns:
            An Earthquake instance.
        """
        props = feature["properties"]
        coords = feature["geometry"]["coordinates"]
        return cls(
            id=feature["id"],
            time=datetime.fromtimestamp(props["time"] / 1000, tz=UTC),
            latitude=coords[1],
            longitude=coords[0],
            depth=coords[2],
            magnitude=props["mag"],
            place=props.get("place", "Unknown"),
            url=props.get("url", ""),
        )


@dataclass
class EarthquakeCatalog:
    """A collection of earthquake events with filtering and sorting helpers.

    Attributes:
        earthquakes: List of Earthquake objects.
    """

    earthquakes: list[Earthquake] = field(default_factory=list)

    @classmethod
    def from_geojson(cls, geojson: dict) -> EarthquakeCatalog:
        """Parse a USGS GeoJSON response into an EarthquakeCatalog.

        Args:
            geojson: Full GeoJSON FeatureCollection from the USGS API.

        Returns:
            An EarthquakeCatalog containing all parsed events.
        """
        quakes = [
            Earthquake.from_geojson_feature(f)
            for f in geojson.get("features", [])
            if f["properties"].get("mag") is not None
        ]
        return cls(earthquakes=quakes)

    def __len__(self) -> int:
        return len(self.earthquakes)

    def __iter__(self):
        return iter(self.earthquakes)

    def filter_by_magnitude(
        self, min_mag: float | None = None, max_mag: float | None = None
    ) -> EarthquakeCatalog:
        """Return a new catalog filtered by magnitude range.

        Args:
            min_mag: Minimum magnitude (inclusive).
            max_mag: Maximum magnitude (inclusive).

        Returns:
            Filtered EarthquakeCatalog.
        """
        filtered = self.earthquakes
        if min_mag is not None:
            filtered = [eq for eq in filtered if eq.magnitude >= min_mag]
        if max_mag is not None:
            filtered = [eq for eq in filtered if eq.magnitude <= max_mag]
        return EarthquakeCatalog(earthquakes=filtered)

    def filter_by_depth(
        self, min_depth: float | None = None, max_depth: float | None = None
    ) -> EarthquakeCatalog:
        """Return a new catalog filtered by depth range.

        Args:
            min_depth: Minimum depth in km (inclusive).
            max_depth: Maximum depth in km (inclusive).

        Returns:
            Filtered EarthquakeCatalog.
        """
        filtered = self.earthquakes
        if min_depth is not None:
            filtered = [eq for eq in filtered if eq.depth >= min_depth]
        if max_depth is not None:
            filtered = [eq for eq in filtered if eq.depth <= max_depth]
        return EarthquakeCatalog(earthquakes=filtered)

    def sort_by_time(self, reverse: bool = False) -> EarthquakeCatalog:
        """Return a new catalog sorted by event time.

        Args:
            reverse: If True, sort newest first.

        Returns:
            Sorted EarthquakeCatalog.
        """
        sorted_eqs = sorted(
            self.earthquakes, key=lambda eq: eq.time, reverse=reverse
        )
        return EarthquakeCatalog(earthquakes=sorted_eqs)

    def sort_by_magnitude(self, reverse: bool = True) -> EarthquakeCatalog:
        """Return a new catalog sorted by magnitude.

        Args:
            reverse: If True (default), sort largest first.

        Returns:
            Sorted EarthquakeCatalog.
        """
        return EarthquakeCatalog(
            earthquakes=sorted(
                self.earthquakes, key=lambda eq: eq.magnitude, reverse=reverse
            )
        )

    @property
    def magnitudes(self) -> list[float]:
        """List of all magnitudes in the catalog."""
        return [eq.magnitude for eq in self.earthquakes]

    @property
    def max_magnitude(self) -> float | None:
        """Maximum magnitude in the catalog, or None if empty."""
        if not self.earthquakes:
            return None
        return max(eq.magnitude for eq in self.earthquakes)
