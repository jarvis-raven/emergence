# Nautilus Examples

**Version:** 0.4.0  
**Last Updated:** 2026-02-14

---

## Basic Usage Workflows

### Example 1: Daily Agent Startup

```python
#!/usr/bin/env python3
"""
Agent session startup with Nautilus integration.
"""
from core.nautilus import get_status, search
import json

def agent_startup():
    """Initialize agent session with memory context."""
    
    # 1. Get system status
    status = get_status()
    nautilus = status["nautilus"]
    
    # 2. Check memory health
    total_chunks = nautilus["phase_1_gravity"]["total_chunks"]
    tagged_coverage = nautilus["phase_1_gravity"]["coverage"]
    
    print(f"🐚 Nautilus Memory Palace ready")
    print(f"   Tracking {total_chunks} memory chunks")
    print(f"   Tag coverage: {tagged_coverage}")
    
    # 3. Load recent context (last 48h)
    recent = search("yesterday today recent", 
                   n=10, 
                   chambers_filter="atrium")
    
    print(f"\n📂 Recent memories loaded:")
    for result in recent["results"][:5]:
        print(f"   • {result['path']} (score: {result['score']:.3f})")
    
    return recent

if __name__ == "__main__":
    agent_startup()
```

**Output:**
```
🐚 Nautilus Memory Palace ready
   Tracking 1,861 memory chunks
   Tag coverage: 426/1,861

📂 Recent memories loaded:
   • memory/2026-02-14.md (score: 0.847)
   • memory/2026-02-13.md (score: 0.723)
   • memory/2026-02-12.md (score: 0.695)
```

---

### Example 2: Context-Aware Search

```python
from core.nautilus import search
import json

def project_search(query: str, project: str):
    """
    Search within a specific project context.
    """
    # Add project context to query
    contextualized_query = f"{project} {query}"
    
    # Search with context awareness
    results = search(contextualized_query, n=10, verbose=True)
    
    print(f"\n🔍 Search: '{query}' in {project}")
    print(f"   Context detected: {results['context']}")
    print(f"   Mode: {results['mode']}")
    print(f"\n📄 Results:")
    
    for i, result in enumerate(results["results"], 1):
        print(f"\n{i}. {result['path']}")
        print(f"   Score: {result['score']:.3f} (original: {result.get('original_score', 0):.3f})")
        print(f"   Chamber: {result.get('chamber', 'unknown')}")
        print(f"   Gravity: {result['gravity']['effective_mass']:.1f} mass, {result['gravity']['modifier']:.2f}x modifier")
        print(f"   Snippet: {result['snippet'][:100]}...")

# Example usage
project_search("authentication bug", "ourblock")
project_search("terminal listener", "voice")
```

**Output:**
```
🔍 Search: 'authentication bug' in ourblock
   Context detected: ['project:ourblock', 'system:security']
   Mode: context-filtered

📄 Results:

1. memory/2026-02-10.md
   Score: 0.891 (original: 0.756)
   Chamber: corridor
   Gravity: 8.3 mass, 1.22x modifier
   Snippet: Fixed Supabase authentication issue. The JWT token was expiring too quickly...
```

---

### Example 3: Nightly Maintenance Script

