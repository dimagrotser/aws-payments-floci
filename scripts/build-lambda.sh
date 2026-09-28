#!/usr/bin/env bash
# Lays out a Lambda zip's contents: the payments package plus whatever is in the
# `lambda` dependency group. Terraform's archive_file turns the directory into the zip.
#
# The API subpackage is left out. It pulls in FastAPI, which the handlers never import
# and which would bloat every zip with a compiled dependency.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

name="${1:?usage: build-lambda.sh <function-name>}"
out="build/lambda/${name}"

rm -rf "$out"
mkdir -p "$out"

cp -R src/payments "$out/payments"
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
