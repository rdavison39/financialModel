# ============================================================

# Davison Financial Model

#

# Common development commands

#

# Usage:

#

# make install

# make dev

# make lint

# make format

# make test

# make run

# make clean

#

# ============================================================

.PHONY: help install dev lint format test run clean db

help:
@echo ""
@echo "Davison Financial Model"
@echo ""
@echo "Available commands:"
@echo ""
@echo "  make install   Install runtime dependencies"
@echo "  make dev       Install development dependencies"
@echo "  make lint      Run Ruff linter"
@echo "  make format    Format source code"
@echo "  make test      Run all unit tests"
@echo "  make run       Run application"
@echo "  make clean     Remove temporary files"
@echo ""

install:
pip install -r requirements.txt

dev:
pip install -r requirements-dev.txt

lint:
ruff check .

format:
ruff format .

test:
pytest

run:
python src/main.py

clean:
find . -type d -name "**pycache**" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name ".ruff_cache" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

db:
alembic upgrade head
