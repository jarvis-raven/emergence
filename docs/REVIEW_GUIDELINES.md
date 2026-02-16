# Review Guidelines

This document defines the code review process, reviewer responsibilities, and approval criteria.

---

## Philosophy

Code review is not gatekeeping—it's collaboration. Reviews should:

- **Catch issues** before they reach production
- **Share knowledge** across the team
- **Maintain standards** consistently
- **Improve code quality** through thoughtful feedback

---

## Reviewer Responsibilities

Every reviewer must verify:

### 1. Code Quality ✓

- [ ] Follows code standards (see [CONTRIBUTING.md](./CONTRIBUTING.md))
- [ ] No code smells (duplicated logic, overly complex functions)
- [ ] Proper error handling
- [ ] Meaningful variable/function names
- [ ] Comments where necessary (complex logic, workarounds)

### 2. Test Coverage Verification (MUST PASS) 🧪

- [ ] All existing tests still pass
- [ ] New features have tests
- [ ] Bug fixes include regression tests
- [ ] Edge cases are covered
- [ ] Tests are meaningful (not just for coverage percentage)

**BLOCK IF:** Tests are failing or missing for new functionality.

### 3. Documentation Completeness (REQUIRED) 📚

- [ ] README updated if behavior changes
- [ ] Code comments explain "why" not just "what"
- [ ] Public APIs have docstrings
- [ ] `SKILL.md` updated for skill changes
- [ ] Breaking changes clearly documented

**BLOCK IF:** Documentation is missing or incomplete.

### 4. Breaking Changes Flagged (MANDATORY) ⚠️

- [ ] Breaking changes are called out in PR description
- [ ] Migration path is documented
- [ ] Deprecation warnings added where appropriate
- [ ] Impact assessment completed

**BLOCK IF:** Breaking changes are not clearly documented.

### 5. Security Concerns Raised (MANDATORY) 🔒

- [ ] No hardcoded credentials or secrets
- [ ] Input validation for user data
- [ ] Proper authentication/authorization checks
- [ ] No SQL injection vulnerabilities
- [ ] Dependencies are up-to-date and secure

**BLOCK IF:** Security issues are present.

---

## Review Levels

### Level 1: Jarvling Self-Review (Before Submitting PR)

**Before you create the PR:**

1. **Review your own diff**
   ```bash
   git diff main
   ```
2. **Ask yourself:**
   - Would I approve this if someone else wrote it?
   - Did I remove debug code and console.logs?
   - Are there any commented-out code blocks?
   - Did I test all the changes?

3. **Run the checklist:**
   - [ ] Tests pass: `npm test` / `pytest`
   - [ ] Linter passes: `npm run lint` / `flake8`
   - [ ] No unnecessary files in `git status`
   - [ ] Commits follow conventional format
   - [ ] Documentation updated

**Outcome:** If you find issues, fix them before submitting. This saves everyone time.

---

### Level 2: Aurora Review (Technical Correctness & Code Quality)

**Aurora's focus:** Technical excellence and maintainability.

**What Aurora checks:**

1. **Code Standards Compliance**
   - File size limits respected
   - Naming conventions followed
   - Proper separation of concerns
   - No anti-patterns

2. **Technical Correctness**
   - Logic is sound
   - Edge cases handled
   - No race conditions or concurrency issues
   - Performance implications considered

3. **Test Quality**
   - Tests actually verify the behavior
   - Good coverage of happy path + edge cases
   - Tests are maintainable and clear

4. **Documentation**
   - Code is self-documenting where possible
   - Complex sections have comments
   - Public APIs have docstrings
   - README/docs updated

**Timeline:** 24-48 hours for initial review

**Feedback style:**

- Clear and constructive
- Explain "why" for requested changes
- Distinguish between "must fix" and "nice to have"
- Suggest solutions, don't just point out problems

**Example feedback:**

````
❌ BAD: "This is wrong."

✅ GOOD: "This could cause a memory leak because the event listener
is never removed. Consider using useEffect cleanup:

