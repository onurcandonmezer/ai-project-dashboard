"""Tests for Pydantic data models."""

from datetime import date

import pytest
from pydantic import ValidationError
from src.models import (
    AIProject,
    BudgetCategory,
    BudgetEntry,
    Priority,
    ProjectKPI,
    ProjectStatus,
    RiskEntry,
    Trend,
)

# ── AIProject Tests ───────────────────────────────────────────


class TestAIProject:
    """Test suite for the AIProject model."""

    def test_create_minimal_project(self) -> None:
        """A project can be created with only required fields."""
        project = AIProject(
            name="Test Project",
            owner="Alice",
            start_date=date(2024, 1, 1),
        )
        assert project.name == "Test Project"
        assert project.owner == "Alice"
        assert project.status == ProjectStatus.PLANNING
        assert project.priority == Priority.MEDIUM
        assert project.id  # auto-generated

    def test_create_full_project(self) -> None:
        """A project can be created with all fields specified."""
        project = AIProject(
            id="proj_001",
            name="Full Project",
            description="A complete project",
            status=ProjectStatus.PRODUCTION,
            priority=Priority.CRITICAL,
            owner="Bob",
            start_date=date(2024, 3, 1),
            target_date=date(2024, 12, 31),
            model_used="GPT-4",
            use_case="Chatbot",
            department="Engineering",
        )
        assert project.id == "proj_001"
        assert project.status == ProjectStatus.PRODUCTION
        assert project.priority == Priority.CRITICAL
        assert project.is_active is True

    def test_project_is_active_for_development(self) -> None:
        """Development, testing, and production are active states."""
        for status in [ProjectStatus.DEVELOPMENT, ProjectStatus.TESTING, ProjectStatus.PRODUCTION]:
            project = AIProject(
                name="Active",
                owner="X",
                start_date=date(2024, 1, 1),
                status=status,
            )
            assert project.is_active is True

    def test_project_is_not_active_for_planning_and_retired(self) -> None:
        """Planning and retired are not active states."""
        for status in [ProjectStatus.PLANNING, ProjectStatus.RETIRED]:
            project = AIProject(
                name="Inactive",
                owner="X",
                start_date=date(2024, 1, 1),
                status=status,
            )
            assert project.is_active is False

    def test_project_date_validation_rejects_invalid_dates(self) -> None:
        """Target date before start date raises a validation error."""
        with pytest.raises(ValidationError, match="target_date must not be before start_date"):
            AIProject(
                name="Bad Dates",
                owner="X",
                start_date=date(2024, 6, 1),
                target_date=date(2024, 1, 1),
            )

    def test_project_name_cannot_be_empty(self) -> None:
        """Empty project name raises a validation error."""
        with pytest.raises(ValidationError):
            AIProject(name="", owner="X", start_date=date(2024, 1, 1))

    def test_project_days_until_target(self) -> None:
        """days_until_target returns None when no target date is set."""
        project = AIProject(name="No Target", owner="X", start_date=date(2024, 1, 1))
        assert project.days_until_target is None


# ── ProjectKPI Tests ──────────────────────────────────────────


class TestProjectKPI:
    """Test suite for the ProjectKPI model."""

    def test_create_kpi(self) -> None:
        """A KPI can be created with required fields."""
        kpi = ProjectKPI(
            project_id="proj_001",
            metric_name="Accuracy",
            current_value=85.0,
            target_value=95.0,
            unit="%",
            trend=Trend.UP,
        )
        assert kpi.metric_name == "Accuracy"
        assert kpi.trend == Trend.UP

    def test_kpi_achievement_rate(self) -> None:
        """Achievement rate is correctly calculated."""
        kpi = ProjectKPI(
            project_id="p1",
            metric_name="Test",
            current_value=75.0,
            target_value=100.0,
        )
        assert kpi.achievement_rate == 75.0

    def test_kpi_on_target(self) -> None:
        """is_on_target returns True when current meets target."""
        kpi = ProjectKPI(
            project_id="p1",
            metric_name="Test",
            current_value=100.0,
            target_value=95.0,
        )
        assert kpi.is_on_target is True

    def test_kpi_below_target(self) -> None:
        """is_on_target returns False when below target."""
        kpi = ProjectKPI(
            project_id="p1",
            metric_name="Test",
            current_value=50.0,
            target_value=95.0,
        )
        assert kpi.is_on_target is False

    def test_kpi_achievement_rate_zero_target(self) -> None:
        """Achievement rate returns 0 when target is zero."""
        kpi = ProjectKPI(
            project_id="p1",
            metric_name="Test",
            current_value=50.0,
            target_value=0.0,
        )
        assert kpi.achievement_rate == 0.0


