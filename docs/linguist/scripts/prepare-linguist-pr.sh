#!/usr/bin/env bash
# One-shot: prepare a github-linguist/linguist fork PR locally.
#
# Assumes:
#   - You have already forked github-linguist/linguist to bad-antics/linguist
#   - You have a working clone at $LINGUIST_DIR (default: ../linguist)
#   - The grammar repo has been published (scripts/publish-grammar-repo.sh)
#
# Steps automated:
#   1. cd into the linguist fork, check out a fresh branch
#   2. Add bad-antics/lateralus-grammar as a submodule under
#      vendor/grammars/lateralus-grammar
#   3. Append the languages.yml entry from meta/languages-yml-entry.yml
#      (alphabetically — between Lasso and Latte)
#   4. Copy the 20 sample .ltl files into samples/Lateralus/
#   5. Copy the grammar's LICENSE into vendor/licenses/grammar/lateralus-grammar.txt
#   6. Regenerate grammars.yml via script/convert-grammars
#   7. Stage + commit with a conventional message
#
# You still have to:
#   - run `bundle exec rake test` yourself (ruby env varies)
#   - open the PR via gh or the web UI
#
# Usage:
#   LINGUIST_DIR=../linguist ./scripts/prepare-linguist-pr.sh

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
LINGUIST_DIR="${LINGUIST_DIR:-$ROOT/../linguist}"
BRANCH="add-lateralus"

[[ -d "$LINGUIST_DIR/lib/linguist" ]] || {
  echo "not a linguist checkout: $LINGUIST_DIR" >&2
  echo "clone your fork first:" >&2
  echo "  gh repo fork github-linguist/linguist --clone=true" >&2
  exit 1
}

cd "$LINGUIST_DIR"
git fetch origin
git checkout -B "$BRANCH" origin/main

# 1. Submodule.
if [[ ! -d vendor/grammars/lateralus-grammar ]]; then
  git submodule add https://github.com/bad-antics/lateralus-grammar \
                    vendor/grammars/lateralus-grammar
fi

# 2. languages.yml entry — INSERT alphabetically.
# Lasso < Lateralus < Latte
python3 - <<'PYEOF'
import re
from pathlib import Path

entry = Path(__file__).parent.parent.joinpath(
    "lateralus-lang/docs/linguist/meta/languages-yml-entry.yml"
)
# Script runs in linguist dir; resolve via env.
import os
root = os.environ.get("ROOT_OVERRIDE") or os.path.expanduser(
    "~/lateralus-lang/docs/linguist/meta/languages-yml-entry.yml"
)
entry = Path(root) if Path(root).exists() else entry
text = entry.read_text()
# Strip the leading comment block; keep only the YAML body.
body = "\n".join(l for l in text.splitlines()
                 if not l.lstrip().startswith("#")).strip() + "\n"

langs_path = Path("lib/linguist/languages.yml")
doc = langs_path.read_text()

# Locate "Latte:" top-level entry and insert before it.
m = re.search(r"^Latte:\s*$", doc, flags=re.MULTILINE)
if not m:
    raise SystemExit("could not locate 'Latte:' in languages.yml")
# Ensure we insert at start of that line with a trailing blank line.
insertion = body.rstrip() + "\n\n"
new_doc = doc[:m.start()] + insertion + doc[m.start():]
langs_path.write_text(new_doc)
print("inserted Lateralus entry before Latte:")
PYEOF

# 3. Samples.
mkdir -p samples/Lateralus
cp "$ROOT/docs/linguist/samples/"*.ltl samples/Lateralus/
echo "copied $(ls samples/Lateralus | wc -l) samples"

# 4. Vendor license.
mkdir -p vendor/licenses/grammar
cp vendor/grammars/lateralus-grammar/LICENSE \
   vendor/licenses/grammar/lateralus-grammar.txt

# 5. Regenerate grammars.yml.
if [[ -x script/convert-grammars ]]; then
  script/convert-grammars --add vendor/grammars/lateralus-grammar || true
fi

# 6. Commit.
git add -A
git commit -m "Add Lateralus language support

- Add bad-antics/lateralus-grammar as vendored grammar (MIT)
- Register Lateralus in languages.yml (scope source.ltl, color #FF2A6D)
- Include 20 real-world samples in samples/Lateralus/
- No disambiguation needed: .ltl is currently unclaimed

Upstream: https://github.com/bad-antics/lateralus-lang
Homepage: https://lateralus.dev" || true

echo
echo "branch $BRANCH is ready. next:"
echo "  cd $LINGUIST_DIR"
echo "  bundle exec rake samples"
echo "  bundle exec rspec"
echo "  gh pr create --base main --head $BRANCH \\"
echo "     --title 'Add Lateralus language support' \\"
echo "     --body-file $ROOT/docs/linguist/pr-checklist.md"
