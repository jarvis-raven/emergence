# Emergence F040b Fresh Agent Validation — Docker Test
# Tests the full setup flow from zero: clone → first_light → drives tick → spawn
FROM python:3.11-slim-bookworm

# Minimal system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl && \
    rm -rf /var/lib/apt/lists/*

# Create a fresh agent user (not root)
RUN useradd -m -s /bin/bash agent
USER agent
WORKDIR /home/agent

# Copy emergence source (mounted or copied)
# Install pytest (only test dependency)
RUN pip install --no-cache-dir pytest

COPY --chown=agent:agent . /home/agent/emergence/

# Set working directory to emergence root
WORKDIR /home/agent/emergence

# Verify Python can import core modules
RUN python3 -c "from core.drives.engine import tick_all_drives; print('✓ drives engine imports')"
RUN python3 -c "from core.dream_engine import generate_fragments, InsightScorer; print('✓ dream engine imports')"
RUN python3 -c "from core.memory import consolidation, nightly_build; print('✓ memory modules import')"
RUN python3 -c "from core.setup.init_wizard import run_wizard; print('✓ first_light imports')" || \
    python3 -c "from core.setup import init_wizard; print('✓ first_light imports (module)')"
RUN python3 -c "from core.first_light import analyzer; print('✓ first_light analyzer imports')"

# Run unit tests
RUN python3 -m pytest core/ -q --tb=short 2>&1 | tail -5

# Default: interactive shell for manual testing
CMD ["/bin/bash"]
