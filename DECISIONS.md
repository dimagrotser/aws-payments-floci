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

## Lambda zips are built for the runtime's platform

The original plan was to keep every Lambda dependency pure Python, so that one zip would
run on the arm64 runtime image Floci pulls on an Apple laptop and on the amd64 one it
pulls in CI. SQLAlchemy ended that in stage 2: it ships compiled extensions, and a build
on macOS quietly produced a zip full of `.so` files ending in `darwin`.

So `scripts/build-lambda.sh` now asks the Docker daemon which architecture it is on and
installs wheels for the matching `manylinux` platform. That is the honest fix, and it
costs six lines.

## Plain dataclasses in the domain, pydantic only at the HTTP edge

Part of the original reasoning was about compiled wheels and no longer applies, see above.
What is left still holds: the domain layer describes what a transaction is and when it is
fraudulent, and that has no business depending on a web framework's validation library.
The API converts at the edge, the handlers import the dataclasses, and the rules can be
unit tested with nothing installed.

## pg8000 rather than psycopg

pg8000 speaks the PostgreSQL protocol in Python and needs no libpq, so the only native
thing in a Lambda zip is SQLAlchemy's optional extensions. psycopg would be faster, and
nothing here is fast enough for that to matter.

## The ECR repository is applied before everything else

A task definition has to name an image that already exists, and an image cannot be pushed
to a registry that does not. So `make deploy` applies the repository on its own first,
pushes, and only then applies the rest. In a real account the registry would usually live
in a separate bootstrap stack for the same reason; a narrow `-target` is the same idea
without a second state file.

The tag is a hash of the files that end up in the image rather than a git revision,
because while you are working the tree is almost always ahead of the last commit, and an
image that does not change when the code does is worse than no tag at all.

## The application and the agent have different roles

The ECS task has two roles: the execution role pulls the image and opens the log stream,
the task role is what the application itself runs as. Splitting them means the code can
never accidentally use a permission that only the agent needs, and a `terraform test`
asserts the two sets of actions do not overlap.

Locally this is a claim about the Terraform rather than about the running system, because
Floci does not vend task-role credentials. That caveat is in the README, not hidden here.

## The database password never enters the state file

`random_password` would put the generated password in state in plain text. Instead an
ephemeral `random_password` feeds the write-only arguments `password_wo` on the instance
and `secret_string_wo` on the secret version, both introduced for exactly this. The value
is written once, to the two places that need it, and `terraform.tfstate` records `null`.

The cost is a version counter: `password_version` has to be bumped to rotate the password,
because write-only arguments are only sent when their version changes. That is also what
keeps the instance and the secret from drifting apart.

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
