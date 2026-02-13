"""Integration tests for visualization output."""


import pytest

from seismoalert.models import EarthquakeCatalog
from seismoalert.visualizer import (
    create_earthquake_map,
    plot_gutenberg_richter,
    plot_magnitude_time,
)

pytestmark = pytest.mark.integration


class TestCreateEarthquakeMap:
    def test_generates_html_file(self, sample_catalog, tmp_path):
        output = tmp_path / "test_map.html"
        result = create_earthquake_map(sample_catalog, output_path=output)
        assert result == output
        assert output.exists()
        content = output.read_text()
        assert "folium" in content.lower() or "leaflet" in content.lower()

    def test_empty_catalog(self, tmp_path):
        catalog = EarthquakeCatalog()
        output = tmp_path / "empty_map.html"
        create_earthquake_map(catalog, output_path=output)
        assert output.exists()

    def test_map_contains_markers(self, sample_catalog, tmp_path):
        output = tmp_path / "markers_map.html"
        create_earthquake_map(sample_catalog, output_path=output)
        content = output.read_text()
        # Check that earthquake location data appears in the HTML
        assert "Los Angeles" in content or "CircleMarker" in content


class TestPlotMagnitudeTime:
    def test_generates_image(self, sample_catalog, tmp_path):
        output = tmp_path / "mag_time.png"
        result = plot_magnitude_time(sample_catalog, output_path=output)
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_output_is_valid_png(self, sample_catalog, tmp_path):
        output = tmp_path / "mag_time.png"
        plot_magnitude_time(sample_catalog, output_path=output)
        # PNG files start with these magic bytes
        with open(output, "rb") as f:
            header = f.read(4)
        assert header[1:4] == b"PNG"


class TestPlotGutenbergRichter:
    def test_generates_image(self, sample_catalog, tmp_path):
        output = tmp_path / "gr_plot.png"
        result = plot_gutenberg_richter(
            sample_catalog, a_value=5.0, b_value=1.0, output_path=output
        )
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_output_is_valid_png(self, sample_catalog, tmp_path):
        output = tmp_path / "gr_plot.png"
        plot_gutenberg_richter(
            sample_catalog, a_value=5.0, b_value=1.0, output_path=output
        )
        with open(output, "rb") as f:
            header = f.read(4)
        assert header[1:4] == b"PNG"

    def test_with_mc(self, sample_catalog, tmp_path):
        output = tmp_path / "gr_mc.png"
        result = plot_gutenberg_richter(
            sample_catalog,
            a_value=5.0,
            b_value=1.0,
            output_path=output,
            mc=2.5,
        )
        assert result == output
        assert output.exists()
        assert output.stat().st_size > 0

    def test_without_mc(self, sample_catalog, tmp_path):
        output = tmp_path / "gr_no_mc.png"
        result = plot_gutenberg_richter(
            sample_catalog,
            a_value=5.0,
            b_value=1.0,
            output_path=output,
        )
        assert result == output
        assert output.exists()
