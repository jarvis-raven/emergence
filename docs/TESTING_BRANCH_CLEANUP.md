# Testing Branch Cleanup Automation

## Test Checklist

Use this checklist to verify the branch cleanup automation works correctly.

### Prerequisites

- [ ] Git repository initialized
- [ ] At least one commit exists
- [ ] Script is executable (`chmod +x scripts/cleanup-branches.sh`)
- [ ] npm is installed (for npm script testing)

## 1. Script Functionality Tests

### Test 1.1: Help Output

```bash
./scripts/cleanup-branches.sh --help
```

**Expected Result:**
- Usage information displayed
- All options explained
- Examples shown
- Exit code: 0

### Test 1.2: Dry-Run Mode (Default)

```bash
./scripts/cleanup-branches.sh
# or
./scripts/cleanup-branches.sh --dry-run
# or
npm run cleanup:branches:dry-run
```

**Expected Result:**
- Script runs without errors
- Shows "DRY RUN MODE" message
- Lists branches but doesn't delete anything
- Provides instructions for actual deletion
- Exit code: 0

### Test 1.3: Protected Branches Detection

```bash
# Create test branches
git checkout -b spike/test-spike
git checkout main
git checkout -b release/v1.0
git checkout main

# Run dry-run
./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- `spike/test-spike` appears in "Protected Branches" section (green)
- `release/v1.0` appears in "Protected Branches" section (green)
- `main` does NOT appear in deletion lists
- Exit code: 0

### Test 1.4: Merged Branch Detection

```bash
# Create and merge a test branch
git checkout -b test/merged-feature
echo "test" > test-file.txt
git add test-file.txt
git commit -m "Test commit"
git checkout main
git merge test/merged-feature --no-ff -m "Merge test feature"

# Note: Won't show in deletion list until 7+ days old
# To test immediately, modify MERGED_GRACE_DAYS in script temporarily

./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Merged branch identified correctly
- If < 7 days old: not shown in deletion list (grace period)
- If 7+ days old: appears in "Merged Branches" section (red)
- Exit code: 0

### Test 1.5: Current Branch Protection

```bash
# Create a test branch
git checkout -b test/current-branch

# Run script while on this branch
./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Current branch (`test/current-branch`) NOT in deletion lists
- Protected by current branch safety check
- Exit code: 0

### Test 1.6: Interactive Mode - User Cancellation

```bash
./scripts/cleanup-branches.sh --interactive
# When prompted, type: no
```

**Expected Result:**
- Shows branches to be deleted
- Prompts for confirmation
- User types "no"
- Script cancels operation
- Message: "Cancelled by user"
- Exit code: 2

### Test 1.7: Interactive Mode - User Confirmation

```bash
# Create a merged test branch older than 7 days
# (or temporarily set MERGED_GRACE_DAYS=0 in script for testing)

./scripts/cleanup-branches.sh --interactive
# When prompted, type: yes
```

**Expected Result:**
- Shows branches to be deleted
- Prompts for confirmation
- User types "yes"
- Branches are deleted
- Success message shown
- Undo instructions displayed
- Exit code: 0

### Test 1.8: Force Mode - Missing Confirmation

```bash
./scripts/cleanup-branches.sh --force
```

**Expected Result:**
- Error message: "Force mode requires --yes flag"
- Script exits without deletion
- Exit code: 1

### Test 1.9: Force Mode - With Confirmation

```bash
./scripts/cleanup-branches.sh --force --yes
```

**Expected Result:**
- No prompts shown
- Eligible branches deleted automatically
- Success message shown
- Exit code: 0

### Test 1.10: No Branches to Clean

```bash
# In a fresh repo with only main branch
./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Message: "✓ No branches to clean up!"
- Exit code: 0

## 2. npm Script Integration Tests

### Test 2.1: Dry-Run Script

```bash
npm run cleanup:branches:dry-run
```

**Expected Result:**
- Same as `./scripts/cleanup-branches.sh --dry-run`
- Script executes successfully

### Test 2.2: Interactive Script

```bash
npm run cleanup:branches
```

**Expected Result:**
- Same as `./scripts/cleanup-branches.sh --interactive`
- Prompts for confirmation

### Test 2.3: Force Script

```bash
npm run cleanup:branches:force
```

**Expected Result:**
- Same as `./scripts/cleanup-branches.sh --force --yes`
- Deletes without prompting (if branches exist)

## 3. GitHub Action Tests

### Test 3.1: Workflow File Validation

```bash
# Validate YAML syntax
cat .github/workflows/cleanup-branches.yml | grep "schedule:" -A 1
```

**Expected Result:**
- Shows: `cron: '0 0 * * 0'` (Sunday at midnight UTC)
- Valid YAML syntax

### Test 3.2: Manual Workflow Trigger (Dry Run)

1. Push workflow file to GitHub
2. Go to **Actions** → **Branch Cleanup Automation**
3. Click **Run workflow**
4. Select **dry_run: true**
5. Click **Run workflow**

**Expected Result:**
- Workflow runs successfully
- No branches deleted
- Summary shows "Dry Run (Preview Only)"
- Lists branches that would be deleted

### Test 3.3: Manual Workflow Trigger (Active)

1. Go to **Actions** → **Branch Cleanup Automation**
2. Click **Run workflow**
3. Select **dry_run: false**
4. Click **Run workflow**

**Expected Result:**
- Workflow runs successfully
- Eligible branches deleted
- Summary shows "Active Cleanup"
- Lists deleted branches

### Test 3.4: Protected Branch Enforcement

1. Create branches: `main`, `spike/test`, `release/v1.0`
2. Merge all to main
3. Run GitHub Action

**Expected Result:**
- Protected branches NOT deleted
- Regular merged branches deleted (if 7+ days old)
- Summary shows protected branches were skipped

