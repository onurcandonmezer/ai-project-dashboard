"""Streamlit dashboard for the AI Project Portfolio.

Multi-page dashboard providing portfolio overview, KPI tracking,
budget management, risk register, and executive summary views.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analytics import (
    ExecutiveSummaryGenerator,
    PortfolioHealthScore,
    TrendAnalyzer,
)
from src.database import ProjectDatabase
from src.models import ProjectStatus, RiskStatus
from src.report_generator import ReportGenerator

# ── Configuration ─────────────────────────────────────────────

DB_PATH = os.environ.get("AI_DASHBOARD_DB", "ai_projects.db")
YAML_PATH = os.environ.get("AI_DASHBOARD_YAML", "data/sample_projects.yaml")

st.set_page_config(
    page_title="AI Project Dashboard",
    page_icon="[AI]",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_database() -> ProjectDatabase:
    """Get or create the database connection."""
    db = ProjectDatabase(DB_PATH)
    if not db.get_all_projects():
        yaml_path = Path(YAML_PATH)
        if yaml_path.exists():
            db.seed_from_yaml(str(yaml_path))
    return db


def main() -> None:
    """Main entry point for the Streamlit dashboard."""
    db = get_database()

    st.sidebar.title("AI Project Dashboard")
    page = st.sidebar.radio(
        "Navigation",
        [
            "Portfolio Overview",
            "KPI Tracking",
            "Budget Management",
            "Risk Register",
            "Executive Summary",
        ],
    )

    if page == "Portfolio Overview":
        render_portfolio_overview(db)
    elif page == "KPI Tracking":
        render_kpi_tracking(db)
    elif page == "Budget Management":
        render_budget_management(db)
    elif page == "Risk Register":
        render_risk_register(db)
    elif page == "Executive Summary":
        render_executive_summary(db)


# ── Portfolio Overview ────────────────────────────────────────


def render_portfolio_overview(db: ProjectDatabase) -> None:
    """Render the portfolio overview page with project cards and health score."""
    st.title("AI Portfolio Overview")

    projects = db.get_all_projects()
    kpis = db.get_all_kpis()
    budgets = db.get_all_budgets()
    risks = db.get_all_risks()

    # Health score
    health = PortfolioHealthScore.compute(projects, risks, budgets, kpis)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Health Score", f"{health.overall_score}/100")
    col2.metric("Total Projects", len(projects))
    col3.metric("Active Projects", sum(1 for p in projects if p.is_active))
    col4.metric("Open Risks", sum(1 for r in risks if r.status != RiskStatus.RESOLVED))

    # Health score breakdown
    st.subheader("Health Score Breakdown")
    health_df = pd.DataFrame(
        {
            "Component": ["Status", "Risk", "Budget", "KPI"],
            "Score": [
                health.status_score,
                health.risk_score,
                health.budget_score,
                health.kpi_score,
            ],
        }
    )
    fig = px.bar(
        health_df,
        x="Component",
        y="Score",
        color="Score",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        range_y=[0, 100],
        title="Portfolio Health Components",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Status distribution
    st.subheader("Project Status Distribution")
    status_counts = db.get_project_count_by_status()
    if status_counts:
        fig_status = px.pie(
            names=list(status_counts.keys()),
            values=list(status_counts.values()),
            title="Projects by Status",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # Project cards
    st.subheader("All Projects")
    status_filter = st.multiselect(
        "Filter by Status",
        [s.value for s in ProjectStatus],
        default=[s.value for s in ProjectStatus],
    )

    for project in projects:
        if project.status.value in status_filter:
            with st.expander(
                f"{'*' if project.priority.value in ('critical', 'high') else ''} "
                f"{project.name} - {project.status.value.upper()}"
            ):
                c1, c2, c3 = st.columns(3)
                c1.write(f"**Owner:** {project.owner}")
                c1.write(f"**Department:** {project.department}")
                c2.write(f"**Priority:** {project.priority.value.title()}")
                c2.write(f"**Model:** {project.model_used}")
                c3.write(f"**Start:** {project.start_date}")
                c3.write(f"**Target:** {project.target_date or 'TBD'}")
                st.write(project.description)


# ── KPI Tracking ──────────────────────────────────────────────


def render_kpi_tracking(db: ProjectDatabase) -> None:
    """Render the KPI tracking page with metrics and trends."""
    st.title("KPI Tracking")

    projects = db.get_all_projects()
    kpis = db.get_all_kpis()
    project_map = {p.id: p.name for p in projects}

    if not kpis:
        st.warning("No KPI data available.")
        return

    # Summary metrics
    on_target = sum(1 for k in kpis if k.is_on_target)
    trends = TrendAnalyzer.get_trend_summary(kpis)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total KPIs", len(kpis))
    col2.metric("On Target", f"{on_target}/{len(kpis)}")
    col3.metric("Improving", trends.get("up", 0))
    col4.metric("Declining", trends.get("down", 0))

    # Achievement chart
    st.subheader("KPI Achievement Rates")
    kpi_data = [
        {
            "Project": project_map.get(k.project_id, k.project_id),
            "KPI": k.metric_name,
            "Achievement (%)": min(k.achievement_rate, 120),
            "Trend": k.trend.value,
        }
        for k in kpis
    ]
    kpi_df = pd.DataFrame(kpi_data)

    fig = px.bar(
        kpi_df,
        x="KPI",
        y="Achievement (%)",
        color="Trend",
        color_discrete_map={"up": "#2ecc71", "stable": "#3498db", "down": "#e74c3c"},
        hover_data=["Project"],
        title="KPI Achievement by Metric",
    )
    fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Target")
    st.plotly_chart(fig, use_container_width=True)

    # Underperforming KPIs
    underperforming = TrendAnalyzer.get_underperforming_kpis(kpis)
    if underperforming:
        st.subheader("Attention Required: Below Target KPIs")
        for kpi in underperforming:
            proj_name = project_map.get(kpi.project_id, kpi.project_id)
            st.warning(
                f"**{proj_name}** - {kpi.metric_name}: "
                f"{kpi.current_value} / {kpi.target_value} {kpi.unit} "
                f"({kpi.achievement_rate:.1f}%)"
            )


# ── Budget Management ────────────────────────────────────────


def render_budget_management(db: ProjectDatabase) -> None:
    """Render the budget management page with planned vs actual charts."""
    st.title("Budget Management")

    projects = db.get_all_projects()
    budgets = db.get_all_budgets()
    project_map = {p.id: p.name for p in projects}

    if not budgets:
        st.warning("No budget data available.")
        return

    # Summary
    summary = db.get_budget_summary()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Planned", f"${summary['total_planned']:,.2f}")
    col2.metric("Total Actual", f"${summary['total_actual']:,.2f}")
    variance = summary["total_variance"]
    col3.metric(
        "Variance",
        f"${abs(variance):,.2f}",
        delta=f"{'Over' if variance > 0 else 'Under'} budget",
        delta_color="inverse",
    )

    # Planned vs Actual by project
    st.subheader("Planned vs Actual by Project")
    project_budgets: dict[str, dict[str, float]] = {}
    for b in budgets:
        name = project_map.get(b.project_id, b.project_id)
        if name not in project_budgets:
            project_budgets[name] = {"planned": 0, "actual": 0}
        project_budgets[name]["planned"] += b.planned_amount
        project_budgets[name]["actual"] += b.actual_amount

    budget_df = pd.DataFrame(
        [
            {"Project": name, "Type": "Planned", "Amount": vals["planned"]}
            for name, vals in project_budgets.items()
        ]
        + [
            {"Project": name, "Type": "Actual", "Amount": vals["actual"]}
            for name, vals in project_budgets.items()
        ]
    )

    fig = px.bar(
        budget_df,
        x="Project",
        y="Amount",
        color="Type",
        barmode="group",
        color_discrete_map={"Planned": "#3498db", "Actual": "#e74c3c"},
        title="Budget: Planned vs Actual",
    )
    st.plotly_chart(fig, use_container_width=True)

    # By category
    st.subheader("Budget by Category")
    cat_summary = db.get_budget_by_category()
    if cat_summary:
        cat_df = pd.DataFrame(
            [
                {
                    "Category": cat.replace("_", " ").title(),
                    "Planned": vals["planned"],
                    "Actual": vals["actual"],
                    "Variance": vals["variance"],
                }
                for cat, vals in cat_summary.items()
            ]
        )
        st.dataframe(cat_df, use_container_width=True)


# ── Risk Register ─────────────────────────────────────────────


def render_risk_register(db: ProjectDatabase) -> None:
    """Render the risk register page with risk matrix visualization."""
    st.title("Risk Register")

    projects = db.get_all_projects()
    risks = db.get_all_risks()
    project_map = {p.id: p.name for p in projects}

    if not risks:
        st.warning("No risk data available.")
        return

    # Summary
    open_count = sum(1 for r in risks if r.status == RiskStatus.OPEN)
    mitigating_count = sum(1 for r in risks if r.status == RiskStatus.MITIGATING)
    resolved_count = sum(1 for r in risks if r.status == RiskStatus.RESOLVED)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Risks", len(risks))
    col2.metric("Open", open_count)
    col3.metric("Mitigating", mitigating_count)
    col4.metric("Resolved", resolved_count)

    # Risk matrix heatmap
    st.subheader("Risk Matrix")
    active_risks = [r for r in risks if r.status != RiskStatus.RESOLVED]
    matrix = [[0] * 5 for _ in range(5)]
    for r in active_risks:
        matrix[5 - r.probability][r.impact - 1] += 1

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=["Impact 1", "Impact 2", "Impact 3", "Impact 4", "Impact 5"],
            y=["P5 (High)", "P4", "P3", "P2", "P1 (Low)"],
            colorscale="YlOrRd",
            text=matrix,
            texttemplate="%{text}",
            hovertemplate="Probability: %{y}<br>Impact: %{x}<br>Count: %{z}<extra></extra>",
        )
    )
    fig.update_layout(title="Risk Heatmap (Probability vs Impact)")
    st.plotly_chart(fig, use_container_width=True)

    # Risk details table
    st.subheader("Risk Details")
    risk_data = [
        {
            "Project": project_map.get(r.project_id, r.project_id),
            "Risk": r.risk_description[:80],
            "Probability": r.probability,
            "Impact": r.impact,
            "Score": r.risk_score,
            "Level": r.risk_level.title(),
            "Status": r.status.value.title(),
        }
        for r in sorted(risks, key=lambda x: x.risk_score, reverse=True)
    ]
    st.dataframe(pd.DataFrame(risk_data), use_container_width=True)


# ── Executive Summary ─────────────────────────────────────────


def render_executive_summary(db: ProjectDatabase) -> None:
    """Render the auto-generated executive summary page."""
    st.title("Executive Summary")

    projects = db.get_all_projects()
    kpis = db.get_all_kpis()
    budgets = db.get_all_budgets()
    risks = db.get_all_risks()

    health = PortfolioHealthScore.compute(projects, risks, budgets, kpis)

    # Health gauge
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=health.overall_score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Portfolio Health Score"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 40], "color": "#e74c3c"},
                    {"range": [40, 70], "color": "#f39c12"},
                    {"range": [70, 100], "color": "#2ecc71"},
                ],
            },
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # Generated summary
    summary = ExecutiveSummaryGenerator.generate(projects, kpis, budgets, risks, health)
    st.markdown(summary)

    # Download reports
    st.subheader("Download Reports")
    col1, col2, col3 = st.columns(3)

    with col1:
        report = ReportGenerator.portfolio_overview(projects, kpis, budgets, risks)
        st.download_button(
            "Portfolio Overview (MD)",
            report,
            file_name="portfolio_overview.md",
            mime="text/markdown",
        )

    with col2:
        report = ReportGenerator.budget_variance_report(projects, budgets)
        st.download_button(
            "Budget Report (MD)",
            report,
            file_name="budget_variance.md",
            mime="text/markdown",
        )

    with col3:
        report = ReportGenerator.risk_register_report(projects, risks)
        st.download_button(
            "Risk Report (MD)",
            report,
            file_name="risk_register.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
