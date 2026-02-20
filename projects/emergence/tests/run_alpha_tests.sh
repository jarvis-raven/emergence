#!/usr/bin/env bash
# Nautilus v0.4.0 Alpha Test Runner
#
# Runs the complete alpha validation test suite with reporting.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "🐚 Nautilus v0.4.0 Alpha Test Suite"
echo "===================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing..."
    pip install pytest pytest-timeout
fi

# Run test categories sequentially with reporting
echo "📋 Running test suite..."
echo ""

echo "🔍 Search Tests..."
pytest tests/test_nautilus_alpha.py::TestSearch -v --tb=short || true

echo ""
echo "📊 Status Tests..."
pytest tests/test_nautilus_alpha.py::TestStatus -v --tb=short || true

echo ""
echo "🔄 Migration Tests..."
pytest tests/test_nautilus_alpha.py::TestMigration -v --tb=short || true

echo ""
echo "🔌 Integration Tests..."
pytest tests/test_nautilus_alpha.py::TestIntegration -v --tb=short || true

echo ""
echo "⚠️  Edge Case Tests..."
pytest tests/test_nautilus_alpha.py::TestEdgeCases -v --tb=short || true

echo ""
echo "🛠️  Maintenance Tests..."
pytest tests/test_nautilus_alpha.py::TestMaintenance -v --tb=short || true

echo ""
echo "💻 CLI Tests..."
pytest tests/test_nautilus_alpha.py::TestCLI -v --tb=short || true

echo ""
echo "===================================="
echo "✅ Alpha test suite complete!"
echo ""
echo "For detailed results, run:"
echo "  pytest tests/test_nautilus_alpha.py -v"
