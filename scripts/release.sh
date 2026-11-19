#!/bin/bash

set -euo pipefail

# Enable debug mode with xtrace - uncomment next line to debug
# When enabled, this will print each command before it's executed
# Useful for debugging but can be verbose
# set -x

GET_VERSION_CMD="${GET_VERSION_CMD:-"uv version --short"}"

# Display usage instructions 
show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] VERSION

Update project version using uv and create a git tag.

Arguments:
    VERSION     New version or bump rule (optional leading v is stripped, e.g. v1.2.3)

Version Keywords:
    major          Bump major version (1.0.0 -> 2.0.0)
    minor          Bump minor version (1.2.0 -> 1.3.0)
    patch          Bump patch version (1.2.3 -> 1.2.4)
    premajor       Bump to pre-release major (1.2.3 -> 2.0.0a1)
    preminor       Bump to pre-release minor (1.2.3 -> 1.3.0a1)
    prepatch       Bump to pre-release patch (1.2.3 -> 1.2.4a1)
    prerelease     Bump pre-release version (1.2.3a1 -> 1.2.3a2, 1.2.3 -> 1.2.4a1)

Options:
    -h, --help     Show this help message
    --dry, --dry-run  Only show what would happen (dirty tree is a warning)
    --next-phase   Use next phase, only for pre-release

Reference:
    https://docs.astral.sh/uv/reference/cli/#uv-version

Examples:
    # Set exact version:
    $(basename "$0") 1.2.3                    # Set to specific version
    $(basename "$0") v1.2.3                   # Same (leading v is stripped)
    $(basename "$0") 2.0.0a1                  # Set to specific pre-release version
    
    # Release version bumps:
    $(basename "$0") patch                    # 1.2.3 -> 1.2.4
    $(basename "$0") minor                    # 1.2.3 -> 1.3.0
    $(basename "$0") major                    # 1.2.3 -> 2.0.0
    
    # Pre-release version bumps:
    $(basename "$0") prepatch                 # 1.2.3 -> 1.2.4a1
    $(basename "$0") preminor                 # 1.2.3 -> 1.3.0a1
    $(basename "$0") premajor                 # 1.2.3 -> 2.0.0a1
    $(basename "$0") prerelease               # 1.2.3a1 -> 1.2.3a2
    $(basename "$0") prerelease               # 1.2.3b1 -> 1.2.3b2
    
    # Pre-release next-phase:
    $(basename "$0") prerelease --next-phase  # 1.2.3a2 -> 1.2.3b1
    $(basename "$0") prerelease --next-phase  # 1.2.3b2 -> 1.2.3rc1
    $(basename "$0") prerelease --next-phase  # 1.2.3rc1 -> 1.2.3
    
    # Preview changes:
    $(basename "$0") --dry patch        # Show what would happen
    $(basename "$0") --dry-run patch    # Same as --dry

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

# Return current project version, by default it uses uv version --short
get_current_version() {
    $GET_VERSION_CMD
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
    if git diff-index --quiet HEAD --; then
        return 0
    fi
    if is_dry_run "$@"; then
        echo "Warning: uncommitted changes (ignored for dry-run)"
        git status -sb
        return 0
    fi
    echo "Error: There are uncommitted changes in the repository"
    git status -sb
    exit 1
}

# True if dry-run was requested (--dry or --dry-run)
is_dry_run() {
    local arg
    for arg in "$@"; do
        if [[ "$arg" == "--dry" || "$arg" == "--dry-run" ]]; then
            return 0
        fi
    done
    return 1
}

# Strip leading v/V prefixes from a version string (vv1.2.3 -> 1.2.3)
# Leaves bump keywords and flags unchanged
strip_v_prefix() {
    local value="$1"
    # Only strip when it looks like a version: v/V followed by a digit
    if [[ "$value" =~ ^[vV]+[0-9] ]]; then
        while [[ "$value" == [vV]* ]]; do
            value="${value:1}"
        done
    fi
    echo "$value"
}

# Git tag name with exactly one leading v (1.2.3 / v1.2.3 / vv1.2.3 -> v1.2.3)
format_version_tag() {
    local version
    version=$(strip_v_prefix "$1")
    echo "v$version"
}

