SHELL := /bin/bash

.DEFAULT_GOAL := help

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PACKAGE ?= seismoalert
CLI_CMD ?= PYTHONPATH=src $(PYTHON) -m seismoalert.cli

RUN_DIR ?= .run
PID_FILE ?= $(RUN_DIR)/seismoalert.pid
LOG_FILE ?= $(RUN_DIR)/seismoalert.log

MONITOR_DAYS ?= 1
MONITOR_MIN_MAG ?= 4.0
ALERT_MAG ?= 6.0
ALERT_COUNT ?= 50
POLL_INTERVAL ?= 300
MONITOR_ARGS ?= --days $(MONITOR_DAYS) --min-magnitude $(MONITOR_MIN_MAG) --alert-magnitude $(ALERT_MAG) --alert-count $(ALERT_COUNT)
ARGS ?=

.PHONY: help install install-dev uninstall run close stop restart status logs \
	fetch analyze map monitor test test-unit test-integration \
	test-e2e lint format check docs clean

help: ## Show available targets.
	@awk 'BEGIN {FS = ":.*##"; print "Available targets:"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install package in editable mode.
	$(PIP) install -e .

install-dev: ## Install package with dev, test, and docs extras.
	$(PIP) install -e ".[dev,test,docs]"

uninstall: ## Uninstall package.
	$(PIP) uninstall -y $(PACKAGE)

run: ## Start a background monitoring loop.
	@mkdir -p "$(RUN_DIR)"
	@if [ -f "$(PID_FILE)" ] && kill -0 "$$(cat "$(PID_FILE)")" 2>/dev/null; then \
		echo "Monitor is already running with PID $$(cat "$(PID_FILE)")."; \
		exit 1; \
	fi
	@if [ -f "$(PID_FILE)" ]; then rm -f "$(PID_FILE)"; fi
	@nohup /bin/bash -c 'while true; do $(CLI_CMD) monitor $(MONITOR_ARGS); sleep "$(POLL_INTERVAL)"; done' >>"$(LOG_FILE)" 2>&1 & echo $$! >"$(PID_FILE)"
	@echo "Started monitor loop with PID $$(cat "$(PID_FILE)")."
	@echo "Logs: $(LOG_FILE)"

close: ## Stop the background monitoring loop.
	@if [ ! -f "$(PID_FILE)" ]; then \
		echo "Monitor is not running."; \
		exit 0; \
	fi
	@pid="$$(cat "$(PID_FILE)")"; \
	if kill -0 "$$pid" 2>/dev/null; then \
		kill "$$pid"; \
		echo "Stopped monitor loop (PID $$pid)."; \
	else \
		echo "PID $$pid is not active. Cleaning stale PID file."; \
	fi; \
	rm -f "$(PID_FILE)"

stop: close ## Alias for close.

restart: ## Restart the background monitoring loop.
	@$(MAKE) --no-print-directory close
	@$(MAKE) --no-print-directory run

status: ## Show monitoring loop status.
	@if [ -f "$(PID_FILE)" ] && kill -0 "$$(cat "$(PID_FILE)")" 2>/dev/null; then \
		echo "running (PID $$(cat "$(PID_FILE)"))"; \
	else \
		echo "stopped"; \
	fi

logs: ## Tail monitoring logs.
	@mkdir -p "$(RUN_DIR)"
	@touch "$(LOG_FILE)"
	@tail -f "$(LOG_FILE)"

fetch: ## Run CLI fetch command (set ARGS="...").
	$(CLI_CMD) fetch $(ARGS)

analyze: ## Run CLI analyze command (set ARGS="...").
	$(CLI_CMD) analyze $(ARGS)

map: ## Run CLI map command (set ARGS="...").
	$(CLI_CMD) map $(ARGS)

monitor: ## Run one-shot monitor command (set ARGS="...").
	$(CLI_CMD) monitor $(ARGS)

test: ## Run full test suite.
	pytest

test-unit: ## Run unit tests.
	pytest -m unit

test-integration: ## Run integration tests.
	pytest -m integration

test-e2e: ## Run e2e tests.
	pytest -m e2e

lint: ## Run Ruff linter.
	ruff check .

format: ## Run Ruff formatter.
	ruff format .

check: lint test ## Run lint and test.

docs: ## Build Sphinx documentation.
	$(MAKE) -C docs html

clean: ## Remove local runtime and build artifacts.
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov build dist .run
	find . -type d -name "*.egg-info" -prune -exec rm -rf {} +