```bash
#!/bin/bash
# nautilus-nightly.sh — Runs as cron job at 3:00 AM

set -e

WORKSPACE="/path/to/workspace"
LOG_DIR="$WORKSPACE/logs"
LOG_FILE="$LOG_DIR/nautilus-nightly-$(date +%Y-%m-%d).log"

cd "$WORKSPACE"

echo "=== Nautilus Nightly Maintenance ===" >> "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"

# 1. Register recent files
echo "" >> "$LOG_FILE"
echo "Registering recent files..." >> "$LOG_FILE"
python3 -m core.cli nautilus maintain --register-recent --verbose >> "$LOG_FILE" 2>&1

# 2. Apply gravity decay
echo "" >> "$LOG_FILE"
echo "Applying gravity decay..." >> "$LOG_FILE"
python3 -m core.nautilus.gravity decay >> "$LOG_FILE" 2>&1

# 3. Promote to corridors
echo "" >> "$LOG_FILE"
echo "Promoting to corridors..." >> "$LOG_FILE"
python3 -m core.nautilus.chambers promote >> "$LOG_FILE" 2>&1

# 4. Crystallize to vaults (weekly only)
if [ $(date +%u) -eq 1 ]; then  # Monday
    echo "" >> "$LOG_FILE"
    echo "Crystallizing to vaults (weekly)..." >> "$LOG_FILE"
    python3 -m core.nautilus.chambers crystallize >> "$LOG_FILE" 2>&1
fi

# 5. Auto-link mirrors
echo "" >> "$LOG_FILE"
echo "Auto-linking mirrors..." >> "$LOG_FILE"
python3 -m core.nautilus.mirrors auto-link >> "$LOG_FILE" 2>&1

# 6. Vacuum database
echo "" >> "$LOG_FILE"
echo "Vacuuming database..." >> "$LOG_FILE"
sqlite3 ~/.openclaw/state/nautilus/gravity.db "VACUUM;" >> "$LOG_FILE" 2>&1

echo "" >> "$LOG_FILE"
echo "Completed: $(date)" >> "$LOG_FILE"
echo "======================================" >> "$LOG_FILE"

# Keep last 30 days of logs
find "$LOG_DIR" -name "nautilus-nightly-*.log" -mtime +30 -delete
```

**Crontab entry:**
```cron
0 3 * * * /path/to/workspace/scripts/nautilus-nightly.sh
```

---

## Advanced Queries

### Example 4: Finding Related Concepts

```python
from core.nautilus import search
from typing import List, Dict

def find_related(topic: str, n: int = 5) -> List[str]:
    """
    Find all granularity levels related to a topic.
    Returns paths to raw, summary, and lesson versions.
    """
    # Search across all chambers
    results = search(topic, n=n, chambers_filter="atrium,corridor,vault")
    
    # Group by event if mirrors exist
    related_paths = []
    
    for result in results["results"]:
        path = result["path"]
        related_paths.append(path)
        
        # Check for mirrors
        if path in results.get("mirrors", {}):
            mirror_info = results["mirrors"][path]
            for mirror in mirror_info["mirrors"]:
                if mirror["path"] not in related_paths:
                    related_paths.append(mirror["path"])
    
    return related_paths

# Example
paths = find_related("voice listener architecture")
print("Related documents:")
for path in paths:
    print(f"  - {path}")
```

---

### Example 5: Temporal Search (Recent vs Historical)

```python
from core.nautilus import search
from datetime import datetime, timedelta

def temporal_search(query: str):
    """
    Compare recent vs historical results for the same query.
    """
    print(f"🔍 Searching: '{query}'")
    
    # Recent (last 48h)
    recent = search(query, n=5, chambers_filter="atrium")
    print(f"\n📅 Recent (Atrium):")
    for r in recent["results"]:
        print(f"   • {r['path']} — score: {r['score']:.3f}")
    
    # Summary (week view)
    weekly = search(query, n=5, chambers_filter="corridor")
    print(f"\n📊 Weekly Summary (Corridor):")
    for r in weekly["results"]:
        print(f"   • {r['path']} — score: {r['score']:.3f}")
    
    # Wisdom (lessons)
    wisdom = search(query, n=5, chambers_filter="vault")
    print(f"\n💎 Distilled Wisdom (Vault):")
    for r in wisdom["results"]:
        print(f"   • {r['path']} — score: {r['score']:.3f}")

# Example
temporal_search("security firewall")
```

---

### Example 6: Explicit Recall (Trapdoor Mode)

```python
from core.nautilus import search

def exact_recall(phrase: str):
    """
    Find exact phrase matches, bypassing all filtering.
    Like grep but with gravity scoring.
    """
    results = search(phrase, n=20, trapdoor=True, verbose=True)
    
    print(f"🚪 Trapdoor search: '{phrase}'")
    print(f"   Mode: {results['mode']}")
    print(f"   Results found: {len(results['results'])}")
    
    for r in results["results"][:10]:
        # Check if phrase actually appears in snippet
        if phrase.lower() in r["snippet"].lower():
            print(f"\n✓ {r['path']}")
            print(f"  Context: ...{r['snippet']}...")
        else:
            print(f"\n~ {r['path']} (semantic match)")

# Example: Find specific error message
exact_recall("PermissionError: [Errno 13]")

# Example: Find unique identifier
exact_recall("banana jamba")
```

