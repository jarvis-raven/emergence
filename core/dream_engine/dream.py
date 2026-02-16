#!/usr/bin/env python3
"""Dream Engine — Creative memory recombination system.

Extracts concepts from recent memory files, randomly pairs them,
and generates "dream fragments" with insight scores. These dreams
power the "asleep" mode in The Room.

Usage:
    python3 -m core.dream_engine.dream run [--date YYYY-MM-DD] [--verbose]
    python3 -m core.dream_engine.dream status
    python3 -m core.dream_engine.dream test [--verbose]

Designed to run via cron at 4:00 AM (configurable).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import load_config, get_memory_dir, get_dream_dir, get_dream_engine_config
from .concepts import extract_concepts
from .pairs import generate_pairs
from .fragments import generate_fragments
from .scoring import score_pairs


VERSION = "1.0.0"


def _print_header(
    reference_date: datetime, memory_dir: Path, lookback_days: int, max_concepts: int
):
    """Print dream generation header."""
    print(f"Dream Engine v{VERSION}")
    print(f"====================={ '=' * len(VERSION) }")
    print(f"Date: {reference_date.strftime('%Y-%m-%d')}")
    print(f"Memory directory: {memory_dir}")
    print(f"Lookback: {lookback_days} days, Max concepts: {max_concepts}")
    print()


def _create_error_result(
    reference_date: datetime, source_files: int, source_concepts: int, error: str
) -> dict:
    """Create an error result dictionary."""
    return {
        "date": reference_date.strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_files": source_files,
        "source_concepts": source_concepts,
        "dreams": [],
        "error": error,
    }


def _generate_concept_pairs(
    concepts: list, pairs_to_generate: int, reference_date: datetime, verbose: bool
) -> list:
    """Generate concept pairs with fallback to same-source if needed."""
    if verbose:
        print("Step 2: Generating concept pairs...")

    pairs = generate_pairs(
        concepts=concepts,
        pairs_to_generate=pairs_to_generate,
        require_cross_source=True,
        reference_date=reference_date,
        verbose=verbose,
    )

    # Fallback: allow same-source pairs if cross-source produced nothing
    if not pairs:
        if verbose:
            print("  No cross-source pairs possible, allowing same-source pairs...")
        pairs = generate_pairs(
            concepts=concepts,
            pairs_to_generate=pairs_to_generate,
            require_cross_source=False,
            reference_date=reference_date,
            verbose=verbose,
        )

    if verbose and pairs:
        print(f"  Generated {len(pairs)} pairs")
        print()

    return pairs


def _generate_and_score_fragments(
    pairs: list, concepts: list, config: dict, reference_date: datetime, verbose: bool
) -> tuple[list, list]:
    """Generate fragments and score pairs. Returns (fragments, scored_pairs)."""
    # Step 3: Generate dream fragments
    if verbose:
        print("Step 3: Generating dream fragments...")

    fragments = generate_fragments(
        concept_pairs=pairs, reference_date=reference_date, config=config, verbose=verbose
    )

    if verbose:
        print(f"  Generated {len(fragments)} fragments")
        print()

    # Step 4: Score pairs for insight
    if verbose:
        print("Step 4: Scoring for insight...")

    scored_pairs = score_pairs(
        pairs=pairs, concepts=concepts, reference_date=reference_date, verbose=verbose
    )

    if verbose:
        print()

    return fragments, scored_pairs


def _build_result(
    dreams: list, source_files: list, concepts: list, reference_date: datetime, verbose: bool
) -> dict:
    """Build the final result dictionary with optional verbose output."""
    result = {
        "date": reference_date.strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_files": len(source_files),
        "source_concepts": len(concepts),
        "dreams": dreams,
    }

    if verbose:
        print(f"Generated {len(dreams)} dreams")
        if dreams:
            print(f"  Highest insight score: {dreams[0]['insight_score']}")
            print(f"  Top dream: \"{dreams[0]['fragment'][:50]}...\"")

    return result


def _build_dreams(scored_pairs: list, fragments: list, verbose: bool) -> list:
    """Build dream dictionaries from scored pairs and fragments."""
    dreams = []
    for (pair, score), fragment in zip(scored_pairs, fragments):
        # Get unique sources from both concepts
        all_sources = list(set(pair.sources_a) | set(pair.sources_b))

        dream = {
            "concepts": [pair.concept_a, pair.concept_b],
            "fragment": fragment["fragment"],
            "insight_score": score["total"],
            "sources": all_sources,
            "template": fragment["template"],
            "score_breakdown": score["breakdown"] if verbose else None,
        }

        # Remove None values
        dream = {k: v for k, v in dream.items() if v is not None}
        dreams.append(dream)

    # Sort dreams by insight score
    dreams.sort(key=lambda d: d["insight_score"], reverse=True)
    return dreams


def generate_dreams(
    config: dict, reference_date: Optional[datetime] = None, verbose: bool = False
) -> dict:
    """Generate dreams for a specific date.

    Args:
        config: Configuration dictionary
        reference_date: Date to generate dreams for (default: today)
        verbose: Print progress messages

    Returns:
        Dictionary with dream generation results
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)

    de_config = get_dream_engine_config(config)
    memory_dir = get_memory_dir(config)

    lookback_days = de_config.get("lookback_days", 7)
    max_concepts = de_config.get("concepts_per_run", 50)
    pairs_to_generate = de_config.get("pairs_to_generate", 8)

    if verbose:
        _print_header(reference_date, memory_dir, lookback_days, max_concepts)

    # Step 1: Extract concepts
    if verbose:
        print("Step 1: Extracting concepts from memory files...")

    concepts, source_files = extract_concepts(
        memory_dir=memory_dir,
        lookback_days=lookback_days,
        max_concepts=max_concepts,
        reference_date=reference_date,
        verbose=verbose,
    )

    if not concepts:
        if verbose:
            print("No concepts found. Nothing to dream about.")
        return _create_error_result(reference_date, 0, 0, "No concepts extracted from memory files")

    if verbose:
        print(f"  Extracted {len(concepts)} concepts from {len(source_files)} files")
        print()

    # Step 2: Generate pairs
    pairs = _generate_concept_pairs(concepts, pairs_to_generate, reference_date, verbose)

    if not pairs:
        if verbose:
            print("Could not generate any pairs.")
        return _create_error_result(
            reference_date, len(source_files), len(concepts), "Could not generate concept pairs"
        )

    # Step 3-4: Generate fragments and score
    fragments, scored_pairs = _generate_and_score_fragments(
        pairs, concepts, config, reference_date, verbose
    )

    # Step 5: Build final output
    dreams = _build_dreams(scored_pairs, fragments, verbose)
    return _build_result(dreams, source_files, concepts, reference_date, verbose)


