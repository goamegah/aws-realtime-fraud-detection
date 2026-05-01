# Makefile — aws-realtime-fraud-detection
# Usage:  make <target>
# Override vars on CLI, e.g.  make tf.apply STAGE=prod

SHELL   := /bin/bash
ROOT    := $(CURDIR)
VENV    := .venv
PY      := $(ROOT)/$(VENV)/bin/python
PIP     := $(ROOT)/$(VENV)/bin/pip
ENV     := .env
STAGE   ?= dev
TF_DIR  := devops/infra/$(STAGE)
TF_VARS := $(TF_DIR)/$(STAGE).tfvars

JAR       := src/resources/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar
JOB       := src/fraudit/glue_job.py
NOTEBOOKS := sagemaker

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show available targets
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z_.%-]+:.*##/{printf "  \033[36m%-22s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)

# ── Setup ─────────────────────────────────────────────────────────────────────
.PHONY: setup
setup: ## Create venv and install all dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .[all]

# ── Infrastructure (Terraform) ────────────────────────────────────────────────
.PHONY: tf.init
tf.init: ## Initialize Terraform (run once)
	cd $(TF_DIR) && terraform init

.PHONY: tf.plan
tf.plan: ## Preview infrastructure changes
	cd $(TF_DIR) && terraform plan -var-file=$(notdir $(TF_VARS))

.PHONY: tf.apply
tf.apply: ## Provision AWS infrastructure
	cd $(TF_DIR) && terraform apply -var-file=$(notdir $(TF_VARS))

.PHONY: tf.destroy
tf.destroy: ## Destroy all AWS infrastructure
	cd $(TF_DIR) && terraform destroy -var-file=$(notdir $(TF_VARS))

# ── Sync .env from Terraform outputs ─────────────────────────────────────────
.PHONY: env.sync
env.sync: ## Sync .env with Terraform outputs (run after tf.apply)
	@cd $(TF_DIR) && \
	SPARK_BUCKET=$$(terraform output -raw spark_streaming_bucket_name) && \
	DATA_BUCKET=$$(terraform output -raw fraud_data_bucket_name) && \
	ML_BUCKET=$$(terraform output -raw fraud_ml_bucket_name) && \
	KINESIS=$$(terraform output -raw kinesis_stream_name) && \
	PG_HOST=$$(terraform output -raw rds_postgres_endpoint) && \
	PG_PORT=$$(terraform output -raw rds_postgres_port) && \
	LAMBDA_ROLE=$$(terraform output -raw lambda_exec_role_arn) && \
	cd - > /dev/null && \
	sed -i "s|^SPARK_STREAMING_BUCKET=.*|SPARK_STREAMING_BUCKET=\"$$SPARK_BUCKET\"|" $(ENV) && \
	sed -i "s|^SPARK_DATA_BUCKET=.*|SPARK_DATA_BUCKET=\"$$DATA_BUCKET\"|" $(ENV) && \
	sed -i "s|^SPARK_ML_BUCKET=.*|SPARK_ML_BUCKET=\"$$ML_BUCKET\"|" $(ENV) && \
	sed -i "s|^KINESIS_STREAM=.*|KINESIS_STREAM=\"$$KINESIS\"|" $(ENV) && \
	sed -i "s|^stream_name=.*|stream_name=\"$$KINESIS\"|" $(ENV) && \
	sed -i "s|^POSTGRES_HOST=.*|POSTGRES_HOST=\"$$PG_HOST\"|" $(ENV) && \
	sed -i "s|^POSTGRES_PORT=.*|POSTGRES_PORT=\"$$PG_PORT\"|" $(ENV) && \
	python3 -c "import json; p='app/api/.chalice/config.json'; c=json.load(open(p)); c['stages']['dev']['iam_role_arn']='$$LAMBDA_ROLE'; open(p,'w').write(json.dumps(c, indent=4))" && \
	echo ".env updated from Terraform outputs." && \
	echo "app/api/.chalice/config.json: iam_role_arn → $$LAMBDA_ROLE"

# ── Chalice (Serverless API) ──────────────────────────────────────────────────
.PHONY: chalice.local
chalice.local: ## Run Chalice API locally on port 8000
	cd app/api && $(ROOT)/$(VENV)/bin/chalice local --port 8000

