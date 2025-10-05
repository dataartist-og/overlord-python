"""
Impact Analyzer (Blast Radius) MCP Server.

Computes the blast radius - the impact surface of code changes across
systems, modules, interfaces, and databases.
"""

import ast
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from overlord.models import BlastRadius, Story

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Analyzes code dependencies and computes blast radius.
    
    Uses static analysis to build dependency graphs and identify
    all systems, modules, and interfaces affected by changes.
    """
    
    def __init__(self, repo_paths: Optional[Dict[str, str]] = None):
        """
        Initialize impact analyzer.
        
        Args:
            repo_paths: Mapping of repo names to local paths
        """
        self.repo_paths = repo_paths or {}
        self.graphs: Dict[str, nx.DiGraph] = {}
        logger.info("Initialized ImpactAnalyzer")
    
    def compute_blast_radius(
        self,
        story: Story,
        repos: List[str],
        depth: int = 3
    ) -> BlastRadius:
        """
        Compute blast radius for a story.
        
        Args:
            story: Story to analyze
            repos: List of repositories to analyze
            depth: Dependency traversal depth
        
        Returns:
            BlastRadius object with computed impacts
        """
        logger.info(f"Computing blast radius for story: {story.title}")
        
        blast_radius = BlastRadius()
        
        # Extract potential modules/files from story content
        keywords = self._extract_keywords(story)
        
        for repo in repos:
            if repo not in self.graphs:
                self._build_repo_graph(repo)
            
            graph = self.graphs.get(repo)
            if not graph:
                blast_radius.gaps.append(f"Could not analyze repo: {repo}")
                continue
            
            # Find impacted nodes
            impacted_nodes = self._find_impacted_nodes(
                graph, keywords, depth
            )
            
            # Categorize impacts
            self._categorize_impacts(
                impacted_nodes, graph, blast_radius, repo
            )
        
        # Calculate confidence based on analysis completeness
        blast_radius.confidence = self._calculate_confidence(
            blast_radius, len(repos)
        )
        
        blast_radius.metadata = {
            "analyzed_at": "",
            "analyzer_version": "1.0.0",
            "repos_analyzed": str(len(repos))
        }
        
        logger.info(f"Blast radius computed: {blast_radius.total_impact_count} items, "
                   f"confidence: {blast_radius.confidence:.2%}")
        
        return blast_radius
    
    def _build_repo_graph(self, repo: str) -> None:
        """
        Build dependency graph for a repository.
        
        Args:
            repo: Repository name
        """
        repo_path = self.repo_paths.get(repo)
        if not repo_path or not Path(repo_path).exists():
            logger.warning(f"Repo path not found for {repo}")
            return
        
        graph = nx.DiGraph()
        
        # Analyze Python files
        for py_file in Path(repo_path).rglob("*.py"):
            self._analyze_python_file(py_file, graph, repo)
        
        # Analyze JavaScript/TypeScript files
        for js_file in Path(repo_path).rglob("*.{js,ts,jsx,tsx}"):
            self._analyze_js_file(js_file, graph, repo)
        
        # Analyze API specs
        for spec_file in Path(repo_path).rglob("*.{yaml,yml,json}"):
            if "openapi" in spec_file.name.lower() or "swagger" in spec_file.name.lower():
                self._analyze_openapi_spec(spec_file, graph, repo)
        
        self.graphs[repo] = graph
        logger.info(f"Built graph for {repo}: {graph.number_of_nodes()} nodes, "
                   f"{graph.number_of_edges()} edges")
    
    def _analyze_python_file(
        self, file_path: Path, graph: nx.DiGraph, repo: str
    ) -> None:
        """Analyze Python file and add to graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            module_path = str(file_path.relative_to(self.repo_paths[repo]))
            
            # Add module node
            graph.add_node(
                module_path,
                type="module",
                language="python",
                repo=repo
            )
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        graph.add_edge(
                            module_path,
                            alias.name,
                            type="imports"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        graph.add_edge(
                            module_path,
                            node.module,
                            type="imports"
                        )
                
                # Extract class and function names
                elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    graph.add_node(
                        f"{module_path}::{node.name}",
                        type="class" if isinstance(node, ast.ClassDef) else "function",
                        repo=repo
                    )
                    graph.add_edge(
                        module_path,
                        f"{module_path}::{node.name}",
                        type="contains"
                    )
                
                # Extract SQL queries (heuristic)
                elif isinstance(node, ast.Str):
                    if "SELECT" in node.s or "INSERT" in node.s or "UPDATE" in node.s:
                        # Extract table names (simple pattern)
                        tables = self._extract_table_names(node.s)
                        for table in tables:
                            graph.add_node(
                                f"db::{table}",
                                type="db_table",
                                repo=repo
                            )
                            graph.add_edge(
                                module_path,
                                f"db::{table}",
                                type="queries"
                            )
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
    
    def _analyze_js_file(
        self, file_path: Path, graph: nx.DiGraph, repo: str
    ) -> None:
        """Analyze JavaScript/TypeScript file and add to graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            module_path = str(file_path.relative_to(self.repo_paths[repo]))
            
            # Add module node
            graph.add_node(
                module_path,
                type="module",
                language="javascript",
                repo=repo
            )
            
            # Extract imports (simple regex-based)
            import_pattern = r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]'
            for match in re.finditer(import_pattern, content):
                imported = match.group(1)
                graph.add_edge(
                    module_path,
                    imported,
                    type="imports"
                )
            
            # Extract API calls (heuristic)
            api_pattern = r'(?:fetch|axios|http)\s*\(\s*[\'"]([^\'"]+)[\'"]'
            for match in re.finditer(api_pattern, content):
                endpoint = match.group(1)
                graph.add_node(
                    f"api::{endpoint}",
                    type="api_endpoint",
                    repo=repo
                )
                graph.add_edge(
                    module_path,
                    f"api::{endpoint}",
                    type="calls"
                )
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
    
    def _analyze_openapi_spec(
        self, file_path: Path, graph: nx.DiGraph, repo: str
    ) -> None:
        """Analyze OpenAPI spec and add to graph."""
        try:
            import yaml
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix == '.json':
                    import json
                    spec = json.load(f)
                else:
                    spec = yaml.safe_load(f)
            
            # Extract paths (endpoints)
            paths = spec.get('paths', {})
            for path, methods in paths.items():
                for method in methods.keys():
                    if method in ['get', 'post', 'put', 'delete', 'patch']:
                        endpoint = f"api::{method.upper()} {path}"
                        graph.add_node(
                            endpoint,
                            type="api_endpoint",
                            repo=repo,
                            spec=str(file_path)
                        )
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
    
    def _extract_keywords(self, story: Story) -> Set[str]:
        """Extract relevant keywords from story for matching."""
        keywords = set()
        
        # Extract from title and user value
        text = f"{story.title} {story.user_value}"
        
        # Common terms that might map to modules
        patterns = [
            r'\b(auth|user|payment|order|product|cart|checkout|admin)\b',
            r'\b(api|service|handler|model|view|controller)\b',
            r'\b(database|db|table|schema)\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.update(m.lower() for m in matches)
        
        return keywords
    
    def _find_impacted_nodes(
        self,
        graph: nx.DiGraph,
        keywords: Set[str],
        depth: int
    ) -> Set[str]:
        """Find nodes impacted by keywords up to certain depth."""
        impacted = set()
        
        # Find nodes matching keywords
        for node in graph.nodes():
            node_lower = str(node).lower()
            if any(keyword in node_lower for keyword in keywords):
                impacted.add(node)
                
                # Add successors (dependencies) up to depth
                try:
                    successors = nx.single_source_shortest_path_length(
                        graph, node, cutoff=depth
                    )
                    impacted.update(successors.keys())
                except nx.NetworkXError:
                    pass
                
                # Add predecessors (dependents) up to depth
                try:
                    predecessors = nx.single_source_shortest_path_length(
                        graph.reverse(), node, cutoff=depth
                    )
                    impacted.update(predecessors.keys())
                except nx.NetworkXError:
                    pass
        
        return impacted
    
    def _categorize_impacts(
        self,
        nodes: Set[str],
        graph: nx.DiGraph,
        blast_radius: BlastRadius,
        repo: str
    ) -> None:
        """Categorize impacted nodes into blast radius categories."""
        for node in nodes:
            node_data = graph.nodes.get(node, {})
            node_type = node_data.get('type', '')
            
            if node_type == 'module':
                blast_radius.modules.append(f"{repo}/{node}")
            elif node_type in ['class', 'function']:
                blast_radius.modules.append(f"{repo}/{node}")
            elif node_type == 'api_endpoint':
                blast_radius.interfaces.append(node.replace('api::', ''))
            elif node_type == 'db_table':
                blast_radius.db_objects.append(node.replace('db::', ''))
            elif 'service' in node.lower():
                if repo not in blast_radius.systems:
                    blast_radius.systems.append(repo)
    
    def _calculate_confidence(
        self, blast_radius: BlastRadius, repo_count: int
    ) -> float:
        """Calculate confidence score based on analysis completeness."""
        confidence = 0.5  # Base confidence
        
        # Increase if we found impacts
        if blast_radius.total_impact_count > 0:
            confidence += 0.2
        
        # Increase if we analyzed multiple repos
        if repo_count > 1:
            confidence += 0.1
        
        # Decrease if we have gaps
        if blast_radius.gaps:
            confidence -= 0.1 * len(blast_radius.gaps)
        
        # Increase if we have diverse impact types
        categories = sum([
            len(blast_radius.systems) > 0,
            len(blast_radius.modules) > 0,
            len(blast_radius.interfaces) > 0,
            len(blast_radius.db_objects) > 0
        ])
        confidence += 0.05 * categories
        
        return max(0.0, min(1.0, confidence))
    
    def _extract_table_names(self, sql: str) -> Set[str]:
        """Extract table names from SQL query (simple heuristic)."""
        tables = set()
        
        # Match common patterns: FROM/JOIN table_name
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.update(matches)
        
        return tables