def save_dreams(
    dreams_data: dict, config: dict, dry_run: bool = False, verbose: bool = False
) -> bool:
    """Save dreams to JSON file.

    Args:
        dreams_data: Dream generation results
        config: Configuration dictionary
        dry_run: If True, don't actually write
        verbose: Print progress messages

    Returns:
        True if successful
    """
    dream_dir = get_dream_dir(config)
    date_str = dreams_data["date"]
    output_path = dream_dir / f"{date_str}.json"

    if verbose:
        print(f"\nSaving to: {output_path}")

    if dry_run:
        if verbose:
            print("  (DRY RUN - not writing)")
        return True

    try:
        # Ensure directory exists
        dream_dir.mkdir(parents=True, exist_ok=True)

        # Write atomically (temp file then rename)
        temp_path = output_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dreams_data, f, indent=2, ensure_ascii=False)

        temp_path.replace(output_path)

        if verbose:
            print(f"  ✓ Saved {len(dreams_data['dreams'])} dreams")

        return True

    except (IOError, OSError) as e:
        print(f"  ✗ Error saving dreams: {e}", file=sys.stderr)
        return False


def run_dream_generation(
    config: Optional[dict] = None,
    reference_date: Optional[datetime] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[bool, dict]:
    """Run the complete dream generation process.

    Args:
        config: Configuration dictionary (loaded if None)
        reference_date: Date to generate for (default: today)
        dry_run: Preview without writing
        verbose: Print progress

    Returns:
        Tuple of (success, dreams_data)
    """
    if config is None:
        config = load_config()

    # Generate dreams
    dreams_data = generate_dreams(config, reference_date, verbose)

    # Check if generation failed
    if dreams_data.get("error"):
        return False, dreams_data

    # Save to file
    success = save_dreams(dreams_data, config, dry_run, verbose)

    return success, dreams_data


def get_status(config: Optional[dict] = None) -> dict:
    """Get dream engine status.

    Args:
        config: Configuration dictionary

    Returns:
        Status dictionary
    """
    if config is None:
        config = load_config()

    memory_dir = get_memory_dir(config)
    dream_dir = get_dream_dir(config)
    de_config = get_dream_engine_config(config)

    # Check for memory files
    from .concepts import get_recent_memory_files

    recent_files = get_recent_memory_files(
        memory_dir, lookback_days=de_config.get("lookback_days", 7)
    )

    # Check for existing dream files
    existing_dreams = list(dream_dir.glob("*.json")) if dream_dir.exists() else []

    return {
        "memory_dir": str(memory_dir),
        "dream_dir": str(dream_dir),
        "recent_memory_files": len(recent_files),
        "existing_dreams": len(existing_dreams),
        "latest_dreams": [d.name for d in sorted(existing_dreams)[-5:]],
        "config": de_config,
    }


def print_usage():
    """Print usage information."""
    print(
        """Dream Engine — Creative memory recombination system

Usage:
    python3 -m core.dream_engine.dream run [--date YYYY-MM-DD] [--dry-run] [--verbose]
    python3 -m core.dream_engine.dream status
    python3 -m core.dream_engine.dream test [--verbose]

Commands:
    run          Generate dreams for today (or specified date)
    status       Show dream engine status
    test         Run a test generation (dry-run by default)

Options:
    --date       Generate dreams for specific date (YYYY-MM-DD)
    --dry-run    Preview without writing files
    --verbose    Show detailed progress
    --config     Path to emergence.json config file
    --help       Show this help message

Examples:
    python3 -m core.dream_engine.dream run
    python3 -m core.dream_engine.dream run --date 2026-02-07 --verbose
    python3 -m core.dream_engine.dream status
    python3 -m core.dream_engine.dream test --verbose

Cron setup:
    0 4 * * * cd /path/to/workspace && python3 -m core.dream_engine.dream run
"""
    )


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Datetime object or None if invalid
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _handle_status_command(config: dict):
    """Handle the 'status' command."""
    status = get_status(config)
    print("Dream Engine Status")
    print("==================")
    print(f"Memory directory: {status['memory_dir']}")
    print(f"Dream directory: {status['dream_dir']}")
    print(f"Recent memory files (7 days): {status['recent_memory_files']}")
    print(f"Existing dream files: {status['existing_dreams']}")
    if status["latest_dreams"]:
        print(f"Latest dreams: {', '.join(status['latest_dreams'])}")
    print()
    print("Configuration:")
    for key, value in status["config"].items():
        print(f"  {key}: {value}")


def _handle_run_command(
    config: dict, reference_date: Optional[datetime], dry_run: bool, verbose: bool
) -> bool:
    """Handle the 'run' command. Returns success status."""
    success, dreams_data = run_dream_generation(
        config=config, reference_date=reference_date, dry_run=dry_run, verbose=verbose
    )

    if verbose:
        print()
        if success:
            print("✓ Dream generation complete")
        else:
            print("✗ Dream generation failed")

    return success


def _handle_test_command(
    args: list, config: dict, reference_date: Optional[datetime], verbose: bool
) -> bool:
    """Handle the 'test' command. Returns success status."""
    # Test mode: always dry-run unless explicitly told otherwise
    dry_run = "--write" not in args
    if dry_run and verbose:
        print("Test mode (dry-run). Use --write to actually save.")
        print()

    success, dreams_data = run_dream_generation(
        config=config, reference_date=reference_date, dry_run=dry_run, verbose=verbose
    )

    # Print sample output
    if dreams_data.get("dreams"):
        print("\nSample dreams:")
        print("==============")
        for i, dream in enumerate(dreams_data["dreams"][:3], 1):
            print(f"\n{i}. Score: {dream['insight_score']}")
            print(f"   Concepts: {', '.join(dream['concepts'])}")
            print(f"   Fragment: \"{dream['fragment']}\"")
            print(f"   Template: {dream['template']}")

    return success


def main():
    """CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print_usage()
        sys.exit(0)

    command = args[0]

    # Parse options
    dry_run = "--dry-run" in args
    verbose = "--verbose" in args or "-v" in args

    config_path = None
    if "--config" in args:
        idx = args.index("--config")
        if idx + 1 < len(args):
            config_path = Path(args[idx + 1])

    reference_date = None
    if "--date" in args:
        idx = args.index("--date")
        if idx + 1 < len(args):
            reference_date = parse_date(args[idx + 1])
            if reference_date is None:
                print("Error: Invalid date format. Use YYYY-MM-DD.", file=sys.stderr)
                sys.exit(1)

    # Load config
    config = load_config(config_path)

    if command == "status":
        _handle_status_command(config)
        sys.exit(0)

    elif command == "run":
        success = _handle_run_command(config, reference_date, dry_run, verbose)
        sys.exit(0 if success else 1)

    elif command == "test":
        success = _handle_test_command(args, config, reference_date, verbose)
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
