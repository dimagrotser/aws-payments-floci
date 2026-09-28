#!/usr/bin/env bash
# Lays out what goes into a Lambda zip; terraform's archive_file does the zipping.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

name="${1:?usage: build-lambda.sh <function-name>}"
out="build/lambda/${name}"
python_version="3.13"

# Floci pulls the runtime image matching the Docker daemon's architecture, and SQLAlchemy
# ships compiled extensions, so the wheels have to be picked for that platform rather than
# for the laptop running this script.
case "$(docker version --format '{{.Server.Arch}}')" in
  arm64) platform="aarch64-manylinux2014" ;;
  amd64) platform="x86_64-manylinux2014" ;;
  *) echo "unsupported docker architecture" >&2; exit 1 ;;
esac

rm -rf "$out"
mkdir -p "$out"

cp -R src/payments "$out/payments"
# The API subpackage would drag FastAPI into every zip, and migrations only ever run from
# the host or from CI, never from a handler.
rm -rf "$out/payments/api" "$out/payments/db/migrations"
find "$out" -name '__pycache__' -type d -prune -exec rm -rf {} +

requirements="build/lambda/requirements.txt"
uv export --frozen --no-hashes --no-emit-project --only-group lambda -o "$requirements" --quiet

if grep -qvE '^\s*(#|$)' "$requirements"; then
  uv pip install --quiet --target "$out" -r "$requirements" \
    --python-version "$python_version" --python-platform "$platform" --only-binary=:all:
else
  echo "no third-party dependencies for ${name}"
fi

echo "built ${out} for ${platform} ($(du -sh "$out" | cut -f1))"
