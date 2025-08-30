# Real-time Fraud Detection on AWS

Detecting potential fraud in financial systems is a major challenge for organizations worldwide. Building robust 
solutions that enable real-time actions is essential for companies aiming to provide greater security to their 
customers during financial transactions.

This repository demonstrates a complete machine learning pipeline for credit card fraud detection using the 
[Kaggle Credit Card Fraud Detection dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud), which contains 
284,807 European cardholder transactions from 2013 (including 492 fraudulent cases) with 28 PCA-transformed features 
plus original Amount and Time variables. 

The project showcases a production-ready streaming architecture that integrates Amazon SageMaker for training 
both supervised and unsupervised ML models and deploying them as managed endpoints. The complete AWS solution includes:


- Training of supervised and unsupervised ML models and deployment to a managed-endpoint using Amazon SageMaker
- REST API deployment via Chalice (Lambda + API Gateway)
- Streaming data pipeline (Kinesis → Spark/Glue → RDS)
- (Optional) Interactive dashboard for real-time fraud monitoring and analysis.

Architecture overview:

![Architecture](./assets/flowtrack-e2e-serverless-aws.png)

Useful links:
- Our detailed [architecture documentation](docs/architecture.md)
- AWS Chalice [documentation](https://chalice.readthedocs.io/en/latest/)

## Project structure

```
aws-realtime-fraud-detection/
├── app/                 
│   ├── chalice/                  # Serverless API (Chalice)
│   └── streamlit/                # Dashboard (Streamlit)
├── assets/                       # Images, diagrams
├── devops/infra/                 # Infrastructure-as-Code (Terraform, etc.)
├── docs/                         # Documentation
├── scripts/                      # Data generation (client simulator)
├── src/fraudit/                  # Streaming pipeline & utilities
│   ├── jobs/elt/                 # Schema, transformations, loading
│   └── utils/                    # PostgreSQL DDL, logging, etc.
├── dataset/                      # Local datasets (e.g., creditcard.csv)
├── docker-compose.yml            # Launching the dashboard (optional)
└── pyproject.toml                # Package configuration (single source of truth)
```

## Prerequisites
- Python 3.10
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) and configure it with your [AWS credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html).
- [Terraform](https://learn.hashicorp.com/tutorials/terraform/install-cli)
- Docker (optional)

## Developer setup
### AWS Resource Provisioning
- A Terraform stack is provided in `devops/infra/main` to create AWS building blocks (Kinesis, IAM Lambda/Glue, S3, RDS, optional Secrets).
- Detailed usage guide: [terraform guide](docs/terraform.md)
```shell
$ cd devops/infra/main
$ terraform init
$ terraform plan 
$ terraform apply
```

- Map outputs to your `.env`:
  - stream_name / KINESIS_STREAM = output.kinesis_stream_name
  - POSTGRES_HOST = output.rds_postgres_endpoint
  - POSTGRES_PORT = output.rds_postgres_port
  - aws_region = var.aws_region
  
### Set up virtual environment
Install the package in development mode with the necessary extras.

- All-in-one (recommended for a complete local setup):
```bash
$ python -m pip install -e .[all]
```
- Chalice API only:
```bash
$ python -m pip install -e .[chalice]
```
- Data generation scripts only:
```bash
$ python -m pip install -e .[scripts]
```

### AWS SageMaker
Sagemaker is used to train and deploy the ML models. The training and deployment notebooks are located in the 
`sagemaker/` folder.

### Inference API (Chalice)
- Route: POST /predict

#### Setup
1. Setup Chalice configuration file: `app/chalice/.chalice/config.json`

```json
{
    "version": "2.0",
    "app_name": "ml-inference-api",
    "stages": {
        "dev": {
            "api_gateway_stage": "api",
            "manage_iam_role": false,
            "iam_role_arn": "<terraform_lambda_exec_role_arn_output>",
            "environment_variables": {
                "solution_prefix": "fraud-detection",
                "stream_name": "fraud-predictions-stream",
                "aws_region": "eu-west-1"
            }
        }
    }
}
```
2. (Optional) Test Chalice deployment locally

```shell
$ chalice local --port 8000 # Optional -> urls: http://localhost:8000/
```

3. Deploy Chalice app to **AWS Lambda**
```bash
$ cd app/chalice
$ chalice deploy
```

#### Minimal example
- JSON input (minimal example):
```json
{
  "metadata": {
    "timestamp": "2025-08-21T17:45:00Z",
    "user_id": "u_123",
    "source": "checkout",
    "device_info": {"device_type": "mobile", "os_version": "iOS 17", "app_version": "2.4.1"},
    "ip_address": "203.0.113.10",
    "geo": {"country": "fr", "region": "IDF", "city": "Paris", "latitude": 48.85, "longitude": 2.35}
  },
  "data": "0.12, 50.3, 1, 0, 3, ..."
}
```
- Output (excerpt):
```json
{
  "anomaly_detector": {"score": 0.02},
  "fraud_classifier": {"pred_proba": 0.13, "prediction": 0}
}
```

### Environment variables
Create a `.env` file at the repo root (do not commit secrets).
**Tip**: use a `.env.example` without secrets in the repo and keep your .env locally.

### Spark Streaming job
#### Glue Job Deployment

1. Install the build package

```shell
$ python3 -m pip install build
```

2. Package the project (wheel)

```shell
$ python3 -m build
```
This will result in a wheel file `fraudit-0.0.1-py3-none-any.whl` in the `dist/` directory.

2. Deploy the **job**, **wheel** and **Kinesis connector for Spark** to their respective **AWS S3** for Glue 

    **Tip:** See devops/infra/main/glue.tf `--additional-python-modules` and `--extra-jars` **Terraform options** 
   for more details.
    - Download the Kinesis connector **JAR** for Spark: https://github.com/awslabs/spark-sql-kinesis-connector
    - Upload the **wheel**, **job** and **Kinesis connector** to S3:

```shell
$ aws s3 cp dist/fraudit-0.0.1-py3-none-any.whl s3://credit-card-fraud-detection-spark-streaming-bucket/wheel/fraudit-0.0.1-py3-none-any.whl
$ aws s3 cp src/fraudit/glue_job.py s3://credit-card-fraud-detection-spark-streaming-bucket/spark-jobs/
$ aws s3 cp src/resources/spark-streaming-sql-kinesis-connector_2.12-1.0.0 s3://credit-card-fraud-detection-spark-streaming-bucket/jars/spark-streaming-sql-kinesis-connector_2.12-1.0.0
```

4. Once the artifacts are uploaded, you can start the Glue job from the console, ensuring the default arguments defined 
in `glue.tf` are set.

#### Local Job Running
1. Download and setup Apache Spark locally. To do so, refer to the [spark installation guide](docs/spark.md).
2. Make sure environment variables are set in `.env`.
    - Download the Kinesis connector **JAR** for Spark: https://github.com/awslabs/spark-sql-kinesis-connector
    - Place the JAR and/or set KINESIS_CONNECTOR_PATH to: `src/resources/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar`
3. Run the job

```bash
$ python fraudit.main
```
The job reads the Kinesis stream (KINESIS_STREAM), transforms the data (src/fraudit/jobs/elt/transform.py), and 
appends into the fraud_predictions table.

## Simulated data generation
Prerequisites: .env with CHALICE_API_URL and dataset/creditcard.csv present.

```bash
$ python -m pip install -e .[scripts]
$ python scripts/generate_data.py
```
- PARALLEL_INVOCATION in scripts/generate_data.py allows sending in parallel.
- Adjust max_requests according to desired throughput.

## Dashboard (Streamlit)
- Via Docker:
```bash
$ docker compose up dashboard
```
- Or locally:
```bash
$ cd streamlit
$ pip install -r requirements.txt
$ streamlit run app.py
```
Ensure POSTGRES_HOST/DB/USER/PASSWORD/PORT are configured.


## Clean up
- Destroy the infrastructure:
```shell
$ cd devops/infra/main && terraform destroy
```
- Delete the Chalice API:
```shell
$ cd app/chalice && chalice delete

```

## Troubleshooting
- Error "Missing required environment variables" when starting locally: check your .env (see variables above).
- Kinesis connector not found: set KINESIS_CONNECTOR_PATH to the JAR.
- API 4xx/5xx during generation: check CHALICE_API_URL and quotas; reduce PARALLEL_INVOCATION.
- Do not commit secrets in .env.

## License
Educational/demo project. Adapt before production use.