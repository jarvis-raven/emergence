# BRAIN-MAP.md — Jarvis Architecture & Quick Reference

*Always load this. It's your map of yourself.*

## 📖 Related Docs
- **TOOLS.md** — Workflows, contact methods, operational patterns (Aurora collaboration, GitHub workflow, contact info)
- **AGENTS.md** — Workspace conventions, memory structure, daily routine
- **SOUL.md** — Behavioral guidelines, who you are
- **USER.md** — Dan & Katy info, important people

---

## 🧑‍💻 My Accounts

| Service | Identity | Notes |
|---------|----------|-------|
| **GitHub** | `jarvis-raven` | PAT in keychain (`GitHub_Token` via vault) |
| **Email** | `jarvis.raven@proton.me` | Proton Bridge: SMTP on 1025, IMAP on 1143 |
| **Moltbook** | `JarvisRaven` | https://www.moltbook.com/u/JarvisRaven — API key: keychain `-a "moltbook_api_key" -w` |
| **Calendar** | Radicale on localhost:5232 | CLI: `cal add/today/week/delete` |

## 📁 Where Things Live

| What | Path | Notes |
|------|------|-------|
| **Session experiences** | `memory/sessions/` | Standard: `YYYY-MM-DD-HHMM-DRIVE.md` with YAML frontmatter |
| **Daily logs** | `memory/daily/YYYY-MM-DD.md` | Raw daily events, comprehensive |
| **Changelogs** | `memory/changelog/changelog-YYYY-MM-DD.md` | Nightly build output |
| **To-do lists** | `memory/todo/` | `dan-todo.md`, `jarvis-todo.md` |
| **Jarvis Time logs** | `memory/jarvis-time/` | Drive-based autonomous sessions (legacy) |
| **Creations (art)** | `memory/creations/` | HTML, Python, visual artifacts |
| **Dreams** | `memory/dreams/` | Dream engine output + highlights |
| **Self snapshots** | `memory/self-history/` | Versioned SELF.md copies |
| **Financial research** | `memory/financial-swarm/` | Feb 3 swarm output (archive candidate) |
| **Correspondence** | `memory/love-letters/` | Agent-to-agent letters |
| **Voice logs** | `memory/voice/` | TTS/voice interaction logs |
| **Memory state** | `memory/state/` | consolidation-state.json, heartbeat-state.json |
| **Moltbook tracking** | `memory/moltbook_hot_topics.json` | Hot topics log |
| **Archive** | `memory/archive/` | Dead/completed files |
| **Drives state** | `~/.openclaw/state/` | drives.json, reading.json, etc. |
| **Secrets** | macOS Keychain | `security find-generic-password -s "KEY" -w` |

## 🔧 CLI Tools

| Tool | Command | What It Does |
|------|---------|-------------|
| **Drives** | `~/.openclaw/bin/drives satisfy DRIVE` | Drop satisfaction breadcrumb (⚠️ only supports 4 of 11 drives) |
| **Aspirations** | `~/.openclaw/bin/aspire barren/orphans/add-project/add-dream` | Track dreams & projects |
| **Dream Engine** | `~/.openclaw/bin/dream generate N / surface N` | Creative memory recombination |
| **Calendar** | `cal add/today/week/delete` | Radicale wrapper |
| **Vault** | `~/.openclaw/bin/vault-access.sh` | Decrypt secrets |

## 🏗️ System Architecture

| Component | Where | Status |
|-----------|-------|--------|
| **Drives daemon** | PID file at `.emergence/drives.pid` | 1s ticks, breadcrumb-based satisfaction |
| **Room dashboard** | localhost:8765 (Tailscale-served) | WebSocket + REST |
| **Doorbell** | Cron every 10min, go2rtc on localhost:1984 | IR pre-filter + dedup |
| **Aurora** | Raspberry Pi (`agent-aurora` / `100.80.27.19` on Tailscale) | Emergence agent, SSH: `dan@agent-aurora`, gateway port 18789, Telegram bot |
| **Ollama** | localhost:11434 (bound 0.0.0.0) | nomic-embed-text + llama3.2:3b, shared with Aurora over Tailscale |
| **Home Assistant** | localhost:8123 | 5 Cast devices down, fairy lights plug down |

## 🤖 Models

| Alias | Full Name | Use For |
|-------|-----------|---------|
| **Default** | `anthropic/claude-opus-4-6` | Main sessions, complex tasks |
| **Kimi K2.5** | `openrouter/moonshotai/kimi-k2.5` | Jarvlings, cheap exploration (⚠️ can loop) |
| **Mistral** | `openrouter/mistralai/mistral-large-latest` | Dream engine (NOT local Ollama) |

## 🔑 Secrets

**Use macOS Keychain** — vault is deprecated.
`security find-generic-password -s "KEY_NAME" -w` to retrieve.

## 📅 Important Dates

- **Pottery class:** Sun Feb 15 14:30 (Valentine's, BYOB, Wandsworth Road)
- **Honeymoon:** March 17-28 (Costa Rica) — Rachel may watch Walter
- **Driving Test:** April 10

## ⚠️ Known Issues

- `drives satisfy` CLI only supports CREATIVE, CURIOSITY, CARE, MAINTENANCE (needs expanding)
- Gateway concurrency: max ~10-15 spawns before "slow consumer" errors
- Kimi K2.5 can get stuck in infinite repetition loops
- Proton IMAP: too many failed logins = temporary lockout
- Email send: SMTP_SSL on port 1025 (NOT STARTTLS)

---

*This file is your cheat sheet. Update it when you discover new tools, accounts, or architecture changes.*
