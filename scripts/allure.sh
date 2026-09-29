#!/usr/bin/env bash
# Builds one report out of everything under build/allure-results, whichever runner
# produced it. Allure needs a JVM, which is why this runs in a container rather than
# asking you to install one.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

ALLURE_VERSION="2.46.1"
results="build/allure-results"
report="build/allure-report"

if [ ! -d "$results" ]; then
  echo "no results in ${results}; run make test, make integration and make e2e first" >&2
  exit 1
fi

# Carrying the history forward is what turns a report into a trend.
if [ -d "${report}/history" ]; then
  for suite in "$results"/*/; do
    cp -R "${report}/history" "${suite}history"
  done
fi

docker run --rm -v "$PWD:/work" -w /work -e HOME=/tmp \
  eclipse-temurin:21-jre-alpine \
  sh -c "apk add --no-cache nodejs npm >/dev/null \
    && npx --yes allure-commandline@${ALLURE_VERSION} generate --clean \
       -o ${report} $(printf '%s ' "$results"/*/) \
    && chown -R $(id -u):$(id -g) ${report}"

echo "report at ${report}/index.html"
