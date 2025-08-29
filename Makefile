# Makefile for aws-realtime-fraud-detection
#
# Usage:
#   make <target>
#
# Philosophy:
# - Provide a single, well-documented entry point for common developer tasks
# - Avoid hidden state: most behavior is driven by variables you can override
# - Keep targets idempotent where practical
#
# Conventions:
# - Documented targets with `##` will appear in `make help`
# - You can override variables on the command line, e.g. `make install EXTRAS=all`
#
# -----------------------------------------------------------------------------
# Configurable variables (override on CLI or env)
# -----------------------------------------------------------------------------
PY ?= python3
PIP ?= $(PY) -m pip
VENV ?= .venv
SHELL := /bin/bash

# Project layout
ROOT_DIR := $(abspath $(CURDIR))
SRC_DIR := src
APP_DIR := app
SCRIPTS_DIR := scripts
DOCS_DIR := docs
TF_DIR ?= devops/infra/main
COMPOSE_FILE ?= docker-compose.yml
ENV_FILE ?= .env
ENV_EXAMPLE ?= .env.example

# Python install extras (defined in pyproject.toml)
# Options: dev, chalice, scripts, all
EXTRAS ?= dev

# Terraform
TF_VARS ?= $(TF_DIR)/dev.tfvars

# Data/generation configuration
MAX_REQUESTS ?= 100000
PARALLEL ?= 0

# Chalice stage
CHALICE_STAGE ?= dev

# Default goal
.DEFAULT_GOAL := help

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
# Activate venv helper (use in recipe lines with `source $(VENV)/bin/activate`)
VENV_BIN := $(VENV)/bin
ACT := source $(VENV_BIN)/activate

