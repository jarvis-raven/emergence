#!/usr/bin/env bash
# Setup script for development tools and code quality enforcement
# This script is idempotent - safe to run multiple times

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main setup function
main() {
    echo ""
    echo "🚀 Setting up development tools for Emergence"
    echo "=============================================="
    echo ""

    # Check prerequisites
    info "Checking prerequisites..."
    
    if ! command_exists python3; then
        error "Python 3 is not installed. Please install Python 3.9 or later."
        exit 1
    fi
    success "Python 3 found: $(python3 --version)"

    if ! command_exists node; then
        warning "Node.js is not installed. JavaScript linting will be limited."
    else
        success "Node.js found: $(node --version)"
    fi

    if ! command_exists git; then
        error "Git is not installed. Please install Git."
        exit 1
    fi
    success "Git found: $(git --version)"

    echo ""

    # Install Python tools
    info "Installing Python development tools..."
    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install black flake8 pytest pytest-cov pre-commit --quiet
    success "Python tools installed (black, flake8, pytest, pytest-cov, pre-commit)"

    echo ""

    # Install Node.js tools if Node is available
    if command_exists npm; then
        info "Installing Node.js development tools..."
        npm install --save-dev prettier eslint eslint-config-prettier --silent
        success "Node.js tools installed (prettier, eslint)"
    fi

    echo ""

    # Install pre-commit hooks
    info "Installing pre-commit hooks..."
    if [ -f ".pre-commit-config.yaml" ]; then
        pre-commit install --install-hooks
        pre-commit install --hook-type commit-msg
        success "Pre-commit hooks installed"
    else
        error ".pre-commit-config.yaml not found. Please run this script from the repository root."
        exit 1
    fi

    echo ""

    # Verify setup
    info "Verifying setup..."
    
    # Check Black
    if command_exists black; then
        success "Black is available: $(black --version | head -n1)"
    else
        warning "Black not found in PATH"
    fi

    # Check flake8
    if command_exists flake8; then
        success "Flake8 is available: $(flake8 --version | head -n1)"
    else
        warning "Flake8 not found in PATH"
    fi

    # Check pytest
    if command_exists pytest; then
        success "Pytest is available: $(pytest --version | head -n1)"
    else
        warning "Pytest not found in PATH"
    fi

    # Check Prettier
    if [ -f "node_modules/.bin/prettier" ]; then
        success "Prettier is available: $(npx prettier --version)"
    else
        warning "Prettier not found (Node.js tools may not be installed)"
    fi

    # Check ESLint
    if [ -f "node_modules/.bin/eslint" ]; then
        success "ESLint is available: $(npx eslint --version)"
    else
        warning "ESLint not found (Node.js tools may not be installed)"
    fi

    # Check pre-commit
    if command_exists pre-commit; then
        success "Pre-commit is available: $(pre-commit --version)"
    else
        warning "Pre-commit not found in PATH"
    fi

    echo ""

    # Test pre-commit hooks
    info "Testing pre-commit hooks..."
    if pre-commit run --all-files --show-diff-on-failure 2>/dev/null; then
        success "Pre-commit hooks test passed"
    else
        warning "Pre-commit hooks found issues. This is normal if code needs formatting."
        info "Run 'npm run format' or 'black .' to fix formatting issues."
    fi

    echo ""
    echo "=============================================="
    success "Development tools setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Run 'npm run lint' to check code quality"
    echo "  2. Run 'npm run format' to auto-fix formatting"
    echo "  3. Run 'pytest --cov=core' to run tests with coverage"
    echo "  4. Commit your changes - pre-commit hooks will run automatically"
    echo "  5. Use --no-verify flag to bypass hooks if needed (not recommended)"
    echo ""
}

# Run main function
main "$@"
