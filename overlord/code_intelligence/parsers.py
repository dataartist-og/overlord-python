"""
Framework-aware parsers for extracting routes, DI, jobs, and entities.

These parsers understand framework conventions and patterns, not just AST structure.
"""

import ast
import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class Route:
    """Represents a web route."""
    method: str  # GET, POST, PUT, DELETE, etc.
    path: str  # /api/users/:id
    handler: str  # UserController.getById
    middleware: List[str] = field(default_factory=list)
    file_path: str = ""
    line_number: int = 0


@dataclass
class DIEdge:
    """Represents a dependency injection relationship."""
    provider: str  # What is being provided
    consumer: str  # Who consumes it
    scope: str = "singleton"  # singleton, transient, request
    file_path: str = ""


@dataclass
class Job:
    """Represents a background job or scheduled task."""
    name: str
    schedule: Optional[str]  # Cron expression or None for queue
    handler: str  # Function/method that runs
    dependencies: List[str] = field(default_factory=list)
    file_path: str = ""


@dataclass
class Entity:
    """Represents an ORM entity/model."""
    name: str
    table_name: str
    fields: Dict[str, str]  # field_name -> type
    relationships: List[str] = field(default_factory=list)
    file_path: str = ""


class FrameworkParser(ABC):
    """Base class for framework-aware parsers."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.routes: List[Route] = []
        self.di_edges: List[DIEdge] = []
        self.jobs: List[Job] = []
        self.entities: List[Entity] = []
    
    @abstractmethod
    def parse(self) -> None:
        """Parse the repository and extract framework structures."""
        pass
    
    def get_all_structures(self) -> Dict:
        """Get all parsed structures."""
        return {
            "routes": [vars(r) for r in self.routes],
            "di_edges": [vars(d) for d in self.di_edges],
            "jobs": [vars(j) for j in self.jobs],
            "entities": [vars(e) for e in self.entities],
        }


class NextJSParser(FrameworkParser):
    """
    Parser for Next.js projects (App Router and Pages Router).
    
    Extracts:
    - Routes (from app/ or pages/ directory structure)
    - API routes
    - Server Actions
    - Middleware
    """
    
    def parse(self) -> None:
        """Parse Next.js project."""
        logger.info(f"Parsing Next.js project: {self.repo_path}")
        
        # Try App Router first (app/ directory)
        app_dir = self.repo_path / "app"
        if app_dir.exists():
            self._parse_app_router(app_dir)
        
        # Try Pages Router (pages/ directory)
        pages_dir = self.repo_path / "pages"
        if pages_dir.exists():
            self._parse_pages_router(pages_dir)
        
        # Parse API routes
        api_dir = self.repo_path / "pages" / "api"
        if not api_dir.exists():
            api_dir = self.repo_path / "app" / "api"
        if api_dir.exists():
            self._parse_api_routes(api_dir)
        
        # Parse middleware
        middleware_file = self.repo_path / "middleware.ts"
        if not middleware_file.exists():
            middleware_file = self.repo_path / "middleware.js"
        if middleware_file.exists():
            self._parse_middleware(middleware_file)
        
        logger.info(f"Found {len(self.routes)} routes in Next.js project")
    
    def _parse_app_router(self, app_dir: Path) -> None:
        """Parse Next.js App Router."""
        for route_dir in app_dir.rglob("*"):
            if not route_dir.is_dir():
                continue
            
            # Look for page.tsx, page.jsx, route.ts, route.js
            for file_name in ["page.tsx", "page.jsx", "page.ts", "page.js"]:
                page_file = route_dir / file_name
                if page_file.exists():
                    route_path = self._dir_to_route_path(app_dir, route_dir)
                    self._extract_page_route(page_file, route_path)
            
            # Look for route.ts (API routes in App Router)
            for file_name in ["route.ts", "route.js"]:
                route_file = route_dir / file_name
                if route_file.exists():
                    route_path = self._dir_to_route_path(app_dir, route_dir)
                    self._extract_app_api_route(route_file, route_path)
    
    def _parse_pages_router(self, pages_dir: Path) -> None:
        """Parse Next.js Pages Router."""
        for page_file in pages_dir.rglob("*.{tsx,jsx,ts,js}"):
            # Skip API routes (handled separately)
            if "api" in page_file.parts:
                continue
            
            route_path = self._file_to_route_path(pages_dir, page_file)
            self._extract_page_route(page_file, route_path)
    
    def _parse_api_routes(self, api_dir: Path) -> None:
        """Parse API routes in pages/api."""
        for api_file in api_dir.rglob("*.{ts,js}"):
            route_path = self._file_to_api_route_path(api_dir, api_file)
            self._extract_pages_api_route(api_file, route_path)
    
    def _parse_middleware(self, middleware_file: Path) -> None:
        """Parse middleware configuration."""
        try:
            with open(middleware_file, 'r') as f:
                content = f.read()
            
            # Extract middleware matcher patterns
            matcher_pattern = r'matcher:\s*\[([^\]]+)\]'
            matches = re.findall(matcher_pattern, content)
            
            if matches:
                patterns = [p.strip().strip('"\'') for p in matches[0].split(',')]
                logger.info(f"Found middleware for patterns: {patterns}")
        
        except Exception as e:
            logger.warning(f"Failed to parse middleware: {e}")
    
    def _extract_page_route(self, file_path: Path, route_path: str) -> None:
        """Extract route from a Next.js page component."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract component name (simplified)
            component_pattern = r'export\s+default\s+function\s+(\w+)'
            match = re.search(component_pattern, content)
            handler = match.group(1) if match else "Page"
            
            route = Route(
                method="GET",
                path=route_path,
                handler=f"{file_path.stem}.{handler}",
                file_path=str(file_path.relative_to(self.repo_path)),
                line_number=1
            )
            self.routes.append(route)
        
        except Exception as e:
            logger.warning(f"Failed to parse page {file_path}: {e}")
    
    def _extract_app_api_route(self, file_path: Path, route_path: str) -> None:
        """Extract API route from App Router route.ts."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Find exported HTTP methods (GET, POST, PUT, DELETE, PATCH)
            methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']
            
            for method in methods:
                pattern = rf'export\s+async\s+function\s+{method}'
                if re.search(pattern, content):
                    route = Route(
                        method=method,
                        path=route_path,
                        handler=f"{file_path.stem}.{method}",
                        file_path=str(file_path.relative_to(self.repo_path)),
                        line_number=1
                    )
                    self.routes.append(route)
        
        except Exception as e:
            logger.warning(f"Failed to parse API route {file_path}: {e}")
    
    def _extract_pages_api_route(self, file_path: Path, route_path: str) -> None:
        """Extract API route from Pages Router pages/api."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Default export is the handler
            route = Route(
                method="GET/POST",  # Pages API routes handle multiple methods
                path=route_path,
                handler=f"{file_path.stem}.handler",
                file_path=str(file_path.relative_to(self.repo_path)),
                line_number=1
            )
            self.routes.append(route)
        
        except Exception as e:
            logger.warning(f"Failed to parse API route {file_path}: {e}")
    
    def _dir_to_route_path(self, base_dir: Path, route_dir: Path) -> str:
        """Convert directory structure to route path."""
        relative = route_dir.relative_to(base_dir)
        parts = []
        
        for part in relative.parts:
            if part == ".":
                continue
            elif part.startswith("[") and part.endswith("]"):
                # Dynamic route
                param_name = part[1:-1]
                if param_name.startswith("..."):
                    # Catch-all route
                    parts.append(f"*{param_name[3:]}")
                else:
                    # Dynamic param
                    parts.append(f":{param_name}")
            elif part.startswith("(") and part.endswith(")"):
                # Route group - don't include in path
                continue
            else:
                parts.append(part)
        
        path = "/" + "/".join(parts) if parts else "/"
        return path
    
    def _file_to_route_path(self, base_dir: Path, file_path: Path) -> str:
        """Convert file path to route path for Pages Router."""
        relative = file_path.relative_to(base_dir)
        parts = []
        
        for part in relative.parts[:-1]:  # Exclude filename
            if part.startswith("[") and part.endswith("]"):
                param_name = part[1:-1]
                parts.append(f":{param_name}")
            else:
                parts.append(part)
        
        # Handle filename
        stem = file_path.stem
        if stem != "index":
            if stem.startswith("[") and stem.endswith("]"):
                param_name = stem[1:-1]
                parts.append(f":{param_name}")
            else:
                parts.append(stem)
        
        path = "/" + "/".join(parts) if parts else "/"
        return path
    
    def _file_to_api_route_path(self, api_dir: Path, file_path: Path) -> str:
        """Convert API file path to route path."""
        relative = file_path.relative_to(api_dir)
        parts = ["/api"]
        
        for part in relative.parts:
            if part.endswith(('.ts', '.js')):
                stem = Path(part).stem
                if stem != "index":
                    if stem.startswith("[") and stem.endswith("]"):
                        param_name = stem[1:-1]
                        parts.append(f":{param_name}")
                    else:
                        parts.append(stem)
            else:
                if part.startswith("[") and part.endswith("]"):
                    param_name = part[1:-1]
                    parts.append(f":{param_name}")
                else:
                    parts.append(part)
        
        return "/".join(parts)