# Colors for pretty help
YELLOW := \033[1;33m
GREEN  := \033[1;32m
BLUE   := \033[1;34m
RESET  := \033[0m

# -----------------------------------------------------------------------------
# Meta
# -----------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@echo "$(BLUE)Project: aws-realtime-fraud-detection$(RESET)"
	@echo ""
	@echo "$(GREEN)Available targets:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ { printf "  $(YELLOW)%-28s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort
	@echo ""
	@echo "Examples:" \
	    "\n  make venv install EXTRAS=all" \
	    "\n  make test" \
	    "\n  make run.stream" \
	    "\n  make compose.up" \
	    "\n  make tf.plan TF_VARS=$(TF_VARS)" \
	    "\n  make chalice.deploy CHALICE_STAGE=$(CHALICE_STAGE)" \
	    "\n  make deploy.glue"

# -----------------------------------------------------------------------------
# Environment & dependencies
# -----------------------------------------------------------------------------
.PHONY: venv
venv: ## Create a local Python virtual environment in $(VENV)
	@test -d $(VENV) || ($(PY) -m venv $(VENV); echo "Created $(VENV)")
	@echo "Python: $$($(VENV_BIN)/python --version 2>/dev/null || echo 'activate venv to see version')"

.PHONY: install
install: venv ## Install the project in editable mode with extras (EXTRAS=$(EXTRAS))
	@$(ACT) && $(PIP) install --upgrade pip wheel setuptools
	@$(ACT) && $(PIP) install -e .[$(EXTRAS)]

.PHONY: install.all
install.all: EXTRAS=all
install.all: install ## Install all extras defined in pyproject (full local toolchain)

.PHONY: env
env: ## Create .env from .env.example if missing
	@if [ ! -f "$(ENV_FILE)" ]; then \
	  if [ -f "$(ENV_EXAMPLE)" ]; then cp "$(ENV_EXAMPLE)" "$(ENV_FILE)" && echo ".env created from $(ENV_EXAMPLE)"; \
	  else echo "No $(ENV_EXAMPLE) found."; fi; \
	else echo "$(ENV_FILE) already exists"; fi

# -----------------------------------------------------------------------------
# Code quality & tests
# -----------------------------------------------------------------------------
.PHONY: lint
lint: ## Run pylint on src and scripts (requires extras=dev)
	@$(ACT) && pylint $(SRC_DIR) $(SCRIPTS_DIR) || true

.PHONY: test
test: ## Run tests with pytest (requires extras=dev)
	@$(ACT) && pytest -q

.PHONY: test.cov
test.cov: ## Run tests with coverage report
	@$(ACT) && pytest --cov=fraudit --cov-report=term-missing

# -----------------------------------------------------------------------------
# Build & packaging
# -----------------------------------------------------------------------------
.PHONY: build
build: ## Build wheel into dist/ (installs build if needed)
	@$(ACT) && $(PIP) show build >/dev/null 2>&1 || (echo "Installing build..." && $(ACT) && $(PIP) install build)
	@$(ACT) && $(PY) -m build

.PHONY: clean
clean: ## Remove Python build/test artifacts
	@find . -name "__pycache__" -type d -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info src/*.egg-info

.PHONY: distclean
distclean: clean ## Clean plus remove venv
	@rm -rf $(VENV)

# -----------------------------------------------------------------------------
# Application run (local)
# -----------------------------------------------------------------------------
.PHONY: run.stream
run.stream: ## Run the local Spark/Glue-compatible streaming job (python -m fraudit.main)
	@$(ACT) && set -a && [ -f $(ENV_FILE) ] && source $(ENV_FILE) || true; set +a; \
	$(PY) -m fraudit.main

.PHONY: data.download
data.download: ## Download dataset from S3 using scripts/download_data.py (env must be set)
	@$(ACT) && set -a && [ -f $(ENV_FILE) ] && source $(ENV_FILE) || true; set +a; \
	$(PY) $(SCRIPTS_DIR)/download_data.py

.PHONY: data.generate
data.generate: ## Generate and send simulated transactions via Chalice API (uses scripts/generate_data.py)
	@echo "Note: PARALLEL_INVOCATION is controlled inside the script. MAX_REQUESTS default is 100000."
	@$(ACT) && set -a && [ -f $(ENV_FILE) ] && source $(ENV_FILE) || true; set +a; \
	$(PY) $(SCRIPTS_DIR)/generate_data.py

# -----------------------------------------------------------------------------
# Docker / Compose
# -----------------------------------------------------------------------------
.PHONY: compose.up
compose.up: ## Start services via docker compose (dashboard)
	@docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d

.PHONY: compose.down
compose.down: ## Stop docker compose services
	@docker compose -f $(COMPOSE_FILE) down

.PHONY: compose.logs
compose.logs: ## Tail logs from docker compose services
	@docker compose -f $(COMPOSE_FILE) logs -f --tail=200

# -----------------------------------------------------------------------------
# Terraform (Infrastructure as Code)
# -----------------------------------------------------------------------------
.PHONY: tf.init
tf.init: ## Initialize Terraform in $(TF_DIR)
	@cd $(TF_DIR) && terraform init

.PHONY: tf.plan
tf.plan: ## Terraform plan using TF_VARS=$(TF_VARS)
	@cd $(TF_DIR) && terraform plan -var-file=$(TF_VARS)

.PHONY: tf.apply
tf.apply: ## Terraform apply using TF_VARS=$(TF_VARS)
	@cd $(TF_DIR) && terraform apply -var-file=$(TF_VARS)

.PHONY: tf.destroy
tf.destroy: ## Terraform destroy using TF_VARS=$(TF_VARS)
	@cd $(TF_DIR) && terraform destroy -var-file=$(TF_VARS)

# -----------------------------------------------------------------------------
# Chalice (Serverless API)
# -----------------------------------------------------------------------------
.PHONY: chalice.local
chalice.local: ## Run Chalice locally (port 8000 by default)
	@$(ACT) && $(PIP) show chalice >/dev/null 2>&1 || (echo "Installing chalice..." && $(ACT) && $(PIP) install chalice)
	@cd $(APP_DIR)/chalice && $(VENV_BIN)/chalice local --port 8000

.PHONY: chalice.deploy
chalice.deploy: ## Deploy Chalice app to AWS (stage=$(CHALICE_STAGE))
	@$(ACT) && $(PIP) show chalice >/dev/null 2>&1 || (echo "Installing chalice..." && $(ACT) && $(PIP) install chalice)
	@cd $(APP_DIR)/chalice && $(VENV_BIN)/chalice deploy --stage $(CHALICE_STAGE)

.PHONY: chalice.delete
chalice.delete: ## Delete Chalice app from AWS (stage=$(CHALICE_STAGE))
	@$(ACT) && $(PIP) show chalice >/dev/null 2>&1 || (echo "Installing chalice..." && $(ACT) && $(PIP) install chalice)
	@cd $(APP_DIR)/chalice && $(VENV_BIN)/chalice delete --stage $(CHALICE_STAGE)

# -----------------------------------------------------------------------------
# Glue deployment (S3 uploads for Glue job artifacts)
# -----------------------------------------------------------------------------
.PHONY: deploy.glue
deploy.glue: ## Build wheel and upload Glue artifacts (wheel, job script, kinesis jar) to S3
	@$(ACT) && set -a && [ -f $(ENV_FILE) ] && source $(ENV_FILE) || true; set +a; \
	$(PY) -m devops.deploy.cli deploy --bucket $$SPARK_SOLUTION_S3_BUCKET --region $$AWS_REGION --prefix $$SPARK_SOLUTION_NAME

# -----------------------------------------------------------------------------
# Documentation helpers
# -----------------------------------------------------------------------------
.PHONY: docs.open
docs.open: ## Print path to docs and important guides
	@echo "Docs folder: $(DOCS_DIR)"
	@echo "Spark guide: $(DOCS_DIR)/spark.md"
	@echo "Terraform guide: $(DOCS_DIR)/terraform.md"
	@echo "Chalice guide: $(DOCS_DIR)/chalice.md"

