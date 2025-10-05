# Code Intelligence Quick Start

Get ground truth about your codebase with framework-aware analysis and MCP access.

## What You Get

🧠 **Framework-Aware Understanding**:
- Routes → Handlers → Services → Repositories (full flow)
- Dependency Injection graphs (who provides, who consumes)
- Background jobs and schedules
- Database entities and relationships

🔍 **Deep Code Analysis**:
- Symbol-level call graphs (who calls what)
- File import dependencies
- Transitive dependency tracking
- Impact analysis with confidence scores

💥 **Enhanced Blast Radius**:
- Framework-specific impacts (routes, DI, jobs affected)
- Test coverage mapping
- Historical breakage data
- Risk assessment with recommendations

🤖 **MCP Server for Agents**:
- Resources: files, symbols, routes, DI graph, jobs
- Tools: search_code, who_calls, impact_of, get_symbol
- Agents get citations and ground truth, not guesses

## Installation

Already included in Overlord! The code intelligence layer is integrated.

## Quick Examples

### 1. Build Code Graphs

```python
from overlord.code_intelligence import CodeGraphBuilder

# Initialize for a Next.js project
builder = CodeGraphBuilder(
    repo_path="/path/to/nextjs-project",
    framework="nextjs"
)

# Build all graphs
graphs = builder.build_all_graphs()

print(f"Files: {graphs['files'].number_of_nodes()}")
print(f"Symbols: {graphs['symbols'].number_of_nodes()}")
print(f"Routes: {len(builder.routes)}")
print(f"DI edges: {len(builder.di_edges)}")
```

### 2. Find Who Calls a Function

```python
# Get all callers of UserService.create
callers = builder.get_callers("src/users/service.ts::UserService.create")

for caller_id in callers:
    caller = builder.symbols[caller_id]
    print(f"Called by: {caller.name} at {caller.file_path}:{caller.start_line}")

# Output:
# Called by: UserController.register at src/users/controller.ts:45
# Called by: AdminService.bulkCreate at src/admin/service.ts:89
```

### 3. Compute Enhanced Blast Radius

```python
from overlord.code_intelligence import EnhancedBlastRadiusEngine
from overlord.models import Story

# Create story
story = Story(
    title="Add user export functionality",
    user_value="As an admin, I want to export user data, so I can analyze it",
    acceptance_criteria=[
        "Given admin permissions, When clicking Export, Then CSV downloads"
    ]
)

# Initialize enhanced engine
engine = EnhancedBlastRadiusEngine(
    graph_builders={"api-service": builder}
)

# Compute enhanced blast radius
blast_radius = engine.compute_enhanced_blast_radius(
    story=story,
    repos=["api-service"],
    depth=3
)

print(f"Risk Level: {blast_radius.risk_level}")
print(f"Confidence: {blast_radius.confidence:.0%}")
print(f"Routes affected: {len(blast_radius.interfaces)}")
print(f"Modules affected: {len(blast_radius.modules)}")
print(f"DB objects: {', '.join(blast_radius.db_objects)}")

# Output:
# Risk Level: Medium
# Confidence: 88%
# Routes affected: 2
# Modules affected: 5
# DB objects: users, user_exports
```

### 4. Get Detailed Impact Report

```python
report = engine.get_detailed_impact_report(
    story=story,
    repos=["api-service"],
    depth=3
)

print("Summary:")
for key, value in report["summary"].items():
    print(f"  {key}: {value}")

print("\nRecommendations:")
for rec in report["recommendations"]:
    print(f"  {rec}")

# Output:
# Summary:
#   total_impact: 7
#   risk_level: Medium
#   confidence: 0.88
#   systems: 1
#   modules: 5
#   apis: 2
#   databases: 2
#
# Recommendations:
#   ⚠️ Database changes required - prepare migration scripts
#   ⚠️ Many API endpoints affected - update API documentation
```

### 5. Use MCP Server

