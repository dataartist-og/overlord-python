# Code Intelligence Layer - Overlord Extension

## Vision

Give coding agents and developers the **ground truth** about multi-repo projects through framework-aware graphs, dependency analysis, and intelligent search. No more guessing - agents get the same context a senior engineer carries in their head.

## Problem Statement

**Current State**: 
- Agents rely on file contents and basic AST analysis
- No understanding of framework patterns (routes, DI, jobs, entities)
- Blast radius is approximate, missing runtime connections
- No memory of "what broke when we changed X"
- Specs drift from implementation immediately

**Desired State**:
- **Reverse-map reality**: Parse code → build framework-aware graphs → generate dependency summaries
- **Forward spec generation**: Problem → PRD → Stories → Schema → Prototype
- **Continuous sync**: Detect drift between spec and code automatically
- **Agent-accessible**: Expose via MCP so agents can answer "who-calls/what-breaks/how-to" with citations

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Code Intelligence Layer                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Framework-Aware  │  │  Dependency      │  │   Spec-Code      │ │
│  │   Parsers        │→ │  Graph Builder   │→ │   Sync Engine    │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│         ↓                      ↓                       ↓            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Tree-sitter     │  │  NetworkX +      │  │  Drift           │ │
│  │  + AST           │  │  PostgreSQL      │  │  Detection       │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                ↓                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │            MCP Server (Model Context Protocol)                │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  Resources:                    Tools:                         │ │
│  │  • repo://files               • search_code()                 │ │
│  │  • graph://symbols            • who_calls()                   │ │
│  │  • graph://routes             • impact_of()                   │ │
│  │  • graph://di                 • get_symbol()                  │ │
│  │  • graph://jobs               • diff_spec_vs_code()           │ │
│  │  • kb://summaries             • generate_reverse_prd()        │ │
│  │  • docs://{pkg}@{version}     • add_library()                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                ↓                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              Enhanced Blast Radius Engine                     │ │
│  │  • Framework-aware impact (routes, DI, jobs)                  │ │
│  │  • Test coverage mapping                                      │ │
│  │  • Runtime dependency tracking                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Framework-Aware Parsers

Parse code with understanding of framework patterns:

**Web Frameworks**:
- **Next.js**: Pages/App Router, API routes, Server Actions, Middleware
- **NestJS**: Controllers, Providers, Modules, Guards, Interceptors
- **Django**: Views, URLs, Models, Middleware, Signals
- **Spring**: Controllers, Services, Repositories, Beans, Aspects
- **FastAPI**: Routes, Dependencies, Middleware, Background Tasks

**Features Extracted**:
- Routes → Handlers → Services → Repositories (full flow)
- DI/IoC containers (who provides, who consumes)
- Background jobs, schedulers, queues, listeners
- ORM entities and their relationships
- Auth guards, middleware chains
- Database migrations

### 2. Multi-Level Graphs

Build interconnected graphs:

```python
# File Graph (imports)
files: {
  "src/users/service.ts": {
    imports: ["src/db/connection", "src/auth/jwt"],
    exports: ["UserService"]
  }
}

# Symbol Graph (caller ↔ callee)
symbols: {
  "UserService.create": {
    calls: ["Database.insert", "EmailService.send"],
    called_by: ["UserController.register", "AdminService.bulkCreate"]
  }
}

# Framework Graphs (routes, DI, jobs)
routes: {
  "POST /api/users": {
    handler: "UserController.create",
    middleware: ["AuthGuard", "RateLimiter"],
    flow: ["validate", "service.create", "respond"]
  }
}

di_graph: {
  "UserService": {
    provides: "IUserService",
    consumes: ["DatabaseConnection", "EmailService"],
    scope: "singleton"
  }
}

jobs: {
  "send-daily-digest": {
    schedule: "0 9 * * *",
    handler: "DigestService.send",
    dependencies: ["UserRepository", "EmailService"]
  }
}
```

### 3. Dependency-Aware Summaries

For each symbol/file/feature, generate:

```yaml
symbol: UserService.create
purpose: Creates a new user account with validation and notification
inputs:
  - email: string (validated, unique)
  - password: string (hashed)
  - metadata: UserMetadata (optional)
outputs:
  - User object with id, email, created_at
  - Returns null if validation fails
side_effects:
  - DB: INSERT into users table
  - Network: Sends welcome email via SendGrid
  - Cache: Invalidates user list cache
  - Events: Emits user.created event
invariants:
  - Email must be unique
  - Password must be hashed before storage
  - User ID is auto-generated
error_paths:
  - DuplicateEmailError: If email exists
  - ValidationError: If inputs invalid
  - EmailServiceError: If notification fails (non-blocking)
tests:
  - tests/users/service.test.ts:45-67 (happy path)
  - tests/users/service.test.ts:69-82 (duplicate email)
  - tests/integration/user-flow.test.ts:10-30 (full flow)
blast_radius:
  affects: ["/api/users", "/api/admin/users", "RegisterForm.tsx"]
  impacts: ["users table", "email queue", "user cache"]
```

