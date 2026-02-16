# Jarvling Workflow - Real-World Guide

**Based on actual experience from v0.4.2 development (2026-02-15)**

**Success metrics:** 8 jarvlings, 100% completion rate, ~45 min total runtime, ~5,000+ lines generated

---

## Quick Start

```bash
# 1. Spawn jarvling
sessions_spawn task="Fix #105: Create dev state init scripts" \
  label="v0.4.2-dev-state-init" \
  model="kimi" \
  cleanup="keep"

# 2. Wait for completion announcement (~5-15 min)

# 3. Find jarvling workspace
ls ~/.openclaw/workspace-kimi/

# 4. Copy files to main repo
cd ~/projects/emergence
git checkout -b feature/105-dev-state-init
cp ~/.openclaw/workspace-kimi/{files} .
git add -A && git commit -m "feat(dev): add dev state scripts"
git push -u origin feature/105-dev-state-init

# 5. Create PR
gh pr create --base main --head feature/105-dev-state-init \
  --title "feat(dev): add dev state initialization scripts" \
  --body-file ~/.openclaw/workspace-kimi/PR_DESCRIPTION.md

# 6. Send to Aurora for review
```

---

## Understanding Jarvling Workspaces

### Where Jarvlings Work

**Jarvlings are ISOLATED** - they work in their own workspace directories:

```
~/.openclaw/
├── workspace/              # Your main workspace
├── workspace-kimi/         # Kimi jarvlings work here
├── workspace-sonnet/       # Sonnet jarvlings work here
└── agents/
    └── kimi/sessions/      # Jarvling session transcripts
```

**What this means:**

- ✅ Jarvlings don't pollute your main workspace
- ✅ Multiple jarvlings can work in parallel
- ✅ Work persists after jarvling completes
- ⚠️ Files don't automatically appear in your repo
- ⚠️ Manual PR creation required

### Jarvling Workspace Contents

Example from today's `workspace-kimi/`:

```
workspace-kimi/
├── AGENTS.md                    # Full bootstrap files
├── SOUL.md
├── USER.md
├── TOOLS.md
├── HEARTBEAT.md
├── IDENTITY.md
├── BOOTSTRAP.md
├── scripts/
│   ├── cleanup-branches.sh      # Jarvling's work
│   └── README.md
├── .github/
│   └── workflows/
│       └── cleanup-branches.yml
├── docs/
│   ├── CONTRIBUTING.md
│   ├── REVIEW_GUIDELINES.md
│   └── TESTING_BRANCH_CLEANUP.md
├── PR_SUMMARY.md                # PR description ready to use
├── TASK_COMPLETION_REPORT.md    # Detailed completion report
└── FIX_106_COMPLETION.md        # Verification checklist
```

---

## Manual PR Creation Workflow

**After jarvling completes, you MUST create the PR manually.**

### Step 1: Review Jarvling Output

```bash
# Navigate to jarvling workspace
cd ~/.openclaw/workspace-kimi/

# Review what was created
ls -la

# Read completion report
cat TASK_COMPLETION_REPORT.md

# Review PR description
cat PR_SUMMARY.md  # or PR_*_DESCRIPTION.md
```

### Step 2: Copy Files to Main Repo

```bash
# Go to your main repository
cd ~/projects/emergence

# Create feature branch
git checkout -b feature/106-branch-cleanup

# Copy jarvling files
cp ~/.openclaw/workspace-kimi/scripts/cleanup-branches.sh scripts/
chmod +x scripts/cleanup-branches.sh

cp ~/.openclaw/workspace-kimi/.github/workflows/cleanup-branches.yml .github/workflows/

cp ~/.openclaw/workspace-kimi/docs/GITHUB_SETTINGS.md docs/
cp ~/.openclaw/workspace-kimi/docs/TESTING_BRANCH_CLEANUP.md docs/
cp ~/.openclaw/workspace-kimi/scripts/README.md scripts/

# Review changes
git status
git diff
```

### Step 3: Commit with Conventional Commits

```bash
# Add all files
git add -A

# Commit (use jarvling's suggested commit messages)
git commit -m "feat(cleanup): add branch cleanup automation script"
git commit --allow-empty -m "ci(cleanup): add weekly branch cleanup GitHub Action"
git commit --allow-empty -m "docs(cleanup): document branch cleanup workflow"

# Push branch
git push -u origin feature/106-branch-cleanup
```

### Step 4: Create PR on GitHub

```bash
# Option A: Use jarvling's PR description file
gh pr create --base main --head feature/106-branch-cleanup \
  --title "feat(cleanup): add branch cleanup automation" \
  --body-file ~/.openclaw/workspace-kimi/PR_SUMMARY.md

# Option B: Manual PR description
gh pr create --base main --head feature/106-branch-cleanup \
  --title "feat(cleanup): add branch cleanup automation" \
  --body "## Summary
Created comprehensive branch cleanup automation...

Closes #106"
```

### Step 5: Send to Aurora

**Message Aurora:**

