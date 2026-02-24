"""Analytics engine for the AI Project Dashboard.

Provides ROI calculations, executive summary generation,
portfolio health scoring, and KPI trend analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean

from src.models import (
    AIProject,
    BudgetEntry,
    Priority,
    ProjectKPI,
    ProjectStatus,
    RiskEntry,
    RiskStatus,
    Trend,
)


@dataclass
class ROIResult:
    """Result of an ROI calculation for a project."""

    project_id: str
    project_name: str
    total_investment: float
    estimated_return: float
    roi_percentage: float
    payback_months: float | None


class ROICalculator:
    """Computes Return on Investment from budget and KPI data.

    Uses budget actuals as investment and revenue-related KPIs
    as return indicators.
    """

    @staticmethod
    def compute_roi(
        project: AIProject,
        budgets: list[BudgetEntry],
        kpis: list[ProjectKPI],
        monthly_return_estimate: float = 0.0,
    ) -> ROIResult:
        """Calculate ROI for a single project.

        Args:
            project: The AI project.
            budgets: Budget entries for the project.
            kpis: KPIs for the project.
            monthly_return_estimate: Estimated monthly return in currency units.

        Returns:
            ROIResult with investment, return, and ROI percentage.
        """
        total_investment = sum(b.actual_amount for b in budgets)

        # Use monthly return estimate or derive from KPI achievement
        if monthly_return_estimate > 0:
            months_active = max(1, (date.today() - project.start_date).days / 30)
            estimated_return = monthly_return_estimate * months_active
        else:
            # Estimate return based on average KPI achievement
            if kpis:
                avg_achievement = mean(k.achievement_rate for k in kpis) / 100.0
                estimated_return = total_investment * avg_achievement
            else:
                estimated_return = 0.0

        roi_percentage = 0.0
        if total_investment > 0:
            roi_percentage = round(
                ((estimated_return - total_investment) / total_investment) * 100, 2
            )

        payback_months = None
        if monthly_return_estimate > 0 and total_investment > 0:
            payback_months = round(total_investment / monthly_return_estimate, 1)

        return ROIResult(
            project_id=project.id,
            project_name=project.name,
            total_investment=round(total_investment, 2),
            estimated_return=round(estimated_return, 2),
            roi_percentage=roi_percentage,
            payback_months=payback_months,
        )

    @staticmethod
    def compute_portfolio_roi(
        projects: list[AIProject],
        all_budgets: list[BudgetEntry],
        all_kpis: list[ProjectKPI],
    ) -> list[ROIResult]:
        """Calculate ROI for all projects in the portfolio."""
        results = []
        for project in projects:
            proj_budgets = [b for b in all_budgets if b.project_id == project.id]
            proj_kpis = [k for k in all_kpis if k.project_id == project.id]
            result = ROICalculator.compute_roi(project, proj_budgets, proj_kpis)
            results.append(result)
        return results


@dataclass
class HealthScore:
    """Portfolio health score breakdown."""

    overall_score: float
    status_score: float
    risk_score: float
    budget_score: float
    kpi_score: float
    details: dict[str, str] = field(default_factory=dict)


class PortfolioHealthScore:
    """Computes an overall portfolio health score (0-100).

    Combines project status distribution, risk levels,
    budget adherence, and KPI achievement into a single score.
    """

    @staticmethod
    def compute(
        projects: list[AIProject],
        risks: list[RiskEntry],
        budgets: list[BudgetEntry],
        kpis: list[ProjectKPI],
    ) -> HealthScore:
        """Calculate the portfolio health score.

        Scoring weights:
            - Status distribution: 25%
            - Risk profile: 25%
            - Budget adherence: 25%
            - KPI achievement: 25%

        Returns:
            HealthScore with overall and component scores.
        """
        status_score = PortfolioHealthScore._score_status(projects)
        risk_score = PortfolioHealthScore._score_risks(risks)
        budget_score = PortfolioHealthScore._score_budget(budgets)
        kpi_score = PortfolioHealthScore._score_kpis(kpis)

        overall = round(
            (status_score * 0.25 + risk_score * 0.25 + budget_score * 0.25 + kpi_score * 0.25), 1
        )

        details = {
            "status": PortfolioHealthScore._status_detail(status_score),
            "risk": PortfolioHealthScore._risk_detail(risk_score),
            "budget": PortfolioHealthScore._budget_detail(budget_score),
            "kpi": PortfolioHealthScore._kpi_detail(kpi_score),
        }

        return HealthScore(
            overall_score=overall,
            status_score=round(status_score, 1),
            risk_score=round(risk_score, 1),
            budget_score=round(budget_score, 1),
            kpi_score=round(kpi_score, 1),
            details=details,
        )

    @staticmethod
    def _score_status(projects: list[AIProject]) -> float:
        """Score based on project status distribution.

        Rewards production projects, penalizes retired ones.
        """
        if not projects:
            return 50.0

        scores = {
            ProjectStatus.PRODUCTION: 100,
            ProjectStatus.TESTING: 80,
            ProjectStatus.DEVELOPMENT: 70,
            ProjectStatus.PLANNING: 50,
            ProjectStatus.RETIRED: 30,
        }
        return mean(scores.get(p.status, 50) for p in projects)

    @staticmethod
    def _score_risks(risks: list[RiskEntry]) -> float:
        """Score based on risk profile. Lower risk = higher score."""
        if not risks:
            return 80.0

        open_risks = [r for r in risks if r.status != RiskStatus.RESOLVED]
        if not open_risks:
            return 95.0

        avg_risk_score = mean(r.risk_score for r in open_risks)
        # Scale: risk_score 1 => 100, risk_score 25 => 0
        return max(0, min(100, 100 - (avg_risk_score - 1) * (100 / 24)))

    @staticmethod
    def _score_budget(budgets: list[BudgetEntry]) -> float:
        """Score based on budget adherence. On/under budget = higher score."""
        if not budgets:
            return 75.0

        total_planned = sum(b.planned_amount for b in budgets)
        total_actual = sum(b.actual_amount for b in budgets)

        if total_planned == 0:
            return 75.0

        variance_pct = ((total_actual - total_planned) / total_planned) * 100

        if variance_pct <= 0:
            return min(100, 90 + abs(variance_pct) * 0.5)
        if variance_pct <= 5:
            return 85
        if variance_pct <= 10:
            return 70
        if variance_pct <= 20:
            return 55
        return max(0, 40 - (variance_pct - 20))

    @staticmethod
    def _score_kpis(kpis: list[ProjectKPI]) -> float:
        """Score based on KPI achievement rates."""
        if not kpis:
            return 60.0

        avg_achievement = mean(min(k.achievement_rate, 120) for k in kpis)
        # Cap at 100 for the score
        return min(100, avg_achievement)

    @staticmethod
    def _status_detail(score: float) -> str:
        if score >= 80:
            return "Strong project pipeline with active production systems"
        if score >= 60:
            return "Healthy mix of projects across lifecycle stages"
        return "Portfolio needs attention - many projects in early or retired stages"

    @staticmethod
    def _risk_detail(score: float) -> str:
        if score >= 80:
            return "Risk profile is well managed"
        if score >= 60:
            return "Some risks require attention"
        return "Significant risks need immediate mitigation"

    @staticmethod
    def _budget_detail(score: float) -> str:
        if score >= 80:
            return "Budget is on track or under planned spending"
        if score >= 60:
            return "Minor budget overruns detected"
        return "Significant budget overruns require corrective action"

    @staticmethod
    def _kpi_detail(score: float) -> str:
        if score >= 80:
            return "KPIs are largely on target"
        if score >= 60:
            return "Some KPIs are below target"
        return "Multiple KPIs significantly below target"


class TrendAnalyzer:
    """Analyzes KPI trends across the portfolio."""

    @staticmethod
    def analyze(kpis: list[ProjectKPI]) -> dict[str, list[ProjectKPI]]:
        """Group KPIs by trend direction.

        Returns:
            Dict with keys 'up', 'down', 'stable', each containing a list of KPIs.
        """
        result: dict[str, list[ProjectKPI]] = {
            "up": [],
            "down": [],
            "stable": [],
        }
        for kpi in kpis:
            result[kpi.trend.value].append(kpi)
        return result

    @staticmethod
    def get_underperforming_kpis(
        kpis: list[ProjectKPI], threshold: float = 70.0
    ) -> list[ProjectKPI]:
        """Find KPIs with achievement rate below threshold.

        Args:
            kpis: List of KPIs to analyze.
            threshold: Achievement percentage threshold (default 70%).

        Returns:
            List of underperforming KPIs sorted by achievement rate.
        """
        underperforming = [k for k in kpis if k.achievement_rate < threshold]
        return sorted(underperforming, key=lambda k: k.achievement_rate)

    @staticmethod
    def get_trend_summary(kpis: list[ProjectKPI]) -> dict[str, int]:
        """Get count of KPIs by trend direction."""
        trends = TrendAnalyzer.analyze(kpis)
        return {direction: len(items) for direction, items in trends.items()}

    @staticmethod
    def get_top_performers(kpis: list[ProjectKPI], limit: int = 5) -> list[ProjectKPI]:
        """Get the top performing KPIs by achievement rate."""
        return sorted(kpis, key=lambda k: k.achievement_rate, reverse=True)[:limit]


class ExecutiveSummaryGenerator:
    """Auto-generates executive summary text from portfolio statistics."""

    @staticmethod
    def generate(
        projects: list[AIProject],
        kpis: list[ProjectKPI],
        budgets: list[BudgetEntry],
        risks: list[RiskEntry],
        health_score: HealthScore | None = None,
    ) -> str:
        """Generate a comprehensive executive summary.

        Args:
            projects: All projects in the portfolio.
            kpis: All KPIs across projects.
            budgets: All budget entries.
            risks: All risk entries.
            health_score: Optional pre-computed health score.

        Returns:
            Formatted executive summary text.
        """
        if health_score is None:
            health_score = PortfolioHealthScore.compute(projects, risks, budgets, kpis)

        sections = [
            ExecutiveSummaryGenerator._overview_section(projects, health_score),
            ExecutiveSummaryGenerator._status_section(projects),
            ExecutiveSummaryGenerator._budget_section(budgets),
            ExecutiveSummaryGenerator._kpi_section(kpis),
            ExecutiveSummaryGenerator._risk_section(risks),
            ExecutiveSummaryGenerator._recommendations_section(
                projects, kpis, budgets, risks, health_score
            ),
        ]

        return "\n\n".join(sections)

    @staticmethod
    def _overview_section(projects: list[AIProject], health: HealthScore) -> str:
        total = len(projects)
        active = sum(1 for p in projects if p.is_active)
        label = "Excellent" if health.overall_score >= 80 else (
            "Good" if health.overall_score >= 60 else (
                "Fair" if health.overall_score >= 40 else "Needs Attention"
            )
        )
        return (
            f"## Portfolio Overview\n\n"
            f"The AI portfolio consists of **{total} projects**, "
            f"of which **{active}** are actively in development, testing, or production. "
            f"The overall portfolio health score is **{health.overall_score}/100** ({label})."
        )

    @staticmethod
    def _status_section(projects: list[AIProject]) -> str:
        counts: dict[str, int] = {}
        for p in projects:
            counts[p.status.value] = counts.get(p.status.value, 0) + 1

        lines = ["## Project Status Distribution\n"]
        for status in ProjectStatus:
            count = counts.get(status.value, 0)
            if count > 0:
                lines.append(f"- **{status.value.title()}**: {count} project(s)")

        critical = [p for p in projects if p.priority == Priority.CRITICAL]
        if critical:
            names = ", ".join(p.name for p in critical)
            lines.append(f"\n**Critical priority projects**: {names}")

        return "\n".join(lines)

    @staticmethod
    def _budget_section(budgets: list[BudgetEntry]) -> str:
        if not budgets:
            return "## Budget Summary\n\nNo budget data available."

        total_planned = sum(b.planned_amount for b in budgets)
        total_actual = sum(b.actual_amount for b in budgets)
        variance = total_actual - total_planned
        variance_pct = (variance / total_planned * 100) if total_planned > 0 else 0

        status_text = "under budget" if variance <= 0 else "over budget"

        return (
            f"## Budget Summary\n\n"
            f"- **Total Planned**: ${total_planned:,.2f}\n"
            f"- **Total Actual**: ${total_actual:,.2f}\n"
            f"- **Variance**: ${abs(variance):,.2f} ({abs(variance_pct):.1f}% {status_text})"
        )

    @staticmethod
    def _kpi_section(kpis: list[ProjectKPI]) -> str:
        if not kpis:
            return "## KPI Performance\n\nNo KPI data available."

        on_target = sum(1 for k in kpis if k.is_on_target)
        avg_achievement = mean(k.achievement_rate for k in kpis) if kpis else 0

        trends = TrendAnalyzer.get_trend_summary(kpis)
        underperforming = TrendAnalyzer.get_underperforming_kpis(kpis)

        lines = [
            f"## KPI Performance\n",
            f"- **Total KPIs tracked**: {len(kpis)}",
            f"- **On target**: {on_target}/{len(kpis)} ({on_target/len(kpis)*100:.0f}%)",
            f"- **Average achievement**: {avg_achievement:.1f}%",
            f"- **Trends**: {trends.get('up', 0)} improving, "
            f"{trends.get('stable', 0)} stable, "
            f"{trends.get('down', 0)} declining",
        ]

        if underperforming:
            lines.append(f"\n**Attention needed**: {len(underperforming)} KPI(s) below 70% target.")

        return "\n".join(lines)

    @staticmethod
    def _risk_section(risks: list[RiskEntry]) -> str:
        if not risks:
            return "## Risk Profile\n\nNo risks recorded."

        open_risks = [r for r in risks if r.status == RiskStatus.OPEN]
        mitigating = [r for r in risks if r.status == RiskStatus.MITIGATING]
        resolved = [r for r in risks if r.status == RiskStatus.RESOLVED]
        critical_risks = [r for r in open_risks if r.risk_level == "critical"]

        lines = [
            f"## Risk Profile\n",
            f"- **Open risks**: {len(open_risks)}",
            f"- **Being mitigated**: {len(mitigating)}",
            f"- **Resolved**: {len(resolved)}",
        ]

        if critical_risks:
            lines.append(
                f"\n**Critical risks ({len(critical_risks)})** require immediate attention."
            )

        return "\n".join(lines)

    @staticmethod
    def _recommendations_section(
        projects: list[AIProject],
        kpis: list[ProjectKPI],
        budgets: list[BudgetEntry],
        risks: list[RiskEntry],
        health: HealthScore,
    ) -> str:
        recs = ["## Recommendations\n"]

        if health.budget_score < 70:
            recs.append(
                "- **Budget Review**: Conduct an immediate review of projects exceeding "
                "planned budgets and implement cost controls."
            )

        if health.risk_score < 70:
            recs.append(
                "- **Risk Mitigation**: Prioritize mitigation plans for high-impact risks "
                "in the active portfolio."
            )

        underperforming = TrendAnalyzer.get_underperforming_kpis(kpis)
        if underperforming:
            recs.append(
                f"- **KPI Improvement**: {len(underperforming)} KPI(s) are significantly "
                "below target. Consider resource reallocation or scope adjustment."
            )

        planning = [p for p in projects if p.status == ProjectStatus.PLANNING]
        if len(planning) > len(projects) * 0.4:
            recs.append(
                "- **Pipeline Acceleration**: A large portion of the portfolio is still "
                "in planning. Consider accelerating development timelines."
            )

        if len(recs) == 1:
            recs.append("- Portfolio is performing well. Continue current trajectory.")

        return "\n".join(recs)
