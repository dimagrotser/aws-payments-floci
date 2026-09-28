#!/usr/bin/env bash
# Terraform in a pinned container, on the compose network, so that the Floci endpoint
# is the same string here, in the Lambda containers and in the ECS task.
set -euo pipefail

TERRAFORM_VERSION="1.16.4"
NETWORK="${COMPOSE_PROJECT_NAME:-payments}_default"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_DIR="${REPO_ROOT}/.cache/terraform"

mkdir -p "${CACHE_DIR}/plugins"

# Anything the caller set as TF_VAR_* has to survive the trip into the container.
tf_vars=()
while IFS='=' read -r name _; do
  tf_vars+=(-e "$name")
done < <(env | grep '^TF_VAR_' || true)

exec docker run --rm -i \
  ${TF_TTY:+-t} \
  --network "${NETWORK}" \
  --user "$(id -u):$(id -g)" \
  -v "${REPO_ROOT}:/work" \
  -v "${CACHE_DIR}:/tf-cache" \
  -w /work/terraform \
  -e HOME=/tf-cache \
  -e TF_PLUGIN_CACHE_DIR=/tf-cache/plugins \
  -e TF_IN_AUTOMATION=1 \
  -e AWS_ACCESS_KEY_ID=test \
  -e AWS_SECRET_ACCESS_KEY=test \
  -e AWS_DEFAULT_REGION=us-east-1 \
  "${tf_vars[@]+"${tf_vars[@]}"}" \
  "hashicorp/terraform:${TERRAFORM_VERSION}" "$@"
