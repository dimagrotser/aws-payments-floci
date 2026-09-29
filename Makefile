# Every tool that would otherwise need installing runs in a pinned container.
# What you need locally: Docker. (uv and Node arrive with the test stages.)
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

COMPOSE := docker compose
TF := ./scripts/tf.sh
AWS_ENV := AWS_ENDPOINT_URL=http://localhost:4566 AWS_ACCESS_KEY_ID=test \
	AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
OUTPUT = uv run python -c "import json,sys;print(json.load(open('build/outputs.json'))[sys.argv[1]]['value'])"

.PHONY: help up build deploy migrate destroy down clean logs test integration e2e tf prose

help: ## Show available targets
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

up: ## Start Floci and wait until it is healthy
	$(COMPOSE) up -d
	@printf 'waiting for floci'
	@for i in $$(seq 1 60); do \
		[ "$$($(COMPOSE) ps floci --format '{{.Health}}')" = "healthy" ] && { echo " ok"; exit 0; }; \
		printf '.'; sleep 1; \
	done; echo " timed out"; $(COMPOSE) logs --tail=40 floci; exit 1

down: ## Stop Floci and everything it started
	@# Floci starts RDS/Lambda/ECS/ECR containers itself and compose knows nothing about
	@# them; they have to go first, or they keep the network alive.
	@leftovers=$$(docker ps -aq --filter 'name=floci-'); \
	if [ -n "$$leftovers" ]; then docker rm -f $$leftovers >/dev/null; echo "removed $$(echo $$leftovers | wc -w | tr -d ' ') floci-managed containers"; fi
	$(COMPOSE) down -v --remove-orphans
	@# The ECR registry and the database keep their data in volumes of their own, which
	@# is how a repository survives a restart and greets the next deploy with
	@# RepositoryAlreadyExists.
	@volumes=$$(docker volume ls -q --filter 'name=floci-'); \
	if [ -n "$$volumes" ]; then docker volume rm $$volumes >/dev/null; echo "removed $$(echo $$volumes | wc -w | tr -d ' ') floci-managed volumes"; fi

build: ## Lay out the Lambda packages
	./scripts/build-lambda.sh processor
	./scripts/build-lambda.sh reporter

deploy: build ## Apply the Terraform stack, push the API image, migrate the database
	$(TF) init -input=false
	@# The registry has to exist before there is anything to push to it, and the task
	@# definition has to name an image that is already there. Hence the narrow first apply.
	$(TF) apply -auto-approve -input=false -target=module.api.aws_ecr_repository.this
	@repository=$$($(TF) output -raw api_repository_url) && \
		tag=$$($(AWS_ENV) ./scripts/push-api-image.sh $$repository) && \
		echo "pushed $$repository:$$tag" && \
		TF_VAR_api_image_tag=$$tag $(TF) apply -auto-approve -input=false
	@mkdir -p build && $(TF) output -json > build/outputs.json
	@$(MAKE) --no-print-directory migrate
	@echo "stack deployed; outputs in build/outputs.json"

# Alembic runs from the host, which is why it overrides the hostname: Floci advertises
# the database under a name only containers can resolve, but publishes its port.
migrate: ## Apply database migrations
	@DB_SECRET_ARN=$$($(OUTPUT) db_secret_arn) DB_HOST=localhost $(AWS_ENV) \
		uv run alembic upgrade head

destroy: ## Remove everything Terraform created
	$(TF) destroy -auto-approve -input=false

test: ## Run the unit tests
	uv run pytest tests/unit

integration: ## Run the tests that talk to Floci (needs make deploy first)
	@$(AWS_ENV) uv run pytest tests/integration

e2e: ## Run the Playwright tests against the deployed API
	cd tests/e2e && npm ci --no-audit --no-fund && npx playwright test

clean: down ## Also drop local state and caches
	rm -rf terraform/.terraform terraform/*.tfstate* terraform/*.tfplan .cache build

logs: ## Tail Floci logs
	$(COMPOSE) logs -f floci

prose: ## Check docs and comments for em dashes
	./scripts/check-prose.sh

tf: ## Run terraform with ARGS, e.g. make tf ARGS="plan"
	$(TF) $(ARGS)
