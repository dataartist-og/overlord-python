"""
Plan Decomposer & Story Mapper MCP Server.

Transforms high-level product plans into structured story trees using LLM.
"""

import json
import logging
from typing import Dict, List, Optional

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from overlord.models import (
    CreateStoryRequest,
    Plan,
    PlanConstraint,
    PlanObjective,
    PlanRisk,
    Priority,
    RiskLevel,
    Story,
)

logger = logging.getLogger(__name__)


class PlanDecomposer:
    """
    Plan decomposition service using Claude LLM.
    
    Parses product plans and generates structured story trees with
    acceptance criteria and estimates.
    """
    
    def __init__(self, anthropic_api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize plan decomposer.
        
        Args:
            anthropic_api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = Anthropic(api_key=anthropic_api_key)
        self.model = model
        logger.info(f"Initialized PlanDecomposer with model: {model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def parse_plan(self, plan: Plan) -> Plan:
        """
        Parse a plan and extract objectives, constraints, and risks.
        
        Args:
            plan: Plan object with raw text
        
        Returns:
            Updated Plan with parsed elements
        """
        prompt = self._build_parse_prompt(plan.text, plan.context)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            result_text = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:].strip()
            
            parsed = json.loads(result_text)
            
            # Map to Plan model
            plan.objectives = [
                PlanObjective(**obj) for obj in parsed.get("objectives", [])
            ]
            plan.constraints = [
                PlanConstraint(**c) for c in parsed.get("constraints", [])
            ]
            plan.risks = [
                PlanRisk(**r) for r in parsed.get("risks", [])
            ]
            plan.stakeholders = parsed.get("stakeholders", [])
            
            logger.info(f"Parsed plan: {len(plan.objectives)} objectives, "
                       f"{len(plan.constraints)} constraints, {len(plan.risks)} risks")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to parse plan: {e}")
            plan.processing_error = str(e)
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def generate_stories(
        self,
        plan: Plan,
        max_stories: int = 20
    ) -> List[Story]:
        """
        Generate stories from parsed plan objectives.
        
        Args:
            plan: Parsed plan with objectives
            max_stories: Maximum number of stories to generate
        
        Returns:
            List of Story objects
        """
        if not plan.objectives:
            raise ValueError("Plan must be parsed before generating stories")
        
        prompt = self._build_story_generation_prompt(plan, max_stories)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse JSON response
            result_text = response.content[0].text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:].strip()
            
            parsed = json.loads(result_text)
            
            # Convert to Story objects
            stories = []
            for story_data in parsed.get("stories", []):
                story = Story(
                    title=story_data["title"],
                    user_value=story_data["user_value"],
                    acceptance_criteria=story_data.get("acceptance_criteria", []),
                    risk=RiskLevel[story_data.get("risk", "MEDIUM").upper()],
                    priority=Priority[story_data.get("priority", "P2")],
                    estimate=story_data.get("estimate"),
                )
                stories.append(story)
            
            logger.info(f"Generated {len(stories)} stories from plan")
            return stories
            
        except Exception as e:
            logger.error(f"Failed to generate stories: {e}")
            raise
    
    def generate_acceptance_criteria(
        self,
        story: Story,
        count: int = 5
    ) -> List[str]:
        """
        Generate acceptance criteria for a story.
        
        Args:
            story: Story object
            count: Number of AC to generate
        
        Returns:
            List of acceptance criteria strings
        """
        prompt = f"""Generate {count} specific, testable acceptance criteria for this user story.

Story: {story.title}
User Value: {story.user_value}

Format each as: "Given [context], When [action], Then [outcome]"

Respond with ONLY a JSON array of strings, like:
["Given...", "Given...", ...]
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:].strip()
            
            ac_list = json.loads(result_text)
            logger.info(f"Generated {len(ac_list)} AC for story: {story.title}")
            return ac_list
            
        except Exception as e:
            logger.error(f"Failed to generate AC: {e}")
            return []
    
    def _build_parse_prompt(self, plan_text: str, context: Dict) -> str:
        """Build prompt for plan parsing."""
        return f"""Analyze this product plan and extract structured information.

Plan:
{plan_text}

Context:
- Organization: {context.get('org', 'Unknown')}
- Repositories: {', '.join(context.get('repos', []))}
- Additional constraints: {context.get('constraints', [])}

Extract the following and respond with ONLY valid JSON (no markdown, no explanation):

{{
  "objectives": [
    {{
      "title": "Clear objective title",
      "description": "Detailed description",
      "success_metrics": ["metric1", "metric2"],
      "priority": "P0|P1|P2|P3"
    }}
  ],
  "constraints": [
    {{
      "type": "technical|business|timeline|resource",
      "description": "Constraint description"
    }}
  ],
  "risks": [
    {{
      "description": "Risk description",
      "likelihood": "Low|Medium|High",
      "impact": "Low|Medium|High",
      "mitigation": "Mitigation strategy (optional)"
    }}
  ],
  "stakeholders": ["stakeholder1", "stakeholder2"]
}}

Focus on extracting concrete, actionable objectives. Identify technical and business constraints.
Assess risks realistically based on the plan's scope and complexity.
"""
    
    def _build_story_generation_prompt(self, plan: Plan, max_stories: int) -> str:
        """Build prompt for story generation."""
        objectives_text = "\n".join([
            f"- {obj.title}: {obj.description}" for obj in plan.objectives
        ])
        
        constraints_text = "\n".join([
            f"- [{c.type}] {c.description}" for c in plan.constraints
        ])
        
        return f"""Generate user stories from these product objectives.

Objectives:
{objectives_text}

Constraints:
{constraints_text}

Generate up to {max_stories} user stories following these guidelines:

1. Each story must provide independent user value
2. Use format: "As a [role], I want [feature], so that [benefit]"
3. Stories should be small enough to complete in 3-10 days
4. Include 3-5 acceptance criteria per story (Given-When-Then format)
5. Assess risk level (Low/Medium/High) based on:
   - Technical complexity
   - Dependencies on other systems
   - Potential for breaking changes
6. Assign priority (P0-P3) based on business value
7. Provide rough estimate (e.g., "3-5d", "1-2w")

Respond with ONLY valid JSON (no markdown, no explanation):

{{
  "stories": [
    {{
      "title": "Short story title",
      "user_value": "As a [role], I want [feature], so that [benefit]",
      "acceptance_criteria": [
        "Given [context], When [action], Then [outcome]",
        "Given [context], When [action], Then [outcome]",
        "Given [context], When [action], Then [outcome]"
      ],
      "risk": "Low|Medium|High",
      "priority": "P0|P1|P2|P3",
      "estimate": "3-5d"
    }}
  ]
}}

Ensure stories are atomic, testable, and independently deliverable.
"""