### Test 3.5: Open PR Protection

1. Create a branch and open a PR
2. Merge the branch to main (but don't close PR, if possible)
3. Run GitHub Action

**Expected Result:**
- Branch with open PR NOT deleted
- Other merged branches without open PRs deleted

## 4. Color Output Tests

### Test 4.1: Color Codes

```bash
./scripts/cleanup-branches.sh --dry-run | cat
```

**Expected Result:**
- Output contains ANSI color codes:
  - `\033[0;32m` (green) for protected
  - `\033[0;31m` (red) for deletable
  - `\033[1;33m` (yellow) for warnings

### Test 4.2: Visual Color Check

```bash
./scripts/cleanup-branches.sh --dry-run
```

**Visual Inspection:**
- Protected branches: green text
- Merged branches: red text
- Stale branches: yellow text
- Headings: blue text

## 5. Edge Case Tests

### Test 5.1: Repository Without Remote

```bash
# In a local-only repo
git remote -v
# (should show nothing)

./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Script handles gracefully
- No remote branch analysis
- Local branches analyzed correctly
- Exit code: 0

### Test 5.2: Non-Git Directory

```bash
cd /tmp
./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Error: "Not a git repository"
- Exit code: 1

### Test 5.3: Multiple Protected Patterns

```bash
git checkout -b spike/feature-a
git checkout -b spike/feature-b
git checkout -b release/1.0
git checkout -b release/2.0
git checkout main

./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- All spike/* and release/* branches shown as protected
- None appear in deletion lists

## 6. Recovery Tests

### Test 6.1: Restore Deleted Local Branch

```bash
# Delete a branch
git branch -D test/deleted-branch

# View reflog
git reflog

# Find commit hash (e.g., a1b2c3d)
# Restore branch
git checkout -b test/deleted-branch a1b2c3d
```

**Expected Result:**
- Branch successfully restored
- Commit history intact

### Test 6.2: Remote Branch Recovery

**Note**: Remote branches cannot be easily recovered. This test verifies documentation accuracy.

```bash
# After deleting a remote branch
git push origin --delete test/remote-branch

# Attempt to restore (should fail without local copy)
git checkout test/remote-branch
```

**Expected Result:**
- Error (branch doesn't exist)
- Documentation warns about this

## 7. Performance Tests

### Test 7.1: Many Branches

```bash
# Create 50 test branches
for i in {1..50}; do
  git branch test/branch-$i
done

# Run script
time ./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Script completes in reasonable time (< 10 seconds)
- All branches analyzed correctly

### Test 7.2: Large Repository

```bash
# In a repo with hundreds of commits
./scripts/cleanup-branches.sh --dry-run
```

**Expected Result:**
- Script completes without hanging
- No memory issues

## Test Summary Report Template

```markdown
## Branch Cleanup Automation - Test Results

### Date: YYYY-MM-DD
### Tester: [Name]
### Environment: [OS, Git version]

#### Script Tests
- [ ] Help output: PASS / FAIL
- [ ] Dry-run mode: PASS / FAIL
- [ ] Protected branches: PASS / FAIL
- [ ] Merged detection: PASS / FAIL
- [ ] Interactive mode: PASS / FAIL
- [ ] Force mode: PASS / FAIL

#### npm Scripts
- [ ] cleanup:branches:dry-run: PASS / FAIL
- [ ] cleanup:branches: PASS / FAIL
- [ ] cleanup:branches:force: PASS / FAIL

#### GitHub Action
- [ ] Workflow file valid: PASS / FAIL
- [ ] Manual trigger (dry-run): PASS / FAIL
- [ ] Manual trigger (active): PASS / FAIL
- [ ] Protected branch enforcement: PASS / FAIL

#### Visual/Output
- [ ] Color codes work: PASS / FAIL
- [ ] Clear messaging: PASS / FAIL
- [ ] Undo instructions: PASS / FAIL

#### Edge Cases
- [ ] Non-git directory: PASS / FAIL
- [ ] No branches to clean: PASS / FAIL
- [ ] Current branch protection: PASS / FAIL

### Issues Found:
[List any issues or bugs discovered]

### Screenshots:
- [ ] Dry-run output attached
- [ ] GitHub Action summary attached
- [ ] GitHub repository setting attached

### Overall: PASS / FAIL
```

---

## Automated Test Script

For convenience, here's a test script that runs basic checks:

```bash
#!/usr/bin/env bash
# test-branch-cleanup.sh

set -e

echo "=== Branch Cleanup Automation Tests ==="
echo ""

echo "Test 1: Help output"
./scripts/cleanup-branches.sh --help > /dev/null
echo "✓ PASS"

echo "Test 2: Dry-run mode"
./scripts/cleanup-branches.sh --dry-run > /dev/null
echo "✓ PASS"

echo "Test 3: Force mode requires --yes"
if ./scripts/cleanup-branches.sh --force 2>/dev/null; then
  echo "✗ FAIL: Should require --yes flag"
  exit 1
else
  echo "✓ PASS"
fi

echo "Test 4: npm script (dry-run)"
npm run cleanup:branches:dry-run > /dev/null
echo "✓ PASS"

echo "Test 5: Protected branch detection"
git checkout -b spike/test-protection 2>/dev/null || true
git checkout main
OUTPUT=$(./scripts/cleanup-branches.sh --dry-run)
if echo "$OUTPUT" | grep -q "spike/test-protection"; then
  echo "✓ PASS"
else
  echo "✗ FAIL: Protected branch not detected"
  exit 1
fi

echo ""
echo "=== All tests passed! ==="
```

Save as `test-branch-cleanup.sh`, make executable, and run:

```bash
chmod +x test-branch-cleanup.sh
./test-branch-cleanup.sh
```
