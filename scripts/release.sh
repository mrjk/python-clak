#!/bin/bash

set -euo pipefail

# Enable debug mode with xtrace - uncomment next line to debug
# When enabled, this will print each command before it's executed
# Useful for debugging but can be verbose
# set -x

GET_VERSION_CMD="${GET_VERSION_CMD:-"poetry version -s"}"

# Display usage instructions 
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] VERSION

Update project version using poetry and create a git tag.

Arguments:
    VERSION     New version or bump rule

Version Keywords:
    major          Bump major version (1.0.0 -> 2.0.0)
    minor          Bump minor version (1.2.0 -> 1.3.0)
    patch          Bump patch version (1.2.3 -> 1.2.4)
    premajor       Bump to pre-release major (1.2.3 -> 2.0.0-alpha.0)
    preminor       Bump to pre-release minor (1.2.3 -> 1.3.0-alpha.0)
    prepatch       Bump to pre-release patch (1.2.3 -> 1.2.4-alpha.0)
    prerelease     Bump pre-release version (1.2.3-alpha.0 -> 1.2.3-alpha.1)

Options:
    -h, --help     Show this help message
    --dry-run      Only show what would happen
    --next-phase   Use next phase, only for pre-release

Reference:
    https://python-poetry.org/docs/cli/#version

Examples:
    # Set exact version:
    $(basename "$0") 1.2.3                    # Set to specific version
    $(basename "$0") 2.0.0a0                  # Set to specific pre-release version
    
    # Release version bumps:
    $(basename "$0") patch                    # 1.2.3 -> 1.2.4
    $(basename "$0") minor                    # 1.2.3 -> 1.3.0
    $(basename "$0") major                    # 1.2.3 -> 2.0.0
    
    # Pre-release version bumps:
    $(basename "$0") prepatch                 # 1.2.3 -> 1.2.4a0
    $(basename "$0") preminor                 # 1.2.3 -> 1.3.0a0
    $(basename "$0") premajor                 # 1.2.3 -> 2.0.0a0
    $(basename "$0") prerelease               # 1.2.3a0 -> 1.2.3a1
    $(basename "$0") prerelease               # 1.2.3b0 -> 1.2.3b1
    
    # Pre-release next-phase:
    $(basename "$0") prerelease --next-phase  # 1.2.3a0 -> 1.2.3b0
    $(basename "$0") prerelease --next-phase  # 1.2.3b0 -> 1.2.3rc0
    $(basename "$0") prerelease --next-phase  # 1.2.3b0 -> 1.2.3
    
    # Preview changes:
    $(basename "$0") --dry-run patch    # Show what would happen

EOF

    cat << EOF
Project Informations:
    Version command: $GET_VERSION_CMD
    Current project version: $(get_current_version)
EOF
    exit 0
}

# Validate command line arguments
# Show help if no args provided or if help flags are present
# This ensures user provides necessary version information
# Accepts -h, --help, or help as valid help requests
check_args() {
    if [ $# -eq 0 ] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]] || [[ "$1" == "help" ]]; then
        show_help
    fi
}

# Detect if version is a pre-release by checking if any argument starts with 'pre'
# Returns 0 (success) if pre-release, 1 (failure) if not
# This function is used to enforce different branch rules for pre-releases
# Examples of pre-release versions: pre-alpha, pre-beta, pre-rc1
is_prerelease() {
    for arg in "$@"; do
        if [[ "$arg" == pre* ]]; then
            return 0
        fi
    done
    return 1
}

# Return current project version, by default it uses poetry version -s
get_current_version() {
    $GET_VERSION_CMD
}

# Dump way to get current project name
get_project_name() {
    grep "^name" pyproject.toml | cut -d'"' -f2
}

# Enforce branch restrictions based on version type:
# - Pre-releases must NOT be on main/master (typically done on feature branches)
# - Regular releases must be on main/master (ensures proper release workflow)
# This helps maintain clean versioning and release processes:
# - Feature branches for pre-releases (e.g., beta versions)
# - Main branch for production releases
check_branch() {
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    
    if is_prerelease "$@"; then
        # For pre-releases, prevent release from main/master
        # This ensures pre-releases are done on feature branches
        if [[ "$current_branch" == "main" || "$current_branch" == "master" ]]; then
            echo "Error: Pre-release versions cannot be created on main/master branch"
            exit 1
        fi
    else
        # For regular releases, ensure we're on main/master
        # This enforces the policy that releases come from main branch
        if [[ "$current_branch" != "main" && "$current_branch" != "master" ]]; then
            echo "Error: Must be on main or master branch for regular releases"
            exit 1
        fi
    fi
}

# Ensure working directory is clean before proceeding
# Uses git diff-index to check for uncommitted changes
# This prevents accidental mixing of version changes with other work
# A clean working directory ensures version bumps are isolated commits
check_git_status() {
    if ! git diff-index --quiet HEAD --; then
        echo "Error: There are uncommitted changes in the repository"
        git status -sb
        exit 1
    fi
}

# Update version using poetry and handle dry-run mode
# Passes all arguments directly to poetry version command
# Supports various version formats:
# - Explicit versions (1.2.3)
# - Version parts (major, minor, patch)
# - Pre-release versions (pre-alpha, pre-beta)
update_version() {
    # Forward args to poetry version
    poetry version "$@"
    local exit_code=$?
    # Check if poetry command succeeded
    # Poetry returns non-zero exit code if version format is invalid
    if [ $exit_code -ne 0 ]; then
        echo "Error: Failed to update version"
        exit $exit_code
    fi

    # Exit early if --dry-run flag is present in arguments
    # This allows testing the release process without making changes
    if [[ "$*" == *"--dry-run"* ]]; then
        echo ">>> Dry run completed"
        exit 0
    fi
}

# Create git commit and tag for the version change
commit_and_tag() {
    echo ">>> Starting commit and tag process"
    # Get current version from poetry without extra output
    local version
    version=$(poetry version -s)
    prj_name=$(get_project_name)
    
    local target="$prj_name/__init__.py"
    local targets=""
    for file in pyproject.toml "$target" ; do
        [[ -f "$file" ]] || continue
        targets="$targets $file"
    done

    git add $targets    
    echo ">>> Committing version bump and create tag"
    git commit -m "bump: version v$version" $targets
    git tag -m "release: version v$version" "v$version"
}

# Main execution flow
# Handles the entire release process in sequence
# Each step must succeed for the script to continue
# The order is important:
# 1. Validate input
# 2. Check branch rules
# 3. Ensure clean working directory
# 4. Update version
# 5. Commit and tag changes
main() {
    echo ">>> Starting release process"
    check_args "$@"      # Validate input
    check_branch "$@"    # Enforce branch restrictions
    check_git_status     # Ensure clean working directory
    update_version "$@"  # Update version in poetry
    commit_and_tag       # Create git commit and tag
    
    
    echo ">>> Release process completed"
    echo ">>> Use 'git push && git push --tags' to publish changes"
}

# Uncomment next line to enable debug tracing
# This will show each command as it's executed
# Useful for debugging but produces verbose output
# set -x

main "$@"