.PHONY: chalice.deploy
chalice.deploy: ## Deploy Chalice app to AWS Lambda + API Gateway
	cd app/api && $(ROOT)/$(VENV)/bin/chalice deploy --stage $(STAGE)
	@API_URL=$$(python3 -c "import json; d=json.load(open('app/api/.chalice/deployed/$(STAGE).json')); print(next(r['rest_api_url'].rstrip('/') for r in d['resources'] if r['resource_type']=='rest_api'))") && \
	sed -i "s|^CHALICE_API_URL=.*|CHALICE_API_URL=$$API_URL|" $(ENV) && \
	echo ".env: CHALICE_API_URL → $$API_URL"

.PHONY: chalice.delete
chalice.delete: ## Remove Chalice app from AWS
	cd app/api && $(ROOT)/$(VENV)/bin/chalice delete --stage $(STAGE)

# ── Glue artifacts deployment ─────────────────────────────────────────────────
.PHONY: glue.deploy
glue.deploy: ## Build wheel and upload Glue artifacts (wheel + script + JAR) to S3
	@set -a && source $(ENV) && set +a && \
	$(PY) -m build --wheel --outdir dist/ && \
	WHEEL=$$(ls -t dist/*.whl | head -1) && \
	aws s3 cp $$WHEEL  s3://$$SPARK_STREAMING_BUCKET/wheel/ && \
	aws s3 cp $(JOB)   s3://$$SPARK_STREAMING_BUCKET/spark-jobs/ && \
	aws s3 cp $(JAR)   s3://$$SPARK_STREAMING_BUCKET/jars/ && \
	echo "Done — Glue artifacts uploaded to s3://$$SPARK_STREAMING_BUCKET"

# ── SageMaker notebooks ───────────────────────────────────────────────────────
.PHONY: sagemaker.sync
sagemaker.sync: ## Upload notebooks to S3 then restart instance (lifecycle syncs on start)
	@set -a && source $(ENV) && set +a && \
	NB_NAME=$$(cd $(TF_DIR) && terraform output -raw sagemaker_notebook_name) && \
	aws s3 sync $(NOTEBOOKS)/ s3://$$SPARK_ML_BUCKET/notebooks/ --delete && \
	echo "Notebooks uploaded. Restarting $$NB_NAME..." && \
	STATUS=$$(aws sagemaker describe-notebook-instance --notebook-instance-name $$NB_NAME --query NotebookInstanceStatus --output text) && \
	if [ "$$STATUS" = "InService" ]; then \
		aws sagemaker stop-notebook-instance --notebook-instance-name $$NB_NAME && \
		aws sagemaker wait notebook-instance-stopped --notebook-instance-name $$NB_NAME; \
	fi && \
	aws sagemaker start-notebook-instance --notebook-instance-name $$NB_NAME && \
	aws sagemaker wait notebook-instance-in-service --notebook-instance-name $$NB_NAME && \
	echo "Done — $$NB_NAME is ready. Open Jupyter now."

# ── Full deploy (all-in-one) ──────────────────────────────────────────────────
.PHONY: deploy
deploy: tf.apply env.sync chalice.deploy glue.deploy sagemaker.sync ## Provision infra + deploy everything (API + Glue + notebooks)

# ── Local run ─────────────────────────────────────────────────────────────────
.PHONY: run
run: ## Run the streaming pipeline locally
	@set -a && source $(ENV) && set +a && $(PY) -m fraudit.main

.PHONY: data.upload
data.upload: ## Upload local dataset to S3 (required before running SageMaker notebooks)
	@set -a && source $(ENV) && set +a && \
	aws s3 sync dataset/ s3://$$SPARK_DATA_BUCKET/dataset/ && \
	echo "Done — dataset available at s3://$$SPARK_DATA_BUCKET/dataset/"

.PHONY: data.download
data.download: ## Download dataset from S3 to local dataset/
	@set -a && source $(ENV) && set +a && $(PY) scripts/download_data.py

.PHONY: data.generate
data.generate: ## Send simulated transactions to the Chalice API
	@set -a && source $(ENV) && set +a && $(PY) scripts/generate_data.py

# ── Dashboard (Docker) ────────────────────────────────────────────────────────
.PHONY: compose.up
compose.up: ## Start Streamlit dashboard
	docker compose --env-file $(ENV) up -d

.PHONY: compose.down
compose.down: ## Stop dashboard
	docker compose down

# ── Quality & tests ───────────────────────────────────────────────────────────
.PHONY: test
test: ## Run tests
	$(VENV)/bin/pytest -q

.PHONY: lint
lint: ## Run linter
	$(VENV)/bin/pylint src/ scripts/ || true

.PHONY: clean
clean: ## Remove build artifacts and caches
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; true
	@rm -rf dist build .pytest_cache src/*.egg-info

