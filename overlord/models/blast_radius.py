"""
Blast Radius data models.

The blast radius represents the minimal connected subgraph of systems, modules,
and interfaces impacted by a change.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BlastRadius(BaseModel):
    """
    Represents the impact surface of a change.
    
    Includes all systems, modules, interfaces, and resources that will be
    affected by implementing a story or task.
    """
    
    systems: List[str] = Field(
        default_factory=list,
        description="Microservices, applications, or infrastructure components"
    )
    modules: List[str] = Field(
        default_factory=list,
        description="Code packages, libraries, or shared utilities"
    )
    interfaces: List[str] = Field(
        default_factory=list,
        description="APIs, message contracts, or integration points"
    )
    contracts: List[str] = Field(
        default_factory=list,
        description="API specification URLs (OpenAPI, GraphQL, Protobuf)"
    )
    db_objects: List[str] = Field(
        default_factory=list,
        description="Database tables, views, stored procedures"
    )
    queues: List[str] = Field(
        default_factory=list,
        description="Message queue topics, subscriptions, channels"
    )
    configs: List[str] = Field(
        default_factory=list,
        description="Environment variables, feature flags, deployment manifests"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of the analysis (0.0-1.0)"
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="Known limitations or gaps in the analysis"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional analysis metadata"
    )
    
    @property
    def total_impact_count(self) -> int:
        """Total number of impacted items across all categories."""
        return (
            len(self.systems) +
            len(self.modules) +
            len(self.interfaces) +
            len(self.db_objects) +
            len(self.queues) +
            len(self.configs)
        )
    
    @property
    def risk_level(self) -> str:
        """
        Determine risk level based on impact count and confidence.
        
        Returns:
            'Low', 'Medium', or 'High'
        """
        if self.total_impact_count == 0:
            return "Low"
        
        # High impact count or low confidence increases risk
        if self.total_impact_count > 10 or self.confidence < 0.6:
            return "High"
        elif self.total_impact_count > 5 or self.confidence < 0.8:
            return "Medium"
        else:
            return "Low"
    
    def to_markdown(self) -> str:
        """
        Generate a markdown summary of the blast radius.
        
        Returns:
            Formatted markdown string
        """
        lines = ["## Blast Radius", ""]
        lines.append(f"**Risk Level**: {self.risk_level}")
        lines.append(f"**Confidence**: {self.confidence:.0%}")
        lines.append(f"**Total Impact**: {self.total_impact_count} items")
        lines.append("")
        
        if self.systems:
            lines.append("### Systems")
            for system in self.systems:
                lines.append(f"- {system}")
            lines.append("")
        
        if self.modules:
            lines.append("### Modules")
            for module in self.modules:
                lines.append(f"- {module}")
            lines.append("")
        
        if self.interfaces:
            lines.append("### Interfaces")
            for interface in self.interfaces:
                lines.append(f"- {interface}")
            lines.append("")
        
        if self.db_objects:
            lines.append("### Database Objects")
            for obj in self.db_objects:
                lines.append(f"- {obj}")
            lines.append("")
        
        if self.queues:
            lines.append("### Message Queues")
            for queue in self.queues:
                lines.append(f"- {queue}")
            lines.append("")
        
        if self.configs:
            lines.append("### Configurations")
            for config in self.configs:
                lines.append(f"- {config}")
            lines.append("")
        
        if self.gaps:
            lines.append("### Known Gaps")
            for gap in self.gaps:
                lines.append(f"- {gap}")
            lines.append("")
        
        return "\n".join(lines)
    
    def to_github_markdown(self) -> str:
        """
        Generate GitHub-flavored markdown for issue body.
        
        Returns:
            Formatted markdown with checkboxes and collapsible sections
        """
        lines = ["## 💥 Blast Radius Analysis", ""]
        lines.append(f"> **Risk Level**: {self.risk_level} | **Confidence**: {self.confidence:.0%}")
        lines.append("")
        
        lines.append("<details>")
        lines.append("<summary>Click to expand blast radius details</summary>")
        lines.append("")
        
        if self.systems:
            lines.append("### 🏢 Impacted Systems")
            for system in self.systems:
                lines.append(f"- [ ] {system}")
            lines.append("")
        
        if self.modules:
            lines.append("### 📦 Impacted Modules")
            for module in self.modules:
                lines.append(f"- [ ] {module}")
            lines.append("")
        
        if self.interfaces:
            lines.append("### 🔌 Impacted Interfaces")
            for interface in self.interfaces:
                lines.append(f"- [ ] {interface}")
            lines.append("")
        
        if self.db_objects:
            lines.append("### 🗄️ Database Changes")
            for obj in self.db_objects:
                lines.append(f"- [ ] {obj}")
            lines.append("")
        
        if self.queues:
            lines.append("### 📮 Message Queues")
            for queue in self.queues:
                lines.append(f"- [ ] {queue}")
            lines.append("")
        
        if self.configs:
            lines.append("### ⚙️ Configuration Changes")
            for config in self.configs:
                lines.append(f"- [ ] {config}")
            lines.append("")
        
        lines.append("</details>")
        lines.append("")
        
        return "\n".join(lines)


class BlastRadiusRequest(BaseModel):
    """Request to compute blast radius for a story or code change."""
    
    story_id: Optional[str] = Field(None, description="Story ID to analyze")
    code_changes: Optional[List[str]] = Field(
        None,
        description="List of file paths that will be changed"
    )
    repos: List[str] = Field(
        default_factory=list,
        description="Repository names to analyze (format: 'owner/repo')"
    )
    depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Dependency traversal depth"
    )


class BlastRadiusResponse(BaseModel):
    """Response containing computed blast radius."""
    
    blast_radius: BlastRadius
    story_id: Optional[str] = None
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    visualization_url: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }