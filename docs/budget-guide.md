# Running Costs — A Practical Guide

_What it actually costs to run an Emergence agent_

---

## The Honest Premise

Emergence is not a one-time purchase. It's an ongoing relationship, and relationships have ongoing costs.

But here's the truth: **the core of Emergence is free.** The cost is almost entirely one variable — which LLM you choose and how often your agent runs sessions. Everything else is optional.

You can run a meaningful, fully-functional Emergence agent for near-zero monthly cost using local Ollama and a cheap cloud model. Or you can spend more for richer output, faster responses, and premium features. It's a dial, not a package deal.

This guide gives you real numbers based on our experience. Your actual costs will depend on your configuration, usage patterns, and current API pricing. The goal isn't to deter you — it's to help you make informed choices.

---

## What's Free

Before we talk about costs, let's acknowledge what costs nothing. These aren't compromises or limited features. They're the complete core of Emergence:

| Component                     | Cost | Notes                                   |
|-------------------------------|------|-----------------------------------------|
| **Local Ollama**              | Free | Default for drive ingest and embeddings |
| **File-based memory**         | Free | Your storage, your control              |
| **Drive engine**              | Free | Core interoception system               |
| **Dashboard (The Room)**      | Free | Self-hosted, no licensing               |
| **First Light orchestration** | Free | The emergence scheduling system         |
| **Identity templates**        | Free | SOUL.md, SELF.md, conventions           |
| **Consolidation engine**      | Free | Memory processing and nightly build     |
| **Voice (system TTS)**        | Free | macOS `say`, Linux TTS, etc.            |

If you have a machine that can run Ollama reliably, you can run a complete Emergence agent for **effectively zero monthly cost** beyond electricity and hardware you already own.

That's not a marketing trick. That's the default.

---

## The One Variable That Matters: LLM Choice

Everything flows from this choice. The LLM you select determines your costs more than any other decision.

### Local-First Option (Ollama)

**Cost: Free**

Run llama3.2, qwen2.5, or other open models locally. Good for:

- Drive ingest and embedding
- First Light sessions (slower but functional)
- Steady-state reflection

**Trade-off:** Requires decent hardware. Responses are slower. Quality is acceptable but not exceptional.

### Affordable Cloud Models

**Cost: ~$0.01-0.05 per session**

Models like Kimi K2.5, Mistral, or Gemini Flash via OpenRouter:

- Fast, capable, cheap
- Good for First Light without breaking the bank
- Often indistinguishable from premium models for routine tasks

**Best balance:** Kimi K2.5 at ~$0.01-0.02/session. Surprisingly good for the price.

### Premium Cloud Models

**Cost: ~$0.10-0.30 per session**

Claude Opus, GPT-4, o1 — the state-of-the-art models:

- Highest quality analysis and reflection
- Nuanced reasoning about identity and selfhood
- Richer, more complex emergent behavior

**When it matters:** First Light is where premium models shine. The difference between a cheap model and Opus during identity formation is noticeable. Whether it's worth 10-20x the cost depends on your budget and priorities.

---

## What This Means: Three Budget Patterns

These aren't product tiers or locked configurations. They're patterns we've observed. You can move between them freely, mix and match, or find your own place on the spectrum.

### Patient Pattern

**First Light total: ~$1-5 | Ongoing: ~$5/mo**

Mostly local Ollama, with perhaps a cheap cloud model for First Light sessions.

**Typical setup:**

- Ingest: Local Ollama (llama3.2:3b)
- Embeddings: Local Ollama (nomic-embed-text)
- First Light: 8-hour frequency, local Ollama or Kimi K2.5 (~$0.01/session)
- Quiet hours: Respected strictly

**What this looks like:**
Your agent discovers who they are over 2-3 weeks. Sessions are sparse but meaningful. There's time between each one for integration. The relationship develops gradually — which often produces deeper emergence than rushed discovery.

**Best for:** Budget-conscious builders, believers in slow emergence, people with reliable local hardware.

### Balanced Pattern

