# Scripts Documentation

## Branch Cleanup Automation

### Overview

The branch cleanup automation system helps maintain repository hygiene by identifying and removing merged and stale branches safely.

### Quick Start

```bash
# Preview what would be deleted (safe, default mode)
npm run cleanup:branches:dry-run

# Interactive cleanup with confirmation prompts
npm run cleanup:branches

# Automated cleanup (use with caution!)
npm run cleanup:branches:force
```

### Usage

#### Dry Run Mode (Default)

Preview branches that would be deleted without making any changes:

```bash
./scripts/cleanup-branches.sh
# or
npm run cleanup:branches:dry-run
```

**Safe to run anytime** - no changes are made.

#### Interactive Mode

Review and confirm deletions:

```bash
./scripts/cleanup-branches.sh --interactive
# or
npm run cleanup:branches
```

Shows all branches and asks for confirmation before deletion.

#### Force Mode

Automated deletion (requires `--yes` flag):

```bash
./scripts/cleanup-branches.sh --force --yes
# or
npm run cleanup:branches:force
```

⚠️ **Use with caution!** This will delete branches without prompting.

### What Gets Deleted

The script identifies and removes:

1. **Merged Branches**: Local and remote branches that have been merged to `main` (or `master`) and are older than 7 days
2. **Stale Branches**: Branches with no commits for 30+ days

### Protected Branches

The following branches are **NEVER** deleted:

- `main` / `master` / `develop`
- Any branch matching `spike/*`
- Any branch matching `release/*`
- The currently checked out branch

### Safety Features

✅ **Default to Dry-Run**: Always previews changes unless explicitly confirmed

✅ **Protected Branch Detection**: Automatically skips protected branches

✅ **Current Branch Safety**: Never deletes the branch you're currently on

✅ **Clear Visual Output**:
- 🟢 Green = Safe/Protected
- 🔴 Red = Will be deleted
- 🟡 Yellow = Warning/Stale

✅ **Confirmation Prompts**: Interactive mode requires explicit confirmation

✅ **Grace Periods**:
- Merged branches: 7 days
- Stale branches: 30 days

### Recovery / Undo

If you accidentally delete a local branch, you can recover it:

```bash
# View recent branch activity
git reflog

# Find the commit hash of the deleted branch
# Look for entries like: "commit: <message>" or "checkout: moving from <branch>"

# Recreate the branch
git checkout -b <branch-name> <commit-hash>
```

**Example:**

```bash
# View reflog
git reflog

# Output shows:
# a1b2c3d HEAD@{0}: commit: Add feature
# e4f5g6h HEAD@{1}: checkout: moving from old-branch to main

# Restore old-branch
git checkout -b old-branch e4f5g6h
```

⚠️ **Note**: Remote branches cannot be easily recovered once deleted. Always review carefully before deleting remote branches.

### Exit Codes

The script returns the following exit codes:

- `0`: Success - operation completed successfully
- `1`: Error - something went wrong (not in git repo, invalid arguments, etc.)
- `2`: User cancelled - user declined confirmation in interactive mode

### GitHub Action

The automated cleanup runs weekly on Sundays at 00:00 UTC via GitHub Actions.

#### Manual Trigger

You can manually trigger the workflow:

1. Go to **Actions** → **Branch Cleanup Automation**
2. Click **Run workflow**
3. Choose **dry run mode** (preview only) or active cleanup
4. Click **Run workflow**

#### What It Does

- Fetches all branches
- Identifies merged branches (7+ days old)
- Skips protected branches (`main`, `spike/*`, etc.)
- Skips branches with open pull requests
- Deletes eligible remote branches
- Posts summary to GitHub Actions summary
- Comments on maintenance issues (if they exist)

#### Weekly Schedule

```yaml
schedule:
  - cron: '0 0 * * 0'  # Every Sunday at midnight UTC
```

### GitHub Repository Setting

To automatically delete branches when pull requests are merged:

1. Go to **Settings** → **General**
2. Scroll to **Pull Requests** section
3. Enable **"Automatically delete head branches"**

This setting complements the automated cleanup by immediately removing branches when PRs merge, while the weekly action catches any that were missed.

### Best Practices

#### Before Deleting Branches

1. ✅ Run dry-run mode first: `npm run cleanup:branches:dry-run`
2. ✅ Review the list of branches to be deleted
3. ✅ Ensure you have no uncommitted work on those branches
4. ✅ Verify important branches are protected

#### Regular Cleanup

- Run interactive cleanup **weekly** during grooming sessions
- Review the automated cleanup **summaries** in GitHub Actions
- Keep the **protected patterns** updated for your workflow

#### Protection Patterns

Edit `scripts/cleanup-branches.sh` to customize protected patterns:

```bash
# Add your own protected patterns
PROTECTED_BRANCHES=("main" "master" "develop")
PROTECTED_PATTERNS=("spike/*" "release/*" "hotfix/*")
```

### Troubleshooting

#### "Not a git repository" error

Make sure you're running the script from within a git repository:

```bash
cd /path/to/your/repo
npm run cleanup:branches
```

#### Permission denied when deleting remote branches

You need push permissions to delete remote branches. Contact your repository administrator if you need access.

#### Branch shows as stale but has recent activity

The script checks the **last commit date**, not last modified date. If you've rebased or cherry-picked, the commit dates may be old even if the work is recent.

### Integration with Development Pipeline

This cleanup automation integrates with the broader development workflow:

1. **Pre-Merge**: Create feature branch
2. **Review**: Submit pull request
3. **Merge**: PR merged to main
4. **Auto-Delete**: GitHub setting removes branch immediately
5. **Weekly Cleanup**: Catches any branches that were missed
6. **Manual Cleanup**: Run `npm run cleanup:branches` as needed

See the development-pipeline skill documentation for complete workflow details.

---

## Other Scripts

### (Future scripts will be documented here)

When adding new scripts to this directory:

1. Create the script in `scripts/`
2. Make it executable: `chmod +x scripts/script-name.sh`
3. Add npm script in `package.json`
4. Document usage here
5. Include safety warnings if applicable
