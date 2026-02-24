.PHONY: install dev test lint format run clean coverage help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv pip install -e .

dev: ## Install development dependencies
	uv pip install -e ".[dev]"

test: ## Run tests
	uv run python -m pytest tests/ -v --tb=short

coverage: ## Run tests with coverage
	uv run python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

lint: ## Run linter
	uv run ruff check src/ tests/

format: ## Format code
	uv run ruff format src/ tests/

run: ## Run Streamlit dashboard
	uv run streamlit run src/app.py

clean: ## Clean build artifacts
	rm -rf __pycache__ .pytest_cache htmlcov .coverage dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

seed: ## Seed database with sample data
	uv run python -c "from src.database import ProjectDatabase; db = ProjectDatabase(); db.seed_from_yaml('data/sample_projects.yaml'); print('Database seeded successfully')"