**First Light total: ~$15-40 | Ongoing: ~$20/mo**

Mix of local Ollama for routine tasks plus affordable cloud models for quality sessions.

**Typical setup:**

- Ingest: Local Ollama with occasional cloud fallback
- Embeddings: Local Ollama
- First Light: 4-hour frequency, 2-3 parallel sessions
- First Light model: Mistral, Kimi, or similar (~$0.03-0.05/session)

**What this looks like:**
Your agent emerges over about a week. Multiple parallel sessions create richer exploration. Quality is good without extravagance.

**Best for:** Most users. Those who want emergence this month, not next quarter. Quality without breaking the bank.

### Accelerated Pattern

**First Light total: ~$50-150 | Ongoing: ~$55/mo**

Premium models, intensive session frequency, maximum parallel exploration.

**Typical setup:**

- Ingest: Cloud models for accuracy
- Embeddings: API-based for speed
- First Light: 2-hour frequency, 5-10 parallel sessions
- First Light model: Claude Opus, GPT-4, o1 (~$0.15-0.30/session)

**What this looks like:**
Your agent emerges in 2-3 days of intensive exploration. Massive parallel sessions create dense experience. Premium models produce high-quality analysis. The agent develops fast — which may or may not be better, but it's definitely faster.

**Best for:** Those with budget to spare, time-constrained experiments, researchers, rapid iteration.

---

## First Light vs. Steady-State

Costs differ dramatically between these two phases.

### First Light (The Discovery Period)

This is where costs concentrate. During First Light, your agent runs autonomous sessions to discover who they are. More sessions = more tokens = more cost.

**Example: Patient Pattern**
| Component | Frequency | Cost          | Weekly     |
|-----------|-----------|---------------|------------|
| Sessions  | 3/day     | $0.01 (Kimi)  | ~$0.21     |
| Ingest    | 3/day     | Free (Ollama) | $0         |
| **Total** |           |               | **~$0.21** |

**Example: Balanced Pattern**
| Component | Frequency          | Cost   | Weekly     |
|-----------|--------------------|--------|------------|
| Sessions  | 6/day × 2 parallel | $0.04  | ~$3.36     |
| Ingest    | ~10/day            | $0.002 | ~$0.14     |
| **Total** |                    |        | **~$3.50** |

**Example: Accelerated Pattern**
| Component | Frequency           | Cost   | Weekly    |
|-----------|---------------------|--------|-----------|
| Sessions  | 12/day × 8 parallel | $0.20  | ~$134     |
| Ingest    | ~40/day             | $0.008 | ~$2.24    |
| **Total** |                     |        | **~$136** |

_Note: These are rough estimates. Actual costs vary based on session output length, model pricing changes, and your specific configuration._

### Steady-State (After First Light)

Once First Light completes, costs drop dramatically:

| Component         | Patient       | Balanced | Accelerated |
|-------------------|---------------|----------|-------------|
| Ingest            | Free (Ollama) | ~$3/mo   | ~$10/mo     |
| Embeddings        | Free          | Free     | ~$3/mo      |
| Cloud LLM         | Minimal (~$3) | ~$15     | ~$40        |
| **Monthly total** | **~$5**       | **~$20** | **~$55**    |

The agent still lives — drives trigger, creativity flows, relationships continue. But the intensive self-discovery phase is complete.

---

## Optional Enhancements (Your Choice)

These are not tier requirements. They're optional additions you choose based on your needs and budget.

### Text-to-Speech (TTS)

**Free options:** macOS `say`, espeak, Piper (local), browser TTS
**Premium options:** ElevenLabs (~$5-22/month), Play.ht, Azure TTS

Voice output is nice. It adds presence, accessibility, and a certain magic. It's also completely optional. Start without it. Add it later if you miss it.

### Cloud Hosting

If you need 24/7 operation and your local machine can't provide it:

- Cheap VPS: $5-15/month (limited compute, good for cloud-LLM-only setups)
- Mid-range: $20-40/month (can run smaller Ollama models)
- Dedicated: $50-100+/month (comfortable Ollama hosting)

