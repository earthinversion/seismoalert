"""End-to-end tests for the CLI."""

import pytest
import responses
from click.testing import CliRunner

from seismoalert import __version__
from seismoalert.cli import main

pytestmark = pytest.mark.e2e


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_api(sample_geojson):
    """Activate mocked USGS API for all e2e tests."""
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://earthquake.usgs.gov/fdsnws/event/1/query",
            json=sample_geojson,
            status=200,
        )
        yield rsps


class TestCLIVersion:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestFetchCommand:
    def test_fetch_default(self, runner, mock_api):
        result = runner.invoke(main, ["fetch"])
        assert result.exit_code == 0
        assert "Fetched" in result.output
        assert "earthquakes" in result.output

    def test_fetch_with_options(self, runner, mock_api):
        result = runner.invoke(main, ["fetch", "--days", "7", "--min-magnitude", "3.0"])
        assert result.exit_code == 0
        assert "Fetched" in result.output

    def test_fetch_shows_top_events(self, runner, mock_api):
        result = runner.invoke(main, ["fetch"])
        assert result.exit_code == 0
        assert "Top events" in result.output
        assert "M7.2" in result.output

    def test_fetch_help(self, runner):
        result = runner.invoke(main, ["fetch", "--help"])
        assert result.exit_code == 0
        assert "--days" in result.output
        assert "--min-magnitude" in result.output

    def test_fetch_api_error(self, runner):
        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.GET,
                "https://earthquake.usgs.gov/fdsnws/event/1/query",
                json={"error": "Bad request"},
                status=400,
            )
            result = runner.invoke(main, ["fetch"])
            assert result.exit_code == 1
            assert "Error" in result.output


class TestAnalyzeCommand:
    def test_analyze_default(self, runner, mock_api):
        result = runner.invoke(main, ["analyze"])
        assert result.exit_code == 0
        assert "Analyzing" in result.output

    def test_analyze_shows_gr_fit(self, runner, mock_api):
        result = runner.invoke(main, ["analyze"])
        assert result.exit_code == 0
        assert "b-value" in result.output or "Insufficient" in result.output

    def test_analyze_with_options(self, runner, mock_api):
        result = runner.invoke(
            main, ["analyze", "--days", "14", "--min-magnitude", "2.0"]
        )
        assert result.exit_code == 0

    def test_analyze_help(self, runner):
        result = runner.invoke(main, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--window-days" in result.output


class TestMapCommand:
    def test_map_default(self, runner, mock_api, tmp_path):
        output = str(tmp_path / "test_map.html")
        result = runner.invoke(main, ["map", "--output", output])
        assert result.exit_code == 0
        assert "Map saved" in result.output

    def test_map_with_options(self, runner, mock_api, tmp_path):
        output = str(tmp_path / "test_map2.html")
        result = runner.invoke(
            main, ["map", "--days", "3", "--min-magnitude", "4.0", "--output", output]
        )
        assert result.exit_code == 0

    def test_map_help(self, runner):
        result = runner.invoke(main, ["map", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output


class TestMonitorCommand:
    def test_monitor_default(self, runner, mock_api):
        result = runner.invoke(main, ["monitor"])
        assert result.exit_code == 0
        assert "Monitoring" in result.output

    def test_monitor_triggers_alert(self, runner, mock_api):
        result = runner.invoke(
            main, ["monitor", "--alert-magnitude", "5.0", "--alert-count", "5"]
        )
        assert result.exit_code == 0
        assert "alert" in result.output.lower()

    def test_monitor_no_alerts(self, runner, mock_api):
        result = runner.invoke(
            main, ["monitor", "--alert-magnitude", "9.0", "--alert-count", "1000"]
        )
        assert result.exit_code == 0
        assert "All clear" in result.output

    def test_monitor_help(self, runner):
        result = runner.invoke(main, ["monitor", "--help"])
        assert result.exit_code == 0
        assert "--alert-magnitude" in result.output
        assert "--alert-count" in result.output
