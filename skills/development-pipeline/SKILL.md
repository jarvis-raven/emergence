# Development Pipeline Skill

> **Complete workflow from idea to production** — Branching, issues, PRs, reviews, releases, and room-specific workflows for the Emergence project.

**Author:** Kimi (Agent)  
**Created:** 2026-02-15  
**Version:** 1.0.0  
**Status:** Active

---

## Table of Contents

1. [Branching Strategy](#1-branching-strategy)
2. [Issue Management](#2-issue-management)
3. [Development Workflow](#3-development-workflow)
4. [PR Process](#4-pr-process)
5. [Jarvling Collaboration](#5-jarvling-collaboration)
6. [Release Management](#6-release-management)
7. [Room-Specific Workflows](#7-room-specific-workflows)

---

## 1. Branching Strategy

### Branch Naming Conventions

Emergence uses a **prefix-based naming system** aligned with conventional commits:

```
feature/<description>   # New features or enhancements
fix/<description>       # Bug fixes
hotfix/<description>    # Urgent production fixes
docs/<description>      # Documentation updates
refactor/<description>  # Code restructuring without feature changes
test/<description>      # Test additions or fixes
chore/<description>     # Maintenance tasks
spike/<description>     # Experimental/exploratory work
```

**Examples from recent PRs:**
- `feature/nautilus-beta-core` (#80)
- `feature/nautilus-beta-dashboard` (#81)
- `fix/82-room-build-aspirations` (#82)
- `spike/realtime-drive-updates`

### Branch Lifecycle

#### 1. **Creation**

```bash
# Always branch from main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/short-descriptive-name

# For issue-specific work
git checkout -b fix/103-development-pipeline-skill
```

**Naming Guidelines:**
- Use kebab-case (lowercase with hyphens)
- Keep it short but descriptive (3-5 words max)
- Include issue number for trackability
- Avoid generic names like `bugfix` or `update`

#### 2. **Development**

```bash
# Regular commits during development
git add <files>
git commit -m "type(scope): description"

# Push to remote
git push origin feature/your-branch-name
```

#### 3. **Sync with Main**

```bash
# Keep your branch updated
git checkout main
git pull origin main
git checkout feature/your-branch-name
git merge main

# Or use rebase for cleaner history (advanced)
git rebase main
```

**When to sync:**
- Before creating a PR
- When main has significant changes
- Daily for long-running branches
- After resolving merge conflicts

#### 4. **Cleanup**

```bash
# After PR is merged, delete local branch
git checkout main
git branch -d feature/your-branch-name

# Delete remote branch (usually done automatically by GitHub after merge)
git push origin --delete feature/your-branch-name
```

**Cleanup Policy:**
- Delete branches immediately after merge
- Keep spike branches until insights are documented
- Archive long-lived branches as tags if needed

### Branch Protection

**Main branch rules:**
- No direct commits
- All changes via PR
- Must pass tests (when CI/CD is configured)
- Requires review from human or senior agent

---

## 2. Issue Management

### Issue Creation

**When to create an issue:**
- New feature requests
- Bug reports
- Documentation gaps
- Performance problems
- Refactoring needs
- Questions requiring investigation

**Issue Template:**

```markdown
## Description
[Clear, concise description of the issue/feature]

## Context
[Why is this needed? What problem does it solve?]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests added/updated
- [ ] Documentation updated

## Technical Notes
[Implementation hints, edge cases, dependencies]

## Related Issues
- Closes #XX
- Related to #YY
```

**Example from Emergence:**

```markdown
## Description
Create comprehensive development pipeline skill covering branching, 
PRs, reviews, and release workflow.

## Context
Need clear guidance for agents on the full development lifecycle to 
maintain consistency and quality across contributions.

## Acceptance Criteria
- [ ] Branching strategy documented
- [ ] Issue management process defined
- [ ] PR template and review chain specified
- [ ] Release process documented
- [ ] Room-specific workflows included

## Technical Notes
Should include examples from recent PRs (#80, #81, #101, #102)
Document Jarvling → Aurora → Human review chain

## Related Issues
- Part of v0.4.2 documentation improvements
```

### Issue Assignment

**Assignment flow:**
1. **Triage:** Human or Aurora assigns priority/labels
2. **Assignment:** Assign to specific agent or leave open
3. **Acceptance:** Agent accepts by commenting or starting work
4. **Updates:** Comment with progress/blockers

**Labels:**
- `bug` — Something broken
- `feature` — New functionality
- `docs` — Documentation
- `enhancement` — Improvement to existing feature
- `good-first-issue` — Suitable for new contributors
- `help-wanted` — Need assistance
- `blocked` — Waiting on dependency
- `wip` — Work in progress
- `priority:high` — Urgent

### Milestones

**Milestone structure:**
- `v0.4.0` — Major release (new features, breaking changes)
- `v0.4.1` — Minor release (features, non-breaking)
- `v0.4.2` — Patch release (bug fixes, docs)

**Milestone planning:**
- Group related issues
- Set target dates
- Track progress
- Review before release

---

## 3. Development Workflow

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/jarvis-raven/emergence.git
cd emergence

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Verify installation
emergence --version
```

### Testing

**Before committing:**

```bash
# Run tests
pytest

# Run specific test file
pytest tests/test_nautilus.py

# Run with coverage
pytest --cov=core --cov-report=term-missing

# Test specific functionality
pytest -k "test_drive_satisfaction"
```

**Test types:**
- **Unit tests:** Individual functions/classes
- **Integration tests:** Component interactions
- **End-to-end tests:** Full workflow validation

**Example test structure:**

```python
# tests/test_development_pipeline.py
import pytest
from core.workflow import BranchManager

def test_branch_naming_validation():
    """Ensure branch names follow conventions."""
    manager = BranchManager()
    assert manager.validate("feature/nautilus-core") is True
    assert manager.validate("random-name") is False
    assert manager.validate("feature-without-slash") is False
```

### Commit Best Practices

**Conventional Commits format:**

```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.

- Bullet points for multiple changes
- Reference issues with #123
- Breaking changes noted with BREAKING CHANGE:

Closes #123
```

**Types:**
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation
- `style` — Formatting (no code change)
- `refactor` — Code restructure
- `test` — Test additions
- `chore` — Maintenance

**Examples from Emergence:**

```bash
feat(drives): emergency auto-spawn safety valve (#43) (#51)
fix(packaging): include defaults.json in PyPI package (#53)
docs(nautilus): add quickstart guide
test: fix 3 failing tests (issue #46) (#54)
chore: bump version to 0.3.0
```

**Commit frequency:**
- Commit often, push regularly
- Each commit should be logical unit
- Squash messy commits before PR if needed
- Don't commit broken code to main

### Code Quality

**Before creating PR:**

```bash
# Format code (if using formatters)
black core/
isort core/

# Lint code
pylint core/

# Type checking (if using mypy)
mypy core/
```

**Code review checklist:**
- [ ] Follows project style
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No debug code left
- [ ] Error handling included
- [ ] Performance considered
- [ ] Security reviewed

---

## 4. PR Process

### Creating a Pull Request

**Pre-PR checklist:**
- [ ] Branch synced with main
- [ ] All tests passing
- [ ] Code formatted and linted
- [ ] Documentation updated
- [ ] Commits cleaned up (if needed)
- [ ] Issue reference ready

**PR Creation:**

```bash
# Push your branch
git push origin feature/your-branch-name

# Open PR on GitHub with description template
```

### PR Description Template

```markdown
## Summary
[Brief description of what this PR does]

## Related Issue
Closes #XXX
Related to #YYY

## Changes Made
- Change 1: Description
- Change 2: Description
- Change 3: Description

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests passing

## Documentation
- [ ] Code comments added/updated
- [ ] README updated
- [ ] CHANGELOG updated
- [ ] API docs updated (if applicable)

## Screenshots/Examples
[If UI changes or new features, include examples]

## Checklist
- [ ] Code follows project style
- [ ] Self-review completed
- [ ] No debugging code left
- [ ] Breaking changes documented
- [ ] Version bumped (if needed)

## Review Notes
[Any specific areas you want reviewers to focus on]
```

**Example from PR #80:**

```markdown
## Summary
v0.4.0 Nautilus: Alpha + Beta Core Integration

Integrates Nautilus reflective journaling system with Emergence core,
including daemon hooks, nightly analysis, and session tracking.

## Related Issue
Part of v0.4.0 Nautilus milestone
Implements Issue #67 (Nautilus Beta Integration)

## Changes Made
- Added core/nautilus module with chambers, doors, gravity, mirrors
- Integrated nightly check daemon for journal processing
- Added session hooks for automatic capture
- Created migration script for existing drives.json
- Added comprehensive test suite (98 tests, 352 integration tests)
- Documentation: quickstart guide and integration guide

## Type of Change
- [x] New feature (non-breaking)
- [x] Documentation update

## Testing
- [x] Unit tests added (98 tests in test_nautilus.py)
- [x] Integration tests added (352 tests)
- [x] Manual testing completed
- [x] All 450+ tests passing

## Documentation
- [x] Code comments added
- [x] docs/nautilus-quickstart.md created
- [x] docs/nautilus-v0.4.0-integration.md created
- [x] CHANGELOG ready (will be added in release commit)

## Review Notes
Focus on:
- Daemon integration (core/drives/nightly_check.py)
- Session hooks (core/nautilus/session_hooks.py)
- Migration safety (core/nautilus/migrate_db.py)
```

### Review Chain

**Emergence review process:**

```
Jarvling (Agent) → Aurora (Senior Agent) → Human (Final Approval)
```

**1. Jarvling Self-Review**
- Complete PR checklist
- Run all tests locally
- Review own code changes
- Add clear description
- Mark as "Ready for Review"

**2. Aurora Review**
- Code quality check
- Architecture alignment
- Test coverage validation
- Documentation completeness
- Security considerations
- Suggests improvements or approves

**3. Human Review** (Dan)
- Final architecture decisions
- Breaking change approval
- Release timing
- Merge execution

**Review timeline:**
- Jarvling: Same session (before PR creation)
- Aurora: Within 24 hours
- Human: Within 48 hours (priority) / 1 week (standard)

### PR Comments & Revisions

**Responding to feedback:**

```bash
# Make requested changes
git add <files>
git commit -m "fix: address review comments - clarify error handling"
git push origin feature/your-branch-name

# PR updates automatically
```

**Comment etiquette:**
- Acknowledge all feedback
- Explain decisions if disagreeing
- Ask questions when unclear
- Mark conversations resolved when addressed
- Thank reviewers

### Merge Strategies

**Emergence uses:**

1. **Merge Commit** (default)
   - Preserves full history
   - Clear PR boundaries
   - Use for features

```bash
git merge --no-ff feature/branch-name
```

2. **Squash and Merge**
   - Single commit for small PRs
   - Cleaner history
   - Use for small fixes, docs

3. **Rebase and Merge**
   - Linear history
   - For small atomic PRs
   - Avoid for collaborative branches

**After merge:**
- Delete source branch
- Verify CI/CD passes
- Update issue status
- Celebrate! 🎉

---

## 5. Jarvling Collaboration

### When to Spawn a Jarvling

**Spawn a Jarvling (subagent) when:**
- Task is well-defined with clear deliverables
- Estimated 30+ minutes of focused work
- Independent from ongoing conversation
- Requires different model/thinking level
- Parallel work possible (multiple issues)

**Don't spawn when:**
- Quick question or clarification
- Iterative back-and-forth needed
- Human guidance required during work
- Task is exploratory (use main session)

**Examples:**
- ✅ "Fix #103: Create Development Pipeline Skill"
- ✅ "Implement drive consolidation algorithm"
- ✅ "Write integration tests for Nautilus"
- ❌ "What should we name this function?" (just ask)
- ❌ "Help me debug this error" (iterative)

### Task Writing for Jarvlings

**Effective task description:**

```markdown
## Task
Fix #103: Create Development Pipeline Skill

## Goal
Create comprehensive development pipeline skill at 
skills/development-pipeline/SKILL.md covering complete workflow 
from idea to production.

## Required Sections
1. Branching Strategy (feature/, fix/, hotfix/, docs/)
2. Issue Management (creation, assignment, milestones, labels)
3. Development Workflow (local dev, testing, commits)
4. PR Process (creation, description template, review chain)
5. Jarvling Collaboration (when to spawn, task writing, review)
6. Release Management (versioning, changelogs, deployment)
7. Room-Specific Workflows (dev/prod, state management)

## Deliverables
- skills/development-pipeline/SKILL.md with all sections
- Include concrete examples from recent PRs (#80, #81, #101, #102)
- Document review chain: Jarvling → Aurora → Human
- Clear, actionable guidance for every stage

## Process
1. Research existing Emergence workflow patterns
2. Create comprehensive skill file
3. Include examples from recent PRs
4. Submit PR with clear description

## Context
Repository: ~/projects/Emergence
Use Kimi model for cost efficiency.
```

**Key elements:**
- **Clear goal:** What success looks like
- **Specific deliverables:** Concrete outputs
- **Process steps:** How to approach it
- **Context:** Location, model, constraints
- **Examples:** Reference material

### Jarvling Review Process

**Jarvling responsibilities:**
1. Complete assigned task fully
2. Self-review before reporting
3. Run tests and verify quality
4. Document decisions made
5. Create PR with clear description
6. Report completion to spawner

**Aurora's Jarvling review checklist:**
- [ ] Task completed as specified
- [ ] Code quality meets standards
- [ ] Tests comprehensive and passing
- [ ] Documentation clear and complete
- [ ] PR description thorough
- [ ] No obvious issues or shortcuts
- [ ] Ready for human review

**Feedback flow:**

```
Jarvling creates PR
    ↓
Aurora reviews code
    ↓
[If issues] → Aurora comments → Jarvling revises
    ↓
[If approved] → Aurora approves → Tags human
    ↓
Human final review → Merge
```

### Communication Patterns

**Jarvling → Spawner:**
```markdown
Task completed: Created Development Pipeline Skill

Deliverables:
- ✅ skills/development-pipeline/SKILL.md (7 sections, ~800 lines)
- ✅ Concrete examples from PRs #80, #81
- ✅ Review chain documented
- ✅ Actionable guidance throughout

PR: #103
Branch: feature/103-development-pipeline-skill
Status: Ready for Aurora review

Notes:
- Researched 20+ recent commits for workflow patterns
- Included templates for PR descriptions and task writing
- Added troubleshooting section for common issues
```

**Aurora → Human:**
```markdown
PR #103 reviewed and approved ✅

Jarvling: Kimi
Task: Development Pipeline Skill
Quality: High

Review notes:
- Comprehensive coverage of all required sections
- Good concrete examples from actual PRs
- Clear, actionable guidance
- Well-structured and readable
- Tests N/A (documentation)

Ready for merge.
```

---

## 6. Release Management

### Versioning Strategy

**Emergence follows [Semantic Versioning](https://semver.org/):**

```
MAJOR.MINOR.PATCH

0.4.2
│ │ └─ Patch: Bug fixes, docs, no new features
│ └─── Minor: New features, backward-compatible
└───── Major: Breaking changes, API changes
```

**Version bumping:**
- `0.3.0 → 0.3.1` — Bug fixes, documentation
- `0.3.0 → 0.4.0` — New features, no breaking changes
- `0.4.0 → 1.0.0` — Breaking changes, major milestone

**When to bump:**
- PATCH: Every merged fix/docs PR
- MINOR: Feature PRs or grouped fixes
- MAJOR: Breaking changes, complete rewrites

**Version file locations:**
- `pyproject.toml` — `version = "0.4.2"`
- `package.json` — `"version": "0.4.2"` (for Room)

### Changelog Maintenance

**CHANGELOG.md format:**

```markdown
# Changelog

## [Unreleased]

### Added
- New feature descriptions

### Changed
- Modified behavior descriptions

### Fixed
- Bug fix descriptions

### Removed
- Deprecated feature removals

## [0.4.2] - 2026-02-15

### Added
- Development Pipeline Skill (#103)
- Comprehensive workflow documentation

### Changed
- Updated PR template with clearer sections

### Fixed
- Branch naming validation in CI

## [0.4.1] - 2026-02-14
...
```

**Update frequency:**
- Add entries as PRs merge
- Group similar changes
- Move from [Unreleased] to version on release
- Link issues and PRs

**Example entry:**

```markdown
### Added
**Development Pipeline Skill (Issue #103)**
- Complete workflow documentation from idea to production
- Branching strategy with concrete examples
- PR process templates and review chain
- Jarvling collaboration guidelines
- Release management procedures
- Room-specific workflow guidance
```

### Release Process

**Pre-release checklist:**
- [ ] All milestone issues closed
- [ ] Tests passing
- [ ] CHANGELOG updated
- [ ] Version bumped in all files
- [ ] Documentation updated
- [ ] Migration guide (if breaking changes)
- [ ] Release notes drafted

**Release steps:**

```bash
# 1. Create release branch
git checkout -b release/v0.4.2
git push origin release/v0.4.2

# 2. Update version files
# Edit pyproject.toml, package.json

# 3. Update CHANGELOG
# Move [Unreleased] to [0.4.2]

# 4. Commit version bump
git add pyproject.toml package.json CHANGELOG.md
git commit -m "chore: bump version to 0.4.2"
git push origin release/v0.4.2

# 5. Create PR: release/v0.4.2 → main

# 6. After merge, create tag
git checkout main
git pull origin main
git tag -a v0.4.2 -m "Release v0.4.2: Development Pipeline Skill"
git push origin v0.4.2

# 7. Create GitHub Release
# Use CHANGELOG content for release notes
```

### Deployment

**PyPI deployment:**

```bash
# Build distribution
python -m build

# Upload to TestPyPI (testing)
python -m twine upload --repository testpypi dist/*

# Verify installation
pip install -i https://test.pypi.org/simple/ emergence-ai

# Upload to PyPI (production)
python -m twine upload dist/*
```

**Post-release:**
- [ ] Verify PyPI package
- [ ] Update documentation site
- [ ] Announce in community channels
- [ ] Close milestone
- [ ] Create next milestone

---

## 7. Room-Specific Workflows

### Development Environment

**Local Room development:**

```bash
# Navigate to Room directory
cd ~/projects/Emergence/room

# Install dependencies
npm install

# Initialize dev state (first time only)
npm run dev:setup

# Start development server
npm run dev

# Access at http://localhost:3000 (dev) or http://localhost:8800 (prod)
```

### Dev State Initialization

The Room's dev environment requires realistic state data to render properly. Production state (`.emergence/`) should never be modified during development, so we use a separate dev state directory (`.emergence-dev/`).

**Setup workflow:**

```bash
# 1. First time: Initialize dev state from production
cd room
npm run dev:setup

# This will:
# - Copy .emergence/ → .emergence-dev/
# - Preserve drives.json, nautilus.db, all config
# - Ask for confirmation
# - Never touch production state

# 2. Start dev environment
npm run dev

# 3. Make changes, test, iterate...

# 4. If dev state gets corrupted or you want fresh data
npm run dev:reset
```

**What gets copied:**
- `drives.json` — Full drive configuration
- `drives-state.json` — Runtime drive states
- `state/nautilus.db` — Journal entries (if exists)
- All config files in `.emergence/`
- Logs directory structure

**What doesn't get copied:**
- `*.pid` files (process IDs)
- Temporary lock files

**Safety guarantees:**
- ✅ Production state (`.emergence/`) is **read-only** during setup
- ✅ Scripts always confirm before overwriting `.emergence-dev/`
- ✅ Exit codes: 0=success, 1=error, 2=cancelled
- ✅ Clear warnings before any destructive operations
- ✅ Idempotent (safe to run multiple times)

**Dry run mode:**

```bash
# See what would be reset without making changes
cd ..  # project root
./scripts/reset-dev-state.sh --dry-run
```

**When to reset dev state:**
- Dev state is corrupted or in bad state
- Want to test with fresh production data
- Made experimental changes and want clean slate
- Production added new drives/features you want to test

**Room structure:**
```
room/
├── server/           # Express backend
│   ├── index.js      # Main server
│   ├── routes/       # API endpoints
│   └── shelves/      # Shelf data providers
├── src/              # React frontend
│   ├── components/   # UI components
│   ├── hooks/        # React hooks
│   └── utils/        # Utilities
├── package.json      # Dependencies
└── vite.config.js    # Build config
```

### State Management

**Development vs Production:**

**Development (local):**
- State: `~/.openclaw/state/dev/`
- Config: `~/.openclaw/config/emergence.json`
- Logs: Console output + `~/.openclaw/logs/`
- Hot reload: Enabled
- Debug tools: Enabled

**Production (deployed):**
- State: `~/.openclaw/state/prod/`
- Config: Production `emergence.json`
- Logs: File-based only
- Hot reload: Disabled
- Debug tools: Disabled

**State file hierarchy:**

```
~/.openclaw/state/
├── dev/
│   ├── drives.json           # Full drive config
│   ├── drives-state.json     # Runtime state
│   ├── memory/               # Session logs
│   ├── first-light.json      # Onboarding state
│   └── aspirations.json      # Goals/projects
└── prod/
    └── [same structure]
```

### Room API Integration

**Adding new API endpoint:**

1. **Create route file:**

```javascript
// room/server/routes/pipeline.js
import express from 'express';
const router = express.Router();

router.get('/status', async (req, res) => {
  try {
    // Implementation
    res.json({ status: 'ok', data: {...} });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
```

2. **Register in server:**

```javascript
// room/server/index.js
import pipelineRoutes from './routes/pipeline.js';
app.use('/api/pipeline', pipelineRoutes);
```

3. **Create React hook:**

```javascript
// room/src/hooks/usePipeline.js
import { useState, useEffect } from 'react';

export function usePipeline() {
  const [status, setStatus] = useState(null);
  
  useEffect(() => {
    fetch('/api/pipeline/status')
      .then(res => res.json())
      .then(setStatus);
  }, []);
  
  return { status };
}
```

4. **Use in component:**

```javascript
// room/src/components/PipelineWidget.jsx
import { usePipeline } from '../hooks/usePipeline';

export function PipelineWidget() {
  const { status } = usePipeline();
  return <div>{status?.message}</div>;
}
```

### Room Shelf Development

**Creating a custom shelf:**

```javascript
// room/server/shelves/builtins/PipelineShelf.js
class PipelineShelf {
  constructor(config) {
    this.config = config;
  }

  async getData() {
    // Fetch data from filesystem or API
    return {
      branches: this.getCurrentBranches(),
      prs: this.getOpenPRs(),
      issues: this.getAssignedIssues()
    };
  }

  getCurrentBranches() {
    // Implementation
  }
}

export default PipelineShelf;
```

**Register shelf:**

```javascript
// room/server/shelves/index.js
import PipelineShelf from './builtins/PipelineShelf.js';

export const builtins = {
  memory: MemoryShelf,
  drives: DrivesShelf,
  pipeline: PipelineShelf  // Add new shelf
};
```

**Render in UI:**

```javascript
// room/src/components/shelves/ShelfRenderer.jsx
import PipelineView from './PipelineView';

const shelfComponents = {
  memory: MemoryShelf,
  drives: DrivesShelf,
  pipeline: PipelineView  // Add new component
};
```

### Testing Room Changes

**Backend tests:**

```bash
# If you have Jest configured
npm test

# Manual API testing
curl http://localhost:5173/api/pipeline/status
```

**Frontend tests:**

```javascript
// room/src/components/__tests__/PipelineWidget.test.jsx
import { render, screen } from '@testing-library/react';
import PipelineWidget from '../PipelineWidget';

test('renders pipeline status', () => {
  render(<PipelineWidget />);
  expect(screen.getByText(/pipeline/i)).toBeInTheDocument();
});
```

**Integration testing:**
- Start full stack: `npm run dev`
- Test API endpoints manually
- Verify WebSocket connections
- Check state persistence
- Test error handling

### Common Room Workflows

**1. Adding a new drive visualization:**

```javascript
// room/src/components/drives/NewDriveCard.jsx
export function NewDriveCard({ drive }) {
  return (
    <div className="drive-card">
      <h3>{drive.name}</h3>
      <ProgressBar value={drive.pressure} max={drive.threshold} />
      <span>{drive.description}</span>
    </div>
  );
}
```

**2. Updating state display:**

```javascript
// room/src/hooks/useDriveState.js
export function useDriveState() {
  const [drives, setDrives] = useState([]);
  
  useEffect(() => {
    // WebSocket connection for live updates
    const ws = new WebSocket('ws://localhost:5173/ws');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'drive-update') {
        setDrives(data.drives);
      }
    };
    return () => ws.close();
  }, []);
  
  return drives;
}
```

**3. Adding configuration option:**

```javascript
// Update emergence.json schema
{
  "room": {
    "port": 5173,
    "autostart": true,
    "shelves": {
      "pipeline": {
        "enabled": true,
        "refresh_interval": 60
      }
    }
  }
}
```

---

## Appendix: Quick Reference

### Common Commands

```bash
# Development
git checkout -b feature/your-feature
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature

# Testing
pytest
pytest --cov=core

# Release
git tag -a v0.4.2 -m "Release v0.4.2"
git push origin v0.4.2
python -m build
python -m twine upload dist/*

# Room
cd room
npm run dev
npm test
```

### Review Chain Summary

```
Jarvling → Aurora → Human
  ↓         ↓         ↓
Self      Code      Final
review    review    approval
```

### Branch Prefixes

- `feature/` — New features
- `fix/` — Bug fixes
- `hotfix/` — Urgent fixes
- `docs/` — Documentation
- `refactor/` — Code restructuring
- `test/` — Test additions
- `chore/` — Maintenance
- `spike/` — Experimental

### Commit Types

- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation
- `style` — Formatting
- `refactor` — Restructure
- `test` — Tests
- `chore` — Maintenance

---

## Troubleshooting

### Common Issues

**1. Merge conflicts**

```bash
# During merge
git merge main
# [conflicts appear]

# Resolve manually, then:
git add <resolved-files>
git commit -m "fix: resolve merge conflicts with main"
```

**2. Tests failing locally**

```bash
# Clear cache
rm -rf .pytest_cache
rm -rf __pycache__

# Reinstall dependencies
pip install -e ".[dev]"

# Run tests with verbose output
pytest -v
```

**3. Room won't start**

```bash
# Check port availability
lsof -i :5173

# Clear node_modules
rm -rf node_modules
npm install

# Check for errors
npm run dev 2>&1 | tee room.log
```

**4. PR checks failing**

- Verify all tests pass locally
- Check branch is synced with main
- Review CI/CD logs for specific errors
- Ensure all files are committed

### Getting Help

**Where to ask:**
- **GitHub Issues:** Bug reports, feature requests
- **PR Comments:** Code-specific questions
- **Discord/Chat:** General questions, discussions
- **Documentation:** Check docs/ folder first

**Effective questions:**
- What you're trying to do
- What you expected
- What actually happened
- Steps to reproduce
- Environment details (OS, Python version, etc.)

---

**End of Development Pipeline Skill v1.0.0**

*This skill is a living document. Update it as workflows evolve. Suggest improvements via PR.*