```python
from overlord.code_intelligence import CodeIntelligenceMCP

# Initialize MCP server
mcp = CodeIntelligenceMCP(
    repos={
        "api-service": "/path/to/api-service",
        "web-app": "/path/to/web-app"
    },
    frameworks={
        "api-service": "nestjs",
        "web-app": "nextjs"
    }
)

# Resource: Get all routes
routes = mcp.get_resource_routes("api-service")
print(f"Found {routes['total']} routes")

for route in routes['routes'][:3]:
    print(f"  {route['method']} {route['path']} → {route['handler']}")

# Tool: Search code
results = mcp.tool_search_code(
    query="user authentication",
    repo="api-service",
    top_k=5
)

for result in results['results']:
    print(f"  {result['name']} ({result['kind']}) at {result['file']}:{result['line']}")

# Tool: Impact analysis
impact = mcp.tool_impact_of(
    change={
        "symbol_ids": ["src/users/service.ts::UserService.create"],
        "type": "signature_change"
    },
    repo="api-service",
    depth=3
)

print(f"Routes affected: {len(impact['blast_radius']['routes_affected'])}")
print(f"Files affected: {len(impact['blast_radius']['files_affected'])}")
```

## Framework Support

### Next.js

**What's Extracted**:
- App Router pages (`app/page.tsx`)
- Pages Router pages (`pages/*.tsx`)
- API routes (both App and Pages Router)
- Dynamic routes (`[id]`, `[...slug]`)
- Route groups `(group)`
- Middleware patterns

```python
from overlord.code_intelligence import NextJSParser

parser = NextJSParser("/path/to/nextjs-app")
parser.parse()

for route in parser.routes:
    print(f"{route.method} {route.path} → {route.handler}")

# Output:
# GET / → Home
# GET /users/:id → page.UserProfile
# POST /api/users → handler.POST
# GET /api/users/:id → handler.GET
```

### NestJS

**What's Extracted**:
- Controllers and routes (`@Get()`, `@Post()`, etc.)
- Providers and services (`@Injectable()`)
- Dependency injection (constructor params)
- Guards, interceptors, pipes
- Module structure

```python
from overlord.code_intelligence import NestJSParser

parser = NestJSParser("/path/to/nestjs-app")
parser.parse()

# Routes
for route in parser.routes:
    print(f"{route.method} {route.path} → {route.handler}")

# DI edges
for edge in parser.di_edges:
    print(f"{edge.consumer} depends on {edge.provider}")

# Output:
# POST /users → UserController.create
# GET /users/:id → UserController.findOne
# UserController depends on UserService
# UserService depends on UserRepository
```

## Integration with Overlord API

The code intelligence layer integrates seamlessly with Overlord's existing API:

### Enhanced Plan → Stories → Tasks Flow

```python
import requests

# Submit plan with enhanced blast radius
response = requests.post("http://localhost:8000/api/v1/plans", json={
    "text": "Add user export feature with CSV and JSON formats",
    "context": {
        "org": "myorg",
        "repos": ["myorg/api-service"],
        "repo_paths": {
            "myorg/api-service": "/Users/me/api-service"
        }
    },
    "auto_generate_stories": True,
    "compute_blast_radius": True
})

# Stories now have enhanced blast radius with:
# - Framework-aware impacts (routes, DI, jobs)
# - Test coverage info
# - Historical breakage data
# - Confidence scores

stories = response.json()['plan']['story_ids']
```

## Real-World Use Cases

### Use Case 1: Onboarding New Developer

**Before**: "Read through the codebase for 2 weeks"

**After**:
```python
# What does the authentication flow look like?
routes = mcp.get_resource_routes("api-service")
auth_routes = [r for r in routes['routes'] if 'auth' in r['path'].lower()]

for route in auth_routes:
    print(f"{route['method']} {route['path']}")
    
    # Get handler details
    handler_info = mcp.tool_get_symbol(
        symbol_id=f"{route['file']}::{route['handler']}",
        repo="api-service"
    )
    
    print(f"  Calls: {', '.join(handler_info['callees'])}")
    print(f"  File: {route['file']}:{route['line']}")

# Output:
# POST /auth/login
#   Calls: AuthService.validateCredentials, JWTService.sign
#   File: src/auth/controller.ts:45
# POST /auth/register
#   Calls: UserService.create, EmailService.sendWelcome
#   File: src/auth/controller.ts:78
```

### Use Case 2: Impact Analysis Before Refactor

**Question**: "Can I change UserService.create to require email verification?"

