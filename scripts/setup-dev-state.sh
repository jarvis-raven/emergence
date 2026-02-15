#!/usr/bin/env bash
# setup-dev-state.sh - Initialize dev environment with production state
# Part of Issue #105: Dev Environment State Initialization
#
# SAFETY: This script NEVER modifies .emergence/ (production state)
# It only copies FROM .emergence/ TO .emergence-dev/

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROD_STATE="$PROJECT_ROOT/.emergence"
DEV_STATE="$PROJECT_ROOT/.emergence-dev"

# Exit codes
EXIT_SUCCESS=0
EXIT_ERROR=1
EXIT_CANCELLED=2

# Print functions
print_header() {
    echo -e "${BLUE}📋 Dev Environment State Setup${RESET}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${RESET}"
}

print_error() {
    echo -e "${RED}❌ $1${RESET}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${RESET}"
}

# Confirm with user
confirm() {
    local prompt="$1"
    local response
    
    read -p "$prompt [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Main setup function
main() {
    print_header
    
    # SAFETY CHECK 1: Verify production state exists
    if [[ ! -d "$PROD_STATE" ]]; then
        print_error "Production state directory not found: $PROD_STATE"
        print_info "You need to run Emergence in production mode first to create the state."
        exit $EXIT_ERROR
    fi
    
    print_info "Source (production): $PROD_STATE"
    print_info "Target (development): $DEV_STATE"
    echo ""
    
    # SAFETY CHECK 2: Warn if dev state already exists
    if [[ -d "$DEV_STATE" ]]; then
        print_warning "Development state directory already exists!"
        print_warning "This will DELETE and replace: $DEV_STATE"
        echo ""
        
        if ! confirm "Continue?"; then
            print_info "Setup cancelled. No changes made."
            exit $EXIT_CANCELLED
        fi
        
        echo ""
        print_info "Removing existing dev state..."
        rm -rf "$DEV_STATE"
        print_success "Removed $DEV_STATE"
        echo ""
    fi
    
    # SAFETY CHECK 3: Final confirmation
    print_warning "This will copy production state to dev environment"
    print_success "Production state will remain unchanged"
    echo ""
    
    if ! confirm "Continue?"; then
        print_info "Setup cancelled. No changes made."
        exit $EXIT_CANCELLED
    fi
    
    echo ""
    print_info "Copying production state to dev environment..."
    
    # Create dev state directory
    mkdir -p "$DEV_STATE"
    
    # Copy all contents from production to dev
    # Using rsync for better control and to preserve structure
    if command -v rsync &> /dev/null; then
        rsync -a --exclude='*.pid' "$PROD_STATE/" "$DEV_STATE/"
    else
        # Fallback to cp if rsync not available
        cp -R "$PROD_STATE/"* "$DEV_STATE/" 2>/dev/null || true
        # Remove PID files (shouldn't be copied)
        find "$DEV_STATE" -name "*.pid" -delete 2>/dev/null || true
    fi
    
    # List what was copied
    echo ""
    print_success "Copied state files:"
    if [[ -d "$DEV_STATE/state" ]]; then
        ls -la "$DEV_STATE/state" | tail -n +4 | awk '{print "  - " $NF}'
    fi
    if [[ -f "$DEV_STATE/drives.pid" ]]; then
        rm "$DEV_STATE/drives.pid"
    fi
    
    echo ""
    print_success "Dev state initialized!"
    echo ""
    print_info "Next steps:"
    echo "  1. Run 'cd room && npm run dev' to start dev environment"
    echo "  2. Dev environment will use .emergence-dev/ for state"
    echo "  3. Production state (.emergence/) remains untouched"
    echo ""
    print_warning "Note: Dev and prod environments are now independent!"
    
    exit $EXIT_SUCCESS
}

# Run main function
main "$@"