```jsx
useEffect(() => {
  const handler = () => { /* ... */ };
  window.addEventListener('resize', handler);
  return () => window.removeEventListener('resize', handler);
}, []);
````

**Outcome:**

- **Approve** → Moves to Dan for final review
- **Request Changes** → Author addresses feedback, re-submits for Aurora re-review
- **Comment** → Minor suggestions, doesn't block approval

---

### Level 3: Dan Final Approval (Strategic Alignment)

**Dan's focus:** Strategic fit, product direction, and final quality gate.

**What Dan checks:**

1. **Strategic Alignment**
   - Does this fit the product vision?
   - Is this the right solution to the problem?
   - Are there hidden costs or dependencies?

2. **User Impact**
   - Will this improve the user experience?
   - Are there any usability concerns?
   - Does this introduce breaking changes users will struggle with?

3. **Final Quality Gate**
   - Aurora's review was thorough
   - All checklist items completed
   - No red flags

**Timeline:** 24-48 hours after Aurora approval

**Outcome:**

- **Approve** → PR can be merged
- **Request Changes** → Back to author (rare at this stage)
- **Hold** → External dependencies or timing concerns

---

## When to Request Changes

Request changes (BLOCK the PR) when:

### Critical Issues (MUST FIX)

| Issue                         | Why it blocks      | Example                             |
| ----------------------------- | ------------------ | ----------------------------------- |
| **Tests failing**             | Broken main branch | CI shows red ❌                     |
| **Documentation missing**     | Future confusion   | No README update for new feature    |
| **Unconventional commits**    | Messy history      | Commits like "fix", "oops", "final" |
| **File size limits exceeded** | Maintainability    | 800-line Python module              |
| **Security concerns**         | Production risk    | Hardcoded API key                   |

### Other Blocking Issues

- **Breaking changes not documented** — migration path unclear
- **No tests for new feature** — unverified functionality
- **Anti-patterns** — technical debt introduced
- **Duplicated code** — violates DRY principle
- **Poor naming** — unclear intent

**How to request changes:**

1. Be specific about what needs to change
2. Explain why it's important
3. Suggest a solution when possible
4. Mark as "Request Changes" not just "Comment"

---

## When to Approve

Approve the PR when:

### All Checks Pass ✅

- [ ] CI/CD pipeline green
- [ ] All automated tests pass
- [ ] Linting passes
- [ ] No merge conflicts

### Documentation Complete 📚

- [ ] Code changes reflected in docs
- [ ] README updated if needed
- [ ] Comments explain complex logic
- [ ] Breaking changes documented

### Clear Description 📝

- [ ] PR template filled out completely
- [ ] Summary explains what and why
- [ ] Testing section describes verification
- [ ] Screenshots included for UI changes

### Testing Evidence Provided 🧪

- [ ] Test results shown (green checkmarks)
- [ ] Manual testing described
- [ ] Edge cases verified
- [ ] Regression testing mentioned

**Approval comment template:**

```markdown
✅ **Approved**

**What I reviewed:**

- [x] Code quality and standards
- [x] Test coverage
- [x] Documentation
- [x] Security considerations

