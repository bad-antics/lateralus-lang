#!/usr/bin/env bash
# publish.sh — push every staged seed repo to github.com/bad-antics/<name>.
#
# Prerequisites:
#   - `gh` CLI installed and authenticated (or GITHUB_TOKEN in env)
#   - `yq` installed (for reading manifest.yml)
#   - `python3 generate.py` has been run first
#
# Idempotent: re-running on an existing repo skips `gh repo create` and
# does a fast-forward push of the `main` branch only.
#
# Usage:
#   ./publish.sh                 # publish all repos in manifest
#   ./publish.sh ltl-json-cli    # publish a single repo

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
STAGED="$ROOT/staged"
MANIFEST="$ROOT/manifest.yml"

if ! command -v gh >/dev/null 2>&1; then
    echo "error: gh CLI not found" >&2
    exit 1
fi
if ! command -v yq >/dev/null 2>&1; then
    echo "error: yq not found (try: apt install yq / brew install yq)" >&2
    exit 1
fi

OWNER="$(yq -r '.owner' "$MANIFEST")"
LICENSE="$(yq -r '.license' "$MANIFEST")"
DEFAULT_TOPICS="$(yq -r '.defaults.topics | join(",")' "$MANIFEST")"
BRANCH="$(yq -r '.defaults.branch' "$MANIFEST")"

names_to_publish() {
    if [ $# -gt 0 ]; then
        printf '%s\n' "$@"
    else
        yq -r '.repos[].name' "$MANIFEST"
    fi
}

publish_one() {
    local name="$1"
    local dir="$STAGED/$name"

    if [ ! -d "$dir" ]; then
        echo "  skip     $name  (not staged; run generate.py first)"
        return
    fi

    local tagline
    tagline="$(yq -r ".repos[] | select(.name == \"$name\") | .tagline" "$MANIFEST")"
    local extra_topics
    extra_topics="$(yq -r ".repos[] | select(.name == \"$name\") | (.topics // []) | join(\",\")" "$MANIFEST")"
    local all_topics="$DEFAULT_TOPICS"
    if [ -n "$extra_topics" ]; then
        all_topics="$DEFAULT_TOPICS,$extra_topics"
    fi

    cd "$dir"

    # git init if needed
    if [ ! -d .git ]; then
        git init -q -b "$BRANCH"
        git add -A
        git -c user.email=bot@lateralus.dev \
            -c user.name="Lateralus Bot" \
            commit -q -m "initial commit"
    fi

    # Create remote if absent
    if ! gh repo view "$OWNER/$name" >/dev/null 2>&1; then
        echo "  create   $name"
        gh repo create "$OWNER/$name" \
            --public \
            --description "$tagline" \
            --source "$dir" \
            --remote origin \
            --push \
            --license "$LICENSE" 2>/dev/null || {
                # fallback: minimal create, then push
                gh repo create "$OWNER/$name" --public --description "$tagline" 2>/dev/null || true
                git remote remove origin 2>/dev/null || true
                git remote add origin "https://github.com/$OWNER/$name.git"
                git push -u origin "$BRANCH"
            }
    else
        echo "  push     $name"
        git remote remove origin 2>/dev/null || true
        git remote add origin "https://github.com/$OWNER/$name.git"
        git push -u origin "$BRANCH" 2>/dev/null || git push origin "$BRANCH"
    fi

    # Topics — PUT replaces the entire list, so send all topics in one call
    local topic_args=()
    IFS=',' read -ra TOPICS <<< "$all_topics"
    for topic in "${TOPICS[@]}"; do
        [ -n "$topic" ] && topic_args+=(-f "names[]=$topic")
    done
    if [ ${#topic_args[@]} -gt 0 ]; then
        gh api --silent -X PUT "repos/$OWNER/$name/topics" "${topic_args[@]}" 2>/dev/null || true
    fi

    cd "$ROOT"
}

echo "=== publishing seed repos to $OWNER ==="
count=0
while read -r name; do
    [ -z "$name" ] && continue
    publish_one "$name"
    count=$((count + 1))
done < <(names_to_publish "$@")

echo ""
echo "=== done: $count repo(s) processed ==="
echo ""
echo "Verify language bar (wait ~15 min for Linguist cache):"
echo "  curl -s https://api.github.com/repos/$OWNER/<name>/languages | jq"