### 4. MCP Server

Expose via Model Context Protocol:

**Resources** (read-only context):
- `repo://files` - File metadata with language, SHA, path
- `graph://symbols` - Functions/classes with call graphs
- `graph://routes` - Web routes with handlers and middleware
- `graph://di` - Dependency injection graph
- `graph://jobs` - Background jobs and schedules
- `kb://summaries` - Dependency-aware summaries
- `docs://{pkg}@{version}` - External library documentation

**Tools** (actions agents can invoke):
- `search_code(query, repo, topK)` - Hybrid search with citations
- `get_symbol(symbol_id)` - Full symbol details with graph
- `who_calls(symbol_id)` - All callers with file/line
- `list_dependencies(symbol_id)` - Dependencies graph
- `impact_of(change)` - **Enhanced blast radius**
- `search_docs(query, pkg, version)` - External docs search
- `diff_spec_vs_code(feature_id)` - Detect drift
- `generate_reverse_prd(feature_id)` - Generate spec from code
- `add_library(pkg_or_repo)` - Index external library

## Enhanced Blast Radius

The existing blast radius gets supercharged:

**Before** (Current Overlord):
```python
blast_radius = {
    "systems": ["api-service"],
    "modules": ["handlers/user.py"],
    "interfaces": ["/api/v1/users"],
    "confidence": 0.75
}
```

**After** (With Code Intelligence):
```python
enhanced_blast_radius = {
    # Traditional impacts
    "systems": ["api-service", "web-app"],
    "modules": ["handlers/user.py", "services/user.py"],
    "interfaces": ["/api/v1/users", "/api/v1/admin/users"],
    
    # Framework-aware impacts
    "routes_affected": [
        {"method": "POST", "path": "/api/users", "handler": "UserController.create"},
        {"method": "GET", "path": "/api/users/:id", "handler": "UserController.get"}
    ],
    "di_changes": [
        {"service": "UserService", "providers": ["UserRepository"], "consumers": ["AdminService"]}
    ],
    "job_impacts": [
        {"job": "send-daily-digest", "reason": "uses UserRepository"}
    ],
    
    # Runtime dependencies
    "database_impacts": [
        {"table": "users", "operation": "INSERT/UPDATE", "migration": "v1.5.0"}
    ],
    "cache_impacts": ["user-list", "user-profile-*"],
    "queue_impacts": ["email-queue"],
    
    # Test coverage
    "tests_affected": [
        {"file": "tests/users/service.test.ts", "lines": "45-67", "coverage": "direct"},
        {"file": "tests/integration/user-flow.test.ts", "lines": "10-30", "coverage": "indirect"}
    ],
    "test_gaps": ["No tests for duplicate email scenario"],
    
    # Historical data
    "past_breakages": [
        {"date": "2024-09-15", "issue": "AUTH-123", "reason": "Missing email validation"}
    ],
    
    "confidence": 0.92,
    "analysis_depth": "deep",
    "framework_aware": true
}
```

## Use Cases

### 1. Onboarding New Developers

**Before**:
```
Dev: "How does user authentication work?"
Response: *reads through 15 files manually*
```

**After**:
```python
result = mcp_client.call_tool("search_code", {
    "query": "user authentication flow",
    "repo": "api-service",
    "topK": 5
})

# Returns:
# 1. Route: POST /auth/login → AuthController.login
# 2. Flow: validate → AuthService.verify → JWTService.sign
# 3. Dependencies: UserRepository, RedisCache
# 4. Tests: auth.test.ts:10-45, integration/auth-flow.test.ts:5-30
# 5. Summaries: Purpose, inputs, outputs, error paths
```

### 2. Impact Analysis Before Refactoring

**Before**:
```
Dev: "Can I change UserService.create signature?"
Response: *manually grep, hope for the best*
```

**After**:
```python
impact = mcp_client.call_tool("impact_of", {
    "change": {
        "symbol": "UserService.create",
        "type": "signature_change",
        "details": "add optional metadata param"
    }
})

# Returns:
# Callers: UserController.register, AdminService.bulkCreate
# Routes: POST /api/users, POST /api/admin/users
# Jobs: None
# Tests: 3 direct, 5 indirect
# Migration needed: No
# Breaking: No (optional param)
# Confidence: 0.95
```

