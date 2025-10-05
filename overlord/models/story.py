"""
Story data models.

A Story represents an end-user value increment with acceptance criteria
and computed blast radius.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .blast_radius import BlastRadius


class Priority(str, Enum):
    """Story priority levels."""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class RiskLevel(str, Enum):
    """Risk levels for stories and tasks."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class StoryStatus(str, Enum):
    """Story workflow states."""
    BACKLOG = "Backlog"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"


class Story(BaseModel):
    """
    Represents a user story with acceptance criteria and blast radius.
    
    Stories are atomic units of user value that can be independently
    implemented, tested, and delivered.
    """
    
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=200)
    user_value: str = Field(
        ...,
        description="User value statement (As a X, I want Y, so that Z)",
        min_length=10
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of acceptance criteria (AC)"
    )
    blast_radius: Optional[BlastRadius] = Field(
        None,
        description="Computed blast radius for this story"
    )
    epic_ids: List[UUID] = Field(
        default_factory=list,
        description="Parent epic IDs"
    )
    task_ids: List[UUID] = Field(
        default_factory=list,
        description="Child task IDs"
    )
    risk: RiskLevel = Field(default=RiskLevel.MEDIUM)
    priority: Priority = Field(default=Priority.P2)
    estimate: Optional[str] = Field(None, description="Effort estimate (e.g., '3-5d', '8 points')")
    status: StoryStatus = Field(default=StoryStatus.BACKLOG)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    
    def to_github_issue_body(self) -> str:
        """
        Generate GitHub issue body with story details and blast radius.
        
        Returns:
            Formatted markdown for GitHub issue
        """
        lines = []
        
        # User value
        lines.append("## 📚 Story")
        lines.append("")
        lines.append(self.user_value)
        lines.append("")
        
        # Acceptance criteria
        lines.append("## ✅ Acceptance Criteria")
        lines.append("")
        for i, ac in enumerate(self.acceptance_criteria, 1):
            lines.append(f"{i}. {ac}")
        lines.append("")
        
        # Blast radius
        if self.blast_radius:
            lines.append(self.blast_radius.to_github_markdown())
        
        # Metadata
        lines.append("---")
        lines.append("")
        lines.append(f"**Priority**: {self.priority} | **Risk**: {self.risk} | **Estimate**: {self.estimate or 'TBD'}")
        lines.append(f"**Story ID**: `{self.id}`")
        
        return "\n".join(lines)


class CreateStoryRequest(BaseModel):
    """Request to create a new story."""
    
    title: str = Field(..., min_length=1, max_length=200)
    user_value: str = Field(..., min_length=10)
    acceptance_criteria: Optional[List[str]] = None
    epic_ids: Optional[List[UUID]] = None
    risk: Optional[RiskLevel] = None
    priority: Optional[Priority] = None
    estimate: Optional[str] = None
    compute_blast_radius: bool = Field(
        default=True,
        description="Automatically compute blast radius"
    )


class UpdateStoryRequest(BaseModel):
    """Request to update an existing story."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    user_value: Optional[str] = Field(None, min_length=10)
    acceptance_criteria: Optional[List[str]] = None
    risk: Optional[RiskLevel] = None
    priority: Optional[Priority] = None
    estimate: Optional[str] = None
    status: Optional[StoryStatus] = None


class StoryList(BaseModel):
    """List of stories with pagination."""
    
    stories: List[Story]
    total: int
    page: int = 1
    page_size: int = 50
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size