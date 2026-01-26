# =============================================================================
# Projektor Makefile
# =============================================================================
# Usage:
#   make help              - Show this help
#   make install           - Install dependencies
#   make setup-dev         - Complete development setup
#   make test              - Run all tests
#   make test-unit         - Run unit tests only
#   make test-e2e          - Run E2E tests
#   make lint              - Run linters (ruff, mypy)
#   make format            - Format code with ruff and black
#   make clean             - Clean build artifacts
#   make build             - Build package
#   make publish           - Publish to PyPI (with version bump)
#   make push              - Complete release (bump version + build + push Docker + PyPI + Git tag)
# =============================================================================

.PHONY: help install setup-dev test test-unit test-e2e lint format clean build publish push \
        bump-patch bump-minor bump-major git-tag version info

# Default target
.DEFAULT_GOAL := help

# Project settings
PROJECT_NAME := projektor
PYTHON := python3
PIP := pip3
PYTEST := python3 -m pytest
VENV_PYTHON := $(PYTHON)
VENV_PIP := /home/tom/github/wronai/projektor/venv/bin/pip
VENV_TWINE := /home/tom/github/wronai/projektor/venv/bin/twine

export PYTHONPATH := src

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "$(BLUE)Projektor - LLM-orchestrated project management$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
	   awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make install       # Install in development mode"
	@echo "  make setup-dev     # Complete development setup"
	@echo "  make test          # Run all tests"
	@echo "  make lint          # Run linters"
	@echo "  make format        # Format code"

# =============================================================================
# Development
# =============================================================================

install: ## Install package in development mode
	$(VENV_PIP) install -e ".[dev]"

install-all: ## Install package with all dependencies
	$(VENV_PIP) install -e ".[all]"

install-ci: ## Install for CI (no editable)
	$(VENV_PIP) install ".[dev]"

setup-dev: ## Complete development setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	$(MAKE) install-all
	@echo "$(GREEN)✓ Development setup complete!$(NC)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	$(PYTEST) tests/ -v --tb=short

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/ -v --tb=short

test-e2e: ## Run E2E tests only
	$(PYTEST) tests/e2e/ -v --tb=short

test-cov: ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=$(PROJECT_NAME) --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode (requires pytest-watch)
	ptw tests/ -- -v --tb=short

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linters (ruff, mypy)
	ruff check src/$(PROJECT_NAME)/ tests/
	mypy src/$(PROJECT_NAME)/ --ignore-missing-imports

format: ## Format code with ruff and black
	ruff format src/$(PROJECT_NAME)/ tests/
	black src/$(PROJECT_NAME)/ tests/

format-check: ## Check code formatting
	ruff format --check src/$(PROJECT_NAME)/ tests/
	black --check src/$(PROJECT_NAME)/ tests/

# =============================================================================
# Development Utilities
# =============================================================================

demo: ## Run the basic usage demo
	$(PYTHON) examples/basic_usage.py

run-example: ## Run a specific example (usage: make run-example FILE=basic_usage.py)
	$(PYTHON) examples/$(FILE)

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Release
# =============================================================================

build: clean
	$(VENV_PIP) install build
	$(VENV_PYTHON) -m build

publish-test: build ## Publish to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*

bump-patch: ## Bump patch version (X.Y.Z -> X.Y.Z+1)
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	$(PYTHON) scripts/bump_version.py patch

bump-minor: ## Bump minor version (X.Y.Z -> X.Y+1.0)
	@echo "$(YELLOW)Bumping minor version...$(NC)"
	$(PYTHON) scripts/bump_version.py minor

bump-major: ## Bump major version (X.Y.Z -> X+1.0.0)
	@echo "$(YELLOW)Bumping major version...$(NC)"
	$(PYTHON) scripts/bump_version.py major

publish: build ## Publish to PyPI (with version bump)
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	$(MAKE) bump-patch
	@echo "$(YELLOW)Rebuilding package with new version...$(NC)"
	$(MAKE) build
	@echo "$(YELLOW)Publishing to PyPI...$(NC)"
	$(VENV_TWINE) upload dist/*

push: ## Complete release (bump version + commit + push + build + push Docker + PyPI + Git tag)
	@echo "$(YELLOW)Starting complete release process...$(NC)"
	@echo "$(YELLOW)1. Bumping patch version...$(NC)"
	$(MAKE) bump-patch
	@echo "$(YELLOW)2. Committing version changes...$(NC)"
	git add pyproject.toml src/projektor/__init__.py CHANGELOG.md
	git commit -m "Bump version to $(shell $(PYTHON) -c 'import toml; content = toml.load(open("pyproject.toml")); print(content["project"]["version"])')"
	@echo "$(YELLOW)3. Pushing changes to git...$(NC)"
	git push origin main
	@echo "$(YELLOW)4. Building package...$(NC)"
	$(MAKE) build
	@echo "$(YELLOW)5. Publishing to PyPI...$(NC)"
	$(VENV_TWINE) upload dist/*
	@echo "$(YELLOW)6. Creating and pushing git tag...$(NC)"
	$(MAKE) git-tag
	@echo "$(GREEN)🎉 Complete release finished successfully!$(NC)"
	@echo "$(GREEN)   - Changes committed and pushed ✓$(NC)"
	@echo "$(GREEN)   - Package published to PyPI ✓$(NC)"
	@echo "$(GREEN)   - Git tag created and pushed ✓$(NC)"
	@echo "$(GREEN)   - Version bumped automatically ✓$(NC)"

git-tag: ## Create and push git tag for current version
	@echo "$(YELLOW)Creating and pushing git tag...$(NC)"
	@VERSION=$$($(PYTHON) -c "import toml; content = toml.load(open('pyproject.toml')); print(content['project']['version'])") && \
	git tag v$$VERSION && \
	git push origin v$$VERSION && \
	echo "$(GREEN)Git tag v$$VERSION pushed successfully!$(NC)"

# =============================================================================
# Info
# =============================================================================

version: ## Show version
	@$(PYTHON) -c "import $(PROJECT_NAME); print($(PROJECT_NAME).__version__)"

info: ## Show project info
	@echo "$(BLUE)Project:$(NC) $(PROJECT_NAME)"
	@echo "$(BLUE)Python:$(NC) $(shell $(PYTHON) --version)"
	@echo "$(BLUE)Pip:$(NC) $(shell $(PIP) --version)"
	@echo "$(BLUE)Version:$(NC) $(shell $(PYTHON) -c 'import $(PROJECT_NAME); print($(PROJECT_NAME).__version__)')"

# =============================================================================
# Docker (optional, for future use)
# =============================================================================

docker-build: ## Build Docker image (placeholder)
	@echo "$(YELLOW)Docker support not yet implemented$(NC)"

docker-up: ## Start Docker services (placeholder)
	@echo "$(YELLOW)Docker support not yet implemented$(NC)"

docker-down: ## Stop Docker services (placeholder)
	@echo "$(YELLOW)Docker support not yet implemented$(NC)"
