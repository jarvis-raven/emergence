"""Entry point for python3 -m emergence.core.drives

Allows running the drive CLI as a module:
    python3 -m emergence.core.drives [command] [options]
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
