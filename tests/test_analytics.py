"""Tests for the analytics module."""

from __future__ import annotations

from datetime import date

import pytest
from src.analytics import (
    ExecutiveSummaryGenerator,
    PortfolioHealthScore,
    ROICalculator,
    TrendAnalyzer,
)
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

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def projects() -> list[AIProject]:
    """Sample projects for testing."""
    return [
        AIProject(
            id="p1",
            name="Chatbot",
            status=ProjectStatus.PRODUCTION,
            priority=Priority.CRITICAL,
            owner="Alice",
            start_date=date(2024, 1, 1),
            target_date=date(2024, 12, 31),
        ),
        AIProject(
            id="p2",
            name="Recommender",
            status=ProjectStatus.DEVELOPMENT,
            priority=Priority.HIGH,
            owner="Bob",
            start_date=date(2024, 3, 1),
        ),
        AIProject(
            id="p3",
            name="Fraud Detection",
            status=ProjectStatus.TESTING,
            priority=Priority.HIGH,
            owner="Carol",
            start_date=date(2024, 5, 1),
            target_date=date(2025, 3, 1),
        ),
    ]


@pytest.fixture
def kpis() -> list[ProjectKPI]:
    """Sample KPIs for testing."""
    return [
        ProjectKPI(
            id="k1",
            project_id="p1",
            metric_name="Accuracy",
            current_value=92.0,
            target_value=95.0,
            trend=Trend.UP,
        ),
        ProjectKPI(
            id="k2",
            project_id="p1",
            metric_name="Latency",
            current_value=1.5,
            target_value=2.0,
            unit="s",
            trend=Trend.STABLE,
        ),
        ProjectKPI(
            id="k3",
            project_id="p2",
            metric_name="CTR",
            current_value=8.0,
            target_value=15.0,
            unit="%",
            trend=Trend.UP,
        ),
        ProjectKPI(
            id="k4",
            project_id="p3",
            metric_name="Detection Rate",
            current_value=94.0,
            target_value=99.0,
            unit="%",
            trend=Trend.UP,
        ),
    ]


@pytest.fixture
def budgets() -> list[BudgetEntry]:
    """Sample budgets for testing."""
    return [
        BudgetEntry(
            id="b1",
            project_id="p1",
            category=BudgetCategory.COMPUTE,
            planned_amount=15000.0,
            actual_amount=14000.0,
        ),
        BudgetEntry(
            id="b2",
            project_id="p1",
            category=BudgetCategory.API_CALLS,
            planned_amount=25000.0,
            actual_amount=28000.0,
        ),
        BudgetEntry(
            id="b3",
            project_id="p2",
            category=BudgetCategory.COMPUTE,
            planned_amount=30000.0,
            actual_amount=32000.0,
        ),
        BudgetEntry(
            id="b4",
            project_id="p3",
            category=BudgetCategory.PERSONNEL,
            planned_amount=100000.0,
            actual_amount=95000.0,
        ),
    ]


@pytest.fixture
def risks() -> list[RiskEntry]:
    """Sample risks for testing."""
    return [
        RiskEntry(
            id="r1",
            project_id="p1",
            risk_description="API rate limiting",
            probability=3,
            impact=4,
            mitigation="Caching layer",
            status=RiskStatus.MITIGATING,
        ),
        RiskEntry(
            id="r2",
            project_id="p3",
            risk_description="Model drift",
            probability=4,
            impact=5,
            status=RiskStatus.OPEN,
        ),
        RiskEntry(
            id="r3",
            project_id="p2",
            risk_description="Cold start problem",
            probability=2,
            impact=2,
            status=RiskStatus.RESOLVED,
        ),
    ]


# ── ROI Calculator Tests ─────────────────────────────────────


class TestROICalculator:
    """Test suite for ROI calculations."""

    def test_compute_roi_with_kpis(
        self,
        projects: list[AIProject],
        budgets: list[BudgetEntry],
        kpis: list[ProjectKPI],
    ) -> None:
        """ROI is calculated from budget and KPI data."""
        proj_budgets = [b for b in budgets if b.project_id == "p1"]
        proj_kpis = [k for k in kpis if k.project_id == "p1"]
        result = ROICalculator.compute_roi(projects[0], proj_budgets, proj_kpis)

        assert result.project_id == "p1"
        assert result.project_name == "Chatbot"
        assert result.total_investment == 42000.0  # 14000 + 28000
        assert result.estimated_return > 0
        assert result.payback_months is None  # no monthly estimate

    def test_compute_roi_with_monthly_return(
        self,
        projects: list[AIProject],
        budgets: list[BudgetEntry],
        kpis: list[ProjectKPI],
    ) -> None:
        """ROI uses monthly return estimate when provided."""
        proj_budgets = [b for b in budgets if b.project_id == "p1"]
        proj_kpis = [k for k in kpis if k.project_id == "p1"]
        result = ROICalculator.compute_roi(
            projects[0], proj_budgets, proj_kpis, monthly_return_estimate=5000.0
        )
        assert result.payback_months is not None
        assert result.payback_months > 0

    def test_compute_portfolio_roi(
        self,
        projects: list[AIProject],
        budgets: list[BudgetEntry],
        kpis: list[ProjectKPI],
    ) -> None:
        """Portfolio ROI computes for all projects."""
        results = ROICalculator.compute_portfolio_roi(projects, budgets, kpis)
        assert len(results) == 3

    def test_compute_roi_no_budgets(self, projects: list[AIProject]) -> None:
        """ROI with zero investment returns 0%."""
        result = ROICalculator.compute_roi(projects[0], [], [])
        assert result.total_investment == 0.0
        assert result.roi_percentage == 0.0