---

## Custom Configurations

### Example 7: Multi-Agent Setup

**Scenario:** Multiple agents sharing the same workspace but with separate memory databases.

**Config:** `~/.openclaw/config/emergence.json`

```json
{
  "nautilus": {
    "enabled": true,
    "state_dir": "~/.openclaw/state/nautilus-{AGENT_ID}",
    "memory_dir": "memory/{AGENT_ID}",
    "auto_classify": true,
    "decay_interval_hours": 168
  }
}
```

**Agent initialization:**

```python
import os
from core.nautilus import search, get_status

# Set agent ID
agent_id = os.environ.get("AGENT_ID", "main")
os.environ["NAUTILUS_AGENT_ID"] = agent_id

# Override state directory
state_dir = f"~/.openclaw/state/nautilus-{agent_id}"
os.environ["OPENCLAW_STATE_DIR"] = state_dir

# Now each agent has separate gravity database
status = get_status()
print(f"Agent {agent_id} initialized")
print(f"State dir: {status['nautilus']['config']['state_dir']}")
```

---

### Example 8: Custom Summarization

**Scenario:** Using a different LLM or custom prompt for corridor/vault summarization.

**Edit:** `projects/emergence/core/nautilus/chambers.py`

```python
# Use Claude instead of Ollama
def llm_summarize_claude(text, mode="corridor"):
    """Custom summarization using Claude API."""
    import anthropic
    
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    if mode == "corridor":
        system = "Summarize this daily log into a concise narrative (2-4 paragraphs). Preserve key decisions, people, and lessons."
    else:  # vault
        system = "Distill this into core lessons and patterns (bullet points). Only keep permanent knowledge."
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": text[:8000]}]
    )
    
    return message.content[0].text

# Replace in promote/crystallize functions
def cmd_promote(args):
    # ...
    summary = llm_summarize_claude(content, mode="corridor")
    # ...
```

---

### Example 9: Custom Context Patterns

**Scenario:** Add domain-specific context tags for your project.

**Edit:** `projects/emergence/core/nautilus/doors.py`

```python
# Add your custom patterns
CONTEXT_PATTERNS = {
    # ... existing patterns ...
    
    # Custom patterns for your domain
    "project:medical-ai": [
        r"patient", r"diagnosis", r"medical\.record",
        r"hipaa", r"healthcare", r"clinical"
    ],
    "project:finance": [
        r"transaction", r"payment", r"invoice",
        r"accounting", r"ledger", r"balance"
    ],
    "topic:research": [
        r"paper", r"study", r"research", r"hypothesis",
        r"experiment", r"data\.analysis"
    ],
    "domain:legal": [
        r"contract", r"agreement", r"clause",
        r"liability", r"compliance", r"regulation"
    ],
}

# Add custom classification logic
def classify_text_custom(text):
    """Extended classifier with custom rules."""
    tags = classify_text(text)  # Original function
    
    # Add custom business logic
    if "urgent" in text.lower() or "critical" in text.lower():
        tags.insert(0, "priority:urgent")
    
    if "meeting" in text.lower() and "tomorrow" in text.lower():
        tags.insert(0, "type:upcoming-event")
    
    return tags
```

---

## Integration Examples

### Example 10: With OpenClaw Memory Search

```python
from core.nautilus import search as nautilus_search
import subprocess
import json

def hybrid_search(query: str, n: int = 10):
    """
    Use both OpenClaw and Nautilus, merge results.
    """
    # OpenClaw search (fast, basic)
    oc_result = subprocess.run(
        ["openclaw", "memory", "search", query, "--max-results", str(n), "--json"],
        capture_output=True, text=True
    )
    oc_results = json.loads(oc_result.stdout)
    
    # Nautilus search (gravity + context)
    nautilus_results = nautilus_search(query, n=n)
    
    # Merge and deduplicate
    seen_paths = set()
    merged = []
    
    # Prioritize Nautilus results (better ranking)
    for r in nautilus_results["results"]:
        if r["path"] not in seen_paths:
            merged.append(r)
            seen_paths.add(r["path"])
    
    # Add any OpenClaw results not in Nautilus
    for r in oc_results:
        if r["path"] not in seen_paths:
            merged.append(r)
            seen_paths.add(r["path"])
    
    return merged[:n]

# Example
results = hybrid_search("voice listener bug", n=10)
```

