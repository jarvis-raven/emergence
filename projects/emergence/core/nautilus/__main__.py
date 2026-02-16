#!/usr/bin/env python3
"""
🐚 Nautilus — CLI Entry Point

Usage:
    python -m core.nautilus search <query>
    python -m core.nautilus status
    python -m core.nautilus maintain
    python -m core.nautilus classify <file>
    python -m core.nautilus gravity <file>

Or via Emergence CLI:
    emergence nautilus search <query>
    emergence nautilus status
    emergence nautilus maintain
"""

import sys
from .cli import main

if __name__ == "__main__":
    main()
