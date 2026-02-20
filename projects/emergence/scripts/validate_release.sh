#!/bin/bash
# Release Validation Script for Emergence v0.4.0
# This script performs automated checks before PyPI release

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Emergence v0.4.0 - PyPI Release Validation          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

section() {
    echo ""
    echo -e "${BLUE}▶ $1${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 1. VERSION CONSISTENCY CHECK
section "Version Consistency Check"

VERSION="0.4.0"

# Check setup.py
if grep -q "version=\"$VERSION\"" setup.py 2>/dev/null; then
    check_pass "setup.py version is $VERSION"
else
    check_fail "setup.py version mismatch (expected $VERSION)"
fi

# Check core/nautilus/__init__.py
if grep -q "__version__ = \"$VERSION\"" core/nautilus/__init__.py 2>/dev/null; then
    check_pass "core/nautilus/__init__.py version is $VERSION"
else
    check_fail "core/nautilus/__init__.py version mismatch (expected $VERSION)"
fi

# Check README.md
if grep -q "v$VERSION" README.md 2>/dev/null; then
    check_pass "README.md mentions v$VERSION"
else
    check_warn "README.md may not mention v$VERSION"
fi

# Check CHANGELOG.md exists and has v0.4.0 entry
if [ -f "CHANGELOG.md" ]; then
    if grep -q "\[0.4.0\]" CHANGELOG.md; then
        check_pass "CHANGELOG.md has v0.4.0 entry"
    else
        check_fail "CHANGELOG.md missing v0.4.0 entry"
    fi
else
    check_fail "CHANGELOG.md not found"
fi

# 2. FILE STRUCTURE CHECK
section "File Structure Check"

required_files=(
    "setup.py"
    "README.md"
    "CHANGELOG.md"
    "core/__init__.py"
    "core/nautilus/__init__.py"
    "core/cli.py"
    "docs/RELEASE_CHECKLIST_v0.4.0.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        check_pass "Required file exists: $file"
    else
        check_fail "Missing required file: $file"
    fi
done

# Check for package directories
required_dirs=(
    "core"
    "core/nautilus"
    "room"
    "tests"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        check_pass "Required directory exists: $dir"
    else
        check_fail "Missing required directory: $dir"
    fi
done

# 3. DEPENDENCY CHECK
section "Dependency Check"

if [ -f "setup.py" ]; then
    check_pass "setup.py found"
    
    # Check if it has basic required fields
    required_fields=("name" "version" "description" "author" "packages")
    for field in "${required_fields[@]}"; do
        if grep -q "$field" setup.py; then
            check_pass "setup.py has '$field' field"
        else
            check_warn "setup.py missing '$field' field"
        fi
    done
fi

# 4. TESTING CHECK
section "Testing Check"

if command -v pytest &> /dev/null; then
    echo "Running pytest..."
    if pytest tests/ -q --tb=no 2>/dev/null; then
        check_pass "All tests passed"
    else
        check_warn "Some tests failed (run 'pytest tests/ -v' for details)"
    fi
else
    check_warn "pytest not installed (skipping tests)"
fi

# 5. IMPORT CHECK
section "Import Check"

echo "Checking Python imports..."
python3 -c "import sys; sys.path.insert(0, '.'); import core.nautilus" 2>/dev/null && \
    check_pass "core.nautilus imports successfully" || \
    check_fail "core.nautilus import failed"

python3 -c "import sys; sys.path.insert(0, '.'); from core.nautilus import search, get_status, run_maintain" 2>/dev/null && \
    check_pass "core.nautilus API imports successfully" || \
    check_fail "core.nautilus API import failed"

# 6. VERSION STRING CHECK
section "Version String Consistency"

# Search for any remaining 0.3.0 references that should be 0.4.0
echo "Checking for old version references..."
OLD_VERSION_COUNT=$(grep -r "0\.3\.0" --include="*.py" --include="*.md" . 2>/dev/null | \
    grep -v "CHANGELOG.md" | \
    grep -v "Previous Release" | \
    grep -v ".git" | \
    wc -l | tr -d ' ')

if [ "$OLD_VERSION_COUNT" -eq 0 ]; then
    check_pass "No old version (0.3.0) references found"
else
    check_warn "Found $OLD_VERSION_COUNT references to old version 0.3.0 (review manually)"
fi

# 7. DOCUMENTATION CHECK
section "Documentation Check"

# Check README has key sections
readme_sections=("Overview" "Usage" "Installation")
for section_name in "${readme_sections[@]}"; do
    if grep -qi "$section_name" README.md 2>/dev/null; then
        check_pass "README.md has '$section_name' section"
    else
        check_warn "README.md may be missing '$section_name' section"
    fi
done

# Check if docs exist
if [ -d "docs" ]; then
    check_pass "docs/ directory exists"
    
    if [ -f "docs/RELEASE_CHECKLIST_v0.4.0.md" ]; then
        check_pass "Release checklist exists"
    else
        check_fail "Release checklist missing"
    fi
else
    check_warn "docs/ directory not found"
fi

# 8. BUILD TEST
section "Build Test (Optional)"

if command -v python3 &> /dev/null; then
    echo "Checking if build tools are available..."
    
    if python3 -c "import build" 2>/dev/null; then
        echo "Attempting to build distribution..."
        
        # Clean old builds
        rm -rf dist/ build/ *.egg-info 2>/dev/null
        
        if python3 -m build --quiet 2>/dev/null; then
            check_pass "Package built successfully"
            
            # Check if distributions were created
            if [ -f dist/emergence-ai-${VERSION}.tar.gz ]; then
                check_pass "Source distribution created"
            else
                check_fail "Source distribution not found"
            fi
            
            if ls dist/emergence-ai-${VERSION}-*.whl 1> /dev/null 2>&1; then
                check_pass "Wheel distribution created"
            else
                check_fail "Wheel distribution not found"
            fi
        else
            check_warn "Build failed (install 'build' package: pip install build)"
        fi
    else
        check_warn "Build module not installed (skipping build test)"
    fi
else
    check_warn "Python3 not found (skipping build test)"
fi

# 9. SUMMARY
section "Validation Summary"

echo ""
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${RED}Failed:${NC}   $FAILED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ VALIDATION PASSED - Ready for next steps!         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ✗ VALIDATION FAILED - Fix issues before release     ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
