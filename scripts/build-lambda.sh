#!/usr/bin/env bash
# Lays out what goes into a Lambda zip; terraform's archive_file does the zipping.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

name="${1:?usage: build-lambda.sh <function-name>}"
out="build/lambda/${name}"

rm -rf "$out"
mkdir -p "$out"

cp -R src/payments "$out/payments"
# The API subpackage would drag FastAPI, and a compiled dependency, into every zip.
rm -rf "$out/payments/api"
find "$out" -name '__pycache__' -type d -prune -exec rm -rf {} +

requirements="build/lambda/requirements.txt"
uv export --frozen --no-hashes --no-emit-project --only-group lambda -o "$requirements" --quiet

if grep -qvE '^\s*(#|$)' "$requirements"; then
  uv pip install --quiet --target "$out" -r "$requirements"
else
  echo "no third-party dependencies for ${name}"
fi

echo "built ${out} ($(du -sh "$out" | cut -f1))"
