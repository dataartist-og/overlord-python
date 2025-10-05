"""
Plan data models.

A Plan is a high-level product description that gets decomposed into stories.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PlanObjective(BaseModel):
    """An objective extracted from a plan."""
    
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    success_metrics: List[str] = Field(default_factory=list)
    priority: str = Field(default="P2")


class PlanConstraint(BaseModel):
    """A constraint or limitation in the plan."""
    
    type: str = Field(..., description="technical, business, timeline, or resource")
    description: str


class PlanRisk(BaseModel):
    """A risk identified in the plan."""
    
    description: str
    likelihood: str = Field(..., description="Low, Medium, or High")
    impact: str = Field(..., description="Low, Medium, or High")
    mitigation: Optional[str] = None


class Plan(BaseModel):
    """
    Represents a product plan submitted for decomposition.
    
    Plans are parsed and decomposed into structured objectives, constraints,
    and risks, then further broken down into stories and tasks.
    """
    
    id: UUID = Field(default_factory=uuid4)
    text: str = Field(..., min_length=10, description="Raw plan text (markdown or plain text)")
    context: Dict[str, any] = Field(
        default_factory=dict,
        description="Additional context (org, repos, constraints, etc.)"
    )
    
    # Parsed elements
    objectives: List[PlanObjective] = Field(default_factory=list)
    constraints: List[PlanConstraint] = Field(default_factory=list)
    risks: List[PlanRisk] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)
    
    # Generated stories
    story_ids: List[UUID] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")
    processed: bool = Field(default=False)
    processing_error: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class CreatePlanRequest(BaseModel):
    """Request to create and process a new plan."""
    
    text: str = Field(..., min_length=10)
    context: Optional[Dict[str, any]] = Field(
        default_factory=dict,
        description="Context: org, repos, existing_initiatives, constraints"
    )
    auto_generate_stories: bool = Field(
        default=True,
        description="Automatically generate stories from plan"
    )
    compute_blast_radius: bool = Field(
        default=True,
        description="Compute blast radius for generated stories"
    )


class PlanResponse(BaseModel):
    """Response after processing a plan."""
    
    plan: Plan
    stories_created: int = 0
    github_issues_created: int = 0
    processing_time_ms: float = 0.0
