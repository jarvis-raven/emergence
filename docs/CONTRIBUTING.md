# Contributing Guidelines

Welcome to the project! This document outlines our development standards and PR process.

## Development Setup

### Environments
- **Development:** Local workspace at `~/.openclaw/workspace-kimi`
- **Production:** Main OpenClaw installation

### Setup Instructions
1. Clone the repository
2. Ensure you have the OpenClaw CLI installed
3. Follow any skill-specific setup in individual `SKILL.md` files
4. Run initial tests to verify your environment

---

## Branching Strategy (STRICT)

All branches must follow these prefixes. PRs from invalid branch names will be rejected.

### Valid Branch Prefixes

| Prefix | Purpose | Requirements |
|--------|---------|--------------|
| `feature/` | New features | REQUIRES PR + Aurora review |
| `fix/` | Bug fixes | REQUIRES PR + Aurora review |
| `hotfix/` | Urgent production fixes | REQUIRES PR + immediate review |
| `docs/` | Documentation only | Can skip some automated checks |

### Examples
- ✅ `feature/add-pr-template`
- ✅ `fix/memory-leak-in-heartbeat`
- ✅ `hotfix/security-patch-credentials`
- ✅ `docs/update-contributing-guide`
- ❌ `my-feature` (invalid prefix)
- ❌ `bugfix/...` (use `fix/` instead)

**INVALID BRANCHES:** Any other prefix will be automatically rejected. This ensures clarity and consistency.

---

## Commit Format (MANDATORY)

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <description>

[optional body]

[optional footer]
```

### Valid Types

| Type | Purpose | Example |
|------|---------|---------|
| `feat` | New feature | `feat: add PR template auto-population` |
| `fix` | Bug fix | `fix: resolve heartbeat interval drift` |
| `docs` | Documentation | `docs: update CONTRIBUTING.md` |
| `chore` | Maintenance | `chore: clean up unused imports` |
| `test` | Testing | `test: add unit tests for PR validation` |
| `refactor` | Code refactoring | `refactor: extract validation logic` |
| `ci` | CI/CD changes | `ci: add PR template validation workflow` |

### Multi-Component Commits
Use scope for clarity:
```
feat(pr): add strict PR template
docs(contributing): add contribution guidelines
fix(heartbeat): resolve token accumulation bug
```

### Rules
- **BAD COMMIT = PR BLOCKED** — Non-conforming commits will fail CI checks
- Use imperative mood: "add feature" not "added feature"
- Keep first line under 72 characters
- Reference issues in footer: `Closes #107`

---

## Code Standards

### File Size Limits

**Hard limits** — exceeding these requires justification and approval:

| File Type | Max Lines | Notes |
|-----------|-----------|-------|
| Python modules | 500 | Split into multiple modules if needed |
| JavaScript components | 300 | Use composition for complex UIs |
| Test files | 1000 | Comprehensive test suites allowed |
| Config files | 200 | Keep configuration focused |

### Directory Structure

**Python:**
- Use `snake_case.py` for all modules
- Example: `pr_validator.py`, `review_checker.py`

**JavaScript:**
- Components: `PascalCase.jsx` (e.g., `PullRequestForm.jsx`)
- Utilities: `camelCase.js` (e.g., `validateCommits.js`)

**Tests:**
- Python: `test_*.py` (e.g., `test_pr_validator.py`)
- JavaScript: `*.test.js` (e.g., `PullRequestForm.test.js`)

### Component Organization (React)

```jsx
// 1. Imports grouped at top
import React, { useState, useEffect } from 'react';
import { helper } from './utils';

// 2. Component definition
export default function MyComponent({ prop1, prop2 }) {
  // 3. Hooks before event handlers
  const [state, setState] = useState(null);
  useEffect(() => { /* ... */ }, []);
  
  // 4. Event handlers
  const handleClick = () => { /* ... */ };
  
  // 5. Render
  return (/* JSX */);
}
```

**Rules:**
- **Max 3 nesting levels** — deeper nesting indicates need for extraction
- **Max 5 props** — use composition or context for more complex needs
- Extract logic into custom hooks when appropriate

### Module Organization (Python)

