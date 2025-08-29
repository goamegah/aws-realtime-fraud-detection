# Glue Deployment Utility

This package provides a small CLI to automate deployment of AWS Glue artifacts to S3:
- Project wheel (.whl)
- Glue job script (src/fraudit/glue_job.py)
- Kinesis connector JAR (Spark SQL Kinesis connector)

It uses .env defaults when available and can be overridden via CLI arguments.

## Installation
This lives inside the repo; no separate install required. Ensure your Python environment has:
- boto3
- python-dotenv

You can use the Makefile target `make install EXTRAS=all` to install all project dependencies.

## Usage
From the repository root:

- Build wheel only:
  python -m devops.deploy.cli build

- Upload artifacts to S3:
  python -m devops.deploy.cli upload --bucket <your-bucket> --region <aws-region>

- Build then upload:
  python -m devops.deploy.cli deploy --bucket <your-bucket> --region <aws-region>

Options:
- --bucket: Target S3 bucket (defaults to SOLUTIONS_S3_BUCKET from .env)
- --prefix: Solution prefix for S3 keys (defaults to SOLUTION_NAME)
- --no-solution-prefix: Do not prepend solution prefix to keys
- --job-path: Local Glue job script (default src/fraudit/glue_job.py)
- --jar-path: Local Kinesis connector JAR (default src/resources/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar)
- --jars-prefix, --jobs-prefix, --wheels-prefix: S3 key prefixes (defaults: jars/, spark-jobs/, wheel/)
- --jar-url: If provided and the Kinesis connector JAR is missing locally, it will be downloaded before upload
- --profile: AWS CLI profile to use

Example using a JAR download URL:
  python -m devops.deploy.cli deploy \
    --bucket my-spark-bucket \
    --region eu-west-1 \
    --jar-url https://github.com/awslabs/spark-sql-kinesis-connector/releases/download/v1.0.0/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar

## Notes
- Boto3 follows the standard credential chain: env vars, profiles, EC2/Glued roles, etc. You can force `--profile`.
- This tool only uploads artifacts to S3. Creating/updating the Glue job is handled by Terraform in `devops/infra/main`, where the `script_location`, `--additional-python-modules`, and `--extra-jars` reference these S3 paths.
- By default, keys are prefixed with your solution name (SPARK_SOLUTION_NAME in .env). Use `--no-solution-prefix` to disable.
