"""Tests for the SQLite database layer."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pytest

from src.database import ProjectDatabase
from src.models import (
    AIProject,
    BudgetCategory,
    BudgetEntry,
    Priority,
    ProjectKPI,
    ProjectStatus,
    RiskEntry,
    RiskStatus,
    Trend,
)


@pytest.fixture
def db(tmp_path: Path) -> ProjectDatabase:
    """Create a fresh temporary database for each test."""
    db_path = str(tmp_path / "test.db")
    database = ProjectDatabase(db_path)
    yield database
    database.close()


@pytest.fixture
def sample_project() -> AIProject:
    """Create a sample project for testing."""
    return AIProject(
        id="test_proj_01",
        name="Test Chatbot",
        description="A test chatbot project",
        status=ProjectStatus.DEVELOPMENT,
        priority=Priority.HIGH,
        owner="Test Owner",
        start_date=date(2024, 1, 1),
        target_date=date(2024, 12, 31),
        model_used="GPT-4",
        use_case="Customer Support",
        department="Engineering",
    )


@pytest.fixture
def populated_db(db: ProjectDatabase, sample_project: AIProject) -> ProjectDatabase:
    """Create a database with sample data."""
    db.add_project(sample_project)

    db.add_kpi(
        ProjectKPI(
            id="kpi_01",
            project_id="test_proj_01",
            metric_name="Accuracy",
            current_value=92.0,
            target_value=95.0,
            unit="%",
            trend=Trend.UP,
        )
    )

    db.add_budget(
        BudgetEntry(
            id="budget_01",
            project_id="test_proj_01",
            category=BudgetCategory.COMPUTE,
            planned_amount=10000.0,
            actual_amount=9500.0,
        )
    )

    db.add_risk(
        RiskEntry(
            id="risk_01",
            project_id="test_proj_01",
            risk_description="Model drift risk",
            probability=3,
            impact=4,
            mitigation="Monitoring pipeline",
            status=RiskStatus.OPEN,
        )
    )

    return db


# ── Project CRUD Tests ────────────────────────────────────────


class TestProjectCRUD:
    """Test CRUD operations for projects."""

    def test_add_and_get_project(self, db: ProjectDatabase, sample_project: AIProject) -> None:
        """A project can be added and retrieved by ID."""
        db.add_project(sample_project)
        result = db.get_project("test_proj_01")
        assert result is not None
        assert result.name == "Test Chatbot"
        assert result.status == ProjectStatus.DEVELOPMENT

    def test_get_nonexistent_project(self, db: ProjectDatabase) -> None:
        """Getting a nonexistent project returns None."""
        result = db.get_project("nonexistent_id")
        assert result is None

    def test_get_all_projects(self, db: ProjectDatabase, sample_project: AIProject) -> None:
        """All projects can be retrieved."""
        db.add_project(sample_project)
        second = AIProject(
            id="test_proj_02",
            name="Second Project",
            owner="Other",
            start_date=date(2024, 6, 1),
        )
        db.add_project(second)
        projects = db.get_all_projects()
        assert len(projects) == 2

    def test_update_project(self, db: ProjectDatabase, sample_project: AIProject) -> None:
        """A project can be updated."""
        db.add_project(sample_project)
        sample_project.status = ProjectStatus.PRODUCTION
        sample_project.name = "Updated Chatbot"
        db.update_project(sample_project)

        result = db.get_project("test_proj_01")
        assert result is not None
        assert result.status == ProjectStatus.PRODUCTION
        assert result.name == "Updated Chatbot"

    def test_delete_project(self, db: ProjectDatabase, sample_project: AIProject) -> None:
        """A project can be deleted."""
        db.add_project(sample_project)
        deleted = db.delete_project("test_proj_01")
        assert deleted is True
        assert db.get_project("test_proj_01") is None

    def test_delete_nonexistent_project(self, db: ProjectDatabase) -> None:
        """Deleting a nonexistent project returns False."""
        deleted = db.delete_project("nonexistent")
        assert deleted is False


# ── KPI Tests ─────────────────────────────────────────────────


class TestKPICRUD:
    """Test CRUD operations for KPIs."""

    def test_add_and_get_kpis(self, populated_db: ProjectDatabase) -> None:
        """KPIs can be added and retrieved by project ID."""
        kpis = populated_db.get_kpis_for_project("test_proj_01")
        assert len(kpis) == 1
        assert kpis[0].metric_name == "Accuracy"
        assert kpis[0].current_value == 92.0

    def test_get_all_kpis(self, populated_db: ProjectDatabase) -> None:
        """All KPIs can be retrieved."""
        kpis = populated_db.get_all_kpis()
        assert len(kpis) >= 1


# ── Budget Tests ──────────────────────────────────────────────


class TestBudgetCRUD:
    """Test CRUD operations for budgets."""

    def test_add_and_get_budgets(self, populated_db: ProjectDatabase) -> None:
        """Budgets can be added and retrieved by project ID."""
        budgets = populated_db.get_budgets_for_project("test_proj_01")
        assert len(budgets) == 1
        assert budgets[0].planned_amount == 10000.0

    def test_budget_summary(self, populated_db: ProjectDatabase) -> None:
        """Budget summary is correctly aggregated."""
        summary = populated_db.get_budget_summary()
        assert summary["total_planned"] == 10000.0
        assert summary["total_actual"] == 9500.0
        assert summary["total_variance"] == -500.0

    def test_budget_by_category(self, populated_db: ProjectDatabase) -> None:
        """Budget breakdown by category works correctly."""
        by_cat = populated_db.get_budget_by_category()
        assert "compute" in by_cat
        assert by_cat["compute"]["planned"] == 10000.0


# ── Risk Tests ────────────────────────────────────────────────


class TestRiskCRUD:
    """Test CRUD operations for risks."""

    def test_add_and_get_risks(self, populated_db: ProjectDatabase) -> None:
        """Risks can be added and retrieved by project ID."""
        risks = populated_db.get_risks_for_project("test_proj_01")
        assert len(risks) == 1
        assert risks[0].probability == 3

    def test_risk_register(self, populated_db: ProjectDatabase) -> None:
        """Risk register returns open and mitigating risks sorted by score."""
        register = populated_db.get_risk_register()
        assert len(register) >= 1
        # Should be sorted by risk_score descending
        if len(register) > 1:
            assert register[0].risk_score >= register[1].risk_score


# ── Query Tests ───────────────────────────────────────────────


class TestQueryMethods:
    """Test query and filter methods."""

    def test_get_projects_by_status(
        self, populated_db: ProjectDatabase, sample_project: AIProject
    ) -> None:
        """Projects can be filtered by status."""
        dev_projects = populated_db.get_projects_by_status(ProjectStatus.DEVELOPMENT)
        assert len(dev_projects) == 1
        assert dev_projects[0].name == "Test Chatbot"

        prod_projects = populated_db.get_projects_by_status(ProjectStatus.PRODUCTION)
        assert len(prod_projects) == 0

    def test_get_projects_by_priority(self, populated_db: ProjectDatabase) -> None:
        """Projects can be filtered by priority."""
        high_projects = populated_db.get_projects_by_priority(Priority.HIGH)
        assert len(high_projects) == 1

    def test_project_count_by_status(self, populated_db: ProjectDatabase) -> None:
        """Project count by status is correct."""
        counts = populated_db.get_project_count_by_status()
        assert counts.get("development", 0) == 1


# ── Seed Tests ────────────────────────────────────────────────


class TestSeedMethod:
    """Test database seeding from YAML."""

    def test_seed_from_yaml(self, db: ProjectDatabase) -> None:
        """Database can be seeded from sample YAML file."""
        yaml_path = Path(__file__).parent.parent / "data" / "sample_projects.yaml"
        if yaml_path.exists():
            db.seed_from_yaml(str(yaml_path))
            projects = db.get_all_projects()
            assert len(projects) == 8

            kpis = db.get_all_kpis()
            assert len(kpis) > 0

            budgets = db.get_all_budgets()
            assert len(budgets) > 0

            risks = db.get_all_risks()
            assert len(risks) > 0

    def test_seed_file_not_found(self, db: ProjectDatabase) -> None:
        """Seeding from nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            db.seed_from_yaml("nonexistent.yaml")
