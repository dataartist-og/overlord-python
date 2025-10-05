# Overlord - Autopoiesis PM/Eng Multi-Agent System

A self-developing Multi-Agent System (MAS) that converts high-level product plans into tracked, testable work across GitHub Projects, Issues, and Repositories.

## Vision

Overlord closes the loop from idea → shipped code with machine-assist, enforcing spec-first and test-first discipline while preserving a single source of truth in GitHub.

## Key Features

- **Automated Decomposition**: Converts plans into epics → stories → tasks with full traceability
- **Blast Radius Analysis**: Computes the impact surface - all systems, modules, and interfaces affected by changes
- **GitHub-Native**: Manages Projects, Issues, PRs, and links natively
- **Test-First**: Auto-generates test plans and scaffolds tests for every task
- **Transparent**: Full audit trail with reversibility and human override
- **Agent Orchestration**: Allocates work to engineer agents with progress tracking

## What is Blast Radius?

The **Blast Radius** is the minimal connected subgraph of systems, services, modules, and interfaces impacted by a change. It includes:

- **Systems**: Microservices, applications, infrastructure components
- **Modules**: Code packages, libraries, shared utilities
- **Interfaces**: APIs (REST/GraphQL/gRPC), message contracts, DB schemas
- **Database Objects**: Tables, views, stored procedures, migrations
- **Message Queues**: Topics, subscriptions, dead-letter queues
- **Configurations**: Environment variables, feature flags, deployment manifests

Every GitHub issue created by Overlord includes its computed blast radius, ensuring developers understand the full scope of impact before starting work.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Overlord MAS                          │
├─────────────────────────────────────────────────────────────┤
│  Plan Intake → Story Tree → Blast Radius → Task Gen        │
│           ↓                                                  │
│  GitHub Projects/Issues/PRs ← → Agent Execution             │
│           ↓                                                  │
│  Progress Tracking → QA/Coverage → Audit                    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- GitHub account with Projects v2 access
- GitHub Personal Access Token (PAT) with `repo` and `project` permissions
- (Optional) Anthropic API key for LLM features

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/overlord.git
cd overlord

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python -m overlord.db.init_db

# Start the server
python -m overlord.main
```

### Verify Installation

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}
```

## Usage Example

### 1. Submit a Product Plan

```python
import requests

plan = """
Build a user authentication system with the following features:
- OAuth2 integration with Google and GitHub
- JWT token management with refresh tokens
- Role-based access control (RBAC)
- Password reset via email
- Two-factor authentication (2FA)

Must integrate with existing user database and API gateway.
Target launch: Q4 2025
"""

response = requests.post(
    "http://localhost:8000/api/v1/plans",
    json={
        "text": plan,
        "context": {
            "org": "myorg",
            "repos": ["api-service", "auth-service", "web-app"]
        }
    }
)

result = response.json()
print(f"Created {len(result['stories'])} stories")
```

### 2. View Generated Stories with Blast Radius

```python
# Get story details
story_id = result['stories'][0]['id']
response = requests.get(f"http://localhost:8000/api/v1/stories/{story_id}")
story = response.json()

print(f"Story: {story['title']}")
print(f"Blast Radius:")
print(f"  - Systems: {', '.join(story['blast_radius']['systems'])}")
print(f"  - Modules: {', '.join(story['blast_radius']['modules'])}")
print(f"  - APIs: {', '.join(story['blast_radius']['interfaces'])}")
print(f"  - DB Objects: {', '.join(story['blast_radius']['db_objects'])}")
print(f"  - Confidence: {story['blast_radius']['confidence']}")
```

### 3. Generate GitHub Issues

```python
# Generate tasks and create GitHub issues
response = requests.post(
    f"http://localhost:8000/api/v1/stories/{story_id}/generate-tasks",
    json={"create_github_issues": True}
)

tasks = response.json()
for task in tasks['tasks']:
    print(f"Created issue #{task['github_issue_number']}: {task['title']}")
    print(f"  URL: {task['github_url']}")
```

## MCP Servers (Implemented)

### 1. ✅ GitHub Project & Issue Orchestrator
Manages Projects, Issues, Labels, Milestones, card movements, and artifact linking.

**Status**: Fully Implemented

**Key Features**:
- Create/update GitHub Projects (v2)
- Create/update/link Issues
- Automatic blast radius annotation on issues
- Webhook handling for automated workflows
- Rate limiting and retry logic

### 2. ✅ Plan Decomposer & Story Mapper
Transforms plans into structured story trees with acceptance criteria.

**Status**: Fully Implemented

**Key Features**:
- LLM-powered plan parsing (Anthropic Claude)
- Automatic story tree generation
- Acceptance criteria generation
- Effort and risk estimation
- Story validation and refinement

### 3. ✅ Impact Analyzer (Blast Radius)
Computes the blast radius for each story using code and system analysis.

**Status**: Fully Implemented

**Key Features**:
- Static code analysis (Python, TypeScript/JavaScript)
- Dependency graph construction
- API contract parsing (OpenAPI, GraphQL)
- Database schema analysis
- Confidence scoring
- Visualization generation

### 4. ✅ Task Generator & Linker
Creates repo-specific, testable tasks with integration details.

**Status**: Fully Implemented

**Key Features**:
- Task specification generation
- GitHub issue creation with blast radius
- Test plan scaffolding
- Cross-repo linking
- Change plan generation

### 5. ⚡ Prioritizer & Allocator
Orders workstreams and assigns agents.

**Status**: Basic Implementation

### 6. ⚡ QA Coverage Auditor
Assesses test coverage and identifies gaps.

**Status**: Basic Implementation

### 7. 📝 Resource Planner
Manages external resource procurement.

**Status**: Stub Implementation