### 3. Spec-Code Drift Detection

**Scenario**: Story says "users can reset password via email", but code has SMS too.

```python
drift = mcp_client.call_tool("diff_spec_vs_code", {
    "feature_id": "AUTH-42",
    "repo": "api-service"
})

# Returns:
# Added in code (not in spec):
#   - POST /auth/reset-password/sms
#   - SMSService dependency
#   
# Missing from code (in spec):
#   - Rate limiting on reset endpoint
#   
# Recommendations:
#   - Update spec to include SMS flow OR
#   - Remove SMS implementation
#   - Add rate limiting middleware
```

### 4. Agent-Assisted Development

**Agent with MCP**:
```
User: "Add a feature to export user data as CSV"

Agent (internally):
1. search_code("user export") → finds similar CSV exports
2. who_calls("UserService.list") → understands usage patterns
3. impact_of("add UserService.export") → checks blast radius
4. get_symbol("CSVService") → learns CSV generation pattern

Agent: "I'll add UserService.export that:
- Follows the pattern in OrderService.exportCSV
- Calls UserRepository.findAll (no new DB query needed)
- Uses existing CSVService (already in DI container)
- Adds route POST /api/users/export protected by AuthGuard
- Requires migration: No
- Blast radius: Low (new endpoint, existing services)
- Tests needed: users/export.test.ts"
```

## Storage Layer

```python
# PostgreSQL schema
tables:
  - repositories
  - files (path, language, sha, content_vector)
  - symbols (name, kind, file_id, start_line, end_line)
  - symbol_calls (caller_id, callee_id, call_type)
  - routes (method, path, handler_symbol_id)
  - di_edges (provider_symbol_id, consumer_symbol_id)
  - jobs (name, schedule, handler_symbol_id)
  - summaries (symbol_id, summary_text, embedding)
  - library_docs (package, version, content, embedding)
  - spec_items (type, repo_id, reference_id)
  - drift_reports (spec_item_id, code_reference, drift_type)

# Indexes
indexes:
  - GIN index on content_vector (pgvector)
  - GiST index on symbol_calls (graph queries)
  - FTS index on summaries (keyword search)
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Set up PostgreSQL + pgvector
- [ ] Build Tree-sitter parsers for 2 languages (TypeScript, Python)
- [ ] Create symbol graph builder
- [ ] Implement basic MCP server (search_code, get_symbol)

### Phase 2: Framework Awareness (Week 3-4)
- [ ] Add Next.js route parser
- [ ] Add NestJS DI parser
- [ ] Build route graph
- [ ] Build DI graph
- [ ] Implement who_calls, list_dependencies tools

### Phase 3: Enhanced Blast Radius (Week 5-6)
- [ ] Integrate with existing Overlord blast radius
- [ ] Add framework-aware impact analysis
- [ ] Add test coverage mapping
- [ ] Implement impact_of tool with deep analysis

### Phase 4: Summaries & Search (Week 7-8)
- [ ] Generate dependency-aware summaries with LLM
- [ ] Build hybrid search (vector + FTS + RRF)
- [ ] Add search_docs for external libraries
- [ ] Cache and optimize queries

### Phase 5: Spec-Code Sync (Week 9-10)
- [ ] Link stories to code symbols
- [ ] Build drift detection
- [ ] Implement diff_spec_vs_code
- [ ] Add generate_reverse_prd

### Phase 6: Polish & Scale (Week 11-12)
- [ ] Add more frameworks (Django, Spring, FastAPI)
- [ ] Monorepo support with ownership boundaries
- [ ] Runtime tracing for dynamic code
- [ ] Performance optimization
- [ ] Documentation and examples

## Success Metrics

**Developer Experience**:
- ⏱️ Onboarding time reduced by 60%
- 🎯 Refactor confidence increased (fewer breakages)
- 🚀 Feature development 30% faster (less discovery time)

**Code Quality**:
- 📊 Test coverage visibility improves
- 🔍 Spec-code drift detected in <1 hour
- 💥 Blast radius accuracy >90%

**Agent Effectiveness**:
- ✅ 80% of agent suggestions are actually correct
- 📚 Citations provided for all recommendations
- 🛡️ Breaking changes predicted before PR

## Getting Started

See [CODE_INTELLIGENCE_QUICKSTART.md](./CODE_INTELLIGENCE_QUICKSTART.md) for implementation guide.

## Related Documents

- [README.md](./README.md) - Overlord overview
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Current implementation
- [MCP_SERVER_SPEC.md](./docs/MCP_SERVER_SPEC.md) - MCP protocol details
- [FRAMEWORK_PARSERS.md](./docs/FRAMEWORK_PARSERS.md) - Parser implementation guide
