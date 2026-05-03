<div align="center">

# Real-time Credit Card Fraud Detection on AWS

End-to-end, production-style streaming pipeline that scores card transactions
in real time on AWS — from data ingestion to model serving and live dashboard.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC?logo=terraform&logoColor=white)](https://www.terraform.io/)
[![Spark](https://img.shields.io/badge/Apache%20Spark-Streaming-E25A1C?logo=apachespark&logoColor=white)](https://spark.apache.org/)
[![SageMaker](https://img.shields.io/badge/Amazon-SageMaker-2E73B7?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/sagemaker/)
[![Chalice](https://img.shields.io/badge/Framework-Chalice-232F3E?logo=amazon-aws&logoColor=white)](https://aws.github.io/chalice/)

</div>

---

## Overview

Detecting fraudulent transactions in real time is a critical challenge for
financial institutions. This repository implements a complete, reproducible
machine-learning pipeline that ingests card transactions, scores them in
**near real time** with two complementary models, persists predictions for
analytics, and visualises them in an interactive dashboard.

The dataset used is the public
[Kaggle Credit Card Fraud Detection dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
— 284,807 transactions from European cardholders (2013), 492 of which are
fraudulent, with 28 PCA-anonymised features plus `Amount` and `Time`.

### Key features

- **Real-time scoring** — Kinesis → Spark Structured Streaming → RDS
- **Two-model ensemble** — Random Cut Forest (anomaly) + XGBoost (classifier), trained on Amazon SageMaker
- **Serverless API** — REST endpoint exposed via AWS Lambda + API Gateway (Chalice)
- **Live dashboard** — Streamlit app for monitoring fraud in real time
- **Full IaC** — every AWS resource declared in Terraform
- **One-command workflow** — orchestrated through a single `Makefile`

---

## Architecture

![Architecture](./assets/flowtrack-e2e-serverless-aws.png)

**Flow:**

1. A simulator (or upstream system) sends transactions to the **Chalice REST
   API** (`POST /predict`).
2. Lambda invokes two **SageMaker endpoints** (RCF anomaly detector + XGBoost
   classifier) and writes the enriched record to a **Kinesis Data Stream**.
3. An **AWS Glue / Spark Structured Streaming** job consumes the stream,
   transforms records and appends them to **PostgreSQL on RDS**.
4. A **Streamlit dashboard** queries RDS to display predictions live.

Further reading: [docs/architecture.md](docs/architecture.md) · [docs/spark.md](docs/spark.md) · [docs/glue.md](docs/glue.md) · [docs/terraform.md](docs/terraform.md) · [docs/chalice.md](docs/chalice.md)

---

## Project structure

```
aws-realtime-fraud-detection/
├── app/
│   ├── api/                 # Chalice serverless API (Lambda + API Gateway)
│   └── streamlit/           # Streamlit real-time dashboard
├── assets/                  # Diagrams & images
├── dataset/                 # Local data (gitignored — pulled from Kaggle)
├── devops/infra/dev/        # Terraform stack (S3, RDS, Glue, Kinesis, IAM…)
├── docs/                    # Detailed documentation
├── sagemaker/               # Training & deployment notebooks
├── scripts/                 # Data download / generation utilities
├── src/fraudit/             # Streaming pipeline package (Glue / local Spark)
│   ├── jobs/elt/            # Schema, transforms, loaders
│   ├── utils/               # DDL helpers, logging, Spark utilities
│   ├── glue_job.py          # Entry point used by AWS Glue
│   └── main.py              # Local run entry point
├── tests/
├── docker-compose.yml       # Local Streamlit stack
├── Makefile                 # One-command workflow
└── pyproject.toml           # Single source of truth for the package
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| [Python](https://www.python.org/) | 3.10+ | Runtime |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | latest | Configured with `aws configure` |
| [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli) | ≥ 1.5 | Provision AWS resources |
| [Docker](https://docs.docker.com/get-docker/) | latest | Run dashboard locally (optional) |
| [Kaggle account](https://www.kaggle.com/settings) | — | API token at `~/.kaggle/kaggle.json` for dataset download |

---

## Quick start

```bash
# 1. Create the virtual env and install everything
make setup

# 2. Configure AWS credentials
aws configure

# 3. Provision infrastructure on AWS
make tf.init
make tf.plan
make tf.apply

# 4. Sync the .env file with Terraform outputs (buckets, RDS, Kinesis…)
make env.sync

# 5. Get the dataset locally and push it to S3
make data.download   # Kaggle → ./dataset/creditcard.csv
make data.upload     # ./dataset/ → s3://$SPARK_DATA_BUCKET/dataset/

# 6. Train & deploy SageMaker endpoints
make sagemaker.sync  # uploads notebooks; open Jupyter to run them

# 7. Deploy the inference API (Chalice → Lambda + API Gateway)
make chalice.deploy

# 8. Build the Spark wheel and upload Glue artifacts
make glue.deploy

# 9. Start the dashboard
make compose.up      # http://localhost:8501
```

> **All-in-one shortcut**: once Terraform variables and Chalice config are set, `make deploy` chains `tf.apply → env.sync → chalice.deploy → glue.deploy → sagemaker.sync`.

---

## Makefile reference

Run `make help` to list all targets. Most useful ones:

| Target | Description |
|--------|-------------|
| `make setup` | Create `.venv` and install the package + extras |
| `make tf.init` / `tf.plan` / `tf.apply` / `tf.destroy` | Manage AWS infra |
| `make env.sync` | Refresh `.env` (and Chalice `iam_role_arn`) from TF outputs |
| `make data.download` | Pull `creditcard.csv` from Kaggle into `dataset/` |
| `make data.upload` | Sync `dataset/` to `s3://$SPARK_DATA_BUCKET/dataset/` |
| `make data.generate` | Replay transactions against the Chalice API |
| `make sagemaker.sync` | Upload notebooks to S3 and restart the SageMaker instance |
| `make chalice.local` | Run the inference API on `http://localhost:8000` |
| `make chalice.deploy` / `chalice.delete` | Deploy / remove Lambda + API Gateway |
| `make glue.deploy` | Build wheel and upload Glue artifacts (wheel + script + JAR) |
| `make run` | Run the streaming pipeline locally (`fraudit.main`) |
| `make compose.up` / `compose.down` | Start / stop the Streamlit dashboard |
| `make test` / `lint` / `clean` | Quality & housekeeping |

---

## Environment variables

`make env.sync` populates `.env` automatically after Terraform applies. Keep
secrets out of git — the file is gitignored.

| Variable | Description |
|----------|-------------|
| `AWS_REGION` | AWS region (e.g. `eu-west-1`) |
| `SPARK_STREAMING_BUCKET` | S3 bucket for the Glue job artifacts |
| `SPARK_DATA_BUCKET` | S3 bucket for the raw dataset |
| `SPARK_ML_BUCKET` | S3 bucket for SageMaker notebooks & models |
| `SOLUTION_NAME` | Project prefix (e.g. `fraud-detection`) |
| `CHALICE_API_URL` | Endpoint of the deployed inference API |
| `KINESIS_STREAM` | Kinesis Data Stream name |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | RDS PostgreSQL connection |
| `KAGGLE_USERNAME` / `KAGGLE_KEY` | (optional) alternative to `~/.kaggle/kaggle.json` |

---

## Machine learning (SageMaker)

Two complementary models are trained from the notebooks under
[`sagemaker/`](sagemaker/):

- **Random Cut Forest** — unsupervised anomaly detector that returns an
  `anomaly_score` for every transaction.
- **XGBoost classifier** — supervised binary fraud classifier returning
  `pred_proba` and `prediction`.

Workflow:

1. `make data.upload` — pushes the dataset to `s3://$SPARK_DATA_BUCKET/dataset/`.
2. `make sagemaker.sync` — uploads the notebooks and (re)starts the SageMaker
   notebook instance; a lifecycle hook syncs them on boot.
3. Open Jupyter, run the training notebooks, deploy the endpoints. Their names
   are referenced by the Chalice API.

---

## Inference API (Chalice)

- **Route**: `POST /predict`
- **Local**: `make chalice.local` → `http://localhost:8000/predict`
- **Deploy**: `make chalice.deploy` (writes the new URL back into `.env`)

### Request

```json
{
  "metadata": {
    "timestamp": "2026-05-02T17:45:00Z",
    "user_id": "u_123",
    "source": "checkout",
    "device_info": {"device_type": "mobile", "os_version": "iOS 17", "app_version": "2.4.1"},
    "ip_address": "203.0.113.10",
    "geo": {"country": "fr", "region": "IDF", "city": "Paris", "latitude": 48.85, "longitude": 2.35}
  },
  "data": "0.12, 50.3, 1, 0, 3, ..."
}
```

### Response

```json
{
  "anomaly_detector": {"score": 0.02},
  "fraud_classifier": {"pred_proba": 0.13, "prediction": 0}
}
```

---

## Streaming pipeline (Glue / Spark)

The `fraudit` package implements a Spark Structured Streaming job that:

1. Reads the **Kinesis Data Stream** populated by the Lambda function.
2. Applies the schema and transforms in
   [`src/fraudit/jobs/elt/`](src/fraudit/jobs/elt/).
3. Appends enriched records into the `fraud_predictions` table on **RDS
   PostgreSQL**.

### Deploy on AWS Glue

```bash
make glue.deploy
```

This builds the wheel and uploads it together with the job script and the
[Kinesis connector JAR](https://github.com/awslabs/spark-sql-kinesis-connector)
to `s3://$SPARK_STREAMING_BUCKET/`. Glue defaults
(`--additional-python-modules`, `--extra-jars`) are wired in
[`devops/infra/dev/glue.tf`](devops/infra/dev/glue.tf).

### Run locally

```bash
make run     # equivalent to: python -m fraudit.main
```

Make sure `.env` is populated and the Kinesis connector JAR sits at
`src/resources/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar`. See
[docs/spark.md](docs/spark.md) for installation details.

---

## Simulated traffic

```bash
make data.generate
```

Replays transactions from `dataset/creditcard.csv` against
`$CHALICE_API_URL`. Tunables in [`scripts/generate_data.py`](scripts/generate_data.py):

- `PARALLEL_INVOCATION` — toggle parallel HTTP calls
- `max_requests` — total throughput

---

## Dashboard (Streamlit)

```bash
make compose.up      # Docker
# or, locally
cd app/streamlit && pip install -r requirements.txt && streamlit run app.py
```

Reads from RDS using `POSTGRES_*` variables and renders predictions live.

---

## Testing & quality

```bash
make test    # pytest
make lint    # pylint (non-blocking)
```

---

## Clean up

```bash
make chalice.delete   # remove the Lambda + API Gateway
make tf.destroy       # tear down all AWS resources
make clean            # remove build artifacts & caches locally
```

---

## Troubleshooting

| Symptom | Hint |
|---------|------|
| `ModuleNotFoundError: fraudit` | Run `make setup` (or `pip install -e .`) inside the venv |
| `aws: error: argument command: Invalid choice` | Make sure you are using AWS CLI v2 |
| Kaggle 403 / 401 on `make data.download` | Place a valid `~/.kaggle/kaggle.json` (chmod 600) or set `KAGGLE_USERNAME` / `KAGGLE_KEY` in `.env` |
| Kinesis connector not found | Set `KINESIS_CONNECTOR_PATH` to the JAR path |
| API 4xx/5xx during traffic generation | Check `CHALICE_API_URL`, lower `PARALLEL_INVOCATION` |
| Large file rejected by GitHub | `dataset/creditcard.csv` is gitignored — never commit it |

---

## Roadmap

- [ ] CI/CD with GitHub Actions (lint, test, Terraform plan)
- [ ] Model registry & automatic endpoint promotion
- [ ] Drift / performance monitoring (CloudWatch + SageMaker Model Monitor)
- [ ] Pre-commit hooks (ruff, black, terraform fmt)

---

## Contributing

Issues and pull requests are welcome. Please run `make test` and `make lint`
before opening a PR.

---

## License

Educational / demo project. Review and harden before any production use.

---

<div align="center">
Maintained by <a href="https://github.com/goamegah">@goamegah</a>
</div>
