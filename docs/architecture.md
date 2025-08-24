# Architecture of the real-time fraud detection platform

This documentation describes the project's reference architecture, the end-to-end data flow, as well as the application and infrastructure components.

- Domain: Real-time fraud detection
- Stack: AWS (Chalice/Lambda, SageMaker, Kinesis, Glue/Spark, PostgreSQL, S3, IAM), Python
- Targets: Local environment (demo) and Cloud (managed AWS)

## Reference architecture

![Architecture](../assets/flowtrack-e2e-serverless-aws.png)

## Main components

- Inference API (Chalice → Lambda)
  - File: `app/chalice/app.py`
  - Route: `POST /predict`
  - Role: receives an event (CSV features in `data` + rich `metadata`), calls two SageMaker endpoints (anomaly detection and fraud classification), and pushes an enriched record into a Kinesis stream.
  - Environment variables (Lambda):
    - `stream_name` (Kinesis)
    - `solution_prefix` (SageMaker endpoint prefix, e.g., `fraud-detection`)
    - `aws_region` (e.g., `eu-west-1`)

- Streaming pipeline (Spark Structured Streaming / AWS Glue)
  - Input: Kinesis Data Streams (JSON)
  - Transformations: normalization, selection & quality control in `src/fraudit/jobs/elt/transform.py`
  - Loading: PostgreSQL in append mode via `src/fraudit/jobs/elt/loader.py`
  - Input schema: defined in `src/fraudit/jobs/elt/schema.py`
  - Orchestration: `src/fraudit/main.py` (function `main()`)
  - Checkpoints: S3 (Glue) or local (`CHECKPOINT_PATH`)

- Database (PostgreSQL)
  - Target table: `fraud_predictions`
  - Creation/DDL: `src/fraudit/utils/create_database_table.py`

- Traffic generator (scripts)
  - Script: `scripts/generate_data.py`
  - Role: simulates requests to the API from a dataset (e.g., `dataset/creditcard.csv`).

- Dashboard (Streamlit)
  - Code: `frontend/`
  - Role: visualization of predictions from PostgreSQL.

- Infrastructure as Code (Terraform)
  - Folder: `devops/infra/main`
  - Role: provision Kinesis, IAM (Lambda/Glue), S3, RDS (PostgreSQL), Secrets (optional). See the guide: `devops/infra/main/README.md`.

## End-to-end data flow

1. The client sends an HTTP POST request to the **Chalice** API `/predict` with:
   - `metadata`: context information (timestamp, user_id, source, device_info, ip, geo…)
   - `data`: features in `text/csv` format (string)
2. The API calls two **SageMaker** endpoints (exposed by `solution_prefix`):
   - Anomaly detector (`{solution_prefix}-rcf-endpoint`) → **anomaly score**
   - Classifier (`{solution_prefix}-xgb-smote-endpoint`) → **probability** and **binary prediction**
3. The API constructs an enriched record and writes it to **Kinesis** (`put_record`).
4. The **Spark/Glue** job consumes the Kinesis stream, parses the JSON, flattens the document (nested metadata), and applies transformations (data quality, type casts, standardization).
5. The transformed data are loaded in append mode into **PostgreSQL** (table `fraud_predictions`).
6. The dashboard reads the table and displays indicators/streams.
7. Kinesis read checkpoints are managed by Spark (S3 in prod, local folder in dev mode).

## Target data model (PostgreSQL)

DDL (excerpt, see `fraudit/utils/create_database_table.py`):

```sql
CREATE TABLE IF NOT EXISTS fraud_predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id TEXT NOT NULL,
    source TEXT,
    fraud_prediction INTEGER NOT NULL,
    fraud_proba REAL,
    anomaly_score REAL,
    ip_address TEXT,
    device_type TEXT,
    os_version TEXT,
    app_version TEXT,
    country TEXT,
    region TEXT,
    city TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

The transformed DataFrame selects and standardizes these columns (see `transform_df`), for example
- cast the `timestamp`,
- standardize the country code (`upper(trim(country))`),
- quality filters (non-null user_id/timestamp/prediction).

## Streaming job details

- Local entry point: `python -m fraudit.main`
- Main configuration:
  - `KINESIS_STREAM`, `AWS_REGION`, `AWS_ID_ACCESS_KEY`, `AWS_SECRET_ACCESS_KEY`
  - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - `CHECKPOINT_PATH` (local) or S3 bucket (Glue side)
- Kinesis connection: connector JAR required (see `src/resources/...jar` and `KINESIS_CONNECTOR_PATH`).
- PostgreSQL write: `.writeStream.foreachBatch(write_batch)` with `mode=append` and `checkpointLocation`.

## Deployments

- Local (demo):
  - Install the package: `python -m pip install -e .[all]`
  - Run the Chalice API locally (optional): `chalice local --port 8000`
  - Start the streaming job: `python -m fraudit.main`
  - Generate data: `python scripts/generate_data.py`

- Managed AWS:
  - Chalice: `chalice deploy` (set `stream_name`, `solution_prefix`, `aws_region`)
  - Glue Streaming: package the code (wheel) and attach it to the Glue job (`--extra-py-files`), configure parameters (PostgreSQL, Kinesis, region, S3 checkpoint)
  - RDS/PostgreSQL: use Terraform to provision and retrieve endpoint/port

## Environment variables (.env)

An exhaustive example is provided in `.env.example`. Copy it to `.env` and fill in your local values. Never commit your secrets.

- API (Lambda/Chalice): `stream_name`, `solution_prefix`, `aws_region`
- Local streaming job: variables `AWS_*`, `KINESIS_STREAM`, `POSTGRES_*`, `CHECKPOINT_PATH`, `KINESIS_CONNECTOR_PATH`
- Scripts: `CHALICE_API_URL`

## Security & compliance

- Do not commit secrets. Use AWS Secrets Manager in production (variable `SECRETS_MANAGER_ID` supported by the job config).
- Grant least-privilege IAM permissions to Lambda/Glue roles.
- Be mindful of Kinesis quotas and costs.

## Observability

- API logs in CloudWatch (Chalice/Lambda).
- Spark/Glue logs and job metrics.
- You can enrich with CloudWatch dashboards, or export metrics to another backend.

## Limitations and future work

- SageMaker models are referenced by name; lifecycle management (train/deploy) is not detailed.
- Event schemas are simplified; plan for a versioned API contract.
- Add a dead-letter queue (DLQ) via Kinesis Firehose/SQS for ingestion errors.
- Add end-to-end integration tests (API → Kinesis → Postgres).

## Quick references

- API code: `app/chalice/app.py`
- Job entry point: `src/fraudit/main.py`
- Schema/Transform/Load: `src/fraudit/jobs/elt/{schema,transform,loader}.py`
- Postgres DDL: `src/fraudit/utils/create_database_table.py`
- IaC: `devops/infra/main` (see dedicated README)