> "Hey Aurora! New PR ready for review: #113 - Branch Cleanup Automation. It adds weekly automated cleanup with GitHub Action + manual scripts. All safety checks included. Closes #106."

---

## Task Description Template

Based on successful jarvlings from v0.4.2:

```markdown
Fix #XXX: [Clear Action-Oriented Title]

[1-2 sentence context explaining WHY this work is needed]

**MANDATORY DELIVERABLES:**

1. **[Deliverable 1 with file path]**
   - Specific requirement
   - Acceptance criteria
   - Example or constraint

2. **[Deliverable 2 with file path]**
   - What it must include
   - How it should behave
   - Testing requirements

**[CATEGORY] REQUIREMENTS (MANDATORY/STRICT):**

- ✅ Requirement that must be met
- ✅ Safety constraint
- ✅ Quality standard

**TESTING CHECKLIST:**

- [ ] Specific thing to verify
- [ ] Test that must pass
- [ ] Documentation requirement

**CONVENTIONAL COMMITS REQUIRED:**

- feat(scope): specific commit message format
- docs(scope): documentation commit format
- ci(scope): CI/CD commit format

**[Optional sections like SAFETY, INTEGRATION, etc.]**

Closes #XXX
```

### Real Example: Issue #105

```markdown
Fix #105: Dev Environment State Initialization

Create tooling to safely copy production state to dev environment for realistic testing.

**CONTEXT:**
PR #109 (Room dev/prod split) is now merged. Dev environment runs on port 3000 with `.emergence-dev/` state directory, but we need a safe way to initialize it with production data.

**MANDATORY DELIVERABLES:**

1. **Script: `scripts/setup-dev-state.sh`**
   - Copy `.emergence/` → `.emergence-dev/` (initial setup)
   - Safety checks:
     - Verify `.emergence/` exists (BLOCK if missing)
     - Warn if `.emergence-dev/` already exists
     - Ask for confirmation before overwriting
     - Never modify `.emergence/` (read-only source)
   - Exit codes: 0 = success, 1 = error, 2 = user cancelled

[... continues with specific requirements ...]

**SAFETY REQUIREMENTS (MANDATORY):**

- ✅ Never modify `.emergence/` (production state)
- ✅ Always confirm before overwriting `.emergence-dev/`
- ✅ Clear warnings about state separation

**TESTING CHECKLIST:**

- [ ] Setup script creates `.emergence-dev/` correctly
- [ ] All state files copied
- [ ] Production state never modified

**CONVENTIONAL COMMITS REQUIRED:**

- feat(dev): add dev state initialization scripts
- docs(dev): document dev environment setup process

Closes #105
```

**Why this worked:**

- ✅ Crystal clear deliverables
- ✅ Specific file paths
- ✅ Safety requirements explicit
- ✅ Testing criteria defined
- ✅ Commit format specified

---

## Common Patterns

### Wave-Based Spawning

**Spawn multiple jarvlings in parallel for independent work:**

```bash
# Wave 1: Core infrastructure
sessions_spawn task="Fix #103: Development Pipeline Skill" \
  label="v0.4.2-pipeline-skill" model="kimi" cleanup="keep"

sessions_spawn task="Fix #104: Room Dev/Prod Split" \
  label="v0.4.2-room-dev-prod" model="kimi" cleanup="keep"

# Wave 2A: After wave 1 completes
sessions_spawn task="Fix #106: Branch Cleanup" \
  label="v0.4.2-branch-cleanup" model="kimi" cleanup="keep"

sessions_spawn task="Fix #107: PR Guidelines" \
  label="v0.4.2-pr-guidelines" model="kimi" cleanup="keep"

# Wave 2B: Depends on #104 being merged
sessions_spawn task="Fix #105: Dev State Init" \
  label="v0.4.2-dev-state-init" model="kimi" cleanup="keep"
```

**Benefits:**

- Parallel execution (faster)
- Clear dependencies
- Easy to track progress
- Batch review by Aurora

### Model Selection

**Use Kimi for cost efficiency:**

- Documentation tasks
- Script creation
- Boilerplate code
- Most standard development work

**Use Claude for:**

- Complex reasoning
- Architectural decisions
- Novel problem-solving
- High-stakes code

**Today's results (all Kimi):**

- 100% success rate
- ~$0 cost (Kimi free tier)
- Quality output for well-defined tasks

---

## Troubleshooting

### Can't Find Jarvling Output

**Problem:** Jarvling completed but can't find the files.

**Solution:**

```bash
# Check jarvling workspace
ls ~/.openclaw/workspace-kimi/
ls ~/.openclaw/workspace-sonnet/

# Check session transcripts
ls ~/.openclaw/agents/kimi/sessions/*.jsonl

# Review completion announcement
# (Check chat history for jarvling completion message)
```

### No PR Created Automatically

**Problem:** Jarvling didn't create PR on GitHub.

**Solution:** This is expected behavior! Jarvlings work in isolated workspaces. You must manually copy files and create PR (see "Manual PR Creation Workflow" above).

### Files in Wrong Location

