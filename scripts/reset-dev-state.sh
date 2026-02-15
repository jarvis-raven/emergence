#!/usr/bin/env bash
# reset-dev-state.sh - Reset dev environment to match production
# Part of Issue #105: Dev Environment State Initialization
#
# SAFETY: This script NEVER modifies .emergence/ (production state)
# It only deletes .emergence-dev/ and re-copies from .emergence/

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
    echo -e "${BLUE}🔄 Dev Environment State Reset${RESET}"
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

# Dry run mode
dry_run() {
    print_header
    print_info "DRY RUN MODE - No changes will be made"
    echo ""
    
    if [[ ! -d "$PROD_STATE" ]]; then
        print_error "Production state not found: $PROD_STATE"
        return $EXIT_ERROR
    fi
    
    if [[ ! -d "$DEV_STATE" ]]; then
        print_warning "Dev state directory doesn't exist: $DEV_STATE"
        print_info "Nothing to reset. Run 'npm run dev:setup' first."
        return $EXIT_SUCCESS
    fi
    
    print_info "Would perform these actions:"
    echo "  1. Delete: $DEV_STATE"
    echo "  2. Copy: $PROD_STATE → $DEV_STATE"
    echo ""
    
    print_info "Files that would be reset:"
    if [[ -d "$DEV_STATE/state" ]]; then
        ls -la "$DEV_STATE/state" | tail -n +4 | awk '{print "  - " $NF}'
    fi
    
    echo ""
    print_success "Dry run complete. Run without --dry-run to execute."
    
    return $EXIT_SUCCESS
}

# Main reset function
main() {
    # Check for dry-run flag
    if [[ "${1:-}" == "--dry-run" ]]; then
        dry_run
        exit $?
    fi
    
    print_header
    
    # SAFETY CHECK 1: Verify production state exists
    if [[ ! -d "$PROD_STATE" ]]; then
        print_error "Production state directory not found: $PROD_STATE"
        print_info "Cannot reset dev state without production state."
        exit $EXIT_ERROR
    fi
    
    # Check if dev state exists
    if [[ ! -d "$DEV_STATE" ]]; then
        print_warning "Dev state directory doesn't exist: $DEV_STATE"
        print_info "Nothing to reset. Run 'npm run dev:setup' first."
        exit $EXIT_SUCCESS
    fi
    
    print_info "This will:"
    echo "  1. DELETE all dev state: $DEV_STATE"
    echo "  2. Re-copy fresh from production: $PROD_STATE"
    echo ""
    
    print_warning "All changes in dev environment will be lost!"
    print_success "Production state will remain unchanged"
    echo ""
    
    if ! confirm "Continue?"; then
        print_info "Reset cancelled. No changes made."
        exit $EXIT_CANCELLED
    fi
    
    echo ""
    print_info "Deleting dev state..."
    rm -rf "$DEV_STATE"
    print_success "Deleted $DEV_STATE"
    
    echo ""
    print_info "Copying fresh state from production..."
    
    # Create dev state directory
    mkdir -p "$DEV_STATE"
    
    # Copy all contents from production to dev
    if command -v rsync &> /dev/null; then
        rsync -a --exclude='*.pid' "$PROD_STATE/" "$DEV_STATE/"
    else
        # Fallback to cp if rsync not available
        cp -R "$PROD_STATE/"* "$DEV_STATE/" 2>/dev/null || true
        # Remove PID files
        find "$DEV_STATE" -name "*.pid" -delete 2>/dev/null || true
    fi
    
    # List what was copied
    echo ""
    print_success "Reset complete! Fresh state files:"
    if [[ -d "$DEV_STATE/state" ]]; then
        ls -la "$DEV_STATE/state" | tail -n +4 | awk '{print "  - " $NF}'
    fi
    
    echo ""
    print_success "Dev state reset! Fresh copy from production."
    echo ""
    print_info "Next steps:"
    echo "  1. Run 'cd room && npm run dev' to start dev environment"
    echo "  2. Dev environment now matches production state"
    echo ""
    
    exit $EXIT_SUCCESS
}

# Run main function
main "$@"
