# SeismoAlert — Project Architecture Reference

> **Purpose of this file**: This is the canonical architecture reference for the SeismoAlert project.
> It is intended for both human developers and AI agents (Claude Code, Codex, Copilot, etc.).
> AI agents should read this file before making any modifications to understand the project
> structure, conventions, dependencies, and design decisions.

---

## Project Overview

**SeismoAlert** is a real-time earthquake monitor and anomaly detector that fetches data from the
USGS Earthquake Hazards Program API. It is designed as a CI/CD portfolio showcase project.

| Attribute       | Value                                      |
|-----------------|--------------------------------------------|
| Language        | Python 3.11 — 3.13                         |
| Version         | Defined in `src/seismoalert/__init__.py`    |
| License         | MIT                                        |
| Package layout  | `src/` layout (PEP 621, setuptools)        |
| Entry point     | `seismoalert` CLI via Click                |
| Config file     | `pyproject.toml` (single source of truth)  |

---

## Directory Structure

```
seismoalert/
├── .github/workflows/
│   ├── ci.yml                 # Lint (ruff) + test matrix (3.11–3.13) + coverage
│   ├── release.yml            # Build sdist/wheel, create GitHub Release on tag v*
│   └── docs.yml               # Sphinx build + deploy to GitHub Pages
├── src/seismoalert/
│   ├── __init__.py            # __version__ only
│   ├── models.py              # Earthquake, EarthquakeCatalog dataclasses
│   ├── client.py              # USGSClient — HTTP client with retries
│   ├── analyzer.py            # G-R law, anomaly detection, clustering
│   ├── alerts.py              # AlertRule, AlertManager, webhook/email stubs
│   ├── visualizer.py          # Folium maps, matplotlib plots
│   └── cli.py                 # Click CLI (fetch, analyze, map, monitor)
├── tests/
│   ├── conftest.py            # Shared fixtures (sample_geojson, sample_catalog, etc.)
│   ├── unit/                  # Pure logic tests (no I/O, no network)
│   │   ├── test_models.py
│   │   ├── test_analyzer.py
│   │   └── test_alerts.py
│   ├── integration/           # Tests with mocked HTTP or file I/O
│   │   ├── test_client.py
│   │   └── test_visualizer.py
│   └── e2e/                   # Full CLI invocations via CliRunner
│       └── test_cli.py
├── docs/                      # Sphinx documentation (RTD theme)
│   ├── conf.py
│   ├── index.rst
│   ├── installation.rst
│   ├── usage.rst
│   ├── api.rst                # Auto-generated from docstrings (autodoc)
│   └── Makefile
├── pyproject.toml             # All project metadata, deps, tool config
├── .readthedocs.yaml
├── .gitignore
├── LICENSE
├── README.md
└── CHANGELOG.md
```

---

## Module Dependency Graph

```
__init__.py  (no deps — version string only)

models.py  (no internal deps — foundational)
    │
    ├──► client.py      (models)           + requests
    ├──► analyzer.py    (models)           + numpy
    ├──► alerts.py      (models)           + logging, collections.abc
    ├──► visualizer.py  (models)           + folium, matplotlib, numpy
    │
    └──► cli.py         (ALL modules)      + click, sys
```

**Key invariant**: `models.py` has zero internal dependencies. Every other module depends only
on `models.py` (except `cli.py` which orchestrates everything). This keeps the dependency graph
a clean star topology with `models` at the center and `cli` at the outer edge.

---

## Module Details

### `models.py` — Data Models

The foundational module. All other modules consume its types.

| Type                 | Kind              | Key Details                                       |
|----------------------|-------------------|---------------------------------------------------|
| `Earthquake`         | frozen dataclass  | id, time, lat, lon, depth, magnitude, place, url  |
| `EarthquakeCatalog`  | mutable dataclass | list of Earthquakes + filter/sort/property helpers |

- `Earthquake.from_geojson_feature(feature: dict)` — parses a single USGS GeoJSON feature.
- `EarthquakeCatalog.from_geojson(geojson: dict)` — parses a full USGS FeatureCollection.
  Skips features where `mag` is `None`.
- Filtering/sorting methods return **new** `EarthquakeCatalog` instances (immutable pattern).
- `EarthquakeCatalog` supports `len()`, iteration, `.magnitudes`, `.max_magnitude`.

### `client.py` — USGS API Client

| Type               | Kind       | Key Details                                      |
|--------------------|------------|--------------------------------------------------|
| `USGSClientError`  | Exception  | Raised on HTTP errors, connection errors, bad JSON |
| `USGSClient`       | Class      | Configurable base_url, timeout, max_retries      |

- Uses `requests.Session` with `HTTPAdapter(max_retries=...)`.
- `fetch_earthquakes(...)` returns `EarthquakeCatalog`.
- Default time window: last 24 hours. Default limit: 1000.
- Catches both `requests.exceptions.RequestException` and bare `ConnectionError`.

### `analyzer.py` — Statistical Analysis

