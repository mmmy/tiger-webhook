# Deribit Webhook Python - Makefile

.PHONY: help install dev-install clean test lint format type-check run dev build docker-build docker-run

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  clean        - Clean build artifacts and cache"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting (flake8)"
	@echo "  format       - Format code (black + isort)"
	@echo "  type-check   - Run type checking (mypy)"
	@echo "  run          - Run the application"
	@echo "  dev          - Run in development mode with auto-reload"
	@echo "  build        - Build the package"

# Installation
install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pip install -e ".[dev]"

# Cleaning
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# Testing
test:
	pytest

test-verbose:
	pytest -v -s

test-coverage:
	pytest --cov=src/deribit_webhook --cov-report=html --cov-report=term

# Code quality
lint:
	flake8 src/ tests/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/

# Development
run:
	cd src && python main.py

dev:
	cd src && uvicorn app:app --reload --host 0.0.0.0 --port 3001

# Alternative: run from root directory
run-root:
	python -m src.main

dev-root:
	uvicorn src.app:app --reload --host 0.0.0.0 --port 3001

# Building
build:
	python -m build

# Docker (if needed)
docker-build:
	docker build -t deribit-webhook-python .

docker-run:
	docker run -p 3001:3001 --env-file .env deribit-webhook-python

# Setup development environment
setup-dev: dev-install
	cp .env.example .env
	mkdir -p config data logs
	cp ../deribit_webhook/config/apikeys.example.yml config/
	@echo "Development environment set up!"
	@echo "Please edit .env and config/apikeys.yml with your settings"

# All quality checks
check: lint type-check test

# CI pipeline
ci: clean install check