# ── Portfolio Health Score Tests ──────────────────────────────


class TestPortfolioHealthScore:
    """Test suite for portfolio health scoring."""

    def test_compute_health_score(
        self,
        projects: list[AIProject],
        risks: list[RiskEntry],
        budgets: list[BudgetEntry],
        kpis: list[ProjectKPI],
    ) -> None:
        """Health score is computed with all components."""
        health = PortfolioHealthScore.compute(projects, risks, budgets, kpis)
        assert 0 <= health.overall_score <= 100
        assert 0 <= health.status_score <= 100
        assert 0 <= health.risk_score <= 100
        assert 0 <= health.budget_score <= 100
        assert 0 <= health.kpi_score <= 100
        assert "status" in health.details
        assert "risk" in health.details

    def test_health_score_empty_portfolio(self) -> None:
        """Health score is computed for empty portfolio."""
        health = PortfolioHealthScore.compute([], [], [], [])
        assert health.overall_score > 0  # defaults provide baseline scores

    def test_health_score_all_production(self) -> None:
        """All production projects yield high status score."""
        projects = [
            AIProject(
                id=f"p{i}",
                name=f"Proj {i}",
                owner="X",
                start_date=date(2024, 1, 1),
                status=ProjectStatus.PRODUCTION,
            )
            for i in range(5)
        ]
        health = PortfolioHealthScore.compute(projects, [], [], [])
        assert health.status_score == 100.0

    def test_health_score_high_risk(self) -> None:
        """Many critical risks produce a low risk score."""
        risks = [
            RiskEntry(
                id=f"r{i}",
                project_id="p1",
                risk_description=f"Risk {i}",
                probability=5,
                impact=5,
                status=RiskStatus.OPEN,
            )
            for i in range(5)
        ]
        health = PortfolioHealthScore.compute([], risks, [], [])
        assert health.risk_score < 10


# ── Trend Analyzer Tests ─────────────────────────────────────


class TestTrendAnalyzer:
    """Test suite for KPI trend analysis."""

    def test_analyze_trends(self, kpis: list[ProjectKPI]) -> None:
        """KPIs are correctly grouped by trend direction."""
        trends = TrendAnalyzer.analyze(kpis)
        assert len(trends["up"]) == 3  # Accuracy, CTR, Detection Rate
        assert len(trends["stable"]) == 1  # Latency

    def test_get_underperforming_kpis(self, kpis: list[ProjectKPI]) -> None:
        """Underperforming KPIs are identified below threshold."""
        under = TrendAnalyzer.get_underperforming_kpis(kpis, threshold=70.0)
        # CTR is 8/15 = 53.3%, below 70%
        assert len(under) >= 1
        assert under[0].metric_name == "CTR"

    def test_get_trend_summary(self, kpis: list[ProjectKPI]) -> None:
        """Trend summary returns correct counts."""
        summary = TrendAnalyzer.get_trend_summary(kpis)
        assert summary["up"] == 3
        assert summary["stable"] == 1
        assert summary["down"] == 0

    def test_get_top_performers(self, kpis: list[ProjectKPI]) -> None:
        """Top performers are returned by highest achievement."""
        top = TrendAnalyzer.get_top_performers(kpis, limit=2)
        assert len(top) == 2
        assert top[0].achievement_rate >= top[1].achievement_rate


# ── Executive Summary Tests ──────────────────────────────────


class TestExecutiveSummaryGenerator:
    """Test suite for executive summary generation."""

    def test_generate_summary(
        self,
        projects: list[AIProject],
        kpis: list[ProjectKPI],
        budgets: list[BudgetEntry],
        risks: list[RiskEntry],
    ) -> None:
        """Executive summary is generated with all sections."""
        summary = ExecutiveSummaryGenerator.generate(projects, kpis, budgets, risks)
        assert "Portfolio Overview" in summary
        assert "Project Status Distribution" in summary
        assert "Budget Summary" in summary
        assert "KPI Performance" in summary
        assert "Risk Profile" in summary
        assert "Recommendations" in summary

    def test_generate_summary_empty(self) -> None:
        """Executive summary handles empty data gracefully."""
        summary = ExecutiveSummaryGenerator.generate([], [], [], [])
        assert "Portfolio Overview" in summary
        assert "0 projects" in summary

    def test_summary_includes_critical_projects(
        self,
        projects: list[AIProject],
        kpis: list[ProjectKPI],
        budgets: list[BudgetEntry],
        risks: list[RiskEntry],
    ) -> None:
        """Summary highlights critical priority projects."""
        summary = ExecutiveSummaryGenerator.generate(projects, kpis, budgets, risks)
        assert "Chatbot" in summary  # critical priority project
