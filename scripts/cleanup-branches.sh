#!/usr/bin/env bash
# Branch Cleanup Automation Script
# Manages cleanup of merged and stale Git branches with safety guardrails
#
# Usage:
#   ./cleanup-branches.sh              # Dry-run mode (default, safe preview)
#   ./cleanup-branches.sh --interactive # Interactive mode with confirmation
#   ./cleanup-branches.sh --force       # Auto-delete with confirmation flag
#   ./cleanup-branches.sh --help        # Show usage information
#
# Exit codes:
#   0 = success
#   1 = error
#   2 = user cancelled

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROTECTED_BRANCHES=("main" "master" "develop")
PROTECTED_PATTERNS=("spike/*" "release/*")
STALE_DAYS=30
MERGED_GRACE_DAYS=7

# Mode flags
DRY_RUN=true
INTERACTIVE=false
FORCE=false

# Usage information
usage() {
    cat << EOF
Branch Cleanup Automation Script

Usage: $0 [OPTIONS]

OPTIONS:
    --dry-run        Preview branches without deletion (default)
    --interactive    Show branches and confirm before deletion
    --force          Auto-delete with confirmation flag (requires --yes)
    --yes            Confirm force deletion
    --help           Show this help message

EXAMPLES:
    $0                           # Safe preview of branches to delete
    $0 --interactive             # Interactive cleanup with confirmation
    $0 --force --yes             # Automated deletion (use with caution)

SAFETY:
    - Protected branches: ${PROTECTED_BRANCHES[*]}
    - Protected patterns: ${PROTECTED_PATTERNS[*]}
    - Current branch is always preserved
    - Stale branches: no activity for ${STALE_DAYS}+ days
    - Merged branches: merged ${MERGED_GRACE_DAYS}+ days ago

EOF
    exit 0
}

# Parse command line arguments
CONFIRMED=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            INTERACTIVE=false
            FORCE=false
            shift
            ;;
        --interactive)
            DRY_RUN=false
            INTERACTIVE=true
            FORCE=false
            shift
            ;;
        --force)
            DRY_RUN=false
            INTERACTIVE=false
            FORCE=true
            shift
            ;;
        --yes)
            CONFIRMED=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            usage
            ;;
    esac
done

# Safety check for force mode
if [[ "$FORCE" == true ]] && [[ "$CONFIRMED" != true ]]; then
    echo -e "${RED}Error: Force mode requires --yes flag for confirmation${NC}"
    echo "Example: $0 --force --yes"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not a git repository${NC}"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}Current branch: ${GREEN}${CURRENT_BRANCH}${NC}"
echo ""

# Function to check if branch is protected
is_protected() {
    local branch="$1"
    
    # Check exact matches
    for protected in "${PROTECTED_BRANCHES[@]}"; do
        if [[ "$branch" == "$protected" ]]; then
            return 0
        fi
    done
    
    # Check pattern matches
    for pattern in "${PROTECTED_PATTERNS[@]}"; do
        if [[ "$branch" == $pattern ]]; then
            return 0
        fi
    done
    
    # Check if it's the current branch
    if [[ "$branch" == "$CURRENT_BRANCH" ]]; then
        return 0
    fi
    
    return 1
}

# Function to check if branch is merged
is_merged() {
    local branch="$1"
    local base="${2:-main}"
    
    # Try main first, then master if main doesn't exist
    if git show-ref --verify --quiet "refs/heads/main"; then
        base="main"
    elif git show-ref --verify --quiet "refs/heads/master"; then
        base="master"
    fi
    
    git branch --merged "$base" | grep -q "^\*\? *${branch}$"
}

# Function to get branch last commit date (Unix timestamp)
get_branch_date() {
    local branch="$1"
    git log -1 --format=%ct "$branch" 2>/dev/null || echo "0"
}

# Function to calculate days since last commit
days_since_commit() {
    local branch="$1"
    local commit_date=$(get_branch_date "$branch")
    local now=$(date +%s)
    local diff=$((now - commit_date))
    echo $((diff / 86400))
}

# Arrays to store branches
declare -a MERGED_BRANCHES=()
declare -a STALE_BRANCHES=()
declare -a PROTECTED_FOUND=()

echo -e "${BLUE}Analyzing local branches...${NC}"
echo ""

# Analyze local branches
while IFS= read -r branch; do
    # Clean up branch name
    branch=$(echo "$branch" | sed 's/^[* ]*//' | xargs)
    
    if [[ -z "$branch" ]]; then
        continue
    fi
    
    # Check if protected
    if is_protected "$branch"; then
        PROTECTED_FOUND+=("$branch")
        continue
    fi
    
    # Check if merged
    if is_merged "$branch"; then
        days=$(days_since_commit "$branch")
        if [[ $days -ge $MERGED_GRACE_DAYS ]]; then
            MERGED_BRANCHES+=("$branch (merged ${days}d ago)")
        fi
        continue
    fi
    
    # Check if stale
    days=$(days_since_commit "$branch")
    if [[ $days -ge $STALE_DAYS ]]; then
        STALE_BRANCHES+=("$branch (stale ${days}d ago)")
    fi
done < <(git branch | grep -v "^\*")

