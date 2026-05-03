# AWS Glue streaming job

The streaming pipeline is packaged as a Python wheel (`fraudit`) and run on
AWS Glue with Spark Structured Streaming. Glue consumes the Kinesis stream
written by the Chalice API and appends enriched records to RDS PostgreSQL.

## Artifacts uploaded to S3

`make glue.deploy` builds the wheel and uploads three artifacts to
`s3://$SPARK_STREAMING_BUCKET/`:

| Artifact | S3 path | Source |
|----------|---------|--------|
| Python wheel | `wheel/fraudit-<version>-py3-none-any.whl` | `dist/` (built with `python -m build`) |
| Glue script | `spark-jobs/glue_job.py` | `src/fraudit/glue_job.py` |
| Kinesis connector JAR | `jars/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar` | `src/resources/` |

The connector is the [AWS Labs Spark SQL Kinesis connector](https://github.com/awslabs/spark-sql-kinesis-connector).

## Glue job configuration

The job is declared in [`devops/infra/dev/glue.tf`](../devops/infra/dev/glue.tf).
Key default arguments wired through Terraform:

- `--additional-python-modules` — points to the `fraudit` wheel
- `--extra-jars` — points to the Kinesis connector JAR
- Spark / Glue runtime parameters (worker type, number of workers, timeout)
- Job parameters consumed by `glue_job.py` (Kinesis stream, region, RDS
  connection, S3 checkpoint location)

## Deploy

```bash
# Provision (or refresh) the Glue job + IAM + S3 + Kinesis + RDS
make tf.apply

# Build the wheel and upload all artifacts to S3
make glue.deploy
```

Then start the job from the AWS Glue console (or via `aws glue start-job-run`).

## Run locally

For development you can run the same code locally without Glue:

```bash
make run     # python -m fraudit.main
```

This requires a populated `.env` (Kinesis, AWS, Postgres, checkpoint path) and
the Kinesis connector JAR available at
`src/resources/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar`. See
[spark.md](spark.md) for the local Spark setup.

## Code layout

| Path | Purpose |
|------|---------|
| `src/fraudit/glue_job.py` | Glue entry point (parses Glue args, calls `main`) |
| `src/fraudit/main.py` | Local entry point (reads `.env`, calls `main`) |
| `src/fraudit/jobs/elt/schema.py` | Kinesis JSON schema |
| `src/fraudit/jobs/elt/transform.py` | Parsing, flattening, quality filters |
| `src/fraudit/jobs/elt/loader.py` | `foreachBatch` writer to PostgreSQL |
| `src/fraudit/utils/create_database_table.py` | DDL for `fraud_predictions` |

## Troubleshooting

- **Connector not found** — verify `--extra-jars` in the Glue job parameters
  and that the JAR is present at `s3://$SPARK_STREAMING_BUCKET/jars/`.
- **Wheel not picked up** — check `--additional-python-modules` points to the
  exact wheel path and that the version matches the latest build.
- **PostgreSQL write failures** — confirm the Glue security group can reach
  RDS and that `POSTGRES_*` parameters are correct (synced via
  `make env.sync`).
- **Checkpoint conflicts** — clear the S3 checkpoint prefix when changing the
  output schema or stream offsets.
