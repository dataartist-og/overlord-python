"""
GitHub Project & Issue Orchestrator MCP Server.

Manages GitHub Projects (v2), Issues, Labels, and automated workflows.
This is the foundational server for all GitHub interactions.
"""

import logging
from typing import Dict, List, Optional

from github import Github, GithubException
from github.Issue import Issue
from github.Label import Label
from github.Project import Project
from github.Repository import Repository
from tenacity import retry, stop_after_attempt, wait_exponential

from overlord.models import BlastRadius, Task

logger = logging.getLogger(__name__)


class GitHubOrchestrator:
    """
    GitHub orchestration service.
    
    Handles all interactions with GitHub API including Projects, Issues,
    Labels, and webhooks. Implements rate limiting, retry logic, and
    blast radius annotation on issues.
    """
    
    def __init__(
        self,
        github_token: str,
        org: str,
        dry_run: bool = False
    ):
        """
        Initialize GitHub orchestrator.
        
        Args:
            github_token: GitHub Personal Access Token
            org: GitHub organization name
            dry_run: If True, log actions without executing
        """
        self.github = Github(github_token)
        self.org_name = org
        self.org = self.github.get_organization(org)
        self.dry_run = dry_run
        
        logger.info(f"Initialized GitHub orchestrator for org: {org}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        blast_radius: Optional[BlastRadius] = None,
    ) -> Optional[Issue]:
        """
        Create a GitHub issue with optional blast radius annotation.
        
        Args:
            repo: Repository name (format: 'owner/repo')
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names
            assignees: List of GitHub usernames
            blast_radius: Optional blast radius to annotate
        
        Returns:
            Created Issue object or None if dry_run
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create issue in {repo}: {title}")
            return None
        
        try:
            repository = self.github.get_repo(repo)
            
            # Append blast radius to body if provided
            full_body = body
            if blast_radius:
                full_body = f"{body}\n\n{blast_radius.to_github_markdown()}"
            
            # Ensure labels exist
            if labels:
                existing_labels = [l.name for l in repository.get_labels()]
                for label_name in labels:
                    if label_name not in existing_labels:
                        self._ensure_label(repository, label_name)
            
            # Create issue
            issue = repository.create_issue(
                title=title,
                body=full_body,
                labels=labels or [],
                assignees=assignees or []
            )
            
            logger.info(f"Created issue #{issue.number} in {repo}: {title}")
            return issue
            
        except GithubException as e:
            logger.error(f"Failed to create issue in {repo}: {e}")
            raise
    
    def create_task_issue(
        self,
        task: Task,
        blast_radius: Optional[BlastRadius] = None
    ) -> Optional[Issue]:
        """
        Create a GitHub issue from a Task object.
        
        Args:
            task: Task object with issue details
            blast_radius: Optional blast radius to include
        
        Returns:
            Created Issue object
        """
        labels = task.labels.copy() if task.labels else []
        labels.extend([
            f"risk:{task.risk.lower()}",
            f"story:{task.story_id}",
            "type:task"
        ])
        
        issue = self.create_issue(
            repo=task.repo,
            title=task.title,
            body=task.to_github_issue_body(),
            labels=labels,
            assignees=task.assignees,
            blast_radius=blast_radius
        )
        
        return issue
    
    def _ensure_label(
        self,
        repository: Repository,
        label_name: str,
        color: str = "0366d6",
        description: str = ""
    ) -> Label:
        """
        Ensure a label exists in the repository.
        
        Args:
            repository: Repository object
            label_name: Label name
            color: Hex color code (without #)
            description: Label description
        
        Returns:
            Label object
        """
        try:
            return repository.get_label(label_name)
        except GithubException:
            # Label doesn't exist, create it
            return repository.create_label(
                name=label_name,
                color=color,
                description=description
            )
    
    def update_issue(
        self,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Optional[Issue]:
        """
        Update an existing GitHub issue.
        
        Args:
            repo: Repository name
            issue_number: Issue number
            title: New title
            body: New body
            state: 'open' or 'closed'
            labels: New labels (replaces existing)
            assignees: New assignees (replaces existing)
        
        Returns:
            Updated Issue object
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update issue #{issue_number} in {repo}")
            return None
        
        try:
            repository = self.github.get_repo(repo)
            issue = repository.get_issue(issue_number)
            
            if title:
                issue.edit(title=title)
            if body:
                issue.edit(body=body)
            if state:
                issue.edit(state=state)
            if labels is not None:
                issue.set_labels(*labels)
            if assignees is not None:
                issue.edit(assignees=assignees)
            
            logger.info(f"Updated issue #{issue_number} in {repo}")
            return issue
            
        except GithubException as e:
            logger.error(f"Failed to update issue #{issue_number} in {repo}: {e}")
            raise
    
    def add_issue_comment(
        self,
        repo: str,
        issue_number: int,
        comment: str
    ) -> None:
        """
        Add a comment to an issue.
        
        Args:
            repo: Repository name
            issue_number: Issue number
            comment: Comment text (markdown)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would comment on issue #{issue_number} in {repo}")
            return
        
        try:
            repository = self.github.get_repo(repo)
            issue = repository.get_issue(issue_number)
            issue.create_comment(comment)
            
            logger.info(f"Added comment to issue #{issue_number} in {repo}")
            
        except GithubException as e:
            logger.error(f"Failed to comment on issue #{issue_number} in {repo}: {e}")
            raise
    
    def link_issues(
        self,
        parent_repo: str,
        parent_issue: int,
        child_repo: str,
        child_issue: int,
        relation: str = "child-of"
    ) -> None:
        """
        Link two issues using comments.
        
        GitHub doesn't have native issue relationships, so we use comments
        with a standardized format.
        
        Args:
            parent_repo: Parent repository name
            parent_issue: Parent issue number
            child_repo: Child repository name
            child_issue: Child issue number
            relation: Relationship type (child-of, blocks, blocked-by, relates-to)
        """
        parent_url = f"https://github.com/{parent_repo}/issues/{parent_issue}"
        child_url = f"https://github.com/{child_repo}/issues/{child_issue}"
        
        # Comment on parent
        self.add_issue_comment(
            parent_repo,
            parent_issue,
            f"🔗 **{relation.title()}**: {child_url}"
        )
        
        # Comment on child
        self.add_issue_comment(
            child_repo,
            child_issue,
            f"🔗 **Parent Story**: {parent_url}"
        )
        
        logger.info(f"Linked {child_url} to {parent_url} ({relation})")
    
    def get_issue(self, repo: str, issue_number: int) -> Optional[Issue]:
        """
        Get an issue by number.
        
        Args:
            repo: Repository name
            issue_number: Issue number
        
        Returns:
            Issue object or None if not found
        """
        try:
            repository = self.github.get_repo(repo)
            return repository.get_issue(issue_number)
        except GithubException as e:
            logger.error(f"Failed to get issue #{issue_number} in {repo}: {e}")
            return None
    
    def list_issues(
        self,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None
    ) -> List[Issue]:
        """
        List issues in a repository.
        
        Args:
            repo: Repository name
            state: 'open', 'closed', or 'all'
            labels: Filter by labels
            assignee: Filter by assignee
        
        Returns:
            List of Issue objects
        """
        try:
            repository = self.github.get_repo(repo)
            issues = repository.get_issues(
                state=state,
                labels=labels or [],
                assignee=assignee or Github.GithubObject.NotSet
            )
            return list(issues)
        except GithubException as e:
            logger.error(f"Failed to list issues in {repo}: {e}")
            return []
    
    def get_rate_limit(self) -> Dict[str, int]:
        """
        Get current API rate limit status.
        
        Returns:
            Dictionary with 'remaining' and 'limit' keys
        """
        rate_limit = self.github.get_rate_limit()
        return {
            "remaining": rate_limit.core.remaining,
            "limit": rate_limit.core.limit,
            "reset": rate_limit.core.reset.isoformat()
        }
    
    def close(self) -> None:
        """Close GitHub connection."""
        self.github.close()
        logger.info("Closed GitHub connection")