# ── BudgetEntry Tests ─────────────────────────────────────────


class TestBudgetEntry:
    """Test suite for the BudgetEntry model."""

    def test_create_budget_entry(self) -> None:
        """A budget entry can be created with required fields."""
        budget = BudgetEntry(
            project_id="proj_001",
            category=BudgetCategory.COMPUTE,
            planned_amount=10000.0,
            actual_amount=9500.0,
        )
        assert budget.category == BudgetCategory.COMPUTE
        assert budget.currency == "USD"

    def test_budget_variance_under(self) -> None:
        """Variance is negative when under budget."""
        budget = BudgetEntry(
            project_id="p1",
            category=BudgetCategory.COMPUTE,
            planned_amount=10000.0,
            actual_amount=8000.0,
        )
        assert budget.variance == -2000.0
        assert budget.is_over_budget is False

    def test_budget_variance_over(self) -> None:
        """Variance is positive when over budget."""
        budget = BudgetEntry(
            project_id="p1",
            category=BudgetCategory.API_CALLS,
            planned_amount=5000.0,
            actual_amount=7000.0,
        )
        assert budget.variance == 2000.0
        assert budget.is_over_budget is True

    def test_budget_variance_percentage(self) -> None:
        """Variance percentage is correctly calculated."""
        budget = BudgetEntry(
            project_id="p1",
            category=BudgetCategory.PERSONNEL,
            planned_amount=100000.0,
            actual_amount=110000.0,
        )
        assert budget.variance_percentage == 10.0

    def test_budget_negative_amount_rejected(self) -> None:
        """Negative amounts are rejected."""
        with pytest.raises(ValidationError):
            BudgetEntry(
                project_id="p1",
                category=BudgetCategory.COMPUTE,
                planned_amount=-1000.0,
            )


# ── RiskEntry Tests ───────────────────────────────────────────


class TestRiskEntry:
    """Test suite for the RiskEntry model."""

    def test_create_risk_entry(self) -> None:
        """A risk entry can be created with required fields."""
        risk = RiskEntry(
            project_id="proj_001",
            risk_description="Data breach risk",
            probability=3,
            impact=5,
            mitigation="Encrypt all data at rest",
        )
        assert risk.risk_score == 15
        assert risk.risk_level == "critical"

    def test_risk_level_high(self) -> None:
        """Risk score 10-14 is high level."""
        risk = RiskEntry(
            project_id="p1",
            risk_description="Moderate risk",
            probability=2,
            impact=5,
        )
        assert risk.risk_score == 10
        assert risk.risk_level == "high"

    def test_risk_level_medium(self) -> None:
        """Risk score 5-9 is medium level."""
        risk = RiskEntry(
            project_id="p1",
            risk_description="Some risk",
            probability=2,
            impact=3,
        )
        assert risk.risk_score == 6
        assert risk.risk_level == "medium"

    def test_risk_level_low(self) -> None:
        """Risk score 1-4 is low level."""
        risk = RiskEntry(
            project_id="p1",
            risk_description="Minor risk",
            probability=1,
            impact=2,
        )
        assert risk.risk_score == 2
        assert risk.risk_level == "low"

    def test_risk_probability_out_of_range(self) -> None:
        """Probability outside 1-5 is rejected."""
        with pytest.raises(ValidationError):
            RiskEntry(
                project_id="p1",
                risk_description="Bad",
                probability=6,
                impact=3,
            )

    def test_risk_impact_out_of_range(self) -> None:
        """Impact outside 1-5 is rejected."""
        with pytest.raises(ValidationError):
            RiskEntry(
                project_id="p1",
                risk_description="Bad",
                probability=3,
                impact=0,
            )
