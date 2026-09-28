# Decisions

Short notes on the choices that shaped this repository, so the reasoning does not have to
be reconstructed from the code.

## Floci rather than LocalStack

LocalStack retired its Community edition in March 2026 and now refuses to start without an
auth token tied to an account. A portfolio project that cannot be run by whoever clones it
is not much of a portfolio project. Floci is MIT licensed, needs no account, and takes
`docker compose up`. The cost is maturity: it is a young codebase, its documentation has
gaps, and a few things behave differently from AWS. Rather than hide that, the differences
are measured and written down in the README, and every claim the tests make is checked
against the emulator rather than against the documentation.

## Terraform rather than CDK or CloudFormation

Terraform is what infrastructure roles actually ask for, it reads the same whether or not
you know the language it was generated from, and `terraform test` gives plan-level
assertions without deploying anything. Floci's own documentation ships a Terraform guide,
so the provider configuration is a supported path rather than an experiment.

State lives in a local file. An S3 backend inside Floci would need a bucket that exists
before the stack that creates buckets, and solving that chicken and egg problem would
teach nobody anything.

## ECS for the API, Lambda for everything asynchronous

The API is a long-lived HTTP service with a database connection pool, which is exactly the
shape ECS is for: paying for a container that stays warm buys predictable latency and
connection reuse. Fraud checks and the daily report are short, bursty and event-driven,
which is the shape Lambda is for. Splitting them this way also makes the IAM story
concrete, because the two halves need genuinely different permissions.

## Plain dataclasses in the domain, pydantic only at the HTTP edge

pydantic v2 carries a compiled core. Floci pulls the arm64 Lambda runtime image on an
Apple laptop and the amd64 one in CI, so a zip with a compiled wheel in it would work in
exactly one of those places. Keeping the shared domain on dataclasses means one artifact
runs everywhere. The API still uses pydantic for request validation, because it ships as a
Docker image built for a known platform.

## pg8000 rather than psycopg

Same reason, one layer down: pg8000 is pure Python, so the database code goes into a
Lambda zip unchanged. psycopg would be faster, and nothing here is fast enough for that to
matter.

## One shared Floci rather than testcontainers

`testcontainers-floci` exists, but its only release is 0.1.1 from May 2026 and it has seen
no activity since; the Node version of the same module has an open issue about publishing
several hundred host ports by default. More importantly, Floci starts real Docker
containers for Lambda and RDS, so a fresh emulator per test would trade a few seconds of
cleanup for minutes of waiting. The integration suite uses one emulator from
`docker-compose.yml` and gets isolation from cleanup fixtures and unique identifiers.

## Terraform and the linters run in containers

The promise is that a clone plus Docker is enough. Terraform, tflint, checkov and gitleaks
all run from pinned images through `scripts/tf.sh` and the Makefile, which also means the
versions in CI and the versions on a laptop cannot drift apart. `pytest` and Playwright are
the exceptions: they run locally through uv and npx, because the feedback loop while
writing tests matters more there.

## Python 3.13

The version the Lambda runtime runs, so the tests and the deployed code agree on the
language they are written in.

## Checking least privilege twice

`terraform test` asserts on the actions a role is granted, which are known before anything
is applied, so a wildcard never reaches the emulator. The resources those actions apply to
are only known afterwards, so an integration test asks Floci's IAM simulator about the
deployed role prefix by prefix. Assuming the role from a test is not possible, and
correctly so: its trust policy names `lambda.amazonaws.com` and Floci enforces that.