| Function / Type               | Returns                  | Key Details                                    |
|-------------------------------|--------------------------|------------------------------------------------|
| `magnitude_of_completeness()` | `float`                  | Max-curvature method, 0.1 magnitude bins       |
| `gutenberg_richter()`         | `GutenbergRichterResult` | Aki (1965) MLE b-value, bin correction 0.1     |
| `interevent_times()`          | `np.ndarray`             | Time deltas in seconds between sorted events   |
| `detect_anomalies()`          | `list[AnomalyPeriod]`   | Sliding window, sigma-based threshold          |
| `clustering_coefficient()`    | `float` (0–1)            | Spatio-temporal pair fraction, Haversine dist  |
| `_haversine_km()`             | `float`                  | Private, Earth radius = 6371 km                |

- All functions that need ≥2 events raise `ValueError` on insufficient data.
- `detect_anomalies` returns empty list for catalogs with <2 events or zero std.

### `alerts.py` — Alert System

| Type / Function                   | Kind              | Key Details                                 |
|-----------------------------------|-------------------|---------------------------------------------|
| `Alert`                           | dataclass         | rule_name + message                         |
| `AlertRule`                       | dataclass         | name + condition (callable) + template      |
| `AlertManager`                    | dataclass         | rules list, `add_rule()`, `evaluate()`      |
| `WebhookAlert`                    | class (stub)      | Logs via `logging.info`, does not POST      |
| `EmailAlert`                      | class (stub)      | Logs via `logging.info`, does not send      |
| `large_earthquake_condition()`    | factory → callable | Triggers if any event ≥ threshold           |
| `high_rate_condition()`           | factory → callable | Triggers if event count > threshold         |

- `AlertRule.evaluate()` formats the template with `{count}` and `{max_mag}` placeholders.
- Webhook/Email classes are **stubs** — they log but don't perform real I/O.

### `visualizer.py` — Visualization

| Function                    | Output         | Key Details                                  |
|-----------------------------|----------------|----------------------------------------------|
| `create_earthquake_map()`   | HTML (Folium)  | CircleMarkers, color/size by magnitude       |
| `plot_magnitude_time()`     | PNG (matplotlib)| Scatter plot, YlOrRd colormap, 150 DPI      |
| `plot_gutenberg_richter()`  | PNG (matplotlib)| Observed cumulative + fitted G-R line        |

- `matplotlib.use("Agg")` is set at module level (headless backend).
- Color mapping: red (≥7), orange (≥5), yellow (≥3), green (<3).
- All functions return `Path` to the saved output file.

### `cli.py` — Command-Line Interface

| Command              | Default Options                                          | Purpose                            |
|----------------------|----------------------------------------------------------|------------------------------------|
| `seismoalert fetch`  | --days 1, --min-magnitude 2.5, --limit 100               | Fetch and display recent quakes    |
| `seismoalert analyze`| --days 30, --min-magnitude 1.0, --window-days 7          | G-R fit + anomaly detection        |
| `seismoalert map`    | --days 7, --min-magnitude 2.5, --output earthquakes.html | Generate interactive Folium map    |
| `seismoalert monitor`| --days 1, --min-magnitude 4.0, --alert-magnitude 6.0, --alert-count 50 | One-shot fetch + alert check |

- All commands catch `USGSClientError` and exit with code 1 on API failure.
- `main()` is the Click group entry point registered in `pyproject.toml` as `seismoalert`.

---

## Testing Architecture

### Test Organization

| Level         | Directory              | Marker         | Characteristics                            |
|---------------|------------------------|----------------|--------------------------------------------|
| Unit          | `tests/unit/`          | `@pytest.mark.unit`        | Pure logic, no I/O, no mocking  |
| Integration   | `tests/integration/`   | `@pytest.mark.integration` | Mocked HTTP (`responses`), file I/O |
| End-to-end    | `tests/e2e/`           | `@pytest.mark.e2e`         | Full CLI via `click.testing.CliRunner` |

### Running Tests

```bash
pytest                          # All tests
pytest -m unit                  # Unit tests only
pytest -m integration           # Integration tests only
pytest -m e2e                   # End-to-end tests only
pytest --cov=seismoalert        # With coverage report
```

### Key Fixtures (`tests/conftest.py`)

| Fixture               | Scope   | Provides                                           |
|------------------------|---------|----------------------------------------------------|
| `sample_geojson`       | function | USGS GeoJSON dict with 10 California earthquakes  |
| `sample_catalog`       | function | `EarthquakeCatalog` parsed from `sample_geojson`  |
| `sample_earthquake`    | function | Single `Earthquake` instance (M5.2, Los Angeles)  |
| `mock_usgs_response`   | function | Activates `responses` mock for USGS API endpoint  |

- The sample data contains magnitudes from 1.8 to 7.2, all in California.
- `mock_usgs_response` requires `@responses.activate` on the test (already used in integration tests).
- E2E tests use their own `mock_api` fixture that wraps `responses.RequestsMock` as context manager.

### Coverage Requirements

- Minimum: **80%** (configured in `pyproject.toml` under `[tool.coverage.report]`).
- Current: **~95%**.
- Branch coverage is enabled.

---

## CI/CD Pipelines

### `ci.yml` — Continuous Integration