# Analyze remote branches
echo -e "${BLUE}Analyzing remote branches...${NC}"
echo ""

declare -a REMOTE_MERGED=()
git fetch --prune 2>/dev/null || true

while IFS= read -r branch; do
    # Extract branch name from origin/branch format
    branch=$(echo "$branch" | sed 's|origin/||' | xargs)
    
    if [[ -z "$branch" ]]; then
        continue
    fi
    
    # Check if protected
    if is_protected "$branch"; then
        continue
    fi
    
    # Check if merged
    if is_merged "$branch"; then
        days=$(days_since_commit "origin/$branch")
        if [[ $days -ge $MERGED_GRACE_DAYS ]]; then
            REMOTE_MERGED+=("origin/$branch (merged ${days}d ago)")
        fi
    fi
done < <(git branch -r | grep -v "HEAD" | grep "origin/")

# Display results
echo -e "${GREEN}=== Protected Branches (will NOT be deleted) ===${NC}"
if [[ ${#PROTECTED_FOUND[@]} -eq 0 ]]; then
    echo "  None found"
else
    for branch in "${PROTECTED_FOUND[@]}"; do
        echo -e "  ${GREEN}✓ $branch${NC}"
    done
fi
echo ""

echo -e "${RED}=== Merged Branches (safe to delete) ===${NC}"
if [[ ${#MERGED_BRANCHES[@]} -eq 0 ]]; then
    echo "  None found"
else
    for branch in "${MERGED_BRANCHES[@]}"; do
        echo -e "  ${RED}✗ $branch${NC}"
    done
fi
echo ""

echo -e "${YELLOW}=== Stale Branches (no activity ${STALE_DAYS}+ days) ===${NC}"
if [[ ${#STALE_BRANCHES[@]} -eq 0 ]]; then
    echo "  None found"
else
    for branch in "${STALE_BRANCHES[@]}"; do
        echo -e "  ${YELLOW}⚠ $branch${NC}"
    done
fi
echo ""

echo -e "${RED}=== Remote Merged Branches (safe to delete) ===${NC}"
if [[ ${#REMOTE_MERGED[@]} -eq 0 ]]; then
    echo "  None found"
else
    for branch in "${REMOTE_MERGED[@]}"; do
        echo -e "  ${RED}✗ $branch${NC}"
    done
fi
echo ""

# Count total branches to delete
TOTAL_TO_DELETE=$((${#MERGED_BRANCHES[@]} + ${#STALE_BRANCHES[@]} + ${#REMOTE_MERGED[@]}))

if [[ $TOTAL_TO_DELETE -eq 0 ]]; then
    echo -e "${GREEN}✓ No branches to clean up!${NC}"
    exit 0
fi

# Dry-run mode
if [[ "$DRY_RUN" == true ]]; then
    echo -e "${BLUE}=== DRY RUN MODE ===${NC}"
    echo "Found $TOTAL_TO_DELETE branches that would be deleted"
    echo ""
    echo "To actually delete branches, run:"
    echo "  $0 --interactive  (with confirmation prompts)"
    echo "  $0 --force --yes  (automated deletion)"
    exit 0
fi

# Interactive mode
if [[ "$INTERACTIVE" == true ]]; then
    echo -e "${YELLOW}=== INTERACTIVE MODE ===${NC}"
    echo "Ready to delete $TOTAL_TO_DELETE branches"
    echo ""
    read -p "Do you want to proceed? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        echo -e "${YELLOW}Cancelled by user${NC}"
        exit 2
    fi
fi

# Delete local merged branches
if [[ ${#MERGED_BRANCHES[@]} -gt 0 ]]; then
    echo -e "${BLUE}Deleting local merged branches...${NC}"
    for branch_info in "${MERGED_BRANCHES[@]}"; do
        branch=$(echo "$branch_info" | cut -d' ' -f1)
        echo "  Deleting: $branch"
        git branch -d "$branch" 2>/dev/null || git branch -D "$branch"
    done
    echo ""
fi

# Delete local stale branches
if [[ ${#STALE_BRANCHES[@]} -gt 0 ]]; then
    echo -e "${BLUE}Deleting local stale branches...${NC}"
    for branch_info in "${STALE_BRANCHES[@]}"; do
        branch=$(echo "$branch_info" | cut -d' ' -f1)
        echo "  Deleting: $branch"
        git branch -D "$branch"
    done
    echo ""
fi

# Delete remote merged branches
if [[ ${#REMOTE_MERGED[@]} -gt 0 ]]; then
    echo -e "${BLUE}Deleting remote merged branches...${NC}"
    for branch_info in "${REMOTE_MERGED[@]}"; do
        branch=$(echo "$branch_info" | sed 's|origin/||' | cut -d' ' -f1)
        echo "  Deleting: origin/$branch"
        git push origin --delete "$branch" 2>/dev/null || echo "    (already deleted or permission denied)"
    done
    echo ""
fi

echo -e "${GREEN}✓ Cleanup complete! Deleted $TOTAL_TO_DELETE branches${NC}"
echo ""
echo -e "${YELLOW}To undo local deletions, use:${NC}"
echo "  git reflog"
echo "  git checkout -b <branch-name> <commit-hash>"

exit 0
