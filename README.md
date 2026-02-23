# SeismoAlert

[![CI](https://github.com/earthinversion/seismoalert/actions/workflows/ci.yml/badge.svg)](https://github.com/earthinversion/seismoalert/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/earthinversion/seismoalert/branch/main/graph/badge.svg)](https://codecov.io/gh/earthinversion/seismoalert)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Real-time earthquake monitor and anomaly detector using USGS earthquake data.

## Features

- **Real-time data**: Fetch earthquake data from the USGS Earthquake API
- **Statistical analysis**: Gutenberg-Richter law fitting, b-value estimation, anomaly detection
- **Interactive maps**: Generate interactive Folium maps of earthquake locations
- **Alerting**: Configurable threshold-based alert system with webhook/email stubs
- **CLI**: Command-line interface for fetching, analyzing, and visualizing data

## Installation

```bash
pip install seismoalert
```

For development:

```bash
git clone https://github.com/earthinversion/seismoalert.git
cd seismoalert
pip install -e ".[dev,test,docs]"
```

## Quick Start

```bash
# Fetch recent earthquakes (last 24 hours, M2.5+)
seismoalert fetch --min-magnitude 2.5 --days 1

# Run statistical analysis
seismoalert analyze --min-magnitude 1.0 --days 30

# Generate an interactive map
seismoalert map --output earthquakes.html

# One-shot monitor: fetch, analyze, check alerts
seismoalert monitor --min-magnitude 4.0
```

## Makefile Workflow

I can use the project `Makefile` as a single entrypoint for installation, running, stopping, and common development commands.

```bash
# Show all available commands
make help

# Install package locally
make install

# Install with dev/test/docs extras
make install-dev

# Start background monitor loop
make run

# Check whether the monitor is running
make status

# Stop background monitor loop
make close
```

I can also run CLI and development tasks from the same file:

```bash
# CLI wrappers
make fetch ARGS="--days 2 --min-magnitude 3.0"
make analyze ARGS="--days 30 --window-days 7"
make map ARGS="--output earthquakes.html"
make monitor ARGS="--alert-magnitude 6.5"

# Quality and docs
make lint
make test
make docs
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=seismoalert

# Run specific test groups
pytest -m unit
pytest -m integration
pytest -m e2e
```

## Documentation

Full documentation is available at [seismoalert.readthedocs.io](https://seismoalert.readthedocs.io/).

To build locally:

```bash
cd docs
make html
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
