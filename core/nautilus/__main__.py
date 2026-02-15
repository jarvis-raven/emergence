#!/usr/bin/env python3
"""
Nautilus CLI entry point when run as module:
  python3 -m core.nautilus <command>
"""

from .nautilus_cli import main

if __name__ == '__main__':
    main()