# Translate Poetry-style bump keywords into `uv version` arguments.
# Prints one argument per line.
# - major/minor/patch          -> --bump X
# - premajor/preminor/prepatch -> --bump X --bump alpha
# - prerelease                 -> bump current pre phase (a/b/rc), or
#                                 patch+alpha when on a stable version
# - prerelease --next-phase    -> a -> beta -> rc -> stable
# - anything else              -> explicit version (leading v stripped)
uv_version_args() {
    local next_phase=false
    local -a positional=()
    local arg
    for arg in "$@"; do
        case "$arg" in
            --dry|--dry-run) ;;
            --next-phase) next_phase=true ;;
            *) positional+=("$arg") ;;
        esac
    done

    if [[ ${#positional[@]} -ne 1 ]]; then
        echo "Error: expected exactly one VERSION argument, got: ${positional[*]:-none}" >&2
        return 1
    fi

    local target="${positional[0]}"
    case "$target" in
        major|minor|patch)
            printf '%s\n' --bump "$target"
            ;;
        premajor|preminor|prepatch)
            printf '%s\n' --bump "${target#pre}" --bump alpha
            ;;
        prerelease)
            local current phase=""
            current="$(get_current_version)"
            if [[ "$current" =~ [0-9](a|b|rc)[0-9]+$ ]]; then
                phase="${BASH_REMATCH[1]}"
            fi
            if [[ -z "$phase" ]]; then
                if $next_phase; then
                    echo "Error: --next-phase requires a current pre-release version (got $current)" >&2
                    return 1
                fi
                printf '%s\n' --bump patch --bump alpha
            elif $next_phase; then
                case "$phase" in
                    a) printf '%s\n' --bump beta ;;
                    b) printf '%s\n' --bump rc ;;
                    rc) printf '%s\n' --bump stable ;;
                esac
            else
                case "$phase" in
                    a) printf '%s\n' --bump alpha ;;
                    b) printf '%s\n' --bump beta ;;
                    rc) printf '%s\n' --bump rc ;;
                esac
            fi
            ;;
        *)
            # uv expects bare PEP 440 versions, not git-style v1.2.3
            strip_v_prefix "$target"
            ;;
    esac
}

# Update version using uv and handle dry-run mode
# --dry is accepted as an alias for uv's --dry-run
update_version() {
    local -a uv_args=()
    local line
    while IFS= read -r line; do
        uv_args+=("$line")
    done < <(uv_version_args "$@" || echo "__ERROR__")

    if [[ ${#uv_args[@]} -eq 0 || " ${uv_args[*]} " == *" __ERROR__ "* ]]; then
        echo "Error: Failed to compute version arguments"
        exit 1
    fi

    if is_dry_run "$@"; then
        uv_args+=("--dry-run")
    fi

    # --no-sync: only touch pyproject.toml + uv.lock, not the .venv
    if ! uv version --no-sync "${uv_args[@]}"; then
        echo "Error: Failed to update version"
        exit 1
    fi

    # Exit early if dry-run was requested
    # This allows testing the release process without making changes
    if is_dry_run "$@"; then
        echo ">>> Dry run completed"
        exit 0
    fi
}

# Create git commit and tag for the version change
commit_and_tag() {
    echo ">>> Starting commit and tag process"
    # Get current version from uv without extra output
    local version tag
    version=$(strip_v_prefix "$(get_current_version)")
    tag=$(format_version_tag "$version")

    if git diff --quiet -- pyproject.toml; then
        echo "Error: pyproject.toml was not modified (version unchanged?)"
        exit 1
    fi

    git add pyproject.toml uv.lock
    echo ">>> Committing version bump and create tag $tag"
    git commit -m "bump: version $tag" pyproject.toml uv.lock
    git tag -m "release: version $tag" "$tag"
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
    check_git_status "$@"  # Clean tree (warn-only on dry-run)
    update_version "$@"  # Update version with uv
    commit_and_tag       # Create git commit and tag
    
    
    echo ">>> Release process completed"
    echo ">>> Use 'git push && git push --tags' to publish changes"
}

# Uncomment next line to enable debug tracing
# This will show each command as it's executed
# Useful for debugging but produces verbose output
# set -x

main "$@"


