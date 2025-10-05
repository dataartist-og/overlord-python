"""
Task Generator & Linker MCP Server.

Generates repository-specific, testable tasks from stories with blast radius.
"""

import logging
from typing import List, Optional
from uuid import UUID

from overlord.models import (
    BlastRadius,
    ChangeAction,
    ChangeSpec,
    Story,
    Task,
    TaskStatus,
    TestPlan,
)

logger = logging.getLogger(__name__)


class TaskGenerator:
    """
    Generates tasks from stories with detailed implementation plans.
    
    Creates repo-specific tasks with change plans, integration points,
    acceptance criteria, and test strategies derived from the story
    and its blast radius.
    """
    
    def __init__(self):
        """Initialize task generator."""
        logger.info("Initialized TaskGenerator")
    
    def generate_tasks(
        self,
        story: Story,
        repos: List[str],
        include_tests: bool = True
    ) -> List[Task]:
        """
        Generate tasks from a story.
        
        Args:
            story: Source story
            repos: Target repositories
            include_tests: Generate test plans
        
        Returns:
            List of Task objects
        """
        logger.info(f"Generating tasks for story: {story.title}")
        
        if not story.blast_radius:
            logger.warning("Story has no blast radius - generating basic tasks")
            return self._generate_basic_tasks(story, repos, include_tests)
        
        tasks = []
        
        # Generate tasks based on blast radius
        impacted_repos = self._get_impacted_repos(story.blast_radius, repos)
        
        for repo in impacted_repos:
            task = self._generate_repo_task(
                story, repo, story.blast_radius, include_tests
            )
            if task:
                tasks.append(task)
        
        # If no repos were impacted, create at least one task
        if not tasks and repos:
            task = self._generate_repo_task(
                story, repos[0], story.blast_radius, include_tests
            )
            if task:
                tasks.append(task)
        
        logger.info(f"Generated {len(tasks)} tasks")
        return tasks
    
    def _generate_repo_task(
        self,
        story: Story,
        repo: str,
        blast_radius: BlastRadius,
        include_tests: bool
    ) -> Optional[Task]:
        """Generate a task for a specific repository."""
        
        # Extract repo-specific impacts
        repo_modules = [
            m for m in blast_radius.modules if m.startswith(repo)
        ]
        
        # Create change plan
        change_plan = self._create_change_plan(
            repo_modules, blast_radius
        )
        
        # Extract integration points
        integration_points = self._extract_integration_points(
            blast_radius, repo
        )
        
        # Create test plan
        test_plan = TestPlan()
        if include_tests:
            test_plan = self._create_test_plan(
                story, blast_radius, repo
            )
        
        # Generate description
        description = self._generate_description(
            story, blast_radius, repo
        )
        
        # Create branch hint
        branch_hint = f"feature/{story.id}-{repo.split('/')[-1]}"
        
        task = Task(
            story_id=story.id,
            repo=repo,
            branch_hint=branch_hint,
            title=f"[{repo.split('/')[-1]}] {story.title}",
            description_md=description,
            change_plan=change_plan,
            integration_points=integration_points,
            acceptance_criteria=story.acceptance_criteria.copy(),
            test_plan=test_plan,
            risk=story.risk,
            estimate=story.estimate,
            status=TaskStatus.BACKLOG,
            labels=[f"story:{story.id}", "type:task"]
        )
        
        return task
    
    def _generate_basic_tasks(
        self,
        story: Story,
        repos: List[str],
        include_tests: bool
    ) -> List[Task]:
        """Generate basic tasks without blast radius."""
        tasks = []
        
        for repo in repos[:1]:  # Just first repo for now
            test_plan = TestPlan()
            if include_tests:
                test_plan.unit = [
                    "Test happy path functionality",
                    "Test error handling",
                    "Test edge cases"
                ]
            
            task = Task(
                story_id=story.id,
                repo=repo,
                title=f"[{repo.split('/')[-1]}] {story.title}",
                description_md=f"## Story\n\n{story.user_value}\n\n## Implementation\n\nTODO: Define implementation details",
                acceptance_criteria=story.acceptance_criteria.copy(),
                test_plan=test_plan,
                risk=story.risk,
                estimate=story.estimate,
                status=TaskStatus.BACKLOG,
                labels=[f"story:{story.id}", "type:task"]
            )
            tasks.append(task)
        
        return tasks
    
    def _get_impacted_repos(
        self,
        blast_radius: BlastRadius,
        available_repos: List[str]
    ) -> List[str]:
        """Determine which repos are impacted."""
        impacted = set()
        
        # Check modules
        for module in blast_radius.modules:
            for repo in available_repos:
                if module.startswith(repo):
                    impacted.add(repo)
        
        # Check systems
        for system in blast_radius.systems:
            for repo in available_repos:
                if system in repo or repo.split('/')[-1] in system:
                    impacted.add(repo)
        
        return list(impacted)
    
    def _create_change_plan(
        self,
        modules: List[str],
        blast_radius: BlastRadius
    ) -> List[ChangeSpec]:
        """Create file change plan from blast radius."""
        changes = []
        
        # Add/edit impacted modules
        for module in modules:
            # Extract file path (remove repo prefix)
            path = module.split('/', 1)[-1] if '/' in module else module
            
            changes.append(ChangeSpec(
                action=ChangeAction.EDIT,
                path=path,
                description="Update based on story requirements"
            ))
        
        # Add new files for new interfaces
        for interface in blast_radius.interfaces:
            if "new" in interface.lower():
                # Guess a reasonable path
                path = f"handlers/{interface.lower().replace(' ', '_')}.py"
                changes.append(ChangeSpec(
                    action=ChangeAction.ADD,
                    path=path,
                    description=f"New handler for {interface}"
                ))
        
        return changes
    
    def _extract_integration_points(
        self,
        blast_radius: BlastRadius,
        repo: str
    ) -> List[str]:
        """Extract integration points relevant to this repo."""
        points = []
        
        # Add API interfaces
        points.extend(blast_radius.interfaces)
        
        # Add database objects
        points.extend([f"db.{obj}" for obj in blast_radius.db_objects])
        
        # Add message queues
        points.extend([f"queue.{q}" for q in blast_radius.queues])
        
        return points
    
    def _create_test_plan(
        self,
        story: Story,
        blast_radius: BlastRadius,
        repo: str
    ) -> TestPlan:
        """Generate test plan based on story and blast radius."""
        test_plan = TestPlan()
        
        # Unit tests for modules
        if blast_radius.modules:
            test_plan.unit = [
                f"Test {module.split('/')[-1]} functionality"
                for module in blast_radius.modules[:3]
            ]
        else:
            test_plan.unit = [
                "Test core functionality",
                "Test error handling",
                "Test edge cases"
            ]
        
        # Contract tests for APIs
        if blast_radius.interfaces:
            test_plan.contract = [
                f"Test {interface} contract"
                for interface in blast_radius.interfaces[:2]
            ]
        
        # E2E tests for critical flows
        if story.priority in ["P0", "P1"]:
            test_plan.e2e = [
                f"Test complete {story.title} flow",
                "Test error scenarios end-to-end"
            ]
        
        return test_plan
    
    def _generate_description(
        self,
        story: Story,
        blast_radius: BlastRadius,
        repo: str
    ) -> str:
        """Generate task description with context."""
        lines = [
            f"## Story Context\n",
            f"{story.user_value}\n",
            f"## Implementation for {repo}\n",
        ]
        
        if blast_radius.modules:
            repo_modules = [m for m in blast_radius.modules if m.startswith(repo)]
            if repo_modules:
                lines.append("### Impacted Modules")
                for module in repo_modules:
                    lines.append(f"- {module}")
                lines.append("")
        
        if blast_radius.interfaces:
            lines.append("### API Changes")
            for interface in blast_radius.interfaces:
                lines.append(f"- {interface}")
            lines.append("")
        
        if blast_radius.db_objects:
            lines.append("### Database Changes")
            for obj in blast_radius.db_objects:
                lines.append(f"- {obj}")
            lines.append("")
        
        lines.append("## Implementation Guidance\n")
        lines.append("1. Review the blast radius above to understand full impact")
        lines.append("2. Implement changes following acceptance criteria")
        lines.append("3. Ensure all integration points are properly tested")
        lines.append("4. Update documentation for any API changes")
        
        return "\n".join(lines)