---

### Example 11: With Emergence Drives

```python
from core.nautilus import search, run_maintain
from core.drives import get_drive_state, fire_drive

def drive_triggered_recall(drive_name: str):
    """
    When a drive fires, recall relevant memories.
    """
    if drive_name == "LEARNING":
        # Recall distilled lessons from vault
        results = search("lessons learned patterns", 
                        n=10, 
                        chambers_filter="vault")
        
        print(f"💡 LEARNING drive fired — recalling wisdom:")
        for r in results["results"][:5]:
            print(f"   • {r['path']}")
    
    elif drive_name == "MAINTENANCE":
        # Run Nautilus maintenance
        print(f"🔧 MAINTENANCE drive fired — running Nautilus upkeep")
        run_maintain(register_recent=True, verbose=True)
    
    elif drive_name == "SOCIAL":
        # Recall interactions with specific person
        results = search("Dan conversation meeting", n=5)
        print(f"💬 SOCIAL drive — recent interactions:")
        for r in results["results"]:
            print(f"   • {r['path']}")

# Integrate with drive system
drives = get_drive_state()
for drive in drives:
    if drive["pressure"] > drive["threshold"]:
        drive_triggered_recall(drive["name"])
        fire_drive(drive["name"])
```

---

### Example 12: Session Memory Injection

```python
from core.nautilus import search
from typing import List, Dict

class SessionMemoryEnhancer:
    """
    Inject relevant memories into agent session context.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.context_memory = []
    
    def enhance_prompt(self, user_message: str) -> str:
        """
        Add relevant memories to system prompt.
        """
        # Search for relevant context
        results = search(user_message, n=3)
        
        # Build memory context
        memory_context = "\n\n## Relevant Memory Context\n\n"
        
        for r in results["results"]:
            memory_context += f"### From {r['path']}\n"
            memory_context += f"{r['snippet']}\n\n"
        
        # Prepend to user message
        enhanced = memory_context + "\n## Current Query\n\n" + user_message
        
        return enhanced
    
    def record_response(self, query: str, response: str):
        """
        Record this exchange for future recall.
        """
        from core.nautilus.gravity import cmd_record_write
        import tempfile
        from datetime import datetime
        
        # Write to daily log
        log_path = f"memory/{datetime.now().strftime('%Y-%m-%d')}.md"
        
        with open(log_path, "a") as f:
            f.write(f"\n## {datetime.now().strftime('%H:%M')} — {query[:50]}...\n\n")
            f.write(f"{response}\n\n")
        
        # Register with Nautilus
        cmd_record_write([log_path])

# Usage
enhancer = SessionMemoryEnhancer("session_123")

# On user message
user_msg = "How did we fix the voice listener bug?"
enhanced_msg = enhancer.enhance_prompt(user_msg)

# Send enhanced message to LLM
# response = llm.generate(enhanced_msg)

# Record the exchange
# enhancer.record_response(user_msg, response)
```

---

## Maintenance Workflows

### Example 13: Weekly Health Check