```python
# Analyze impact
impact = mcp.tool_impact_of(
    change={
        "symbol_ids": ["src/users/service.ts::UserService.create"],
        "type": "signature_change",
        "details": "add required emailVerified parameter"
    },
    repo="api-service",
    depth=3
)

print(f"Callers: {len(impact['blast_radius']['symbols_affected'])}")
print(f"Routes: {len(impact['blast_radius']['routes_affected'])}")
print(f"Breaking: {'Yes' if impact['blast_radius']['confidence'] < 0.7 else 'Likely not'}")

print("\nRecommendations:")
for rec in impact['recommendations']:
    print(f"  {rec}")

# Output:
# Callers: 3
# Routes: 2
# Breaking: Likely not
#
# Recommendations:
#   ⚠️ 2 routes affected - update API docs
#   ⚠️ 3 DI consumers affected - check interface compatibility
```

### Use Case 3: Agent-Assisted Development

**User**: "Add an endpoint to export users as CSV"

**Agent** (using MCP tools):

```python
# 1. Search for similar functionality
similar = mcp.tool_search_code(
    query="export CSV",
    repo="api-service",
    top_k=5
)
# Finds: OrderService.exportCSV

# 2. Check UserService dependencies
user_service = mcp.tool_get_symbol(
    symbol_id="src/users/service.ts::UserService",
    repo="api-service"
)
# Already has UserRepository

# 3. Calculate impact of new method
impact = mcp.tool_impact_of(
    change={
        "symbol_ids": ["src/users/service.ts::UserService"],
        "type": "add_method",
        "details": "exportUsersCSV"
    },
    repo="api-service"
)

# Agent response:
"""
I'll add UserService.exportUsersCSV following the pattern from OrderService.exportCSV.

Implementation plan:
1. Add method to UserService (uses existing UserRepository)
2. Add route POST /api/users/export to UserController
3. Use CSVService (already in DI container)
4. Requires: No new dependencies
5. Tests needed: users/export.test.ts
6. Blast radius: Low (new endpoint, existing services)
7. Similar code at: src/orders/service.ts:234
"""
```

## Best Practices

### 1. Keep Graphs Fresh

```python
# Re-index after significant changes
builder.build_all_graphs()

# Or watch for file changes
import watchdog
# ... implement file watcher
```

### 2. Use Depth Wisely

```python
# Quick check (depth=1)
impact = engine.compute_enhanced_blast_radius(story, repos, depth=1)

# Thorough analysis (depth=3-5)
impact = engine.compute_enhanced_blast_radius(story, repos, depth=3)

# Comprehensive (depth=5+, slower)
impact = engine.compute_enhanced_blast_radius(story, repos, depth=5)
```

### 3. Combine with Existing Tools

```python
# Use enhanced blast radius in Overlord workflows
from overlord.mcp_servers import PlanDecomposer, TaskGenerator

# Generate stories
stories = plan_decomposer.generate_stories(plan)

# Enhance each with code intelligence
for story in stories:
    blast_radius = engine.compute_enhanced_blast_radius(
        story, repos=["api-service", "web-app"]
    )
    story.blast_radius = blast_radius

# Generate tasks with enhanced context
tasks = task_generator.generate_tasks(story, repos=["api-service"])
```

## Troubleshooting

### "Repository not found"

Ensure repo paths are configured:
```python
builder = CodeGraphBuilder(
    repo_path="/absolute/path/to/repo",
    framework="nextjs"
)
```

### "No routes found"

Check framework detection:
```python
# Next.js: needs app/ or pages/ directory
# NestJS: needs @Controller decorators

parser = NextJSParser(repo_path)
parser.parse()
print(f"Found {len(parser.routes)} routes")
```

### "Low confidence scores"

- Add more repos to analyze
- Increase analysis depth
- Check for dynamic code that needs runtime tracing
- Ensure framework is correctly detected

## Next Steps

1. **Try it**: Run examples with your codebase
2. **Integrate**: Add to your Overlord workflows
3. **Extend**: Add support for your framework
4. **Scale**: Set up PostgreSQL for larger codebases

## More Resources

- [CODE_INTELLIGENCE.md](./CODE_INTELLIGENCE.md) - Full architecture
- [MCP_SERVER_SPEC.md](./docs/MCP_SERVER_SPEC.md) - MCP protocol details
- [FRAMEWORK_PARSERS.md](./docs/FRAMEWORK_PARSERS.md) - Add new frameworks
- [README.md](./README.md) - Overlord overview

Happy coding! 🚀
