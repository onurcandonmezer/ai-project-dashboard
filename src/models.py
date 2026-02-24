"""Pydantic data models for the AI Project Dashboard.

Defines the core domain models: AIProject, ProjectKPI, BudgetEntry, and RiskEntry.
All models use Pydantic v2 for validation, serialization, and type safety.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, model_validator


class ProjectStatus(StrEnum):
    """Lifecycle status of an AI project."""

    PLANNING = "planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    RETIRED = "retired"


class Priority(StrEnum):
    """Priority level for an AI project."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Trend(StrEnum):
    """Trend direction for a KPI metric."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class BudgetCategory(StrEnum):
    """Budget allocation category."""

    COMPUTE = "compute"
    API_CALLS = "api_calls"
    PERSONNEL = "personnel"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class RiskStatus(StrEnum):
    """Current status of a risk entry."""

    OPEN = "open"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"


def _generate_id() -> str:
    """Generate a short unique identifier."""
    return uuid4().hex[:12]


class AIProject(BaseModel):
    """Represents an AI project in the portfolio.

    Tracks metadata, ownership, timeline, and technical details
    for a single AI initiative within the organization.
    """

    id: str = Field(default_factory=_generate_id, description="Unique project identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str = Field(default="", max_length=2000, description="Project description")
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING, description="Current status")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    owner: str = Field(..., min_length=1, max_length=100, description="Project owner")
    start_date: date = Field(..., description="Project start date")
    target_date: Optional[date] = Field(default=None, description="Target completion date")
    model_used: str = Field(default="", max_length=200, description="AI model being used")
    use_case: str = Field(default="", max_length=500, description="Primary use case")
    department: str = Field(default="", max_length=100, description="Owning department")

    @model_validator(mode="after")
    def validate_dates(self) -> AIProject:
        """Ensure target_date is not before start_date."""
        if self.target_date is not None and self.target_date < self.start_date:
            raise ValueError("target_date must not be before start_date")
        return self

    @computed_field
    @property
    def is_active(self) -> bool:
        """Whether the project is in an active state."""
        return self.status in (
            ProjectStatus.DEVELOPMENT,
            ProjectStatus.TESTING,
            ProjectStatus.PRODUCTION,
        )

    @computed_field
    @property
    def days_until_target(self) -> Optional[int]:
        """Days remaining until target date, or None if no target set."""
        if self.target_date is None:
            return None
        return (self.target_date - date.today()).days


class ProjectKPI(BaseModel):
    """Key Performance Indicator for a project.

    Tracks a specific measurable metric with its current value,
    target, and trend direction.
    """

    id: str = Field(default_factory=_generate_id, description="Unique KPI identifier")
    project_id: str = Field(..., description="Associated project ID")
    metric_name: str = Field(..., min_length=1, max_length=200, description="Name of the metric")
    current_value: float = Field(..., description="Current metric value")
    target_value: float = Field(..., description="Target metric value")
    unit: str = Field(default="", max_length=50, description="Unit of measurement")
    trend: Trend = Field(default=Trend.STABLE, description="Current trend direction")

    @computed_field
    @property
    def achievement_rate(self) -> float:
        """Percentage of target achieved (0-100+)."""
        if self.target_value == 0:
            return 0.0
        return round((self.current_value / self.target_value) * 100, 2)

    @computed_field
    @property
    def is_on_target(self) -> bool:
        """Whether current value meets or exceeds the target."""
        return self.current_value >= self.target_value


class BudgetEntry(BaseModel):
    """Budget line item for a project.

    Tracks planned vs actual spending for a specific cost category.
    """

    id: str = Field(default_factory=_generate_id, description="Unique budget entry identifier")
    project_id: str = Field(..., description="Associated project ID")
    category: BudgetCategory = Field(..., description="Budget category")
    planned_amount: float = Field(..., ge=0, description="Planned budget amount")
    actual_amount: float = Field(default=0.0, ge=0, description="Actual spent amount")
    currency: str = Field(default="USD", max_length=3, description="Currency code")

    @computed_field
    @property
    def variance(self) -> float:
        """Budget variance (actual - planned). Positive means over budget."""
        return round(self.actual_amount - self.planned_amount, 2)

    @computed_field
    @property
    def variance_percentage(self) -> float:
        """Variance as a percentage of planned amount."""
        if self.planned_amount == 0:
            return 0.0
        return round((self.variance / self.planned_amount) * 100, 2)

    @computed_field
    @property
    def is_over_budget(self) -> bool:
        """Whether actual spending exceeds planned budget."""
        return self.actual_amount > self.planned_amount


class RiskEntry(BaseModel):
    """Risk register entry for a project.

    Documents an identified risk with its probability, impact,
    mitigation strategy, and current status.
    """

    id: str = Field(default_factory=_generate_id, description="Unique risk entry identifier")
    project_id: str = Field(..., description="Associated project ID")
    risk_description: str = Field(
        ..., min_length=1, max_length=1000, description="Description of the risk"
    )
    probability: int = Field(..., ge=1, le=5, description="Probability score (1-5)")
    impact: int = Field(..., ge=1, le=5, description="Impact score (1-5)")
    mitigation: str = Field(default="", max_length=1000, description="Mitigation strategy")
    status: RiskStatus = Field(default=RiskStatus.OPEN, description="Current risk status")

    @computed_field
    @property
    def risk_score(self) -> int:
        """Combined risk score (probability x impact). Range: 1-25."""
        return self.probability * self.impact

    @computed_field
    @property
    def risk_level(self) -> str:
        """Qualitative risk level based on risk score."""
        score = self.risk_score
        if score >= 15:
            return "critical"
        if score >= 10:
            return "high"
        if score >= 5:
            return "medium"
        return "low"
