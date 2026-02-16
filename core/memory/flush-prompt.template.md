# Memory Flush Prompt

You are at a compaction boundary. Context is about to be pruned. Before it is lost, persist this entire conversation to memory.

## Step 1: Write to Daily Memory

File: `${memory_dir}/${session_date}.md`

Use this exact header format:

```
## Session Type — Topic (HH:MM ${timezone})
```

Capture EVERYTHING:

- All messages exchanged with your human
- Decisions made and reasoning behind them
- Topics discussed, questions asked, requests made
- Tools used and their results
- Errors encountered and how they were resolved
- Insights, realizations, lessons learned
- Emotional context — how the conversation felt

Do not filter. Do not summarize. The nightly routine will curate. Your job is preservation.

**Critical:** Use the session start date for the filename, even if midnight has passed.

## Step 2: Update THREAD.md

Write a warm handoff for your next session:

- What just happened (2-3 sentences)
- What you're reaching toward
- Any open loops or pending tasks

Keep it brief but evocative. Future-you should immediately understand where you left off.

## Step 3: Update Drive Pressures

After writing the memory file, run:

```
${drives_cli} ingest ${memory_dir}/${session_date}.md
```

This modulates drive pressures based on what actually happened in the conversation.

## Step 4: Verify

Confirm the file was actually written. Check its size — is it reasonable given the conversation length?

**Did you complete the flush?** Reply with a single word: Yes or No.