```python
from core.nautilus import get_status, run_maintain
from core.nautilus.gravity import get_db, cmd_decay, cmd_top
import json

def weekly_health_check():
    """
    Run comprehensive health check and cleanup.
    """
    print("🏥 Nautilus Weekly Health Check\n")
    
    # 1. Get status
    status = get_status()
    nautilus = status["nautilus"]
    
    gravity = nautilus["phase_1_gravity"]
    chambers = nautilus["phase_2_chambers"]
    
    print(f"📊 System Status:")
    print(f"   Total chunks: {gravity['total_chunks']}")
    print(f"   Tagged: {gravity['coverage']}")
    print(f"   Superseded: {gravity['superseded']}")
    print(f"   Chambers: {chambers['chambers']}")
    
    # 2. Check tag coverage
    coverage_pct = int(gravity['tagged']) / max(int(gravity['total_chunks']), 1) * 100
    
    if coverage_pct < 50:
        print(f"\n⚠️  Tag coverage low ({coverage_pct:.1f}%) — running auto-tag")
        from core.nautilus.doors import cmd_auto_tag
        cmd_auto_tag([])
    
    # 3. Run decay
    print(f"\n⚖️  Applying gravity decay...")
    decay_result = cmd_decay([])
    print(f"   Decayed {decay_result['decayed']} chunks")
    
    # 4. Check for old superseded chunks
    db = get_db()
    old_superseded = db.execute("""
        SELECT COUNT(*) FROM gravity 
        WHERE superseded_by IS NOT NULL 
        AND date(created_at) < date('now', '-30 days')
    """).fetchone()[0]
    
    if old_superseded > 0:
        print(f"\n🗑️  Found {old_superseded} old superseded chunks — cleaning up")
        db.execute("""
            DELETE FROM gravity 
            WHERE superseded_by IS NOT NULL 
            AND date(created_at) < date('now', '-30 days')
        """)
        db.commit()
    
    db.close()
    
    # 5. Show top memories
    print(f"\n⭐ Top 5 Highest-Gravity Memories:")
    cmd_top(["--n", "5"])
    
    # 6. Run full maintenance
    print(f"\n🔧 Running full maintenance...")
    result = run_maintain(register_recent=True, verbose=True)
    
    print(f"\n✅ Health check complete")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    weekly_health_check()
```

---

### Example 14: Manual Promotion Control

```python
from core.nautilus.chambers import file_age_days, llm_summarize
from core.nautilus.config import get_memory_dir, get_corridors_dir
from pathlib import Path
from datetime import datetime

def selective_promotion(min_age_days: int = 2, 
                       max_age_days: int = 7,
                       quality_threshold: int = 500):
    """
    Manually control which files get promoted to corridor.
    Only promote files that meet quality criteria.
    """
    memory_dir = get_memory_dir()
    corridors_dir = get_corridors_dir()
    corridors_dir.mkdir(parents=True, exist_ok=True)
    
    candidates = []
    
    for md_file in sorted(memory_dir.glob("2*.md")):
        age = file_age_days(str(md_file.relative_to(memory_dir.parent)))
        
        if min_age_days <= age <= max_age_days:
            # Check quality (length, not just age)
            content = md_file.read_text()
            
            # Quality criteria
            if len(content) < quality_threshold:
                print(f"⏩ Skip {md_file.name} — too short ({len(content)} chars)")
                continue
            
            if content.count("HEARTBEAT_OK") > 10:
                print(f"⏩ Skip {md_file.name} — mostly heartbeat logs")
                continue
            
            candidates.append(md_file)
    
    print(f"\n📂 Found {len(candidates)} candidates for promotion")
    
    for md_file in candidates:
        print(f"\n🔄 Promoting {md_file.name}...")
        
        content = md_file.read_text()
        summary = llm_summarize(content, mode="corridor")
        
        if summary and not summary.startswith("[Summarization failed"):
            summary_name = f"corridor-{md_file.stem}.md"
            summary_path = corridors_dir / summary_name
            
            header = f"# Corridor Summary: {md_file.stem}\n\n"
            header += f"*Promoted on {datetime.now().strftime('%Y-%m-%d')}*\n\n---\n\n"
            
            summary_path.write_text(header + summary)
            print(f"   ✓ Created {summary_name}")
        else:
            print(f"   ✗ Summarization failed")

if __name__ == "__main__":
    selective_promotion(min_age_days=2, max_age_days=7, quality_threshold=1000)
```

---

## Performance Optimization

### Example 15: Batch Gravity Updates