```python
"""Module docstring explaining purpose."""

from typing import List, Dict  # Type hints mandatory

def public_function(arg: str) -> bool:
    """
    Docstring for public functions.
    
    Args:
        arg: Description
        
    Returns:
        Description of return value
    """
    return _private_helper(arg)

def _private_helper(arg: str) -> bool:
    """Private functions can have simpler docstrings."""
    # Implementation
    pass
```

**Rules:**
- **Type hints mandatory** for all function signatures
- **Docstrings required** for all public functions and classes
- **PEP 8 compliance** — enforced by linters
- **Max 50 lines per function** — extract helpers for complex logic

### Separation of Concerns

**Clear boundaries:**
- **Models** ≠ **Logic** ≠ **UI**
  - Models define data structures
  - Logic handles business rules
  - UI presents and captures input

- **API routes** ≠ **Business logic** ≠ **Data access**
  - Routes handle HTTP concerns
  - Business logic contains domain rules
  - Data access abstracts storage

**Example (Python):**
```python
# ❌ BAD: Everything mixed together
@app.route('/submit-pr')
def submit_pr():
    data = request.json
    conn = sqlite3.connect('db.sqlite')
    if not data.get('title'):
        return {'error': 'Invalid'}, 400
    conn.execute('INSERT INTO prs ...')
    return {'success': True}

# ✅ GOOD: Clear separation
@app.route('/submit-pr')
def submit_pr():
    data = request.json
    try:
        pr = PRService.create_pr(data)  # Business logic
        return pr.to_dict(), 201
    except ValidationError as e:
        return {'error': str(e)}, 400
```

### Comments Required For

Always comment:
- **Complex algorithms** — explain the approach
- **Non-obvious decisions** — why this solution?
- **Performance optimizations** — what was the bottleneck?
- **Workarounds** — include issue link for proper fix

```python
# ✅ GOOD: Explains non-obvious decision
# Using LRU cache here because validation is expensive
# and the same commits are checked multiple times during CI
@lru_cache(maxsize=128)
def validate_commit_format(message: str) -> bool:
    # ...
```

```python
# ❌ BAD: States the obvious
# Increment counter
counter += 1
```

---

## PR Process

### 1. Before Creating a PR

- [ ] Run all tests locally: `npm test` / `pytest`
- [ ] Check for uncommitted changes: `git status`
- [ ] Verify branch name follows convention
- [ ] Review your own diff: `git diff main`
- [ ] Update relevant documentation

### 2. Creating the PR

1. **Use the PR template** — it auto-populates when you create a PR
2. **Fill ALL sections** — incomplete PRs will be rejected
3. **Complete the checklist** — all boxes must be checked
4. **Reference the issue** — use `Closes #XXX`

### 3. Review Process

**Timeline:**
- Aurora review: 24-48 hours
- Dan final approval: 24-48 hours after Aurora
- Hotfix: Same day (urgent only)

**What reviewers check:**
- Code quality and standards compliance
- Test coverage
- Documentation completeness
- Security implications
- Breaking changes

### 4. After Approval

- **Squash and merge** for clean history (default)
- **Rebase and merge** for preserving commit structure (if requested)
- **Delete branch immediately** after merge

### 5. Examples

**Good PRs to reference:**
- [#80](../../pull/80) — Feature with comprehensive tests
- [#81](../../pull/81) — Bug fix with clear reproduction steps
- [#101](../../pull/101) — Documentation improvement
- [#102](../../pull/102) — Refactoring with performance metrics

**Bad PR example:**
```
Title: "updates"
Body: "changed some stuff"
Commits: "fix", "fix again", "oops", "final fix"
Checklist: Incomplete
Result: ❌ REJECTED
```

---

## Merge Strategies

### Default: Squash and Merge
- Combines all commits into one
- Keeps main branch history clean
- Use for most PRs

### Rebase and Merge
- Preserves individual commits
- Use when commit history tells a story
- Requires clean, conventional commits

### Regular Merge
- Creates a merge commit
- Rarely used (only for special cases)
- Requires explicit approval

---

## Getting Help

- **Questions?** Open a discussion or ask in team chat
- **Found a bug?** Open an issue with reproduction steps
- **Want to propose a change?** Open an issue first to discuss

---

## Review Guidelines

See [REVIEW_GUIDELINES.md](./REVIEW_GUIDELINES.md) for detailed reviewer responsibilities and approval criteria.

---

**Remember:** These standards exist to maintain quality and consistency. They're not obstacles—they're guardrails that help us build better software together.
