"""
Overlord FastAPI Application.

Main entry point for the Overlord API server.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from overlord.config import get_settings, setup_logging
from overlord.mcp_servers.github_orchestrator import GitHubOrchestrator
from overlord.mcp_servers.impact_analyzer import ImpactAnalyzer
from overlord.mcp_servers.plan_decomposer import PlanDecomposer
from overlord.mcp_servers.task_generator import TaskGenerator
from overlord.models import (
    BlastRadiusRequest,
    BlastRadiusResponse,
    CreatePlanRequest,
    CreateStoryRequest,
    GenerateTasksRequest,
    Plan,
    PlanResponse,
    Story,
    StoryList,
    Task,
    TaskList,
)

# Initialize settings and logging
settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)

# In-memory storage (replace with database in production)
plans_db: dict[UUID, Plan] = {}
stories_db: dict[UUID, Story] = {}
tasks_db: dict[UUID, Task] = {}

# Initialize MCP servers
github_orchestrator: Optional[GitHubOrchestrator] = None
plan_decomposer: Optional[PlanDecomposer] = None
impact_analyzer: Optional[ImpactAnalyzer] = None
task_generator: Optional[TaskGenerator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global github_orchestrator, plan_decomposer, impact_analyzer, task_generator
    
    # Startup
    logger.info("Starting Overlord server...")
    
    try:
        github_orchestrator = GitHubOrchestrator(
            github_token=settings.github_token,
            org=settings.github_org,
            dry_run=settings.dry_run
        )
        logger.info("✓ GitHub Orchestrator initialized")
    except Exception as e:
        logger.error(f"Failed to initialize GitHub Orchestrator: {e}")
    
    if settings.anthropic_api_key:
        try:
            plan_decomposer = PlanDecomposer(
                anthropic_api_key=settings.anthropic_api_key,
                model=settings.llm_model
            )
            logger.info("✓ Plan Decomposer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Plan Decomposer: {e}")
    else:
        logger.warning("ANTHROPIC_API_KEY not set - Plan Decomposer disabled")
    
    impact_analyzer = ImpactAnalyzer(repo_paths=settings.repo_paths)
    logger.info("✓ Impact Analyzer initialized")
    
    task_generator = TaskGenerator()
    logger.info("✓ Task Generator initialized")
    
    logger.info("Overlord server started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Overlord server...")
    if github_orchestrator:
        github_orchestrator.close()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autopoiesis PM/Eng Multi-Agent System",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "services": {
            "github": github_orchestrator is not None,
            "plan_decomposer": plan_decomposer is not None,
            "impact_analyzer": impact_analyzer is not None,
            "task_generator": task_generator is not None,
        }
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Overlord API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# Plan Endpoints
# ============================================================================

@app.post("/api/v1/plans", response_model=PlanResponse)
async def create_plan(request: CreatePlanRequest):
    """
    Create and process a product plan.
    
    This endpoint:
    1. Parses the plan to extract objectives, constraints, and risks
    2. Optionally generates stories from objectives
    3. Optionally computes blast radius for each story
    """
    if not plan_decomposer:
        raise HTTPException(
            status_code=503,
            detail="Plan Decomposer not available (ANTHROPIC_API_KEY not set)"
        )
    
    start_time = time.time()
    
    # Create plan
    plan = Plan(
        text=request.text,
        context=request.context
    )
    
    try:
        # Parse plan
        plan = plan_decomposer.parse_plan(plan)
        plan.processed = True
        
        # Generate stories if requested
        stories_created = 0
        if request.auto_generate_stories:
            stories = plan_decomposer.generate_stories(plan)
            
            for story in stories:
                # Compute blast radius if requested
                if request.compute_blast_radius and impact_analyzer:
                    repos = request.context.get("repos", [])
                    if repos:
                        blast_radius = impact_analyzer.compute_blast_radius(
                            story, repos, depth=3
                        )
                        story.blast_radius = blast_radius
                
                stories_db[story.id] = story
                plan.story_ids.append(story.id)
                stories_created += 1
        
        # Store plan
        plans_db[plan.id] = plan
        
        processing_time = (time.time() - start_time) * 1000
        
        return PlanResponse(
            plan=plan,
            stories_created=stories_created,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Failed to process plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/plans/{plan_id}", response_model=Plan)
async def get_plan(plan_id: UUID):
    """Get plan by ID."""
    plan = plans_db.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# ============================================================================
# Story Endpoints
# ============================================================================

@app.get("/api/v1/stories", response_model=StoryList)
async def list_stories(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """List all stories with pagination."""
    all_stories = list(stories_db.values())
    total = len(all_stories)
    
    start = (page - 1) * page_size
    end = start + page_size
    stories = all_stories[start:end]
    
    return StoryList(
        stories=stories,
        total=total,
        page=page,
        page_size=page_size
    )


@app.get("/api/v1/stories/{story_id}", response_model=Story)
async def get_story(story_id: UUID):
    """Get story by ID with blast radius."""
    story = stories_db.get(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@app.post("/api/v1/stories", response_model=Story)
async def create_story(request: CreateStoryRequest):
    """Create a new story."""
    story = Story(
        title=request.title,
        user_value=request.user_value,
        acceptance_criteria=request.acceptance_criteria or [],
        epic_ids=request.epic_ids or [],
        risk=request.risk or story.risk,
        priority=request.priority or story.priority,
        estimate=request.estimate
    )
    
    # Compute blast radius if requested
    if request.compute_blast_radius and impact_analyzer:
        # Need repos from context - for now skip
        pass
    
    stories_db[story.id] = story
    return story


@app.post("/api/v1/stories/{story_id}/generate-tasks", response_model=TaskList)
async def generate_tasks_for_story(
    story_id: UUID,
    request: GenerateTasksRequest
):
    """
    Generate tasks for a story.
    
    Creates repository-specific tasks with change plans, integration points,
    and test strategies based on the story's blast radius.
    """
    story = stories_db.get(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not task_generator:
        raise HTTPException(status_code=503, detail="Task Generator not available")
    
    # Generate tasks
    tasks = task_generator.generate_tasks(
        story=story,
        repos=request.repos,
        include_tests=request.include_tests
    )
    
    # Create GitHub issues if requested
    github_issues_created = 0
    if request.create_github_issues and github_orchestrator:
        for task in tasks:
            try:
                issue = github_orchestrator.create_task_issue(
                    task=task,
                    blast_radius=story.blast_radius
                )
                if issue:
                    task.github_issue_number = issue.number
                    task.github_url = issue.html_url
                    github_issues_created += 1
            except Exception as e:
                logger.error(f"Failed to create GitHub issue for task {task.id}: {e}")
    
    # Store tasks
    for task in tasks:
        tasks_db[task.id] = task
        if task.id not in story.task_ids:
            story.task_ids.append(task.id)
    
    return TaskList(
        tasks=tasks,
        total=len(tasks),
        page=1,
        page_size=len(tasks)
    )


# ============================================================================
# Task Endpoints
# ============================================================================

@app.get("/api/v1/tasks", response_model=TaskList)
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: Optional[str] = None
):
    """List all tasks with optional filtering."""
    all_tasks = list(tasks_db.values())
    
    # Filter by repo if specified
    if repo:
        all_tasks = [t for t in all_tasks if t.repo == repo]
    
    total = len(all_tasks)
    
    start = (page - 1) * page_size
    end = start + page_size
    tasks = all_tasks[start:end]
    
    return TaskList(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size
    )


@app.get("/api/v1/tasks/{task_id}", response_model=Task)
async def get_task(task_id: UUID):
    """Get task by ID."""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ============================================================================
# Blast Radius Endpoints
# ============================================================================

@app.post("/api/v1/blast-radius/compute", response_model=BlastRadiusResponse)
async def compute_blast_radius(request: BlastRadiusRequest):
    """
    Compute blast radius for a story or code changes.
    
    Analyzes dependencies and identifies all impacted systems,
    modules, interfaces, and databases.
    """
    if not impact_analyzer:
        raise HTTPException(
            status_code=503,
            detail="Impact Analyzer not available"
        )
    
    if request.story_id:
        story = stories_db.get(request.story_id)
        if not story:
            raise HTTPException(status_code=404, detail="Story not found")
        
        blast_radius = impact_analyzer.compute_blast_radius(
            story=story,
            repos=request.repos,
            depth=request.depth
        )
        
        # Update story
        story.blast_radius = blast_radius
        
        return BlastRadiusResponse(
            blast_radius=blast_radius,
            story_id=request.story_id
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either story_id or code_changes must be provided"
        )


@app.get("/api/v1/blast-radius/{story_id}", response_model=BlastRadiusResponse)
async def get_blast_radius(story_id: UUID):
    """Get computed blast radius for a story."""
    story = stories_db.get(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if not story.blast_radius:
        raise HTTPException(
            status_code=404,
            detail="Blast radius not computed for this story"
        )
    
    return BlastRadiusResponse(
        blast_radius=story.blast_radius,
        story_id=story_id
    )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


def main():
    """Main entry point."""
    import uvicorn
    
    uvicorn.run(
        "overlord.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()