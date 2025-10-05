"""
Tests for blast radius computation.
"""

import pytest

from overlord.models import BlastRadius, Story


def test_blast_radius_creation():
    """Test creating a blast radius."""
    blast_radius = BlastRadius(
        systems=["api-service", "web-app"],
        modules=["api-service/handlers/user.py"],
        interfaces=["/api/v1/users"],
        db_objects=["users"],
        confidence=0.85
    )
    
    assert blast_radius.total_impact_count == 4
    assert blast_radius.risk_level == "Low"
    assert blast_radius.confidence == 0.85


def test_blast_radius_risk_levels():
    """Test risk level calculation."""
    # Low risk
    low_risk = BlastRadius(
        systems=["api-service"],
        modules=["api-service/handlers/user.py"],
        confidence=0.9
    )
    assert low_risk.risk_level == "Low"
    
    # Medium risk
    medium_risk = BlastRadius(
        systems=["api-service", "web-app"],
        modules=["module1", "module2", "module3", "module4", "module5", "module6"],
        confidence=0.8
    )
    assert medium_risk.risk_level == "Medium"
    
    # High risk
    high_risk = BlastRadius(
        systems=["api-service", "web-app", "worker"],
        modules=["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9", "m10"],
        db_objects=["users", "orders"],
        confidence=0.5
    )
    assert high_risk.risk_level == "High"


def test_blast_radius_markdown():
    """Test markdown generation."""
    blast_radius = BlastRadius(
        systems=["api-service"],
        modules=["handlers/user.py"],
        interfaces=["/api/v1/users"],
        confidence=0.9
    )
    
    markdown = blast_radius.to_markdown()
    
    assert "## Blast Radius" in markdown
    assert "api-service" in markdown
    assert "/api/v1/users" in markdown
    assert "90%" in markdown


def test_story_with_blast_radius():
    """Test story with blast radius."""
    story = Story(
        title="Add user export endpoint",
        user_value="As a user, I want to export my data, so I can analyze it offline",
        acceptance_criteria=[
            "Given a logged-in user, When they click Export, Then a CSV downloads"
        ],
        blast_radius=BlastRadius(
            systems=["api-service"],
            modules=["handlers/user.py"],
            interfaces=["/api/v1/users/export"],
            db_objects=["users"],
            confidence=0.85
        )
    )
    
    assert story.blast_radius is not None
    assert story.blast_radius.risk_level == "Low"
    
    # Test GitHub issue body generation
    issue_body = story.to_github_issue_body()
    assert "Blast Radius" in issue_body
    assert story.title in issue_body
    assert story.user_value in issue_body