- **Triggers**: push to `main`, PRs to `main`.
- **Lint job**: Python 3.12, runs `ruff check src/ tests/`.
- **Test job**: Matrix over Python 3.11, 3.12, 3.13. Runs `pytest --cov` with XML+terminal reports.
  Uploads coverage to Codecov on Python 3.12 only.

### `release.yml` — Release

- **Triggers**: tag push matching `v*`.
- Builds sdist + wheel with `python -m build`.
- Creates a GitHub Release with the dist artifacts and auto-generated release notes.

### `docs.yml` — Documentation

- **Triggers**: push to `main`.
- Builds Sphinx docs and deploys to GitHub Pages via `actions/deploy-pages`.

---

## Coding Conventions

### Style

- **Linter**: Ruff (rules: E, F, W, I, N, UP, B, SIM).
- **Line length**: 88 characters.
- **Target Python**: 3.11 (uses `from __future__ import annotations` for modern type hints).
- **Imports**: Use `from datetime import UTC` (not `timezone.utc`) per UP017.
- **Docstrings**: Google style (parsed by `sphinx.ext.napoleon`).

### Design Patterns

- **Immutable data flow**: `Earthquake` is a frozen dataclass. Catalog filter/sort methods
  return new instances rather than mutating in place.
- **Star dependency graph**: All domain modules depend only on `models.py`.
  Only `cli.py` imports from multiple modules.
- **Stub pattern for notifications**: `WebhookAlert` and `EmailAlert` log instead of
  performing real I/O, making them safe to use in tests and demos.
- **Factory functions for conditions**: `large_earthquake_condition()` and
  `high_rate_condition()` return callables, keeping `AlertRule` generic.

### Version Management

- **Single source of truth**: `src/seismoalert/__init__.py` contains `__version__`.
- **Changelog**: `CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- **Git tags**: `v0.1.0` format. Tag push triggers the release workflow.

---

## External Dependencies

| Package      | Purpose                        | Used In          |
|--------------|--------------------------------|------------------|
| `requests`   | HTTP client for USGS API       | `client.py`      |
| `click`      | CLI framework                  | `cli.py`         |
| `folium`     | Interactive Leaflet.js maps    | `visualizer.py`  |
| `matplotlib` | Static plots (PNG)             | `visualizer.py`  |
| `numpy`      | Numerical/statistical methods  | `analyzer.py`, `visualizer.py` |

Dev/test/docs dependencies are listed in `pyproject.toml` under `[project.optional-dependencies]`.

---

## Common Tasks for AI Agents

### Adding a new CLI command

1. Define the command function in `cli.py` with `@main.command()` decorator.
2. Use the same pattern: create `USGSClient`, fetch data, process, output.
3. Add e2e tests in `tests/e2e/test_cli.py` using `CliRunner` with mocked API.

### Adding a new analysis function

1. Add the function to `analyzer.py`. It should accept `EarthquakeCatalog` as input.
2. Raise `ValueError` for insufficient data (maintain the existing convention).
3. Add unit tests in `tests/unit/test_analyzer.py`.
4. Optionally expose it via a CLI command in `cli.py`.

### Adding a new alert condition

1. Create a factory function in `alerts.py` that returns `Callable[[EarthquakeCatalog], bool]`.
2. Register it with `AlertManager.add_rule()` using an `AlertRule`.
3. Add unit tests in `tests/unit/test_alerts.py`.

### Adding a new visualization

1. Add the function to `visualizer.py`. Accept `catalog` + `output_path`, return `Path`.
2. Use `matplotlib.pyplot` for static images or `folium` for interactive maps.
3. Add integration tests in `tests/integration/test_visualizer.py` (check file exists, valid format).

### Modifying the USGS client

1. Edit `client.py`. Maintain the `USGSClientError` exception pattern.
2. Update integration tests in `tests/integration/test_client.py` using `@responses.activate`.
3. If adding new API parameters, add them as optional kwargs to `fetch_earthquakes()`.

### Upgrading the version

1. Update `__version__` in `src/seismoalert/__init__.py`.
2. Add a new section to `CHANGELOG.md`.
3. Create a git tag: `git tag v<new_version>`.

---

## Pitfalls and Known Considerations

- **`matplotlib.use("Agg")`** is set at import time in `visualizer.py`. This is required for
  headless environments (CI, servers). Do not remove it.
- **`responses` library mocking**: Integration tests for `client.py` use `@responses.activate`.
  The `mock_usgs_response` fixture in conftest adds the mock but does NOT activate it —
  tests must use `@responses.activate` decorator themselves. E2E tests use a context-manager
  based `mock_api` fixture instead.
- **`ConnectionError` handling**: The USGS client catches both `requests.exceptions.RequestException`
  and bare `ConnectionError` because the `responses` mock library raises `ConnectionError` directly
  (not wrapped in a requests exception).
- **GeoJSON null magnitudes**: `EarthquakeCatalog.from_geojson()` silently skips features where
  `mag` is `None`. This is intentional — USGS sometimes returns events without computed magnitudes.
- **Frozen dataclass**: `Earthquake` is `frozen=True`. Do not attempt to mutate its fields.
