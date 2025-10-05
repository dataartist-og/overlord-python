# Overlord Quick Start Guide

Get up and running with Overlord in minutes!

## Prerequisites

- **Python 3.10+** ([download](https://www.python.org/downloads/))
- **Git**
- **GitHub account** with:
  - Personal Access Token (PAT) with `repo` and `project` scopes
  - Access to an organization or personal repos
- **Anthropic API key** for LLM features ([get key](https://console.anthropic.com/))

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_ORG/overlord.git
cd overlord
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required environment variables:**

```bash
# .env file
GITHUB_TOKEN=ghp_YOUR_GITHUB_TOKEN
GITHUB_ORG=your-org-name
ANTHROPIC_API_KEY=sk-ant-YOUR_ANTHROPIC_KEY
```

**Getting tokens:**

**GitHub Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (all) and `project` (all)
4. Copy token to `.env` file

**Anthropic API Key:**
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Create account or sign in
3. Navigate to API Keys
4. Create new key and copy to `.env` file

### 5. Start the Server

```bash
python -m overlord.main
```

Or use uvicorn directly:

```bash
uvicorn overlord.main:app --reload
```

The server will start on `http://localhost:8000`

## Verify Installation

Check if Overlord is running:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "services": {
    "github": true,
    "plan_decomposer": true,
    "impact_analyzer": true,
    "task_generator": true
  }
}
```

Visit the interactive API docs: http://localhost:8000/docs

## Quick Tutorial

### 1. Submit a Product Plan

Create a file `plan.json`:

```json
{
  "text": "Build a user authentication system with OAuth2 support for Google and GitHub. Include JWT token management, role-based access control (RBAC), password reset via email, and two-factor authentication (2FA). Must integrate with existing user database and API gateway. Target launch: Q4 2025",
  "context": {
    "org": "myorg",
    "repos": ["myorg/api-service", "myorg/web-app"]
  },
  "auto_generate_stories": true,
  "compute_blast_radius": true
}
```

Submit the plan:

```bash
curl -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d @plan.json
```

This will:
- Parse the plan and extract objectives
- Generate user stories
- Compute blast radius for each story
- Return story IDs

### 2. View Generated Stories

```bash
# List all stories
curl http://localhost:8000/api/v1/stories | jq

# Get specific story with blast radius
curl http://localhost:8000/api/v1/stories/{story-id} | jq
```

**Example response:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Implement OAuth2 authentication flow",
  "user_value": "As a user, I want to log in with Google or GitHub, so that I don't need to create another password",
  "acceptance_criteria": [
    "Given a user visits login page, When they click 'Login with Google', Then they are redirected to Google OAuth",
    "Given successful OAuth, When user returns, Then a JWT token is issued",
    "Given an invalid OAuth response, When user returns, Then an error message is displayed"
  ],
  "blast_radius": {
    "systems": ["api-service", "web-app"],
    "modules": [
      "api-service/handlers/auth.py",
      "web-app/src/components/Login.tsx"
    ],
    "interfaces": [
      "/api/v1/auth/oauth/google",
      "/api/v1/auth/oauth/github"
    ],
    "db_objects": ["users", "oauth_tokens"],
    "confidence": 0.85,
    "risk_level": "Medium"
  },
  "risk": "Medium",
  "priority": "P1",
  "estimate": "5-8d"
}
```

### 3. Generate Tasks from Story

```bash
curl -X POST "http://localhost:8000/api/v1/stories/{story-id}/generate-tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "123e4567-e89b-12d3-a456-426614174000",
    "repos": ["myorg/api-service", "myorg/web-app"],
    "include_tests": true,
    "create_github_issues": true
  }'
```

This will:
- Generate repository-specific tasks
- Include change plans and integration points
- Generate test plans
- Create GitHub issues (if `create_github_issues: true`)

**Example task:**

```json
{
  "id": "456e7890-e89b-12d3-a456-426614174001",
  "story_id": "123e4567-e89b-12d3-a456-426614174000",
  "repo": "myorg/api-service",
  "title": "[api-service] Implement OAuth2 authentication flow",
  "change_plan": [
    {
      "action": "add",
      "path": "handlers/oauth.py",
      "description": "New OAuth handler"
    },
    {
      "action": "edit",
      "path": "handlers/auth.py",
      "description": "Update based on story requirements"
    }
  ],
  "integration_points": [
    "/api/v1/auth/oauth/google",
    "/api/v1/auth/oauth/github",
    "db.users",
    "db.oauth_tokens"
  ],
  "test_plan": {
    "unit": [
      "Test OAuth token validation",
      "Test user creation from OAuth response"
    ],
    "contract": [
      "Test /api/v1/auth/oauth/* contract"
    ],
    "e2e": [
      "Test complete OAuth flow end-to-end"
    ]
  },
  "github_issue_number": 42,
  "github_url": "https://github.com/myorg/api-service/issues/42",
  "risk": "Medium",
  "estimate": "3-5d"
}
```

### 4. View GitHub Issues

The generated GitHub issues will include:
- ✅ Acceptance criteria
- 💥 **Blast radius** (systems, modules, APIs, databases impacted)
- 🔧 Change plan
- 🧪 Test plan
- 🔌 Integration points

Go to your repository on GitHub to see the issues!

## Using Python Client

```python
import requests

# Configuration
BASE_URL = "http://localhost:8000"

# Submit a plan
plan_response = requests.post(
    f"{BASE_URL}/api/v1/plans",
    json={
        "text": "Your product plan here...",
        "context": {
            "org": "myorg",
            "repos": ["myorg/api-service"]
        },
        "auto_generate_stories": True,
        "compute_blast_radius": True
    }
)

plan_data = plan_response.json()
print(f"Created plan: {plan_data['plan']['id']}")
print(f"Generated {plan_data['stories_created']} stories")

# Get stories
stories = requests.get(f"{BASE_URL}/api/v1/stories").json()

for story in stories['stories']:
    print(f"\nStory: {story['title']}")
    print(f"Risk: {story['risk']}")
    print(f"Blast Radius Impact: {story['blast_radius']['total_impact_count']} items")
    
    # Generate tasks
    tasks_response = requests.post(
        f"{BASE_URL}/api/v1/stories/{story['id']}/generate-tasks",
        json={
            "story_id": story['id'],
            "repos": ["myorg/api-service"],
            "include_tests": True,
            "create_github_issues": True
        }
    )
    
    tasks = tasks_response.json()
    print(f"Generated {len(tasks['tasks'])} tasks")
    
    for task in tasks['tasks']:
        if task.get('github_url'):
            print(f"  - GitHub Issue: {task['github_url']}")
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=overlord --cov-report=html

# Run specific test
pytest tests/test_blast_radius.py -v
```

## API Documentation

Once the server is running, visit:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative docs (ReDoc)**: http://localhost:8000/redoc

## Common Operations

### Compute Blast Radius for Existing Story

```bash
curl -X POST http://localhost:8000/api/v1/blast-radius/compute \
  -H "Content-Type: application/json" \
  -d '{
    "story_id": "your-story-id",
    "repos": ["myorg/api-service"],
    "depth": 3
  }'
```

### List All Tasks

```bash
curl http://localhost:8000/api/v1/tasks | jq
```

### Filter Tasks by Repository

```bash
curl "http://localhost:8000/api/v1/tasks?repo=myorg/api-service" | jq
```

## Development

### Code Quality

```bash
# Format code
black overlord/ tests/

# Lint
pylint overlord/

# Type check
mypy overlord/
```

### Hot Reload

```bash
uvicorn overlord.main:app --reload
```

## Troubleshooting

### Port Already in Use

```bash
# Change port in .env
PORT=8001

# Or specify when running
PORT=8001 python -m overlord.main
```

### GitHub API Rate Limit

Check rate limit:

```bash
curl http://localhost:8000/api/v1/github/rate-limit
```

Solutions:
- Use GitHub App token (higher limits)
- Enable caching
- Reduce batch sizes

### Missing Anthropic API Key

If you see "Plan Decomposer not available":

1. Get API key from https://console.anthropic.com/
2. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-your-key`
3. Restart server

### Blast Radius Shows Low Confidence

Improve blast radius accuracy:
- Add local repo paths to analyze code
- Increase analysis depth
- Ensure repo structure follows conventions

## Next Steps

1. **Read the docs**: Check out `/docs` directory
2. **Explore API**: Use Swagger UI at `/docs`
3. **Add repositories**: Configure repository paths for code analysis
4. **Customize**: Adjust settings in `.env` for your workflow
5. **Integrate**: Connect to your CI/CD pipeline

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              Your Product Plan              │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│         Plan Decomposer (LLM)               │
│  • Parse objectives, constraints, risks     │
│  • Generate user stories with AC            │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Impact Analyzer (Blast Radius)         │
│  • Analyze code dependencies                │
│  • Identify impacted systems/modules        │
│  • Calculate risk and confidence            │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│          Task Generator                      │
│  • Create repo-specific tasks               │
│  • Generate change plans                    │
│  • Create test strategies                   │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      GitHub Orchestrator                     │
│  • Create GitHub issues with blast radius   │
│  • Link stories to tasks                    │
│  • Track progress                           │
└─────────────────────────────────────────────┘
```

## Support

- **Documentation**: [README.md](./README.md)
- **API Docs**: http://localhost:8000/docs
- **Issues**: [GitHub Issues](https://github.com/YOUR_ORG/overlord/issues)

Happy building! 🚀
