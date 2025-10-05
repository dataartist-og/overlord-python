"""
Enhanced Blast Radius Engine.

Integrates framework-aware code intelligence with existing blast radius computation
for comprehensive impact analysis.
"""

import logging
from typing import Dict, List, Optional, Set

from overlord.code_intelligence.graph_builder import CodeGraphBuilder
from overlord.models import BlastRadius, Story

logger = logging.getLogger(__name__)


class EnhancedBlastRadiusEngine:
    """
    Enhanced blast radius computation with framework awareness.
    
    Combines:
    - Static code analysis (AST)
    - Framework-aware patterns (routes, DI, jobs)
    - Dependency graphs (NetworkX)
    - Historical data (past breakages)
    """
    
    def __init__(
        self,
        graph_builders: Dict[str, CodeGraphBuilder],
        historical_data: Optional[Dict] = None
    ):
        """
        Initialize enhanced blast radius engine.
        
        Args:
            graph_builders: Dictionary of repo_name -> CodeGraphBuilder
            historical_data: Optional historical breakage data
        """
        self.graph_builders = graph_builders
        self.historical_data = historical_data or {}
        logger.info("Initialized EnhancedBlastRadiusEngine")
    
    def compute_enhanced_blast_radius(
        self,
        story: Story,
        repos: List[str],
        depth: int = 3
    ) -> BlastRadius:
        """
        Compute enhanced blast radius with framework awareness.
        
        Args:
            story: Story to analyze
            repos: List of repositories to analyze
            depth: Dependency traversal depth
        
        Returns:
            Enhanced BlastRadius object
        """
        logger.info(f"Computing enhanced blast radius for: {story.title}")
        
        blast_radius = BlastRadius()
        
        # Extract keywords and potential module names from story
        keywords = self._extract_keywords_from_story(story)
        
        for repo in repos:
            if repo not in self.graph_builders:
                blast_radius.gaps.append(f"Repository {repo} not available for analysis")
                continue
            
            builder = self.graph_builders[repo]
            
            # Find impacted symbols based on keywords
            impacted_symbols = self._find_impacted_symbols(builder, keywords)
            
            if not impacted_symbols:
                continue
            
            # Get comprehensive impact set
            impact_set = builder.get_impact_set(impacted_symbols, depth)
            
            # Categorize traditional impacts
            self._add_traditional_impacts(blast_radius, impact_set, repo, builder)
            
            # Add framework-aware impacts
            self._add_framework_impacts(blast_radius, impact_set, repo, builder)
            
            # Add test coverage info
            self._add_test_coverage(blast_radius, impact_set, repo, builder)
            
            # Add historical context
            self._add_historical_context(blast_radius, impacted_symbols, repo)
        
        # Calculate enhanced confidence
        blast_radius.confidence = self._calculate_enhanced_confidence(
            blast_radius, len(repos), len(keywords)
        )
        
        # Add metadata
        blast_radius.metadata.update({
            "analyzer": "enhanced",
            "framework_aware": "true",
            "analysis_depth": str(depth),
            "repos_analyzed": str(len(repos))
        })
        
        logger.info(
            f"Enhanced blast radius: {blast_radius.total_impact_count} items, "
            f"confidence: {blast_radius.confidence:.2%}, "
            f"risk: {blast_radius.risk_level}"
        )
        
        return blast_radius
    
    def _extract_keywords_from_story(self, story: Story) -> Set[str]:
        """Extract relevant keywords from story text."""
        import re
        
        keywords = set()
        text = f"{story.title} {story.user_value}"
        
        # Common patterns for module/feature names
        patterns = [
            r'\b(user|auth|payment|order|product|admin|api|service)\w*\b',
            r'\b(login|register|checkout|cart|profile|dashboard)\b',
            r'\b(create|update|delete|get|list|search)\w*\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.update(m.lower() for m in matches)
        
        return keywords
    
    def _find_impacted_symbols(
        self,
        builder: CodeGraphBuilder,
        keywords: Set[str]
    ) -> List[str]:
        """Find symbols that match keywords."""
        impacted = []
        
        for symbol_id, symbol in builder.symbols.items():
            symbol_lower = symbol.name.lower()
            if any(keyword in symbol_lower for keyword in keywords):
                impacted.append(symbol_id)
        
        return impacted
    
    def _add_traditional_impacts(
        self,
        blast_radius: BlastRadius,
        impact_set: Dict,
        repo: str,
        builder: CodeGraphBuilder
    ) -> None:
        """Add traditional blast radius impacts (systems, modules, interfaces)."""
        # Systems
        if repo not in blast_radius.systems:
            blast_radius.systems.append(repo)
        
        # Modules (files)
        for file_path in impact_set["files"]:
            module = f"{repo}/{file_path}"
            if module not in blast_radius.modules:
                blast_radius.modules.append(module)
        
        # Symbols as modules
        for symbol_id in impact_set["symbols"][:20]:  # Limit to top 20
            if symbol_id not in blast_radius.modules:
                blast_radius.modules.append(symbol_id)
    
    def _add_framework_impacts(
        self,
        blast_radius: BlastRadius,
        impact_set: Dict,
        repo: str,
        builder: CodeGraphBuilder
    ) -> None:
        """Add framework-aware impacts (routes, DI, jobs)."""
        # Routes affected
        for route_id in impact_set["routes"]:
            if route_id in builder.routes:
                route = builder.routes[route_id]
                interface = f"{route.method} {route.path}"
                if interface not in blast_radius.interfaces:
                    blast_radius.interfaces.append(interface)
        
        # DI consumers (services affected)
        for consumer in impact_set["di_consumers"]:
            if consumer not in blast_radius.modules:
                blast_radius.modules.append(f"{repo}/DI:{consumer}")
        
        # Add database impacts (heuristic)
        for symbol_id in impact_set["symbols"]:
            if any(term in symbol_id.lower() for term in ["repository", "model", "entity"]):
                # Likely database interaction
                parts = symbol_id.split("::")
                if len(parts) > 1:
                    entity_name = parts[-1].replace("Repository", "").replace("Model", "")
                    table_name = entity_name.lower() + "s"
                    if table_name not in blast_radius.db_objects:
                        blast_radius.db_objects.append(table_name)
    
    def _add_test_coverage(
        self,
        blast_radius: BlastRadius,
        impact_set: Dict,
        repo: str,
        builder: CodeGraphBuilder
    ) -> None:
        """Add test coverage information to metadata."""
        test_files = [f for f in impact_set["files"] if "test" in f.lower()]
        
        blast_radius.metadata["tests_affected"] = str(len(test_files))
        
        if len(test_files) == 0:
            blast_radius.gaps.append("No tests found for impacted code")
    
    def _add_historical_context(
        self,
        blast_radius: BlastRadius,
        impacted_symbols: List[str],
        repo: str
    ) -> None:
        """Add historical breakage context."""
        if not self.historical_data:
            return
        
        breakages = []
        for symbol_id in impacted_symbols:
            key = f"{repo}:{symbol_id}"
            if key in self.historical_data:
                breakages.extend(self.historical_data[key])
        
        if breakages:
            blast_radius.metadata["past_breakages_count"] = str(len(breakages))
            blast_radius.metadata["last_breakage"] = breakages[0].get("date", "unknown")
    
    def _calculate_enhanced_confidence(
        self,
        blast_radius: BlastRadius,
        repo_count: int,
        keyword_count: int
    ) -> float:
        """Calculate enhanced confidence score."""
        confidence = 0.5  # Base
        
        # Increase for finding impacts
        if blast_radius.total_impact_count > 0:
            confidence += 0.15
        
        # Increase for framework awareness
        if len(blast_radius.interfaces) > 0:
            confidence += 0.1  # Found routes
        
        if len(blast_radius.db_objects) > 0:
            confidence += 0.05  # Found DB impacts
        
        # Increase for analyzing multiple repos
        if repo_count > 1:
            confidence += 0.1
        
        # Increase for having good keywords
        if keyword_count > 2:
            confidence += 0.05
        
        # Decrease for gaps
        confidence -= 0.05 * len(blast_radius.gaps)
        
        # Increase for diverse impact types
        categories = sum([
            len(blast_radius.systems) > 0,
            len(blast_radius.modules) > 3,
            len(blast_radius.interfaces) > 0,
            len(blast_radius.db_objects) > 0
        ])
        confidence += 0.05 * categories
        
        return max(0.3, min(0.95, confidence))
    
    def get_detailed_impact_report(
        self,
        story: Story,
        repos: List[str],
        depth: int = 3
    ) -> Dict:
        """
        Get detailed impact report with recommendations.
        
        Args:
            story: Story to analyze
            repos: List of repositories
            depth: Analysis depth
        
        Returns:
            Detailed impact report dictionary
        """
        blast_radius = self.compute_enhanced_blast_radius(story, repos, depth)
        
        # Generate recommendations
        recommendations = []
        
        if blast_radius.risk_level == "High":
            recommendations.append(
                "⚠️ HIGH RISK: Consider breaking into smaller stories"
            )
        
        if len(blast_radius.interfaces) > 5:
            recommendations.append(
                "⚠️ Many API endpoints affected - update API documentation"
            )
        
        if len(blast_radius.db_objects) > 0:
            recommendations.append(
                "⚠️ Database changes required - prepare migration scripts"
            )
        
        if blast_radius.gaps:
            recommendations.append(
                f"⚠️ Analysis gaps: {', '.join(blast_radius.gaps[:3])}"
            )
        
        if blast_radius.metadata.get("tests_affected") == "0":
            recommendations.append(
                "⚠️ No tests found - add test coverage before implementation"
            )
        
        return {
            "blast_radius": blast_radius,
            "summary": {
                "total_impact": blast_radius.total_impact_count,
                "risk_level": blast_radius.risk_level,
                "confidence": blast_radius.confidence,
                "systems": len(blast_radius.systems),
                "modules": len(blast_radius.modules),
                "apis": len(blast_radius.interfaces),
                "databases": len(blast_radius.db_objects),
            },
            "recommendations": recommendations,
            "next_steps": [
                "Review impacted modules for breaking changes",
                "Update tests for affected code paths",
                "Document API changes if any",
                "Plan deployment strategy based on risk level",
            ]
        }
