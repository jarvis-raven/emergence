"""
Nautilus Search — Full pipeline implementation.

Combines all four phases into a unified search:
  1. Classify context (Doors)
  2. Search with chamber awareness (Chambers)
  3. Apply gravity re-ranking (Gravity)
  4. Resolve mirrors for top results (Mirrors)
"""

import json
import subprocess
import logging
import sqlite3
from typing import List, Dict, Any, Optional, Set

from . import config
from .doors import classify_text
from .gravity import get_db, compute_effective_mass, gravity_score_modifier, now_iso
from .chambers import classify_chamber
from .mirrors import get_db as get_mirrors_db

# Setup logging
logger = logging.getLogger(__name__)


def run_full_search(
    query: str,
    n: int = 5,
    trapdoor: bool = False,
    verbose: bool = False,
    chambers_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the full Nautilus search pipeline.
    
    Args:
        query: Search query string
        n: Number of results to return
        trapdoor: Bypass context filtering if True
        verbose: Print pipeline steps to stderr
        chambers_filter: Comma-separated list of chambers to include
    
    Returns:
        Dict with query, context, results, and mirror info
    """
    import sys
    
    logger.info(f"Running full search for query: '{query}' (n={n}, trapdoor={trapdoor})")
    
    # Step 1: Classify context (Doors)
    try:
        context_tags = classify_text(query)
        logger.debug(f"Context classification: {context_tags}")
    except Exception as e:
        logger.warning(f"Context classification failed: {e}")
        context_tags = []
    
    if verbose:
        print(f"🚪 Context: {context_tags or 'none detected'}", file=sys.stderr)
    
    # Step 2: Run base memory search via openclaw
    try:
        result = subprocess.run(
            ["openclaw", "memory", "search", query, "--max-results", str(n * 3), "--json"],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            logger.warning(f"Memory search returned non-zero: {result.returncode}")
        
        raw_results = json.loads(result.stdout) if result.stdout else []
        
    except subprocess.TimeoutExpired:
        logger.error("Memory search timed out")
        return {"error": "Memory search timed out", "query": query}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse memory search results: {e}")
        return {"error": f"Failed to parse search results: {e}", "query": query}
    except FileNotFoundError:
        logger.error("openclaw command not found")
        return {"error": "openclaw command not found", "query": query}
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return {"error": f"Memory search failed: {e}", "query": query}
    
    if not isinstance(raw_results, list):
        raw_results = raw_results.get("results", []) if isinstance(raw_results, dict) else []
    
    logger.debug(f"Base search returned {len(raw_results)} results")
    
    if verbose:
        print(f"🔍 Base search: {len(raw_results)} results", file=sys.stderr)
    
    # Step 3: Apply gravity re-ranking
    try:
        reranked = _apply_gravity(raw_results, verbose)
    except Exception as e:
        logger.error(f"Gravity re-ranking failed: {e}")
        reranked = raw_results  # Fall back to original results
    
    if verbose:
        print(f"⚖️ Gravity applied: {len(reranked)} results re-ranked", file=sys.stderr)
    
    # Step 4: Chamber filtering (if specified)
    if chambers_filter:
        try:
            allowed_chambers = set(chambers_filter.split(","))
            reranked = _filter_by_chambers(reranked, allowed_chambers)
            
            if verbose:
                print(f"📂 Chamber filter ({chambers_filter}): {len(reranked)} results", file=sys.stderr)
        except Exception as e:
            logger.warning(f"Chamber filtering failed: {e}")
    
    # Step 5: Context filtering (Doors) unless trapdoor
    if not trapdoor and context_tags:
        try:
            reranked = _apply_context_filter(reranked, context_tags, verbose)
            
            if verbose:
                print(f"🚪 Context filtered: {len(reranked)} results", file=sys.stderr)
        except Exception as e:
            logger.warning(f"Context filtering failed: {e}")
    else:
        # Still add chamber info for display
        try:
            reranked = _add_chamber_info(reranked)
        except Exception as e:
            logger.warning(f"Adding chamber info failed: {e}")
    
    # Step 6: Resolve mirrors for top results
    mirror_info = {}
    try:
        mirror_info = _resolve_mirrors(reranked[:n])
    except Exception as e:
        logger.warning(f"Mirror resolution failed: {e}")
    
    # Truncate to n
    final_results = reranked[:n]
    
    logger.info(f"Search complete: {len(final_results)} results returned")
    
    output = {
        "query": query,
        "context": context_tags,
        "mode": "trapdoor" if trapdoor else ("context-filtered" if context_tags else "full"),
        "results": final_results,
    }
    
    if mirror_info:
        output["mirrors"] = mirror_info
    
    return output


def _apply_gravity(results: List[Dict], verbose: bool = False) -> List[Dict]:
    """
    Apply gravity re-ranking to search results.
    
    Args:
        results: List of search results
        verbose: Print debug info
        
    Returns:
        Re-ranked list of results with gravity metadata.
    """
    db_path = config.get_gravity_db_path()
    
    # Ensure database exists
    if not db_path.exists():
        logger.debug("No gravity database found, skipping gravity re-ranking")
        return results
    
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.error(f"Could not connect to gravity database: {e}")
        return results
    
    reranked = []
    now = now_iso()
    
    for r in results:
        path = r.get("path", "")
        start = r.get("startLine", 0)
        end = r.get("endLine", 0)
        base_score = r.get("score", 0)
        
        # Look up gravity
        try:
            row = db.execute(
                "SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?",
                (path, start, end)
            ).fetchone()
            
            if not row:
                # Try file-level match
                row = db.execute("SELECT * FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
            
            if row:
                mass = compute_effective_mass(row)
                modifier = gravity_score_modifier(mass)
                is_superseded = row["superseded_by"] is not None
                
                # Penalize superseded chunks
                if is_superseded:
                    modifier *= 0.5
                
                adjusted_score = base_score * modifier
            else:
                mass = 0
                modifier = 1.0
                adjusted_score = base_score
                is_superseded = False
            
            entry = dict(r)
            entry["original_score"] = base_score
            entry["score"] = round(adjusted_score, 4)
            entry["gravity"] = {
                "effective_mass": round(mass, 3),
                "modifier": round(modifier, 3),
                "superseded": is_superseded
            }
            reranked.append(entry)
            
            # Record access
            try:
                db.execute("""
                    INSERT INTO gravity (path, line_start, line_end, access_count, last_accessed_at)
                    VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                        access_count = access_count + 1,
                        last_accessed_at = ?
                """, (path, start, end, now, now))
            except sqlite3.Error as e:
                logger.debug(f"Failed to record access for {path}: {e}")
                
        except sqlite3.Error as e:
            logger.warning(f"Database error processing {path}: {e}")
            # Add result without gravity data
            entry = dict(r)
            entry["score"] = base_score
            entry["gravity"] = {"effective_mass": 0, "modifier": 1.0, "superseded": False}
            reranked.append(entry)
    
    try:
        db.commit()
        db.close()
    except sqlite3.Error as e:
        logger.warning(f"Failed to commit gravity updates: {e}")
    
    # Sort by adjusted score
    reranked.sort(key=lambda x: x.get("score", 0), reverse=True)
    logger.debug(f"Applied gravity to {len(reranked)} results")
    return reranked


def _filter_by_chambers(results: List[Dict], allowed_chambers: Set[str]) -> List[Dict]:
    """
    Filter results by chamber.
    
    Args:
        results: List of search results
        allowed_chambers: Set of allowed chamber names
        
    Returns:
        Filtered list of results.
    """
    db_path = config.get_gravity_db_path()
    
    if not db_path.exists():
        logger.debug("No gravity database for chamber filtering")
        return results
    
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.error(f"Could not connect to database for chamber filtering: {e}")
        return results
    
    filtered = []
    for r in results:
        path = r.get("path", "")
        
        try:
            # Look up chamber
            row = db.execute("SELECT chamber FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
            
            if row:
                chamber = row["chamber"]
            else:
                # Auto-classify
                chamber = classify_chamber(path)
            
            if chamber in allowed_chambers:
                r["chamber"] = chamber
                filtered.append(r)
                
        except sqlite3.Error as e:
            logger.warning(f"Database error checking chamber for {path}: {e}")
            continue
    
    try:
        db.close()
    except sqlite3.Error as e:
        logger.warning(f"Failed to close database: {e}")
    
    logger.debug(f"Filtered to {len(filtered)} results in chambers {allowed_chambers}")
    return filtered


def _apply_context_filter(
    results: List[Dict], 
    context_tags: List[str],
    verbose: bool = False
) -> List[Dict]:
    """
    Apply context filtering to results.
    
    Args:
        results: List of search results
        context_tags: List of context tags from query classification
        verbose: Print debug info
        
    Returns:
        Filtered list of results with context match scores.
    """
    db_path = config.get_gravity_db_path()
    
    if not db_path.exists():
        logger.debug("No gravity database for context filtering")
        return results
    
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.error(f"Could not connect to database for context filtering: {e}")
        return results
    
    filtered = []
    for r in results:
        path = r.get("path", "")
        
        try:
            row = db.execute(
                "SELECT tags, chamber, context_tags FROM gravity WHERE path = ? LIMIT 1",
                (path,)
            ).fetchone()
            
            if row and row["context_tags"]:
                try:
                    file_tags = json.loads(row["context_tags"])
                    overlap = len(set(context_tags) & set(file_tags))
                    r["context_match"] = overlap / max(len(context_tags), 1) if overlap > 0 else 0.3
                except json.JSONDecodeError as e:
                    logger.debug(f"Invalid context_tags JSON for {path}: {e}")
                    r["context_match"] = 0.5
            else:
                r["context_match"] = 0.5  # Neutral for untagged
            
            r["chamber"] = row["chamber"] if row and row["chamber"] else "unknown"
            
            # Apply context bonus to score
            if r.get("context_match", 0) > 0:
                r["score"] = r.get("score", 0) * (0.8 + 0.2 * r["context_match"])
                filtered.append(r)
                
        except sqlite3.Error as e:
            logger.warning(f"Database error checking context for {path}: {e}")
            continue
    
    try:
        db.close()
    except sqlite3.Error as e:
        logger.warning(f"Failed to close database: {e}")
    
    # Re-sort by adjusted score
    filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
    logger.debug(f"Context filtered to {len(filtered)} results")
    return filtered


def _add_chamber_info(results: List[Dict]) -> List[Dict]:
    """
    Add chamber information to results.
    
    Args:
        results: List of search results
        
    Returns:
        Results with chamber info added.
    """
    db_path = config.get_gravity_db_path()
    
    if not db_path.exists():
        logger.debug("No gravity database for chamber info")
        return results
    
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.error(f"Could not connect to database for chamber info: {e}")
        return results
    
    for r in results:
        path = r.get("path", "")
        try:
            row = db.execute("SELECT chamber FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
            r["chamber"] = row["chamber"] if row and row["chamber"] else "unknown"
        except sqlite3.Error as e:
            logger.debug(f"Database error getting chamber for {path}: {e}")
            r["chamber"] = "unknown"
    
    try:
        db.close()
    except sqlite3.Error as e:
        logger.warning(f"Failed to close database: {e}")
    
    return results


def _resolve_mirrors(results: List[Dict]) -> Dict[str, Any]:
    """
    Resolve mirrors for top results.
    
    Args:
        results: List of search results
        
    Returns:
        Dictionary mapping paths to their mirror information.
    """
    db_path = config.get_gravity_db_path()
    mirror_info = {}
    
    if not db_path.exists():
        logger.debug("No gravity database for mirror resolution")
        return mirror_info
    
    try:
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        logger.error(f"Could not connect to database for mirror resolution: {e}")
        return mirror_info
    
    # Check if mirrors table exists
    try:
        db.execute("SELECT 1 FROM mirrors LIMIT 1")
    except sqlite3.OperationalError:
        logger.debug("Mirrors table does not exist")
        try:
            db.close()
        except sqlite3.Error:
            pass
        return mirror_info
    
    for r in results:
        path = r.get("path", "")
        
        try:
            # Try as path
            rows = db.execute("SELECT * FROM mirrors WHERE path = ?", (path,)).fetchall()
            
            if rows:
                # Get the event key and find all siblings
                event_key = rows[0]["event_key"]
                all_mirrors = db.execute(
                    "SELECT * FROM mirrors WHERE event_key = ? ORDER BY granularity",
                    (event_key,)
                ).fetchall()
                
                mirror_info[path] = {
                    "event_key": event_key,
                    "mirrors": [dict(m) for m in all_mirrors]
                }
                logger.debug(f"Resolved mirrors for {path}: {event_key}")
                
        except sqlite3.Error as e:
            logger.warning(f"Database error resolving mirrors for {path}: {e}")
            continue
    
    try:
        db.close()
    except sqlite3.Error as e:
        logger.warning(f"Failed to close database: {e}")
    
    logger.debug(f"Resolved mirrors for {len(mirror_info)} results")
    return mirror_info
