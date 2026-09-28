#!/usr/bin/env bash
# Builds the API image and pushes it to Floci's ECR. Prints the tag it used, which the
# Makefile passes to terraform so a code change produces a new task definition.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

repository="${1:?usage: push-api-image.sh <repository-url>}"

# Tag by content rather than by git revision: the image has to change when the working
# tree changes, and most of the time the working tree is ahead of the last commit.
tag=$(find src/payments services/api pyproject.toml uv.lock -type f \
  -not -path '*/__pycache__/*' -print0 | sort -z | xargs -0 shasum | shasum | cut -c1-12)

docker build --quiet -f services/api/Dockerfile -t "${repository}:${tag}" . >/dev/null

aws ecr get-login-password | docker login --username AWS --password-stdin "${repository%%/*}" >/dev/null 2>&1
docker push --quiet "${repository}:${tag}" >/dev/null

echo "$tag"
