# Identity Templates

This directory contains **template files** for agent identity. These are the source files that `emerge init` uses to generate an agent's personal identity files.

## Template Pattern

**Templates in this repo** (tracked in git):
- `SOUL.template.md`
- `AGENTS.template.md`
- `SELF.template.md`
- etc.

**Generated files in agent workspace** (NOT tracked in git):
- `SOUL.md` (created from template)
- `AGENTS.md` (created from template)
- `SELF.md` (created from template)
- etc.

## Why This Matters

When agents pull updates to Emergence:
- ✅ Template updates don't conflict with their personal files
- ✅ No risk of overwriting identity data
- ✅ Clean separation between "source code" and "runtime data"

## Protection

The `.gitignore` at repo root protects against accidental commits:
```
# Agent identity files (generated from templates during init)
SOUL.md
AGENTS.md
SELF.md
...
```

**Never commit the generated `.md` files** - only edit the `.template.md` files in this directory.

## Editing Templates

When improving the templates (like adding file size guidance or maintenance patterns):
1. Edit the `.template.md` file in this directory
2. Test with `emerge init` to verify changes work
3. Commit and push
4. Agents get the updates when they pull, but their personal files stay untouched

## first-boot.md

Exception: `first-boot.md` is not a template (no `.template.md` suffix) because it's copied as-is during init. It's a one-time welcome message that doesn't need placeholder replacement.
