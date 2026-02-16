# GitHub Repository Settings for Branch Cleanup

## Automatically Delete Head Branches

This setting automatically deletes branches when pull requests are merged, complementing the automated cleanup workflow.

### How to Enable

1. Navigate to your repository on GitHub
2. Click **Settings** (top menu bar)
3. Scroll to the **Pull Requests** section
4. Check the box for **"Automatically delete head branches"**

### Visual Guide

```
Settings → General → Pull Requests Section

    ┌─────────────────────────────────────────────────┐
    │  Pull Requests                                  │
    ├─────────────────────────────────────────────────┤
    │                                                 │
    │  ☑ Allow merge commits                         │
    │  ☑ Allow squash merging                        │
    │  ☑ Allow rebase merging                        │
    │                                                 │
    │  ☑ Automatically delete head branches  ← HERE  │
    │                                                 │
    └─────────────────────────────────────────────────┘
```

### What This Does

When enabled:

- ✅ Automatically deletes the **source branch** when a PR is merged
- ✅ Only affects **head branches** (the branch being merged)
- ✅ Does **not** delete the **base branch** (e.g., `main`)
- ✅ Works for both **repository members** and **external contributors**

### What It Doesn't Do

- ❌ Does **not** delete branches that were never in a PR
- ❌ Does **not** delete branches if the PR is closed without merging
- ❌ Does **not** apply retroactively to already-merged PRs

### Why Enable This?

**Benefits:**

1. **Immediate cleanup**: Branches are removed right after merge
2. **Less clutter**: Keeps branch list clean automatically
3. **Complements automation**: Works with weekly cleanup workflow
4. **Best practice**: Industry standard for repository hygiene

**Combined Strategy:**

- **GitHub Setting**: Removes branches immediately on PR merge
- **Weekly Action**: Catches branches that were missed or never had a PR
- **Manual Script**: On-demand cleanup when needed

### Verification

To verify the setting is enabled:

1. Go to **Settings** → **General**
2. Check the **Pull Requests** section
3. Confirm **"Automatically delete head branches"** is checked

Or via GitHub API:

```bash
# Check the setting via GitHub CLI
gh api repos/:owner/:repo | jq '.delete_branch_on_merge'
# Should return: true
```

### Testing

Create a test pull request to verify:

1. Create a test branch: `git checkout -b test/auto-delete`
2. Make a small change and commit
3. Push and create a PR
4. Merge the PR
5. Verify the branch is automatically deleted

### Disabling (Not Recommended)

If you need to disable this setting:

1. Go to **Settings** → **General** → **Pull Requests**
2. Uncheck **"Automatically delete head branches"**

**Note**: This is generally not recommended unless you have a specific workflow requirement.

### Edge Cases

#### Protected Branches

Protected branches are **never** auto-deleted, even with this setting enabled.

#### Forked Repositories

For PRs from forks, this setting only deletes the branch **in the base repository** if the PR was created from a branch in the base repo (not common).

#### Merge Methods

This setting works with all merge methods:

- Regular merge commits
- Squash and merge
- Rebase and merge

### Repository Types

This setting is available for:

- ✅ Public repositories
- ✅ Private repositories
- ✅ Organization repositories
- ✅ Personal repositories

### Related Documentation

- [GitHub Documentation: Managing the automatic deletion of branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches)
- [Branch Cleanup Scripts README](../scripts/README.md)
- [GitHub Actions Workflow](.github/workflows/cleanup-branches.yml)

---

## Verification Checklist

Before submitting a PR, verify:

- [ ] Setting is enabled in repository settings
- [ ] Screenshot of setting included in PR description
- [ ] Test PR confirms automatic deletion works
- [ ] GitHub Action workflow file is present
- [ ] npm scripts are configured
- [ ] Documentation is complete

This setting is **mandatory** for Issue #106 completion.