class NestJSParser(FrameworkParser):
    """
    Parser for NestJS projects.
    
    Extracts:
    - Controllers and routes
    - Providers (services)
    - DI relationships
    - Guards, Interceptors, Pipes
    - Modules
    """
    
    def parse(self) -> None:
        """Parse NestJS project."""
        logger.info(f"Parsing NestJS project: {self.repo_path}")
        
        # Find all TypeScript files
        for ts_file in self.repo_path.rglob("*.ts"):
            if "node_modules" in ts_file.parts:
                continue
            
            with open(ts_file, 'r') as f:
                content = f.read()
            
            # Parse controllers
            if "@Controller(" in content:
                self._parse_controller(ts_file, content)
            
            # Parse providers
            if "@Injectable(" in content:
                self._parse_provider(ts_file, content)
        
        logger.info(f"Found {len(self.routes)} routes and {len(self.di_edges)} DI edges")
    
    def _parse_controller(self, file_path: Path, content: str) -> None:
        """Parse NestJS controller."""
        try:
            # Extract controller route prefix
            controller_pattern = r'@Controller\([\'"]([^\'"]*)[\'"]?\)'
            controller_match = re.search(controller_pattern, content)
            base_path = controller_match.group(1) if controller_match else ""
            
            # Extract class name
            class_pattern = r'export\s+class\s+(\w+)'
            class_match = re.search(class_pattern, content)
            class_name = class_match.group(1) if class_match else "Controller"
            
            # Find route methods
            method_pattern = r'@(Get|Post|Put|Delete|Patch)\([\'"]?([^\'")\s]*)[\'"]?\)'
            
            for match in re.finditer(method_pattern, content):
                method = match.group(1).upper()
                path = match.group(2) or ""
                full_path = f"/{base_path}/{path}".replace("//", "/")
                
                # Find method name (next function after decorator)
                rest_content = content[match.end():]
                func_pattern = r'\s+async\s+(\w+)\(|^s+(\w+)\('
                func_match = re.search(func_pattern, rest_content)
                handler_name = func_match.group(1) or func_match.group(2) if func_match else "handler"
                
                route = Route(
                    method=method,
                    path=full_path,
                    handler=f"{class_name}.{handler_name}",
                    file_path=str(file_path.relative_to(self.repo_path)),
                    line_number=content[:match.start()].count('\n') + 1
                )
                self.routes.append(route)
        
        except Exception as e:
            logger.warning(f"Failed to parse controller {file_path}: {e}")
    
    def _parse_provider(self, file_path: Path, content: str) -> None:
        """Parse NestJS provider and extract DI relationships."""
        try:
            # Extract class name
            class_pattern = r'export\s+class\s+(\w+)'
            class_match = re.search(class_pattern, content)
            if not class_match:
                return
            
            provider_name = class_match.group(1)
            
            # Find constructor dependencies
            constructor_pattern = r'constructor\(([^)]*)\)'
            constructor_match = re.search(constructor_pattern, content)
            
            if constructor_match:
                params = constructor_match.group(1)
                # Extract parameter types
                param_pattern = r'(?:private|public|protected)?\s+\w+:\s*(\w+)'
                
                for param_match in re.finditer(param_pattern, params):
                    dependency = param_match.group(1)
                    
                    di_edge = DIEdge(
                        provider=dependency,
                        consumer=provider_name,
                        scope="singleton",  # NestJS default
                        file_path=str(file_path.relative_to(self.repo_path))
                    )
                    self.di_edges.append(di_edge)
        
        except Exception as e:
            logger.warning(f"Failed to parse provider {file_path}: {e}")
