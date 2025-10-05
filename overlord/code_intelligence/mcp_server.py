"""
MCP Server for Code Intelligence.

Exposes code graphs, symbols, and analysis tools via Model Context Protocol.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from overlord.code_intelligence.graph_builder import CodeGraphBuilder, Symbol
from overlord.code_intelligence.search import CodeSearchEngine

logger = logging.getLogger(__name__)


class CodeIntelligenceMCP:
    """
    MCP server for code intelligence.
    
    Provides resources and tools for agents to understand codebases:
    - Resources: files, symbols, routes, DI graph, jobs, summaries
    - Tools: search, who_calls, impact_of, get_symbol, etc.
    """
    
    def __init__(
        self,
        repos: Dict[str, str],  # repo_name -> repo_path
        frameworks: Optional[Dict[str, str]] = None,  # repo_name -> framework
    ):
        """
        Initialize MCP server.
        
        Args:
            repos: Dictionary mapping repo names to local paths
            frameworks: Optional dict mapping repo names to framework types
        """
        self.repos = repos
        self.frameworks = frameworks or {}
        self.graph_builders: Dict[str, CodeGraphBuilder] = {}
        self.search_engines: Dict[str, CodeSearchEngine] = {}
        
        # Initialize graph builders for each repo
        for repo_name, repo_path in repos.items():
            framework = self.frameworks.get(repo_name)
            self.graph_builders[repo_name] = CodeGraphBuilder(repo_path, framework)
            self.graph_builders[repo_name].build_all_graphs()
        
        logger.info(f"Initialized MCP server for {len(repos)} repositories")
    
    # ========================================================================
    # MCP Resources (read-only context)
    # ========================================================================
    
    def get_resource_files(self, repo: str) -> Dict[str, Any]:
        """
        Get file resources for a repository.
        
        Resource URI: repo://files?repo={repo}
        
        Returns:
            Dictionary with file metadata
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        files = []
        
        for path, file_node in builder.files.items():
            files.append({
                "id": path,
                "path": path,
                "language": file_node.language,
                "imports": file_node.imports,
                "exports": file_node.exports,
                "sha": file_node.sha,
            })
        
        return {
            "repo": repo,
            "files": files,
            "total": len(files)
        }
    
    def get_resource_symbols(self, repo: str) -> Dict[str, Any]:
        """
        Get symbol resources for a repository.
        
        Resource URI: graph://symbols?repo={repo}
        
        Returns:
            Dictionary with symbol metadata and call graph info
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        symbols = []
        
        for symbol_id, symbol in builder.symbols.items():
            symbols.append({
                "id": symbol.id,
                "name": symbol.name,
                "kind": symbol.kind,
                "file": symbol.file_path,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
                "callers": builder.get_callers(symbol_id),
                "callees": builder.get_callees(symbol_id),
            })
        
        return {
            "repo": repo,
            "symbols": symbols,
            "total": len(symbols)
        }
    
    def get_resource_routes(self, repo: str) -> Dict[str, Any]:
        """
        Get route resources for a repository.
        
        Resource URI: graph://routes?repo={repo}
        
        Returns:
            Dictionary with web routes and their handlers
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        routes = []
        
        for route_id, route in builder.routes.items():
            routes.append({
                "id": route_id,
                "method": route.method,
                "path": route.path,
                "handler": route.handler,
                "middleware": route.middleware,
                "file": route.file_path,
                "line": route.line_number,
            })
        
        return {
            "repo": repo,
            "routes": routes,
            "total": len(routes)
        }
    
    def get_resource_di_graph(self, repo: str) -> Dict[str, Any]:
        """
        Get DI graph resources for a repository.
        
        Resource URI: graph://di?repo={repo}
        
        Returns:
            Dictionary with DI relationships
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        di_edges = []
        
        for edge in builder.di_edges:
            di_edges.append({
                "provider": edge.provider,
                "consumer": edge.consumer,
                "scope": edge.scope,
                "file": edge.file_path,
            })
        
        return {
            "repo": repo,
            "di_edges": di_edges,
            "total": len(di_edges)
        }
    
    def get_resource_jobs(self, repo: str) -> Dict[str, Any]:
        """
        Get job resources for a repository.
        
        Resource URI: graph://jobs?repo={repo}
        
        Returns:
            Dictionary with background jobs and schedules
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        jobs = []
        
        for job_name, job in builder.jobs.items():
            jobs.append({
                "name": job.name,
                "schedule": job.schedule,
                "handler": job.handler,
                "dependencies": job.dependencies,
                "file": job.file_path,
            })
        
        return {
            "repo": repo,
            "jobs": jobs,
            "total": len(jobs)
        }
    
    # ========================================================================
    # MCP Tools (actions)
    # ========================================================================
    
    def tool_search_code(
        self,
        query: str,
        repo: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Search code with hybrid vector + lexical search.
        
        Tool: search_code(query, repo, topK)
        
        Args:
            query: Search query
            repo: Repository to search
            top_k: Number of results to return
        
        Returns:
            Search results with file/line citations
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        # For now, simple text search through symbols
        # TODO: Implement proper vector + lexical hybrid search
        builder = self.graph_builders[repo]
        results = []
        
        query_lower = query.lower()
        for symbol_id, symbol in builder.symbols.items():
            if query_lower in symbol.name.lower():
                results.append({
                    "symbol_id": symbol.id,
                    "name": symbol.name,
                    "kind": symbol.kind,
                    "file": symbol.file_path,
                    "line": symbol.start_line,
                    "relevance": 1.0,  # TODO: Calculate relevance score
                })
        
        results = results[:top_k]
        
        return {
            "query": query,
            "repo": repo,
            "results": results,
            "total": len(results)
        }
    
    def tool_get_symbol(self, symbol_id: str, repo: str) -> Dict[str, Any]:
        """
        Get detailed information about a symbol.
        
        Tool: get_symbol(symbol_id, repo)
        
        Args:
            symbol_id: Symbol identifier
            repo: Repository name
        
        Returns:
            Symbol details with call graph
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        
        if symbol_id not in builder.symbols:
            return {"error": f"Symbol {symbol_id} not found"}
        
        symbol = builder.symbols[symbol_id]
        
        return {
            "symbol": {
                "id": symbol.id,
                "name": symbol.name,
                "kind": symbol.kind,
                "file": symbol.file_path,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
                "signature": symbol.signature,
            },
            "callers": builder.get_callers(symbol_id),
            "callees": builder.get_callees(symbol_id),
            "transitive_dependencies": list(
                builder.get_transitive_dependencies(symbol_id, depth=2)
            )
        }
    
    def tool_who_calls(self, symbol_id: str, repo: str) -> Dict[str, Any]:
        """
        Find all callers of a symbol.
        
        Tool: who_calls(symbol_id, repo)
        
        Args:
            symbol_id: Symbol identifier
            repo: Repository name
        
        Returns:
            List of callers with file/line info
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        callers = builder.get_callers(symbol_id)
        
        caller_details = []
        for caller_id in callers:
            if caller_id in builder.symbols:
                caller = builder.symbols[caller_id]
                caller_details.append({
                    "id": caller.id,
                    "name": caller.name,
                    "file": caller.file_path,
                    "line": caller.start_line,
                })
        
        return {
            "symbol_id": symbol_id,
            "callers": caller_details,
            "total": len(caller_details)
        }
    
    def tool_list_dependencies(
        self,
        symbol_id: str,
        repo: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        List all dependencies of a symbol.
        
        Tool: list_dependencies(symbol_id, repo, depth)
        
        Args:
            symbol_id: Symbol identifier
            repo: Repository name
            depth: Dependency traversal depth
        
        Returns:
            List of dependencies
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        dependencies = builder.get_transitive_dependencies(symbol_id, depth)
        
        dep_details = []
        for dep_id in dependencies:
            if dep_id in builder.symbols:
                dep = builder.symbols[dep_id]
                dep_details.append({
                    "id": dep.id,
                    "name": dep.name,
                    "kind": dep.kind,
                    "file": dep.file_path,
                })
        
        return {
            "symbol_id": symbol_id,
            "dependencies": dep_details,
            "depth": depth,
            "total": len(dep_details)
        }
    
    def tool_impact_of(
        self,
        change: Dict[str, Any],
        repo: str,
        depth: int = 3
    ) -> Dict[str, Any]:
        """
        Calculate enhanced blast radius for a change.
        
        Tool: impact_of(change, repo, depth)
        
        Args:
            change: Change specification
            repo: Repository name
            depth: Analysis depth
        
        Returns:
            Enhanced blast radius with framework-aware impacts
        """
        if repo not in self.graph_builders:
            return {"error": f"Repository {repo} not found"}
        
        builder = self.graph_builders[repo]
        
        # Extract symbols being changed
        symbol_ids = change.get("symbol_ids", [])
        
        # Get impact set
        impact_set = builder.get_impact_set(symbol_ids, depth)
        
        # Enhance with framework-specific impacts
        routes_affected = []
        for route_id in impact_set["routes"]:
            if route_id in builder.routes:
                route = builder.routes[route_id]
                routes_affected.append({
                    "method": route.method,
                    "path": route.path,
                    "handler": route.handler,
                })
        
        return {
            "change": change,
            "blast_radius": {
                "symbols_affected": impact_set["symbols"],
                "files_affected": impact_set["files"],
                "routes_affected": routes_affected,
                "di_consumers": impact_set["di_consumers"],
                "confidence": 0.85,  # TODO: Calculate actual confidence
                "framework_aware": True,
            },
            "recommendations": self._generate_recommendations(impact_set)
        }
    
    def _generate_recommendations(self, impact_set: Dict) -> List[str]:
        """Generate recommendations based on impact set."""
        recommendations = []
        
        if len(impact_set["routes"]) > 0:
            recommendations.append(
                f"⚠️ {len(impact_set['routes'])} routes affected - update API docs"
            )
        
        if len(impact_set["di_consumers"]) > 0:
            recommendations.append(
                f"⚠️ {len(impact_set['di_consumers'])} DI consumers affected - "
                f"check interface compatibility"
            )
        
        if len(impact_set["files"]) > 10:
            recommendations.append(
                "⚠️ Large blast radius - consider breaking into smaller changes"
            )
        
        return recommendations
    
    # ========================================================================
    # MCP Server Interface
    # ========================================================================
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request.
        
        Args:
            request: MCP request dict
        
        Returns:
            MCP response dict
        """
        request_type = request.get("type")
        
        if request_type == "resource":
            return self._handle_resource_request(request)
        elif request_type == "tool":
            return self._handle_tool_request(request)
        else:
            return {"error": f"Unknown request type: {request_type}"}
    
    def _handle_resource_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource request."""
        resource_uri = request.get("uri", "")
        params = request.get("params", {})
        
        if resource_uri.startswith("repo://files"):
            return self.get_resource_files(params.get("repo"))
        elif resource_uri.startswith("graph://symbols"):
            return self.get_resource_symbols(params.get("repo"))
        elif resource_uri.startswith("graph://routes"):
            return self.get_resource_routes(params.get("repo"))
        elif resource_uri.startswith("graph://di"):
            return self.get_resource_di_graph(params.get("repo"))
        elif resource_uri.startswith("graph://jobs"):
            return self.get_resource_jobs(params.get("repo"))
        else:
            return {"error": f"Unknown resource URI: {resource_uri}"}
    
    def _handle_tool_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool request."""
        tool_name = request.get("tool")
        params = request.get("params", {})
        
        if tool_name == "search_code":
            return self.tool_search_code(**params)
        elif tool_name == "get_symbol":
            return self.tool_get_symbol(**params)
        elif tool_name == "who_calls":
            return self.tool_who_calls(**params)
        elif tool_name == "list_dependencies":
            return self.tool_list_dependencies(**params)
        elif tool_name == "impact_of":
            return self.tool_impact_of(**params)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