**Problem:** Jarvling put files in unexpected places.

**Solution:**

- Review task description - was file path specified?
- Check jarvling workspace for all files
- Manually reorganize when copying to main repo

### Jarvling Didn't Follow Requirements

**Problem:** Deliverables incomplete or incorrect.

**Solution:**

- **Root cause:** Task description wasn't specific enough
- **Prevention:** Use strict requirements, explicit acceptance criteria
- **Fix:** Refine task and re-spawn, or complete manually

### Multiple Jarvlings Conflicting

**Problem:** Two jarvlings modified the same file.

**Solution:**

- Review both outputs
- Merge manually or choose one
- Prevention: Better task scoping

---

## Success Metrics (v0.4.2)

### By The Numbers

**Jarvlings spawned:** 8
**Success rate:** 100% (8/8)
**Total runtime:** ~45 minutes across all
**Lines generated:** ~5,000+ (code + docs)
**Rework needed:** 0
**Manual PR creation:** 8/8 (expected)

### Breakdown

| Issue  | Task           | Runtime | Outcome                            |
| ------ | -------------- | ------- | ---------------------------------- |
| #103   | Pipeline Skill | 4m44s   | ✅ 1,249 lines, merged             |
| #104   | Room Dev/Prod  | 3m53s   | ✅ Complete, merged                |
| #105   | Dev State Init | 4m59s   | ✅ Scripts + docs, pending         |
| #106   | Branch Cleanup | 9m25s   | ✅ Script + Action + docs, pending |
| #107   | PR Guidelines  | 6m34s   | ✅ Template + 2 guides, pending    |
| v0.4.1 | State Sync     | ~3min   | ✅ PR #102, merged                 |
| v0.4.1 | Display Bug    | ~3min   | ✅ Closed duplicates               |
| v0.4.1 | Room Build     | ~3min   | ✅ PR #101, merged                 |

### What Worked

✅ **Clear, strict requirements** - No ambiguity = perfect execution  
✅ **Specific deliverables** - File paths + acceptance criteria  
✅ **Conventional commits enforced** - Consistent git history  
✅ **Wave-based spawning** - Parallel work, faster completion  
✅ **Kimi model** - Cost-effective, high success rate  
✅ **Isolated workspaces** - No conflicts, clean separation

### Lessons Learned

1. **Manual PR creation is required** - Not automatic, plan for it
2. **Task descriptions are critical** - Specificity = success
3. **Jarvling workspaces persist** - Good for reference, remember to check there
4. **Review chain works** - Jarvling → Aurora → Dan is efficient
5. **Batch spawning effective** - Wave approach kept momentum high

---

## Review Chain

### Jarvling → Aurora → Dan

**1. Jarvling Self-Review (during work):**

- Complete all deliverables
- Run tests (if applicable)
- Write completion report
- Prepare PR description
- Signal completion

**2. Aurora Review (24-48 hours):**

- Technical correctness
- Code quality & standards
- Test coverage
- Documentation completeness
- Security concerns
- Approve or request changes

**3. Dan Final Approval (24-48 hours):**

- Strategic alignment
- Breaking change review
- Release timing
- Merge decision

**Communication:**

```
Jarvling completes → Announcement to chat
    ↓
Human creates PR → Tags Aurora
    ↓
Aurora reviews → Approves/Comments
    ↓
Human merges → Closes issue
```

---

## Cleanup After Merge

### What to Keep

**Keep for reference:**

- Jarvling workspaces (small, ~100-500KB each)
- Session transcripts (learning material)
- Completion reports (verification)

**Location:**

```
~/.openclaw/workspace-kimi/        # Jarvling work
~/.openclaw/agents/kimi/sessions/  # Transcripts
```

### What to Delete

**Safe to delete after PR merged:**

- Individual jarvling workspace (if you want)
- Old session transcripts (auto-archived after 60 min)

**Command:**

```bash
# Delete specific jarvling workspace
rm -rf ~/.openclaw/workspace-kimi/

# Or keep for reference - they're small
```

---

## Quick Reference

### Spawn Command

```bash
sessions_spawn \
  task="Fix #XXX: Clear description with deliverables" \
  label="v0.4.2-descriptive-label" \
  model="kimi" \
  cleanup="keep"
```

### Find Output

```bash
cd ~/.openclaw/workspace-kimi/
ls -la
cat TASK_COMPLETION_REPORT.md
```

### Create PR

```bash
cd ~/projects/emergence
git checkout -b feature/xxx-description
cp ~/.openclaw/workspace-kimi/{files} .
git add -A && git commit -m "feat(scope): description"
git push -u origin feature/xxx-description
gh pr create --body-file ~/.openclaw/workspace-kimi/PR_SUMMARY.md
```

### Send to Aurora

Tag her on GitHub or message:

> "New PR ready: #XXX - [Title]. [One-line summary]. Closes #YYY."

---

**Last updated:** 2026-02-15  
**Author:** Jarvis (Main Agent)  
**Experience base:** 8 successful jarvlings, v0.4.2 development