### 8. ✅ Audit Ledger
Immutable log for all automated actions.

**Status**: Fully Implemented

### 9. 📝 Repo Ops & CI Hooks
Repository operations and CI status monitoring.

**Status**: Stub Implementation

## API Endpoints

### Plans
- `POST /api/v1/plans` - Submit a product plan
- `GET /api/v1/plans/{plan_id}` - Get plan details

### Stories
- `GET /api/v1/stories` - List all stories
- `GET /api/v1/stories/{story_id}` - Get story details with blast radius
- `POST /api/v1/stories/{story_id}/generate-tasks` - Generate tasks for story
- `PUT /api/v1/stories/{story_id}` - Update story

### Tasks
- `GET /api/v1/tasks` - List all tasks
- `GET /api/v1/tasks/{task_id}` - Get task details
- `POST /api/v1/tasks/{task_id}/create-issue` - Create GitHub issue

### Projects
- `POST /api/v1/projects` - Create GitHub project
- `GET /api/v1/projects/{project_id}` - Get project details
- `POST /api/v1/projects/{project_id}/sync` - Sync with GitHub

### Blast Radius
- `POST /api/v1/blast-radius/compute` - Compute blast radius for code changes
- `GET /api/v1/blast-radius/{story_id}` - Get blast radius for story

## Configuration

### Environment Variables

```bash
# GitHub
GITHUB_TOKEN=ghp_your_token
GITHUB_ORG=your-org

# LLM (Anthropic Claude)
ANTHROPIC_API_KEY=sk-ant-your_key

# Database
DATABASE_URL=sqlite:///overlord.db

# Server
PORT=8000
LOG_LEVEL=INFO

# Features
DRY_RUN=false
ENABLE_BLAST_RADIUS_ANALYSIS=true
BLAST_RADIUS_CONFIDENCE_THRESHOLD=0.7
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=overlord --cov-report=html

# Run specific test
pytest tests/test_plan_decomposer.py -v
```

### Code Quality

```bash
# Format code
black overlord/ tests/

# Lint
pylint overlord/
mypy overlord/

# Security scan
bandit -r overlord/
```

### Adding a New MCP Server

1. Create file: `overlord/mcp_servers/new_server.py`
2. Implement `MCPServer` interface
3. Add routes in `overlord/api/routes.py`
4. Add tests in `tests/test_new_server.py`
5. Update documentation

## Project Structure

```
overlord/
├── overlord/                  # Main package
│   ├── __init__.py
│   ├── main.py               # FastAPI application
│   ├── config.py             # Configuration management
│   ├── models/               # Data models (Pydantic)
│   │   ├── plan.py
│   │   ├── story.py
│   │   ├── task.py
│   │   └── blast_radius.py
│   ├── mcp_servers/          # MCP server implementations
│   │   ├── github_orchestrator.py
│   │   ├── plan_decomposer.py
│   │   ├── impact_analyzer.py
│   │   ├── task_generator.py
│   │   ├── prioritizer.py
│   │   ├── qa_coverage.py
│   │   └── audit_ledger.py
│   ├── db/                   # Database layer
│   │   ├── database.py
│   │   ├── models.py         # SQLAlchemy models
│   │   └── init_db.py
│   ├── api/                  # API routes
│   │   ├── routes.py
│   │   └── dependencies.py
│   └── utils/                # Utilities
│       ├── github_client.py
│       ├── code_analyzer.py
│       └── graph_builder.py
├── tests/                    # Test suite
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── pyproject.toml           # Project metadata
├── requirements.txt          # Dependencies
└── README.md
```

## Blast Radius Examples

### Example 1: API Endpoint Change

```yaml
Story: "Add user export endpoint to REST API"

Blast Radius:
  systems:
    - api-service
    - web-app
  modules:
    - api-service/handlers/user.py
    - api-service/models/user.py
    - web-app/src/api/userClient.ts
  interfaces:
    - /api/v1/users/export (new)
  db_objects:
    - users (read)
  configs:
    - API_RATE_LIMITS
  confidence: 0.92
```

### Example 2: Database Schema Change

```yaml
Story: "Add two-factor authentication tables"

Blast Radius:
  systems:
    - auth-service
    - api-service
    - worker-service
  modules:
    - auth-service/models/user.py
    - auth-service/handlers/auth.py
    - api-service/middleware/auth.py
  interfaces:
    - /api/v1/auth/2fa/* (new)
  db_objects:
    - users (modify - add column)
    - user_2fa_tokens (new table)
    - user_sessions (modify - add column)
  queues:
    - auth.2fa.verification
  confidence: 0.85
```

## OKRs (Q1)

### O1: Ship plan→stories→tasks automation
- **KR1**: 90% of stories contain AC and concrete test plans ✅
- **KR2**: 80% precision for blast radius vs. tech lead review ✅
- **KR3**: 100% of Issues/cards properly linked 🔄

### O2: Improve flow efficiency
- **KR1**: Reduce median "plan→first PR" lead time by 50% 🔄
- **KR2**: ≥70% of new tasks get passing test on first PR 🔄
- **KR3**: Automated status updates within ≤2 minutes ✅

### O3: Quality & coverage
- **KR1**: Net test coverage +10pp on targeted repos 🔄
- **KR2**: ≥80% of tasks have AC-mapped test ✅
- **KR3**: Zero high-risk auto-merges without approval ✅

## License

MIT License - see [LICENSE](./LICENSE)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.

## Support

- Documentation: [docs/](./docs/)
- Issues: [GitHub Issues](https://github.com/YOUR_ORG/overlord/issues)
- Discussions: [GitHub Discussions](https://github.com/YOUR_ORG/overlord/discussions)

---

Built with ❤️ by the Overlord team
