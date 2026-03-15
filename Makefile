# ============================================================
# FinSight — Makefile
# Common developer commands. Run `make help` to see them all.
# ============================================================

.PHONY: help setup run test lint format typecheck clean

PYTHON  = python3.11
VENV    = .venv
APP     = app/Home.py
SRC     = core config app

help:           ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:          ## Bootstrap the development environment
	bash scripts/setup.sh

run:            ## Start the Streamlit app
	streamlit run $(APP)

test:           ## Run the test suite with coverage
	pytest

test-fast:      ## Run tests without coverage (faster)
	pytest --no-cov -x

lint:           ## Lint with ruff
	ruff check $(SRC) tests

format:         ## Auto-format with black
	black $(SRC) tests

typecheck:      ## Static type checking with mypy
	mypy $(SRC)

clean:          ## Remove caches and compiled files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache  -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache  -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "Cleaned."
