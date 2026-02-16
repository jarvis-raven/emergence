#!/usr/bin/env python3
"""Sync reading.json → library shelf data.

Reads the canonical reading state and generates the library-data.json
that the Room dashboard shelf consumes. Run after each reading session.
"""

import json
import os
from pathlib import Path

STATE_DIR = os.environ.get("EMERGENCE_STATE", str(Path.home() / ".openclaw" / "state"))
READING_PATH = Path(STATE_DIR) / "reading.json"
SHELF_PATH = Path(STATE_DIR) / "shelves" / "library" / "library-data.json"


def sync():
    if not READING_PATH.exists():
        print("No reading.json found")
        return

    reading = json.loads(READING_PATH.read_text())
    library = reading.get("library", {})
    current_key = reading.get("current_book")

    currently_reading = []
    to_read = []

    for key, book in library.items():
        total = book.get("total_words", 0)
        position = book.get("position", 0)
        progress = position / total if total > 0 else 0
        sessions = book.get("sessions_completed", 0)

        entry = {
            "title": book.get("title", key),
            "author": book.get("author", "Unknown"),
            "totalWords": total,
            "interest": book.get("interest", 3),
        }

        if sessions > 0 or key == current_key:
            entry.update(
                {
                    "progress": round(progress, 3),
                    "wordsRead": position,
                    "sessionsCompleted": sessions,
                    "startedAt": (book.get("added_at", "")[:10] if book.get("added_at") else None),
                    "lastReadAt": (
                        book.get("last_read", "")[:10] if book.get("last_read") else None
                    ),
                }
            )
            currently_reading.append(entry)
        else:
            to_read.append(entry)

    # Sort to_read by interest descending
    to_read.sort(key=lambda x: x.get("interest", 0), reverse=True)

    shelf_data = {
        "currentlyReading": currently_reading,
        "toRead": to_read,
    }

    SHELF_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHELF_PATH.write_text(json.dumps(shelf_data, indent=2))

    for book in currently_reading:
        pct = round(book.get("progress", 0) * 100, 1)
        print(f"  {book['title']}: {pct}% ({book.get('wordsRead', 0)}/{book['totalWords']} words)")

    print(f"Synced {len(currently_reading)} reading, {len(to_read)} to-read → {SHELF_PATH}")


if __name__ == "__main__":
    sync()
