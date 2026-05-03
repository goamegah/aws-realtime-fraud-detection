# Infrastructure (Terraform) — AWS Realtime Fraud Detection

An excellent way to allocate cloud resources in AWS is to use infrastructure as code. That's where Terraform comes in.

##### What is Terraform?
Terraform is an infrastructure as code tool that lets you build, change, and version **Cloud** infrastructure safely 
and efficiently. Learn more about [Terraform](https://developer.hashicorp.com/terraform).

This folder contains a minimal Terraform configuration to deploy the main AWS building blocks used by this project.

Deployed resources (demo/dev mode):
- Kinesis Data Streams: ingestion stream for API predictions.
- IAM:
  - Role/policies for Lambda (Chalice) to write to Kinesis and invoke SageMaker Runtime.
  - Role/policies for Glue (access to S3/Kinesis/Logs).
- S3: buckets to store Spark/Glue artifacts (scripts, wheel, jars) and datasets (demo mode).
- RDS PostgreSQL: managed Postgres instance (open for dev, restrict in production).
- (Optional, commented): Secrets Manager to publish Postgres credentials.

Important (security and name collisions):
- S3 bucket names are global. Change values in s3.tf (or introduce a suffix) before apply.
- The RDS security group allows 0.0.0.0/0 (dev only). Restrict to the proper CIDR/VPC in production.

## Prerequisites
- Terraform >= 1.5
- AWS Provider >= v5 (managed in providers.tf)
- AWS credentials configured (AWS_PROFILE, AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY, etc.)

## Quick start
```bash
# From the repo root
make tf.init
make tf.plan       # uses devops/infra/dev/dev.tfvars
make tf.apply
make env.sync      # propagate outputs into .env
```

Or directly with Terraform:
```bash
cd devops/infra/dev
terraform init
terraform apply -var-file=dev.tfvars
```

## Main variables (variables.tf):
- aws_region: AWS region (default eu-west-1)
- kinesis_stream_name: Kinesis stream name (default fraud-predictions-stream)
- kinesis_shard_count: number of shards (default 4)
- postgres_user, postgres_password, postgres_db, postgres_port: RDS parameters
- SageMaker options:
  - sagemaker_notebook_name (default fraudit-notebook)
  - sagemaker_notebook_instance_type (default ml.t3.medium)
  - sagemaker_root_volume_size (default 20)
  - sagemaker_subnet_id (optional)
  - sagemaker_security_group_ids (optional)
  - sagemaker_lifecycle_startup_content (optional bash script)

Example dev.tfvars:
```hcl
aws_region            = "eu-west-1"
kinesis_stream_name   = "fraud-predictions-stream"
kinesis_shard_count   = 4
postgres_user         = "postgres_user"
postgres_password     = "postgres_password"
postgres_db           = "fraudit_postgres_db"
postgres_port         = 5432
```

## Useful outputs (after apply)
Note:
- kinesis_stream_name, kinesis_stream_arn
- rds_postgres_endpoint, rds_postgres_port
- lambda_exec_role_arn

## Mapping to the application (.env)
- Chalice API (Lambda):
  - stream_name = <output.kinesis_stream_name>
  - solution_prefix = fraud-detection (convention)
  - aws_region = <var.aws_region>
- Local streaming / Glue:
  - KINESIS_STREAM = <output.kinesis_stream_name>
  - AWS_REGION = <var.aws_region>
  - POSTGRES_HOST = <output.rds_postgres_endpoint>
  - POSTGRES_PORT = <output.rds_postgres_port>
  - POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD = your values

## Glue artifacts (uploaded to S3)
The Glue job (`glue.tf`) references S3 locations:
- Glue script: `s3://<spark_streaming_bucket>/spark-jobs/glue_job.py`
- Project wheel: `s3://<spark_streaming_bucket>/wheel/fraudit-0.0.1-py3-none-any.whl`
- Kinesis connector JAR: `s3://<spark_streaming_bucket>/jars/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar`

All three are built and uploaded by:

```bash
make glue.deploy
```

This target builds the wheel and runs `aws s3 cp` for the wheel, the Glue script (`src/fraudit/glue_job.py`) and the Kinesis connector JAR (`src/resources/...jar`).

## SageMaker notebooks
Notebooks in `sagemaker/` are synced to `s3://<spark_ml_bucket>/notebooks/` and the notebook instance is restarted with:

```bash
make sagemaker.sync
```

## Cleanup
```bash
make tf.destroy
# or
cd devops/infra/dev && terraform destroy -var-file=dev.tfvars
```

## Notes
- The Secrets Manager module (secrets.tf) is commented out by default. Uncomment and apply if you want to manage Postgres credentials via AWS Secrets Manager, then reference the ARN/name in your application configuration.
- IAM: policies are simplified for the demo; restrict resources (specific ARNs) in production.

