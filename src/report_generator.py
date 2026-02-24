"""Report generation for the AI Project Dashboard.

Generates Markdown and HTML reports for portfolio overview,
budget variance, risk register, and executive summaries.
"""

from __future__ import annotations

from datetime import date, datetime

from src.analytics import (
    ExecutiveSummaryGenerator,
    PortfolioHealthScore,
)
from src.models import (
    AIProject,
    BudgetEntry,
    ProjectKPI,
    ProjectStatus,
    RiskEntry,
    RiskStatus,
)


class ReportGenerator:
    """Generates formatted reports from portfolio data.

    All reports are available in Markdown format, with an optional
    HTML wrapper for browser-based viewing.
    """

    @staticmethod
    def portfolio_overview(
        projects: list[AIProject],
        kpis: list[ProjectKPI],
        budgets: list[BudgetEntry],
        risks: list[RiskEntry],
    ) -> str:
        """Generate a full portfolio overview report in Markdown.

        Includes project listing, status summary, health score,
        and high-level budget and risk indicators.
        """
        health = PortfolioHealthScore.compute(projects, risks, budgets, kpis)
        lines = [
            "# AI Portfolio Overview Report",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
            f"## Health Score: {health.overall_score}/100\n",
            "| Component | Score |",
            "|-----------|-------|",
            f"| Status Distribution | {health.status_score} |",
            f"| Risk Profile | {health.risk_score} |",
            f"| Budget Adherence | {health.budget_score} |",
            f"| KPI Achievement | {health.kpi_score} |",
            "",
        ]

        # Project listing
        lines.append("## Projects\n")
        lines.append("| Project | Status | Priority | Owner | Department |")
        lines.append("|---------|--------|----------|-------|------------|")
        for p in sorted(projects, key=lambda x: x.priority.value):
            status_icon = _status_icon(p.status)
            lines.append(
                f"| {p.name} | {status_icon} {p.status.value.title()} | "
                f"{p.priority.value.title()} | {p.owner} | {p.department} |"
            )

        # Summary stats
        total_planned = sum(b.planned_amount for b in budgets)
        total_actual = sum(b.actual_amount for b in budgets)
        open_risks = sum(1 for r in risks if r.status != RiskStatus.RESOLVED)

        lines.extend(
            [
                "",
                "## Quick Stats\n",
                f"- **Total Projects**: {len(projects)}",
                f"- **Active Projects**: {sum(1 for p in projects if p.is_active)}",
                f"- **Total Budget**: ${total_planned:,.2f} planned / ${total_actual:,.2f} actual",
                f"- **Open Risks**: {open_risks}",
                f"- **KPIs Tracked**: {len(kpis)}",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def budget_variance_report(
        projects: list[AIProject],
        budgets: list[BudgetEntry],
    ) -> str:
        """Generate a budget variance report in Markdown.

        Shows planned vs actual spending by project and category,
        highlighting overruns and savings.
        """
        lines = [
            "# Budget Variance Report",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
        ]

        # Overall summary
        total_planned = sum(b.planned_amount for b in budgets)
        total_actual = sum(b.actual_amount for b in budgets)
        total_variance = total_actual - total_planned

        lines.extend(
            [
                "## Overall Summary\n",
                "| Metric | Amount |",
                "|--------|--------|",
                f"| Total Planned | ${total_planned:,.2f} |",
                f"| Total Actual | ${total_actual:,.2f} |",
                f"| Variance | ${total_variance:+,.2f} |",
                "",
            ]
        )

        # By project
        lines.append("## By Project\n")
        lines.append("| Project | Planned | Actual | Variance | Status |")
        lines.append("|---------|---------|--------|----------|--------|")

        project_map = {p.id: p.name for p in projects}
        project_budgets: dict[str, list[BudgetEntry]] = {}
        for b in budgets:
            project_budgets.setdefault(b.project_id, []).append(b)

        for pid, entries in project_budgets.items():
            p_planned = sum(e.planned_amount for e in entries)
            p_actual = sum(e.actual_amount for e in entries)
            p_var = p_actual - p_planned
            status = "Over" if p_var > 0 else ("Under" if p_var < 0 else "On Track")
            name = project_map.get(pid, pid)
            lines.append(
                f"| {name} | ${p_planned:,.2f} | ${p_actual:,.2f} | ${p_var:+,.2f} | {status} |"
            )

        # By category
        lines.extend(["", "## By Category\n"])
        lines.append("| Category | Planned | Actual | Variance |")
        lines.append("|----------|---------|--------|----------|")

        cat_budgets: dict[str, list[BudgetEntry]] = {}
        for b in budgets:
            cat_budgets.setdefault(b.category.value, []).append(b)

        for cat, entries in sorted(cat_budgets.items()):
            c_planned = sum(e.planned_amount for e in entries)
            c_actual = sum(e.actual_amount for e in entries)
            c_var = c_actual - c_planned
            lines.append(
                f"| {cat.replace('_', ' ').title()} | ${c_planned:,.2f} | "
                f"${c_actual:,.2f} | ${c_var:+,.2f} |"
            )

        return "\n".join(lines)

    @staticmethod
    def risk_register_report(
        projects: list[AIProject],
        risks: list[RiskEntry],
    ) -> str:
        """Generate a risk register report in Markdown.

        Includes risk matrix summary, detailed risk entries,
        and mitigation status tracking.
        """
        lines = [
            "# Risk Register Report",
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
        ]

        # Summary
        open_count = sum(1 for r in risks if r.status == RiskStatus.OPEN)
        mitigating_count = sum(1 for r in risks if r.status == RiskStatus.MITIGATING)
        resolved_count = sum(1 for r in risks if r.status == RiskStatus.RESOLVED)

        lines.extend(
            [
                "## Summary\n",
                f"- **Total Risks**: {len(risks)}",
                f"- **Open**: {open_count}",
                f"- **Mitigating**: {mitigating_count}",
                f"- **Resolved**: {resolved_count}",
                "",
            ]
        )

        # Risk matrix
        lines.extend(
            [
                "## Risk Matrix (Probability x Impact)\n",
                "| | Impact 1 | Impact 2 | Impact 3 | Impact 4 | Impact 5 |",
                "|---|----------|----------|----------|----------|----------|",
            ]
        )

        active_risks = [r for r in risks if r.status != RiskStatus.RESOLVED]
        for prob in range(5, 0, -1):
            row = [f"**P{prob}**"]
            for imp in range(1, 6):
                count = sum(1 for r in active_risks if r.probability == prob and r.impact == imp)
                row.append(str(count) if count > 0 else "-")
            lines.append("| " + " | ".join(row) + " |")

        # Detailed risk entries
        lines.extend(["", "## Risk Details\n"])
        lines.append("| Project | Risk | P | I | Score | Status | Mitigation |")
        lines.append("|---------|------|---|---|-------|--------|------------|")

        project_map = {p.id: p.name for p in projects}

        for r in sorted(risks, key=lambda x: x.risk_score, reverse=True):
            name = project_map.get(r.project_id, r.project_id)
            mitigation = r.mitigation[:50] + "..." if len(r.mitigation) > 50 else r.mitigation
            lines.append(
                f"| {name} | {r.risk_description[:40]} | {r.probability} | "
                f"{r.impact} | {r.risk_score} | {r.status.value.title()} | {mitigation} |"
            )

        return "\n".join(lines)

    @staticmethod
    def executive_summary_report(
        projects: list[AIProject],
        kpis: list[ProjectKPI],
        budgets: list[BudgetEntry],
        risks: list[RiskEntry],
    ) -> str:
        """Generate a formatted executive summary report in Markdown.

        Delegates to ExecutiveSummaryGenerator for content and adds
        report header/footer.
        """
        health = PortfolioHealthScore.compute(projects, risks, budgets, kpis)
        summary = ExecutiveSummaryGenerator.generate(projects, kpis, budgets, risks, health)

        header = (
            f"# Executive Summary - AI Portfolio\n"
            f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"
            f"_Report Period: {date.today().strftime('%B %Y')}_\n"
        )

        footer = (
            "\n---\n"
            "_This report was auto-generated by the AI Project Dashboard. "
            "For questions, contact the AI Center of Excellence._"
        )

        return f"{header}\n{summary}\n{footer}"

    @staticmethod
    def to_html(markdown_content: str, title: str = "AI Dashboard Report") -> str:
        """Wrap Markdown content in a basic HTML page.

        This is a lightweight conversion for simple viewing.
        For production use, consider a full Markdown-to-HTML library.

        Args:
            markdown_content: The Markdown text.
            title: HTML page title.

        Returns:
            Complete HTML document string.
        """
        # Simple markdown to HTML conversion for basic elements
        html_body = markdown_content
        html_body = html_body.replace("&", "&amp;")
        html_body = html_body.replace("<", "&lt;")
        html_body = html_body.replace(">", "&gt;")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 2rem auto;
            padding: 0 1rem;
            line-height: 1.6;
            color: #333;
        }}
        pre {{
            background: #f5f5f5;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1rem 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.5rem;
            text-align: left;
        }}
        th {{
            background: #f0f0f0;
        }}
    </style>
</head>
<body>
<pre>{html_body}</pre>
</body>
</html>"""


def _status_icon(status: ProjectStatus) -> str:
    """Return a text indicator for project status."""
    icons = {
        ProjectStatus.PLANNING: "[PLAN]",
        ProjectStatus.DEVELOPMENT: "[DEV]",
        ProjectStatus.TESTING: "[TEST]",
        ProjectStatus.PRODUCTION: "[PROD]",
        ProjectStatus.RETIRED: "[RET]",
    }
    return icons.get(status, "[?]")