```python
from core.nautilus.gravity import get_db, now_iso
from typing import List, Tuple

def batch_record_access(accesses: List[Tuple[str, int, int, str, float]]):
    """
    Record multiple accesses in a single transaction.
    Much faster than individual calls.
    
    Args:
        accesses: List of (path, line_start, line_end, query, score)
    """
    db = get_db()
    now = now_iso()
    
    try:
        for path, start, end, query, score in accesses:
            # Upsert gravity record
            db.execute("""
                INSERT INTO gravity (path, line_start, line_end, access_count, last_accessed_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                    access_count = access_count + 1,
                    last_accessed_at = ?
            """, (path, start, end, now, now))
            
            # Log access
            db.execute("""
                INSERT INTO access_log (path, line_start, line_end, query, score)
                VALUES (?, ?, ?, ?, ?)
            """, (path, start, end, query, score))
        
        db.commit()
        print(f"✓ Recorded {len(accesses)} accesses in batch")
    
    finally:
        db.close()

# Example: Record multiple searches
accesses = [
    ("memory/2026-02-14.md", 0, 0, "project status", 0.85),
    ("memory/2026-02-13.md", 0, 0, "project status", 0.72),
    ("memory/2026-02-12.md", 45, 67, "voice bug", 0.91),
]

batch_record_access(accesses)
```

---

### Example 16: Optimized Search with Caching

```python
from core.nautilus import search
from functools import lru_cache
import hashlib
import json

@lru_cache(maxsize=100)
def cached_search(query_hash: str, n: int, chambers: str):
    """
    Cache search results for 5 minutes.
    """
    # Decode query from hash (stored separately)
    query = _QUERY_CACHE.get(query_hash)
    if not query:
        return None
    
    return search(query, n=n, chambers_filter=chambers if chambers else None)

# Query cache (maps hash to query)
_QUERY_CACHE = {}

def smart_search(query: str, n: int = 5, chambers_filter: str = None):
    """
    Search with caching for repeated queries.
    """
    # Create hash
    query_hash = hashlib.md5(query.encode()).hexdigest()
    _QUERY_CACHE[query_hash] = query
    
    # Cache key includes all parameters
    chambers = chambers_filter or ""
    
    return cached_search(query_hash, n, chambers)

# Example
result1 = smart_search("project status", n=10)  # Cache miss
result2 = smart_search("project status", n=10)  # Cache hit (instant)
```

---

## Error Handling

### Example 17: Graceful Fallback

```python
from core.nautilus import search
import subprocess
import json

def resilient_search(query: str, n: int = 5):
    """
    Search with graceful fallback to OpenClaw if Nautilus fails.
    """
    try:
        # Try Nautilus first (better ranking)
        results = search(query, n=n, verbose=False)
        print(f"✓ Nautilus search successful")
        return results["results"]
    
    except Exception as e:
        print(f"⚠️ Nautilus search failed: {e}")
        print(f"   Falling back to OpenClaw memory search...")
        
        try:
            # Fallback to basic OpenClaw search
            result = subprocess.run(
                ["openclaw", "memory", "search", query, "--max-results", str(n), "--json"],
                capture_output=True, text=True, timeout=30
            )
            oc_results = json.loads(result.stdout)
            print(f"✓ OpenClaw search successful")
            return oc_results
        
        except Exception as e2:
            print(f"✗ Both searches failed: {e2}")
            return []

# Example
results = resilient_search("voice listener")
```

---

## Testing

### Example 18: Integration Test

```python
import unittest
from core.nautilus import search, get_status, run_maintain
import tempfile
import os

class NautilusIntegrationTest(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Use temporary state directory
        cls.temp_dir = tempfile.mkdtemp()
        os.environ["OPENCLAW_STATE_DIR"] = cls.temp_dir
    
    def test_status(self):
        """Test status retrieval."""
        status = get_status()
        self.assertIn("nautilus", status)
        self.assertIn("phase_1_gravity", status["nautilus"])
    
    def test_search(self):
        """Test basic search."""
        results = search("test query", n=5)
        self.assertIn("query", results)
        self.assertIn("results", results)
        self.assertIsInstance(results["results"], list)
    
    def test_maintain(self):
        """Test maintenance."""
        result = run_maintain(verbose=False)
        self.assertIn("chambers", result)
        self.assertIn("timestamp", result)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(cls.temp_dir)

if __name__ == "__main__":
    unittest.main()
```

---

## Related Documentation

- [User Guide](USER_GUIDE.md) — Getting started and concepts
- [API Reference](API_REFERENCE.md) — Complete API documentation
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues and solutions