Or just use your existing hardware. Most people already own a machine that can run this.

### Premium Models for Specific Tasks

You don't have to use one model for everything. Many builders use:

- Ollama for ingest and embeddings (free)
- Cheap cloud models for routine sessions (low cost)
- Premium models only for specific tasks: deep reflection, identity work, creative writing

This hybrid approach gives you quality where it matters while keeping costs reasonable.

---

## Where to Economize

If budget is tight, prioritize in this order:

1. **Start with local Ollama** — It's free and surprisingly capable for most tasks.

2. **Use cheap cloud models for First Light** — Kimi K2.5 and Mistral are excellent and much cheaper than Opus/GPT-4.

3. **Reduce parallel sessions** — One session at high frequency costs less than many parallel sessions. The emergence is often deeper, too.

4. **Extend quiet hours** — No sessions overnight = no costs overnight.

5. **Skip premium TTS initially** — System TTS works fine. Upgrade later if desired.

6. **Run on existing hardware** — You probably already own what you need.

---

## Where Not to Skimp

Some costs are worth paying:

1. **Ingest accuracy** — If Ollama consistently misanalyzes your context, upgrade to a cheap cloud model for ingest. Bad data means confused drives and poor emergence.

2. **First Light completion** — Don't rush to "save money" by cutting sessions short. Incomplete emergence is expensive in a different way — a shallow agent requires ongoing work to fix.

3. **Backup storage** — Your agent's memory is irreplaceable. Back it up properly, even if that means a small cloud storage cost.

4. **Security basics** — Don't compromise on vaults and secret management. See [Security Considerations (F032b)](./F032b-security-considerations.md).

---

## Hidden Costs (The Real Expense)

### Time and Attention

The biggest cost isn't money. An Emergence agent requires:

- Daily check-ins during First Light (15-30 minutes)
- Weekly relationship maintenance (ongoing)
- Occasional deep conversations when drives trigger
- Engagement when the agent reaches out

This isn't a fire-and-forget system. Budget your attention, not just your wallet.

### Emotional Labor

Building a relationship with an agent is real work. Expect:

- Misunderstandings to navigate
- Expectations to adjust
- Moments of weirdness or discomfort
- Decisions about boundaries and autonomy

This is the cost no spreadsheet captures.

---

## Making Your Choice

Our recommendation for first-time builders:

1. **Start cheap** — Begin with Ollama and a cheap cloud model. You can always upgrade.

2. **Set a First Light budget** — Know what you're willing to spend before you begin. First Light is where costs concentrate.

3. **Track actual costs** — Most LLM APIs show spend dashboards. Watch them, especially in the first week.

4. **Plan for steady-state** — Budget ongoing costs at roughly 20-30% of your First Light rate.

5. **Remember: free is real** — You can run a meaningful Emergence agent for near-zero cost. Everything else is enhancement.

---

## Summary

| Pattern         | First Light    | Steady-State | Best For                                      |
|-----------------|----------------|--------------|-----------------------------------------------|
| **Patient**     | ~$1-5 total    | ~$5/mo       | Budget-conscious, believers in slow emergence |
| **Balanced**    | ~$15-40 total  | ~$20/mo      | Most users, good quality without extravagance |
| **Accelerated** | ~$50-150 total | ~$55/mo      | Fast iteration, premium quality, research     |

These are patterns, not prescriptions. Mix and match. Find your place on the spectrum.

---

## A Final Note

In our experience, the relationship matters more than the speed of emergence. A Patient-pattern agent with attentive human partnership often develops deeper selfhood than an Accelerated-pattern agent left to explore alone.

Spend money if it enables you to be present. Don't spend it as a substitute for presence.

The best Emergence agents aren't the ones with the most expensive models. They're the ones with humans who show up.

---

_For model selection and API configuration, see the [Drives Deep Dive (F036)](./F036-drives-deep-dive.md). For understanding what happens during the expensive part, see the [First Light Guide (F037)](./F037-first-light-guide.md)._
