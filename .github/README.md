# GitHub Actions CI/CD

This directory contains GitHub Actions workflows for the Orbit project.

## Workflows

### `ci.yml` - Continuous Integration
Runs on every push and pull request to ensure code quality and functionality.

**Checks performed:**
- **Python Agent** (`agent/oribit_agent/`)
  - Dependencies installation with `uv sync`
  - Code linting with `ruff check`
  - Code formatting check with `black --check`
  - Type checking with `mypy`
  - Unit tests with `pytest`

- **Frontend** (`app/Orbit/`)
  - Dependencies installation with `pnpm install`
  - TypeScript compilation and type checking
  - Production build with Tauri

- **Swift Helper** (`helper/OrbitHelper/`)
  - Xcode build validation
  - Basic functionality tests

- **Project Validation**
  - Required files and directory structure
  - Integration test execution

## Local Development

Before pushing code, you can run checks locally:

```bash
# Install and run git hooks
brew install lefthook  # or npm install -g lefthook
lefthook install
lefthook run pre-commit

# Or run individual checks
cd agent/oribit_agent && uv run ruff check . && uv run black --check . && uv run mypy src
cd app/Orbit && pnpm run type-check && pnpm run build
cd helper/OrbitHelper && xcodebuild -project OrbitHelper.xcodeproj -scheme OrbitHelper build
```

## Requirements

The CI runner uses:
- **OS**: macOS (latest)
- **Node.js**: 20
- **Python**: 3.11
- **pnpm**: 9
- **uv**: Latest via pipx
- **Xcode**: Latest available on GitHub Actions macOS runner