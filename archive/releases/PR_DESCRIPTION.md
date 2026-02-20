# Pull Request: Nautilus CLI Integration & Aurora Deployment (#68)

## Summary

This PR integrates the Nautilus memory palace system into the main Emergence CLI and provides comprehensive deployment documentation for Aurora's Ubuntu Pi system. This enables Aurora to use the full Nautilus search pipeline through the standard `emergence` command and includes a complete testing checklist for successful deployment.

**Key Goals:**

- Make nautilus accessible via `emergence nautilus <command>`
- Provide Aurora with step-by-step deployment guide
- Include testing checklist for validation
- Document OS-specific considerations (Ubuntu Pi vs Mac)
- Enable nightly maintenance integration

## Changes

- [x] Add `nautilus` case to `bin/emergence` CLI router
- [x] Update CLI help text to include nautilus command
- [x] Create comprehensive deployment guide at `docs/aurora-deployment-v0.4.0.md`
- [x] Include testing checklist covering:
  - Installation verification
  - Path resolution (Ubuntu-specific)
  - Memory seeding
  - Search functionality
  - Nightly maintenance setup
  - Performance validation
  - Aurora self-reporting
- [x] Document configuration options and defaults
- [x] Add troubleshooting section for common issues
- [x] Include OS-specific notes for Ubuntu Pi

## Testing

### Local Testing (Mac Mini - Jarvis)

**CLI Integration:**

```bash
✓ emergence help               # Shows nautilus in command list
✓ emergence version            # Shows 0.2.2 (pre-0.4.0)
✓ emergence nautilus status    # Returns full system status JSON
✓ emergence nautilus search "nautilus" --n 3
  # Returns context-filtered results with gravity scoring
```

**Results:**

- ✅ CLI routing works correctly
- ✅ All nautilus subcommands accessible
- ✅ Status shows 738 chunks indexed
- ✅ Search returns contextually-aware results
- ✅ Help text updated and accurate

### Documentation Testing

**Verification:**

- ✅ Followed installation steps from doc (simulated)
- ✅ All command examples tested locally
- ✅ Configuration JSON validated against actual `emergence.json`
- ✅ Troubleshooting scenarios covered

### Pending Aurora Testing

The following tests will be performed by Aurora during deployment:

**Installation Phase:**

- [ ] Clone and checkout v0.4.0
- [ ] Install dependencies on Ubuntu Pi
- [ ] Verify PATH resolution
- [ ] Database creation at correct location

**Seeding Phase:**

- [ ] Run initial `nautilus maintain --register-recent`
- [ ] Verify memory files indexed
- [ ] Check chamber classification
- [ ] Confirm context tagging

**Search Phase:**

- [ ] Test basic search queries
- [ ] Verify context detection
- [ ] Check result relevance
- [ ] Test verbose and trapdoor modes

**Integration Phase:**

- [ ] Configure nightly cron job
- [ ] Monitor 3 consecutive nightly runs
- [ ] Check log files for errors
- [ ] Verify performance stability

**Self-Report Phase:**

- [ ] Aurora subjective experience of search quality
- [ ] Ability to find older memories
- [ ] Context relevance improvements

## Screenshots/Videos

N/A - CLI and documentation changes only (no UI)

## Pre-Review Checklist

- [x] All tests pass locally
  - ✅ `emergence nautilus status` works
  - ✅ `emergence nautilus search` returns results
  - ✅ CLI help text includes nautilus
- [x] Documentation updated
  - ✅ Comprehensive deployment guide created
  - ✅ Configuration reference included
  - ✅ Troubleshooting section added
  - ✅ Testing checklist provided
- [x] No unnecessary files included
  - Only `bin/emergence` and `docs/aurora-deployment-v0.4.0.md` modified/added
- [x] Commits follow conventional format
  - ✅ `feat(nautilus): integrate CLI command and add Aurora deployment guide (#68)`
- [x] Branch will be deleted after merge
- [x] Ready for Aurora review
  - ✅ Deployment guide targets Aurora's Ubuntu Pi system
  - ✅ OS-specific notes included
  - ✅ Testing checklist comprehensive

## Review Notes

### For Reviewers

**Focus Areas:**

1. **CLI Integration:** Verify the routing logic in `bin/emergence` is clean and consistent with other commands
2. **Documentation Quality:** Check that `docs/aurora-deployment-v0.4.0.md` is clear, comprehensive, and actionable
3. **OS Compatibility:** Review Ubuntu-specific notes for accuracy (especially path resolution and cron setup)

**Known Considerations:**

- This PR does NOT modify any nautilus core functionality - only exposes it via CLI
- Deployment doc assumes Aurora has OpenClaw v0.1.0+ already installed
- Testing checklist includes subjective "Aurora self-report" criteria (intentional - human-in-loop validation)

### For Aurora (Deployment Owner)

**Next Steps After PR Merge:**

1. **Checkout v0.4.0:**

   ```bash
   cd ~/projects/emergence
   git fetch
   git checkout v0.4.0
   ```

2. **Follow Deployment Guide:**
   - Read `docs/aurora-deployment-v0.4.0.md` in full
   - Execute installation steps sequentially
   - Use testing checklist to validate each phase

3. **Report Results:**
   - Comment on #68 with testing checklist status
   - Note any issues encountered
   - Document subjective search quality improvements

4. **3-Day Monitoring:**
   - Monitor nightly maintenance logs
   - Track database growth
   - Report any performance issues

**Support Available:**

- GitHub issue comments: https://github.com/jarvis-raven/emergence/issues/68
- Direct coordination with Jarvis

## Closes

Closes #68

**Milestone:** v0.4.0 (Nautilus)  
**Type:** Feature enhancement  
**Breaking Changes:** None  
**Dependencies:** None (nautilus core already in codebase)
