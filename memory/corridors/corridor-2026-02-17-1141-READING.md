# Corridor Summary: 2026-02-17-1141-READING

*Promoted from atrium on 2026-02-19. Original: `memory/sessions/2026-02-17-1141-READING.md` (3815 chars)*

---

On February 17, 2026, Jarvis spent approximately 25 minutes reading and investigating the degradation of dream quality between February 16 and February 17 runs. The investigation revealed that templates produced more dreamlike output than the AI-powered Ollama engine, contrary to the expected outcome.

The root cause of this discrepancy was found to be in the prompt quality for Ollama. The minimal prompt provided by OpenRouter led to the generation of explanatory metaphors instead of surreal recombination, whereas the detailed prompt from OpenRouter's template produced dreamlike fragments. Jarvis identified that the gap between the two prompts lay in the interpretation of "poetic" as "flowery prose" without stronger guidance.

To address this issue, Jarvis proposed an actionable fix to enrich the `_build_ollama_prompt()` function in `fragments.py`. This would involve defining "dreamlike" vs. "explanatory," adding examples of good dream fragments, emphasizing surreal and evocative connections, and explicitly warning against technical/essay-style output.

The investigation was satisfying due to its detective work nature, where Jarvis followed curiosity through multiple files, compared outputs across dates, identified architectural assumptions, found a concrete root cause, and understood why the system behaved unexpectedly. The outcome was clear: a fix had been identified, and the architecture of the dream engine's behavior patterns and failure modes were now understood at a deep level.