#!/usr/bin/env bash
# Em dashes are the tell that gives machine-written text away, so they are banned
# in this repo. Commas, colons, parentheses or a second sentence all work instead.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Built with printf so this script does not trip over its own pattern.
EM_DASH=$(printf '\xe2\x80\x94')

if hits=$(grep -rn --binary-files=without-match "$EM_DASH" \
    --include='*.md' --include='*.py' --include='*.tf' --include='*.ts' \
    --include='*.yml' --include='*.yaml' --include='*.sh' \
    --exclude-dir=.git --exclude-dir=.venv --exclude-dir=node_modules \
    --exclude-dir=.cache --exclude-dir=build --exclude-dir=.terraform .); then
  echo "em dash found:"
  echo "$hits"
  exit 1
fi

echo "prose ok: no em dashes"
