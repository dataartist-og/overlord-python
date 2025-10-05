"""
Configuration management for Overlord.
"""

import logging
from functools import lru_cache
from typing import Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Overlord"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # GitHub
    github_token: str = Field(..., alias="GITHUB_TOKEN")
    github_org: str = Field(..., alias="GITHUB_ORG")
    github_api_url: str = Field(
        default="https://api.github.com",
        alias="GITHUB_API_URL"
    )
    
    # LLM Provider
    anthropic_api_key: Optional[str] = Field(None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(
        default="claude-sonnet-4-20250514",
        alias="LLM_MODEL"
    )
    llm_max_tokens: int = Field(default=4000, alias="LLM_MAX_TOKENS")
    
    # Database
    database_url: str = Field(
        default="sqlite:///overlord.db",
        alias="DATABASE_URL"
    )
    
    # Features
    dry_run: bool = Field(default=False, alias="DRY_RUN")
    enable_blast_radius_analysis: bool = Field(
        default=True,
        alias="ENABLE_BLAST_RADIUS_ANALYSIS"
    )
    blast_radius_confidence_threshold: float = Field(
        default=0.7,
        alias="BLAST_RADIUS_CONFIDENCE_THRESHOLD"
    )
    
    # Blast Radius Analysis
    graph_cache_dir: str = Field(
        default="./cache/graphs",
        alias="GRAPH_CACHE_DIR"
    )
    graph_max_nodes: int = Field(default=50000, alias="GRAPH_MAX_NODES")
    graph_max_depth: int = Field(default=5, alias="GRAPH_MAX_DEPTH")
    code_analysis_timeout_sec: int = Field(
        default=300,
        alias="CODE_ANALYSIS_TIMEOUT_SEC"
    )
    
    # Story Configuration
    story_min_ac_count: int = Field(default=2, alias="STORY_MIN_AC_COUNT")
    story_max_ac_count: int = Field(default=7, alias="STORY_MAX_AC_COUNT")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")
    
    # Repository Paths (for local analysis)
    repo_paths: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings object loaded from environment
    """
    return Settings()


def setup_logging(settings: Settings) -> None:
    """
    Configure logging for the application.
    
    Args:
        settings: Settings object with log level
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Set specific loggers
    logging.getLogger("github").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)
