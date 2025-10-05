"""
Task data models.

A Task is an atomic, testable unit of work in a specific repository.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .story import RiskLevel


class TaskStatus(str, Enum):
    """Task workflow states."""
    BACKLOG = "Backlog"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"


class ChangeAction(str, Enum):
    """Types of file changes."""
    ADD = "add"
    EDIT = "edit"
    REMOVE = "remove"


class ChangeSpec(BaseModel):
    """Specification for a file change."""
    
    action: ChangeAction
    path: str = Field(..., description="File path relative to repo root")
    description: Optional[str] = Field(None, description="Description of the change")


class TestPlan(BaseModel):
    """Test plan for a task."""
    
    unit: List[str] = Field(default_factory=list, description="Unit test descriptions")
    contract: List[str] = Field(default_factory=list, description="Contract test descriptions")
    e2e: List[str] = Field(default_factory=list, description="End-to-end test descriptions")
    
    @property
    def total_tests(self) -> int:
        """Total number of planned tests."""
        return len(self.unit) + len(self.contract) + len(self.e2e)


class Task(BaseModel):
    """
    Represents an atomic, testable unit of work in a specific repository.
    
    Tasks are created from stories and include detailed implementation
    guidance, change plans, and test strategies.
    """
    
    id: UUID = Field(default_factory=uuid4)
    story_id: UUID = Field(..., description="Parent story ID")
    repo: str = Field(..., description="Repository name (format: 'owner/repo')")
    branch_hint: Optional[str] = Field(None, description="Suggested branch name")
    
    title: str = Field(..., min_length=1, max_length=200)
    description_md: str = Field(..., description="Markdown description")
    
    change_plan: List[ChangeSpec] = Field(
        default_factory=list,
        description="Planned file changes"
    )
    integration_points: List[str] = Field(
        default_factory=list,
        description="Integration points (e.g., 'service-b.api.v2', 'db.orders')"
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Task-specific acceptance criteria"
    )
    test_plan: TestPlan = Field(default_factory=TestPlan)
    
    risk: RiskLevel = Field(default=RiskLevel.MEDIUM)
    estimate: Optional[str] = Field(None, description="Effort estimate")
    
    assignees: List[str] = Field(
        default_factory=list,
        description="Assigned users or agents"
    )
    
    # GitHub integration
    github_issue_number: Optional[int] = None
    github_url: Optional[str] = None
    pr_ids: List[int] = Field(default_factory=list, description="Related PR numbers")
    
    status: TaskStatus = Field(default=TaskStatus.BACKLOG)
    labels: List[str] = Field(default_factory=list)
    
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
    
    def to_github_issue_body(self, include_blast_radius: bool = True) -> str:
        """
        Generate GitHub issue body with task details.
        
        Args:
            include_blast_radius: Include parent story's blast radius
        
        Returns:
            Formatted markdown for GitHub issue
        """
        lines = []
        
        # Description
        lines.append("## 📝 Task Description")
        lines.append("")
        lines.append(self.description_md)
        lines.append("")
        
        # Change Plan
        if self.change_plan:
            lines.append("## 🔧 Change Plan")
            lines.append("")
            for change in self.change_plan:
                icon = {"add": "➕", "edit": "✏️", "remove": "➖"}[change.action]
                lines.append(f"- {icon} **{change.action.upper()}** `{change.path}`")
                if change.description:
                    lines.append(f"  - {change.description}")
            lines.append("")
        
        # Integration Points
        if self.integration_points:
            lines.append("## 🔌 Integration Points")
            lines.append("")
            for point in self.integration_points:
                lines.append(f"- {point}")
            lines.append("")
        
        # Acceptance Criteria
        if self.acceptance_criteria:
            lines.append("## ✅ Acceptance Criteria")
            lines.append("")
            for i, ac in enumerate(self.acceptance_criteria, 1):
                lines.append(f"{i}. {ac}")
            lines.append("")
        
        # Test Plan
        if self.test_plan.total_tests > 0:
            lines.append("## 🧪 Test Plan")
            lines.append("")
            
            if self.test_plan.unit:
                lines.append("### Unit Tests")
                for test in self.test_plan.unit:
                    lines.append(f"- [ ] {test}")
                lines.append("")
            
            if self.test_plan.contract:
                lines.append("### Contract Tests")
                for test in self.test_plan.contract:
                    lines.append(f"- [ ] {test}")
                lines.append("")
            
            if self.test_plan.e2e:
                lines.append("### E2E Tests")
                for test in self.test_plan.e2e:
                    lines.append(f"- [ ] {test}")
                lines.append("")
        
        # Metadata
        lines.append("---")
        lines.append("")
        lines.append(f"**Repo**: {self.repo} | **Risk**: {self.risk} | **Estimate**: {self.estimate or 'TBD'}")
        lines.append(f"**Story ID**: `{self.story_id}` | **Task ID**: `{self.id}`")
        
        return "\n".join(lines)


class CreateTaskRequest(BaseModel):
    """Request to create a new task."""
    
    story_id: UUID
    repo: str
    title: str = Field(..., min_length=1, max_length=200)
    description_md: str
    change_plan: Optional[List[ChangeSpec]] = None
    integration_points: Optional[List[str]] = None
    acceptance_criteria: Optional[List[str]] = None
    test_plan: Optional[TestPlan] = None
    risk: Optional[RiskLevel] = None
    estimate: Optional[str] = None
    create_github_issue: bool = Field(
        default=False,
        description="Automatically create GitHub issue"
    )


class GenerateTasksRequest(BaseModel):
    """Request to generate tasks from a story."""
    
    story_id: UUID
    repos: List[str] = Field(..., description="Target repositories")
    include_tests: bool = Field(default=True, description="Generate test plans")
    create_github_issues: bool = Field(default=False, description="Create GitHub issues")


class TaskList(BaseModel):
    """List of tasks with pagination."""
    
    tasks: List[Task]
    total: int
    page: int = 1
    page_size: int = 50
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.page_size - 1) // self.page_size
