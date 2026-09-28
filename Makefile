# Every tool that would otherwise need installing runs in a pinned container.
# What you need locally: Docker. (uv and Node arrive with the test stages.)
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

COMPOSE := docker compose
TF := ./scripts/tf.sh

.PHONY: help up build deploy destroy down clean logs test integration tf prose

help: ## Show available targets
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

up: ## Start Floci and wait until it is healthy
	$(COMPOSE) up -d
	@printf 'waiting for floci'
	@for i in $$(seq 1 60); do \
		[ "$$($(COMPOSE) ps floci --format '{{.Health}}')" = "healthy" ] && { echo " ok"; exit 0; }; \
		printf '.'; sleep 1; \
	done; echo " timed out"; $(COMPOSE) logs --tail=40 floci; exit 1

down: ## Stop Floci and the containers it started
	@# Floci starts RDS/Lambda/ECS/ECR containers itself and compose knows nothing about
	@# them; they have to go first, or they keep the network alive.
	@leftovers=$$(docker ps -aq --filter 'name=floci-'); \
	if [ -n "$$leftovers" ]; then docker rm -f $$leftovers >/dev/null; echo "removed $$(echo $$leftovers | wc -w | tr -d ' ') floci-managed containers"; fi
	$(COMPOSE) down -v --remove-orphans

build: ## Lay out the Lambda packages
	./scripts/build-lambda.sh processor

deploy: build ## Apply the Terraform stack to the running Floci
	$(TF) init -input=false
	$(TF) apply -auto-approve -input=false
	@mkdir -p build && $(TF) output -json > build/outputs.json
	@echo "stack deployed; outputs in build/outputs.json"

destroy: ## Remove everything Terraform created
	$(TF) destroy -auto-approve -input=false

test: ## Run the unit tests
	uv run pytest tests/unit

integration: ## Run the tests that talk to Floci (needs make deploy first)
	uv run pytest tests/integration

clean: down ## Also drop local state and caches
	rm -rf terraform/.terraform terraform/*.tfstate* terraform/*.tfplan .cache build

logs: ## Tail Floci logs
	$(COMPOSE) logs -f floci

prose: ## Check docs and comments for em dashes
	./scripts/check-prose.sh

tf: ## Run terraform with ARGS, e.g. make tf ARGS="plan"
	$(TF) $(ARGS)
