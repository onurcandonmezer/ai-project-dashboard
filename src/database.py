"""SQLite database layer for the AI Project Dashboard.

Provides CRUD operations, query methods, and data seeding
for projects, KPIs, budgets, and risks.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import yaml

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


class ProjectDatabase:
    """SQLite-backed storage for AI project portfolio data.

    Manages the full lifecycle of projects, KPIs, budgets, and risks
    with atomic operations and structured queries.
    """

    def __init__(self, db_path: str = "ai_projects.db") -> None:
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None
        self._initialize_tables()

    @property
    def connection(self) -> sqlite3.Connection:
        """Lazy database connection with row factory."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _initialize_tables(self) -> None:
        """Create all required tables if they do not exist."""
        conn = self.connection
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'planning',
                priority TEXT NOT NULL DEFAULT 'medium',
                owner TEXT NOT NULL,
                start_date TEXT NOT NULL,
                target_date TEXT,
                model_used TEXT DEFAULT '',
                use_case TEXT DEFAULT '',
                department TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS kpis (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                current_value REAL NOT NULL,
                target_value REAL NOT NULL,
                unit TEXT DEFAULT '',
                trend TEXT NOT NULL DEFAULT 'stable',
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                category TEXT NOT NULL,
                planned_amount REAL NOT NULL DEFAULT 0,
                actual_amount REAL NOT NULL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS risks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                risk_description TEXT NOT NULL,
                probability INTEGER NOT NULL,
                impact INTEGER NOT NULL,
                mitigation TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)
        conn.commit()

    # ── Project CRUD ──────────────────────────────────────────────

    def add_project(self, project: AIProject) -> AIProject:
        """Insert a new project into the database."""
        self.connection.execute(
            """INSERT INTO projects
               (id, name, description, status, priority, owner,
                start_date, target_date, model_used, use_case, department)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                project.id,
                project.name,
                project.description,
                project.status.value,
                project.priority.value,
                project.owner,
                project.start_date.isoformat(),
                project.target_date.isoformat() if project.target_date else None,
                project.model_used,
                project.use_case,
                project.department,
            ),
        )
        self.connection.commit()
        return project

    def get_project(self, project_id: str) -> AIProject | None:
        """Retrieve a project by its ID."""
        row = self.connection.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_project(row)

    def get_all_projects(self) -> list[AIProject]:
        """Retrieve all projects."""
        rows = self.connection.execute("SELECT * FROM projects ORDER BY start_date DESC").fetchall()
        return [self._row_to_project(row) for row in rows]

    def update_project(self, project: AIProject) -> AIProject:
        """Update an existing project."""
        self.connection.execute(
            """UPDATE projects SET
               name=?, description=?, status=?, priority=?, owner=?,
               start_date=?, target_date=?, model_used=?, use_case=?, department=?
               WHERE id=?""",
            (
                project.name,
                project.description,
                project.status.value,
                project.priority.value,
                project.owner,
                project.start_date.isoformat(),
                project.target_date.isoformat() if project.target_date else None,
                project.model_used,
                project.use_case,
                project.department,
                project.id,
            ),
        )
        self.connection.commit()
        return project

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and all associated data."""
        cursor = self.connection.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.connection.commit()
        return cursor.rowcount > 0

    # ── KPI CRUD ──────────────────────────────────────────────────

    def add_kpi(self, kpi: ProjectKPI) -> ProjectKPI:
        """Insert a new KPI."""
        self.connection.execute(
            """INSERT INTO kpis
               (id, project_id, metric_name, current_value, target_value, unit, trend)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                kpi.id,
                kpi.project_id,
                kpi.metric_name,
                kpi.current_value,
                kpi.target_value,
                kpi.unit,
                kpi.trend.value,
            ),
        )
        self.connection.commit()
        return kpi

    def get_kpis_for_project(self, project_id: str) -> list[ProjectKPI]:
        """Retrieve all KPIs for a given project."""
        rows = self.connection.execute(
            "SELECT * FROM kpis WHERE project_id = ?", (project_id,)
        ).fetchall()
        return [self._row_to_kpi(row) for row in rows]

    def get_all_kpis(self) -> list[ProjectKPI]:
        """Retrieve all KPIs."""
        rows = self.connection.execute("SELECT * FROM kpis").fetchall()
        return [self._row_to_kpi(row) for row in rows]

    # ── Budget CRUD ───────────────────────────────────────────────

    def add_budget(self, budget: BudgetEntry) -> BudgetEntry:
        """Insert a new budget entry."""
        self.connection.execute(
            """INSERT INTO budgets
               (id, project_id, category, planned_amount, actual_amount, currency)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                budget.id,
                budget.project_id,
                budget.category.value,
                budget.planned_amount,
                budget.actual_amount,
                budget.currency,
            ),
        )
        self.connection.commit()
        return budget

    def get_budgets_for_project(self, project_id: str) -> list[BudgetEntry]:
        """Retrieve all budget entries for a given project."""
        rows = self.connection.execute(
            "SELECT * FROM budgets WHERE project_id = ?", (project_id,)
        ).fetchall()
        return [self._row_to_budget(row) for row in rows]

    def get_all_budgets(self) -> list[BudgetEntry]:
        """Retrieve all budget entries."""
        rows = self.connection.execute("SELECT * FROM budgets").fetchall()
        return [self._row_to_budget(row) for row in rows]

    # ── Risk CRUD ─────────────────────────────────────────────────

    def add_risk(self, risk: RiskEntry) -> RiskEntry:
        """Insert a new risk entry."""
        self.connection.execute(
            """INSERT INTO risks
               (id, project_id, risk_description, probability, impact, mitigation, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                risk.id,
                risk.project_id,
                risk.risk_description,
                risk.probability,
                risk.impact,
                risk.mitigation,
                risk.status.value,
            ),
        )
        self.connection.commit()
        return risk

    def get_risks_for_project(self, project_id: str) -> list[RiskEntry]:
        """Retrieve all risk entries for a given project."""
        rows = self.connection.execute(
            "SELECT * FROM risks WHERE project_id = ?", (project_id,)
        ).fetchall()
        return [self._row_to_risk(row) for row in rows]

    def get_all_risks(self) -> list[RiskEntry]:
        """Retrieve all risk entries."""
        rows = self.connection.execute("SELECT * FROM risks").fetchall()
        return [self._row_to_risk(row) for row in rows]

    # ── Query Methods ─────────────────────────────────────────────

    def get_projects_by_status(self, status: ProjectStatus) -> list[AIProject]:
        """Retrieve projects filtered by status."""
        rows = self.connection.execute(
            "SELECT * FROM projects WHERE status = ? ORDER BY start_date DESC",
            (status.value,),
        ).fetchall()
        return [self._row_to_project(row) for row in rows]

    def get_projects_by_priority(self, priority: Priority) -> list[AIProject]:
        """Retrieve projects filtered by priority."""
        rows = self.connection.execute(
            "SELECT * FROM projects WHERE priority = ? ORDER BY start_date DESC",
            (priority.value,),
        ).fetchall()
        return [self._row_to_project(row) for row in rows]

    def get_budget_summary(self) -> dict[str, float]:
        """Get aggregated budget summary across all projects.

        Returns a dict with total_planned, total_actual, total_variance.
        """
        row = self.connection.execute(
            """SELECT
                COALESCE(SUM(planned_amount), 0) as total_planned,
                COALESCE(SUM(actual_amount), 0) as total_actual
               FROM budgets"""
        ).fetchone()
        total_planned = row["total_planned"]
        total_actual = row["total_actual"]
        return {
            "total_planned": round(total_planned, 2),
            "total_actual": round(total_actual, 2),
            "total_variance": round(total_actual - total_planned, 2),
        }

    def get_budget_by_category(self) -> dict[str, dict[str, float]]:
        """Get budget breakdown by category."""
        rows = self.connection.execute(
            """SELECT category,
                COALESCE(SUM(planned_amount), 0) as planned,
                COALESCE(SUM(actual_amount), 0) as actual
               FROM budgets GROUP BY category"""
        ).fetchall()
        return {
            row["category"]: {
                "planned": round(row["planned"], 2),
                "actual": round(row["actual"], 2),
                "variance": round(row["actual"] - row["planned"], 2),
            }
            for row in rows
        }

    def get_risk_register(self) -> list[RiskEntry]:
        """Get all open and mitigating risks, ordered by risk score descending."""
        rows = self.connection.execute(
            """SELECT * FROM risks
               WHERE status IN ('open', 'mitigating')
               ORDER BY (probability * impact) DESC"""
        ).fetchall()
        return [self._row_to_risk(row) for row in rows]

    def get_project_count_by_status(self) -> dict[str, int]:
        """Count projects grouped by status."""
        rows = self.connection.execute(
            "SELECT status, COUNT(*) as cnt FROM projects GROUP BY status"
        ).fetchall()
        return {row["status"]: row["cnt"] for row in rows}

    # ── Seed Method ───────────────────────────────────────────────

    def seed_from_yaml(self, yaml_path: str) -> None:
        """Populate the database from a YAML file with sample data."""
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        for proj_data in data.get("projects", []):
            kpis_data = proj_data.pop("kpis", [])
            budgets_data = proj_data.pop("budgets", [])
            risks_data = proj_data.pop("risks", [])

            # Parse dates from strings if needed
            if isinstance(proj_data.get("start_date"), str):
                proj_data["start_date"] = date.fromisoformat(proj_data["start_date"])
            if isinstance(proj_data.get("target_date"), str):
                proj_data["target_date"] = date.fromisoformat(proj_data["target_date"])

            project = AIProject(**proj_data)
            self.add_project(project)

            for kpi_data in kpis_data:
                kpi_data["project_id"] = project.id
                self.add_kpi(ProjectKPI(**kpi_data))

            for budget_data in budgets_data:
                budget_data["project_id"] = project.id
                self.add_budget(BudgetEntry(**budget_data))

            for risk_data in risks_data:
                risk_data["project_id"] = project.id
                self.add_risk(RiskEntry(**risk_data))

    # ── Row Converters ────────────────────────────────────────────

    @staticmethod
    def _row_to_project(row: sqlite3.Row) -> AIProject:
        """Convert a database row to an AIProject model."""
        return AIProject(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            status=ProjectStatus(row["status"]),
            priority=Priority(row["priority"]),
            owner=row["owner"],
            start_date=date.fromisoformat(row["start_date"]),
            target_date=date.fromisoformat(row["target_date"]) if row["target_date"] else None,
            model_used=row["model_used"],
            use_case=row["use_case"],
            department=row["department"],
        )

    @staticmethod
    def _row_to_kpi(row: sqlite3.Row) -> ProjectKPI:
        """Convert a database row to a ProjectKPI model."""
        return ProjectKPI(
            id=row["id"],
            project_id=row["project_id"],
            metric_name=row["metric_name"],
            current_value=row["current_value"],
            target_value=row["target_value"],
            unit=row["unit"],
            trend=Trend(row["trend"]),
        )

    @staticmethod
    def _row_to_budget(row: sqlite3.Row) -> BudgetEntry:
        """Convert a database row to a BudgetEntry model."""
        return BudgetEntry(
            id=row["id"],
            project_id=row["project_id"],
            category=BudgetCategory(row["category"]),
            planned_amount=row["planned_amount"],
            actual_amount=row["actual_amount"],
            currency=row["currency"],
        )

    @staticmethod
    def _row_to_risk(row: sqlite3.Row) -> RiskEntry:
        """Convert a database row to a RiskEntry model."""
        return RiskEntry(
            id=row["id"],
            project_id=row["project_id"],
            risk_description=row["risk_description"],
            probability=row["probability"],
            impact=row["impact"],
            mitigation=row["mitigation"],
            status=RiskStatus(row["status"]),
        )
