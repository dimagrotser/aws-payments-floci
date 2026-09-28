# Every tool that would otherwise need installing runs in a pinned container.
# What you need locally: Docker. (uv and Node arrive with the test stages.)
.DEFAULT_GOAL := help
SHELL := /usr/bin/env bash

COMPOSE := docker compose
TF := ./scripts/tf.sh

.PHONY: help up down clean logs tf

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
	$(COMPOSE) down -v --remove-orphans
	@# Floci starts RDS/Lambda/ECS/ECR containers itself; compose does not know about them.
	@leftovers=$$(docker ps -aq --filter 'name=floci-'); \
	if [ -n "$$leftovers" ]; then docker rm -f $$leftovers >/dev/null; echo "removed $$(echo $$leftovers | wc -w | tr -d ' ') floci-managed containers"; fi

clean: down ## Also drop local state and caches
	rm -rf terraform/.terraform terraform/*.tfstate* terraform/*.tfplan .cache build

logs: ## Tail Floci logs
	$(COMPOSE) logs -f floci

tf: ## Run terraform with ARGS, e.g. make tf ARGS="plan"
	$(TF) $(ARGS)
