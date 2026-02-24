# AI Project Dashboard

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen?logo=github-actions&logoColor=white)](/.github/workflows/ci.yml)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

An enterprise-grade AI project portfolio management dashboard that empowers organizations to track, analyze, and optimize all their AI initiatives from a single unified interface. Built with Streamlit, Pydantic, and SQLite for rapid deployment with zero infrastructure overhead.

## Key Features

- **Portfolio Overview** -- Visualize all AI projects with status indicators, priority levels, and health scoring
- **KPI Tracking** -- Monitor key performance indicators with trend analysis and achievement rate calculations
- **Budget Management** -- Track planned vs actual spending with variance analysis by project and category
- **Risk Register** -- Interactive risk matrix heatmap with probability/impact scoring and mitigation tracking
- **Executive Summary** -- Auto-generated executive reports with actionable recommendations
- **Portfolio Health Score** -- Composite 0-100 health metric across status, risk, budget, and KPI dimensions
- **ROI Calculator** -- Compute return on investment from budget actuals and KPI achievement data
- **Report Generation** -- Export Markdown/HTML reports for portfolio overview, budget variance, and risk register

## Architecture

```
+-------------------+     +-------------------+     +-------------------+
|   Streamlit UI    |     |   Report Engine   |     |   Analytics       |
|   (app.py)        |---->|   (report_gen.py) |     |   (analytics.py)  |
|                   |     +-------------------+     |                   |
|  - Portfolio View |            |                  |  - ROI Calculator |
|  - KPI Tracking   |            |                  |  - Health Score   |
|  - Budget Mgmt    |            v                  |  - Trend Analyzer |
|  - Risk Register  |     +-------------------+     |  - Exec Summary   |
|  - Exec Summary   |---->|   Database Layer  |<----|                   |
+-------------------+     |   (database.py)   |     +-------------------+
                          |                   |
                          |  SQLite Backend   |
                          +-------------------+
                                  |
                          +-------------------+
                          |  Pydantic Models  |
                          |  (models.py)      |
                          |                   |
                          |  - AIProject      |
                          |  - ProjectKPI     |
                          |  - BudgetEntry    |
                          |  - RiskEntry      |
                          +-------------------+
```

## Quick Start

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/onurcandonmezer/ai-project-dashboard.git
cd ai-project-dashboard

# Create virtual environment and install
uv venv
uv pip install -e ".[dev]"
```

### Run the Dashboard

```bash
# Run with Streamlit
uv run streamlit run src/app.py

# Or use the Makefile
make run
```

The dashboard will automatically seed sample data on first run.

### Run Tests

```bash
# Run all tests
uv run python -m pytest tests/ -v --tb=short

# Run with coverage
make coverage
```

## Usage Examples

### Programmatic Access

```python
from src.database import ProjectDatabase
from src.models import AIProject, ProjectStatus, Priority
from src.analytics import PortfolioHealthScore, ROICalculator
from datetime import date

# Initialize database
db = ProjectDatabase("my_portfolio.db")

# Add a project
project = AIProject(
    name="Customer Churn Predictor",
    description="ML model to predict customer churn",
    status=ProjectStatus.DEVELOPMENT,
    priority=Priority.HIGH,
    owner="Data Science Team",
    start_date=date(2024, 6, 1),
    target_date=date(2025, 1, 31),
    model_used="XGBoost",
    use_case="Churn Prediction",
    department="Marketing",
)
db.add_project(project)

# Compute portfolio health
projects = db.get_all_projects()
health = PortfolioHealthScore.compute(
    projects,
    db.get_all_risks(),
    db.get_all_budgets(),
    db.get_all_kpis(),
)
print(f"Portfolio Health: {health.overall_score}/100")
```

### Generate Reports

```python
from src.report_generator import ReportGenerator

report = ReportGenerator.executive_summary_report(
    projects, kpis, budgets, risks
)
print(report)

# Export as HTML
html = ReportGenerator.to_html(report, title="Q4 AI Portfolio Review")
```

### Seed from YAML

```bash
make seed
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit, Plotly |
| Data Models | Pydantic v2 |
| Database | SQLite (WAL mode) |
| Data Processing | Pandas, NumPy |
| Configuration | PyYAML |
| CLI Output | Rich |
| Testing | pytest, pytest-cov |
| Linting | Ruff |
| Package Management | uv |

## Project Structure

```
ai-project-dashboard/
├── README.md
├── pyproject.toml
├── Makefile
├── LICENSE
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── __init__.py
│   ├── models.py            # Pydantic data models
│   ├── database.py          # SQLite database layer
│   ├── analytics.py         # ROI, health score, trends
│   ├── report_generator.py  # Markdown/HTML reports
│   └── app.py               # Streamlit dashboard
├── tests/
│   ├── __init__.py
│   ├── test_models.py       # Model validation tests
│   ├── test_database.py     # CRUD and query tests
│   └── test_analytics.py    # Analytics logic tests
├── data/
│   └── sample_projects.yaml # Sample AI project data
└── assets/
```

## Sample Data

The project includes 8 realistic AI projects across departments:

| Project | Status | Department |
|---------|--------|------------|
| Enterprise AI Chatbot | Production | Customer Success |
| Product Recommendation Engine | Production | E-Commerce |
| Real-time Fraud Detection | Testing | Finance & Risk |
| Intelligent Document Processing | Development | Operations |
| Demand Forecasting Platform | Planning | Supply Chain |
| Brand Sentiment Analyzer | Production | Marketing |
| AI Code Review Assistant | Development | Engineering |
| Legacy NLP Classifier | Retired | Customer Success |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2024 Onurcan Donmezer
