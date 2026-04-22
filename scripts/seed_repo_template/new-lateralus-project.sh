#!/usr/bin/env bash
# new-lateralus-project.sh — bootstrap a new Lateralus project from the seed template.
#
# Usage:  ./new-lateralus-project.sh <project-name> [author]
# Creates ./<project-name> with a compiling hello-world + tests + .gitattributes.

set -euo pipefail

PROJECT_NAME="${1:-}"
AUTHOR="${2:-$(git config --get user.name 2>/dev/null || echo 'Anonymous')}"

if [[ -z "$PROJECT_NAME" ]]; then
    echo "Usage: $0 <project-name> [author]"
    exit 1
fi

if [[ -e "$PROJECT_NAME" ]]; then
    echo "Error: $PROJECT_NAME already exists"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR"
YEAR="$(date +%Y)"

cp -r "$TEMPLATE_DIR" "$PROJECT_NAME"
rm -f "$PROJECT_NAME/new-lateralus-project.sh"

# Substitute template variables
find "$PROJECT_NAME" -type f \( -name '*.md' -o -name '*.ltl' -o -name 'LICENSE' \) -print0 | \
    xargs -0 sed -i "s/{{PROJECT_NAME}}/$PROJECT_NAME/g; s/{{AUTHOR}}/$AUTHOR/g; s/{{YEAR}}/$YEAR/g"

cd "$PROJECT_NAME"
git init --quiet
git add .
git commit --quiet -m "Initial commit from Lateralus seed template"

echo ""
echo "Created: $PROJECT_NAME/"
echo "Next:"
echo "  cd $PROJECT_NAME"
echo "  lateralus run src/main.ltl"
echo ""
echo "To publish:"
echo "  gh repo create $PROJECT_NAME --public --source=. --push"