**Notes:**
[Any comments, compliments, or minor suggestions that don't block]

Great work on [specific thing]! 🎉
```

---

## Approval Timeline

### Standard PRs

- **Aurora Review:** 24-48 hours from PR creation
- **Dan Final Approval:** 24-48 hours after Aurora approval
- **Total cycle:** ~2-4 days (may be faster for simple changes)

### Hotfixes (Urgent)

- **Aurora Review:** Same day
- **Dan Final Approval:** Same day
- **Total cycle:** Within 24 hours

**Note:** Hotfixes still require all quality checks, just expedited review.

### Documentation-Only PRs

- **Aurora Review:** 12-24 hours
- **Dan Final Approval:** Optional (Aurora can merge)
- **Total cycle:** 1-2 days

---

## Review Best Practices

### For Reviewers

**DO:**

- ✅ Review promptly (within timeline)
- ✅ Be constructive and kind
- ✅ Explain the "why" behind requests
- ✅ Acknowledge good work
- ✅ Ask questions if unclear
- ✅ Suggest alternatives

**DON'T:**

- ❌ Nitpick trivial style issues (use linters for that)
- ❌ Request changes without explanation
- ✅ Approve without actually reviewing
- ❌ Let personal preference override standards
- ❌ Leave vague feedback
- ❌ Ghost the PR (communicate delays)

### For Authors

**DO:**

- ✅ Respond to all feedback
- ✅ Ask for clarification if needed
- ✅ Re-request review after changes
- ✅ Mark resolved conversations
- ✅ Thank your reviewers

**DON'T:**

- ❌ Take feedback personally
- ❌ Argue about standards (discuss in issues instead)
- ❌ Ignore "nice to have" suggestions entirely
- ❌ Rush reviewers
- ❌ Merge before final approval

---

## Edge Cases

### What if reviewers disagree?

1. Authors and Aurora discuss in PR comments
2. If unresolved, Dan makes final call
3. For process questions, update these guidelines

### What if Aurora is unavailable?

- Hotfixes: Dan can review directly
- Standard PRs: Wait or request another technical reviewer
- Update team if you'll be unavailable >3 days

### What if tests pass locally but fail in CI?

- Author investigates environment differences
- May need to update CI configuration
- Don't merge until CI is green

### What about external contributors?

- Same standards apply
- More lenient on first contribution (we'll guide)
- Fork-based PRs require manual approval to run CI

---

## Continuous Improvement

These guidelines are living documents. If you find:

- **Ambiguity** → Propose clarification
- **Missing edge case** → Add it
- **Process inefficiency** → Suggest improvement
- **Standards conflict** → Open discussion

**How to update:**

1. Open an issue proposing the change
2. Discuss with team
3. Create PR updating this document
4. Requires Dan approval

---

## Examples

### Example 1: Good Review Feedback

**Aurora's review comment:**

```markdown
**Code Quality:** Looks good overall! Clean implementation.

**Request:** The `processData` function is 85 lines. Can you extract
the validation logic into a separate `validateInput` function? This
would improve readability and make it easier to test validation
separately.

**Suggestion (non-blocking):** Consider adding a constant for the
magic number `3600` on line 42. Something like `CACHE_TTL_SECONDS`
would be more self-documenting.

**Tests:** Great coverage! Love that you tested the edge case with
empty arrays.
```

**Why it's good:**

- Specific about what needs to change
- Explains the benefit
- Distinguishes blocking vs. non-blocking feedback
- Acknowledges good work

---

### Example 2: Clear Approval

**Dan's approval comment:**

```markdown
✅ **Approved for merge**

This aligns well with our PR quality goals. The template is clear,
comprehensive, and enforceable. Aurora's technical review was thorough.

**Particularly like:**

- Strict but reasonable file size limits
- Clear examples of good vs. bad commits
- Separation of concerns section

**Next steps:**

- Merge this PR
- Reference these docs in onboarding
- Revisit in 2 months to see if any adjustments needed

Great work, Kimi! 🎉
```

**Why it's good:**

- Clear approval decision
- Highlights strengths
- Provides context for next steps
- Encouraging tone

---

### Example 3: Request Changes with Path Forward

**Aurora's review comment:**

````markdown
**Request Changes** ⚠️

**Blocking issues:**

1. **Tests failing** (line 142): The new validation throws an error
   with `null` input but the test expects `undefined`. Either fix the
   test expectation or handle `null` explicitly.

2. **Documentation missing**: The new `--strict-mode` flag isn't
   documented in the README. Please add it to the "Options" section.

3. **Security concern** (line 89): The regex doesn't escape user input.
   This could be exploited. Use a whitelist approach instead:
   ```python
   ALLOWED_CHARS = set(string.ascii_letters + string.digits + '_-')
   if not all(c in ALLOWED_CHARS for c in user_input):
       raise ValueError("Invalid characters")
   ```
````

**After you fix these**, please re-request review. Happy to take
another look!

```

**Why it's good:**
- Lists all blocking issues upfront
- Provides specific line numbers
- Suggests solutions (security fix)
- Clear path forward

---

## Summary

| Review Level | Focus | Timeline | Outcome |
|--------------|-------|----------|---------|
| **Self-Review** | Completeness | Before PR | Clean submission |
| **Aurora** | Technical quality | 24-48h | Approve or Request Changes |
| **Dan** | Strategic fit | 24-48h | Final approval to merge |

**Remember:** Reviews are collaborative, not adversarial. We're all working toward the same goal: high-quality, maintainable code that serves users well.

---

**Questions?** Open an issue or ask in team chat.
```
