"""
Graph builder for code intelligence.

Builds interconnected graphs: files, symbols, routes, DI, jobs.
"""

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from overlord.code_intelligence.parsers import (
    DIEdge,
    Entity,
    FrameworkParser,
    Job,
    NestJSParser,
    NextJSParser,
    Route,
)

logger = logging.getLogger(__name__)


@dataclass
class Symbol:
    """Represents a code symbol (function, class, method)."""
    id: str  # Unique identifier
    name: str
    kind: str  # function, class, method, variable
    file_path: str
    start_line: int
    end_line: int
    signature: Optional[str] = None


@dataclass
class FileNode:
    """Represents a file in the codebase."""
    path: str
    language: str
    imports: List[str]
    exports: List[str]
    sha: Optional[str] = None


class CodeGraphBuilder:
    """
    Builds multi-level graphs of code structure.
    
    Creates:
    - File graph (import dependencies)
    - Symbol graph (call graph)
    - Route graph (web routes → handlers)
    - DI graph (dependency injection)
    - Job graph (background tasks)
    """
    
    def __init__(self, repo_path: str, framework: Optional[str] = None):
        """
        Initialize graph builder.
        
        Args:
            repo_path: Path to repository
            framework: Framework type (nextjs, nestjs, django, etc.)
        """
        self.repo_path = Path(repo_path)
        self.framework = framework
        
        # Graphs
        self.file_graph = nx.DiGraph()
        self.symbol_graph = nx.DiGraph()
        self.route_graph = nx.DiGraph()
        self.di_graph = nx.DiGraph()
        self.job_graph = nx.DiGraph()
        
        # Storage
        self.files: Dict[str, FileNode] = {}
        self.symbols: Dict[str, Symbol] = {}
        self.routes: Dict[str, Route] = {}
        self.di_edges: List[DIEdge] = []
        self.jobs: Dict[str, Job] = {}
        self.entities: Dict[str, Entity] = {}
        
        logger.info(f"Initialized CodeGraphBuilder for {repo_path}")
    
    def build_all_graphs(self) -> Dict[str, nx.DiGraph]:
        """
        Build all graphs.
        
        Returns:
            Dictionary of graph name to NetworkX DiGraph
        """
        logger.info("Building all graphs...")
        
        # Build file graph
        self._build_file_graph()
        
        # Build symbol graph
        self._build_symbol_graph()
        
        # Build framework-specific graphs
        if self.framework:
            self._build_framework_graphs()
        
        logger.info(f"Built graphs: "
                   f"{self.file_graph.number_of_nodes()} files, "
                   f"{self.symbol_graph.number_of_nodes()} symbols, "
                   f"{len(self.routes)} routes, "
                   f"{len(self.di_edges)} DI edges")
        
        return {
            "files": self.file_graph,
            "symbols": self.symbol_graph,
            "routes": self.route_graph,
            "di": self.di_graph,
            "jobs": self.job_graph,
        }
    
    def _build_file_graph(self) -> None:
        """Build file import dependency graph."""
        logger.info("Building file graph...")
        
        # Scan for Python files
        for py_file in self.repo_path.rglob("*.py"):
            if "venv" in py_file.parts or "__pycache__" in py_file.parts:
                continue
            self._analyze_python_file(py_file)
        
        # Scan for TypeScript/JavaScript files
        for ts_file in self.repo_path.rglob("*.{ts,tsx,js,jsx}"):
            if "node_modules" in ts_file.parts:
                continue
            self._analyze_typescript_file(ts_file)
    
    def _analyze_python_file(self, file_path: Path) -> None:
        """Analyze Python file and add to file graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            relative_path = str(file_path.relative_to(self.repo_path))
            
            imports = []
            exports = []
            
            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Extract exports (top-level functions and classes)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    exports.append(node.name)
            
            file_node = FileNode(
                path=relative_path,
                language="python",
                imports=imports,
                exports=exports
            )
            self.files[relative_path] = file_node
            
            # Add to graph
            self.file_graph.add_node(
                relative_path,
                language="python",
                exports=exports
            )
            
            for imp in imports:
                self.file_graph.add_edge(
                    relative_path,
                    imp,
                    type="imports"
                )
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
    
    def _analyze_typescript_file(self, file_path: Path) -> None:
        """Analyze TypeScript/JavaScript file and add to file graph."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            relative_path = str(file_path.relative_to(self.repo_path))
            imports = []
            exports = []
            
            # Extract imports (simple regex-based)
            import re
            import_pattern = r'import\s+.*?\s+from\s+[\'"](.+?)[\'"]'
            for match in re.finditer(import_pattern, content):
                imports.append(match.group(1))
            
            # Extract exports
            export_patterns = [
                r'export\s+function\s+(\w+)',
                r'export\s+class\s+(\w+)',
                r'export\s+const\s+(\w+)',
                r'export\s+default\s+function\s+(\w+)',
                r'export\s+default\s+class\s+(\w+)',
            ]
            
            for pattern in export_patterns:
                for match in re.finditer(pattern, content):
                    exports.append(match.group(1))
            
            file_node = FileNode(
                path=relative_path,
                language="typescript" if file_path.suffix in ['.ts', '.tsx'] else "javascript",
                imports=imports,
                exports=exports
            )
            self.files[relative_path] = file_node
            
            # Add to graph
            self.file_graph.add_node(
                relative_path,
                language=file_node.language,
                exports=exports
            )
            
            for imp in imports:
                self.file_graph.add_edge(
                    relative_path,
                    imp,
                    type="imports"
                )
        
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
    
    def _build_symbol_graph(self) -> None:
        """Build symbol call graph."""
        logger.info("Building symbol graph...")
        
        # Analyze Python files for symbols
        for py_file in self.repo_path.rglob("*.py"):
            if "venv" in py_file.parts or "__pycache__" in py_file.parts:
                continue
            self._extract_python_symbols(py_file)
    
    def _extract_python_symbols(self, file_path: Path) -> None:
        """Extract symbols from Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            relative_path = str(file_path.relative_to(self.repo_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    symbol_id = f"{relative_path}::{node.name}"
                    symbol = Symbol(
                        id=symbol_id,
                        name=node.name,
                        kind="function",
                        file_path=relative_path,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno
                    )
                    self.symbols[symbol_id] = symbol
                    
                    # Add to graph
                    self.symbol_graph.add_node(
                        symbol_id,
                        name=node.name,
                        kind="function",
                        file=relative_path,
                        line=node.lineno
                    )
                    
                    # Extract function calls
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name):
                                callee = child.func.id
                                # Simple heuristic: assume same file
                                callee_id = f"{relative_path}::{callee}"
                                self.symbol_graph.add_edge(
                                    symbol_id,
                                    callee_id,
                                    type="calls"
                                )
                
                elif isinstance(node, ast.ClassDef):
                    class_id = f"{relative_path}::{node.name}"
                    symbol = Symbol(
                        id=class_id,
                        name=node.name,
                        kind="class",
                        file_path=relative_path,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno
                    )
                    self.symbols[class_id] = symbol
                    
                    self.symbol_graph.add_node(
                        class_id,
                        name=node.name,
                        kind="class",
                        file=relative_path,
                        line=node.lineno
                    )
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_id = f"{class_id}.{item.name}"
                            method_symbol = Symbol(
                                id=method_id,
                                name=item.name,
                                kind="method",
                                file_path=relative_path,
                                start_line=item.lineno,
                                end_line=item.end_lineno or item.lineno
                            )
                            self.symbols[method_id] = method_symbol
                            
                            self.symbol_graph.add_node(
                                method_id,
                                name=item.name,
                                kind="method",
                                file=relative_path,
                                line=item.lineno
                            )
                            
                            # Link method to class
                            self.symbol_graph.add_edge(
                                class_id,
                                method_id,
                                type="contains"
                            )
        
        except Exception as e:
            logger.warning(f"Failed to extract symbols from {file_path}: {e}")
    
    def _build_framework_graphs(self) -> None:
        """Build framework-specific graphs."""
        logger.info(f"Building framework graphs for: {self.framework}")
        
        parser: Optional[FrameworkParser] = None
        
        if self.framework == "nextjs":
            parser = NextJSParser(str(self.repo_path))
        elif self.framework == "nestjs":
            parser = NestJSParser(str(self.repo_path))
        
        if parser:
            parser.parse()
            
            # Add routes to graph
            for route in parser.routes:
                route_id = f"{route.method} {route.path}"
                self.routes[route_id] = route
                
                self.route_graph.add_node(
                    route_id,
                    method=route.method,
                    path=route.path,
                    handler=route.handler,
                    file=route.file_path,
                    line=route.line_number
                )
                
                # Link route to handler symbol
                if route.handler:
                    handler_file = route.file_path
                    handler_symbol = f"{handler_file}::{route.handler}"
                    self.route_graph.add_edge(
                        route_id,
                        handler_symbol,
                        type="handled_by"
                    )
            
            # Add DI edges to graph
            for di_edge in parser.di_edges:
                self.di_edges.append(di_edge)
                
                self.di_graph.add_edge(
                    di_edge.provider,
                    di_edge.consumer,
                    type="provides",
                    scope=di_edge.scope
                )
            
            # Add jobs to graph
            for job in parser.jobs:
                self.jobs[job.name] = job
                
                self.job_graph.add_node(
                    job.name,
                    schedule=job.schedule,
                    handler=job.handler,
                    dependencies=job.dependencies
                )
    
    def get_callers(self, symbol_id: str) -> List[str]:
        """Get all symbols that call this symbol."""
        if symbol_id not in self.symbol_graph:
            return []
        
        return list(self.symbol_graph.predecessors(symbol_id))
    
    def get_callees(self, symbol_id: str) -> List[str]:
        """Get all symbols called by this symbol."""
        if symbol_id not in self.symbol_graph:
            return []
        
        return list(self.symbol_graph.successors(symbol_id))
    
    def get_transitive_dependencies(
        self,
        symbol_id: str,
        depth: int = 3
    ) -> Set[str]:
        """Get transitive dependencies up to specified depth."""
        if symbol_id not in self.symbol_graph:
            return set()
        
        dependencies = set()
        
        try:
            # BFS to find dependencies
            paths = nx.single_source_shortest_path_length(
                self.symbol_graph,
                symbol_id,
                cutoff=depth
            )
            dependencies.update(paths.keys())
        except nx.NetworkXError:
            pass
        
        return dependencies
    
    def get_impact_set(self, symbol_ids: List[str], depth: int = 3) -> Dict:
        """
        Get comprehensive impact set for changed symbols.
        
        Returns:
            Dictionary with impacted symbols, files, routes, DI edges
        """
        impacted = {
            "symbols": set(),
            "files": set(),
            "routes": set(),
            "di_consumers": set(),
        }
        
        for symbol_id in symbol_ids:
            # Get direct callers (who depends on this)
            callers = self.get_callers(symbol_id)
            impacted["symbols"].update(callers)
            
            # Get transitive impact
            transitive = self.get_transitive_dependencies(symbol_id, depth)
            impacted["symbols"].update(transitive)
            
            # Find affected files
            for sym_id in impacted["symbols"]:
                if sym_id in self.symbols:
                    impacted["files"].add(self.symbols[sym_id].file_path)
            
            # Find affected routes
            for route_id, route in self.routes.items():
                if any(sym in route.handler for sym in impacted["symbols"]):
                    impacted["routes"].add(route_id)
            
            # Find DI consumers
            for di_edge in self.di_edges:
                if symbol_id in di_edge.provider:
                    impacted["di_consumers"].add(di_edge.consumer)
        
        return {
            "symbols": list(impacted["symbols"]),
            "files": list(impacted["files"]),
            "routes": list(impacted["routes"]),
            "di_consumers": list(impacted["di_consumers"]),
        }
    
    def export_graphs(self, output_dir: Path) -> None:
        """Export graphs to JSON files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        import json
        
        # Export file graph
        file_graph_data = nx.node_link_data(self.file_graph)
        with open(output_dir / "file_graph.json", 'w') as f:
            json.dump(file_graph_data, f, indent=2)
        
        # Export symbol graph
        symbol_graph_data = nx.node_link_data(self.symbol_graph)
        with open(output_dir / "symbol_graph.json", 'w') as f:
            json.dump(symbol_graph_data, f, indent=2)
        
        # Export routes
        routes_data = {k: vars(v) for k, v in self.routes.items()}
        with open(output_dir / "routes.json", 'w') as f:
            json.dump(routes_data, f, indent=2)
        
        logger.info(f"Exported graphs to {output_dir}")
