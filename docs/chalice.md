# Chalice
AWS Lambda is an excellent choice for exposing our model in a serverless application. It allows us to deliver our
application much faster while ensuring its scalability, security, performance, and cost-effectiveness with less work
and without having to manage the underlying infrastructure.

To create a serverless application with Lambda, we need to create an API gateway, write Lambda code, and write an IAM
policy to associate with Lambda via an IAM role. This role gives Lambda permissions to access AWS services, such as
SageMaker. However, completing all these steps can be time-consuming. This is where Chalice comes in handy.

##### What is Chalice ?
Chalice is an open source micro-framework for writing serverless applications in Python. It offers a
user-friendly command line interface that simplifies the creation, deployment, and management of your application
on AWS.

For more information about Chalice, visit: https://github.com/aws/chalice.

## Prerequisites
- Python 3.9+ installed
- An AWS account with permissions to create IAM roles/policies, Lambda functions, and API Gateway
- AWS CLI installed and configured
- (Recommended) A virtual environment for Python

## Setup

### 1) Configure AWS credentials
Use the AWS CLI to configure your credentials (typically stored under ~/.aws/credentials and ~/.aws/config):

```shell
aws configure
```
You will be prompted for:
- AWS Access Key ID
- AWS Secret Access Key
- Default region name (for example: eu-west-1)
- Default output format (json, yaml, or text)

More details: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html

### 2) Create an IAM policy and IAM role for Lambda (SageMaker InvokeEndpoint)
If your Lambda needs to call a SageMaker endpoint (InvokeEndpoint), create a dedicated policy and attach it to a role trusted by Lambda.

Steps in the AWS Console:
1. Open Services > IAM.
2. Go to Policies > Create policy.
3. Choose the JSON tab and paste the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:InvokeEndpoint"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

4. Click Review policy, name it sagemaker-lambda-policy, then Create policy.
5. Go to Roles > Create role.
6. Trusted entity: AWS service. Use case: Lambda. Click Next.
7. In Permissions, search and select sagemaker-lambda-policy. Click Next until Review.
8. Name the role sagemaker-lambda-role and Create role.
9. Open the role details and note the Role ARN (you will need it later).

Tip: In production, scope down "Resource" to specific SageMaker endpoint ARNs instead of "*".

### 3) Install Chalice and create a new project (if needed)

```shell
$ python -m pip install chalice 
$ chalice --version 
$ chalice new-project fraud-api 
$ cd fraud-api
```

Run locally to validate the app boots:

```shell
$ chalice local --port 8000
```

Visit http://localhost:8000 to test your routes.

### 4) Configure Chalice to use the IAM role and environment variables
Edit `.chalice/config.json` to reference the IAM role and add any environment variables your app requires 
(e.g., SageMaker solution_prefix, region, stream_name).

```json
{ 
  "version": "2.0",
  "app_name": "fraud-api",
  "stages": {
    "dev": {
      "api_gateway_stage": "api",
      "iam_role_arn": "arn:aws:iam::123456789012:role/sagemaker-lambda-role", 
      "environment_variables": { 
        "solution_prefix": "fraud-detection", 
        "aws_region": "eu-west-1", 
        "stream_name": "your-kinesis-stream-name"
      }
    }
  }
}
```

Notes:
- If you omit iam_role_arn, Chalice can create and manage a role for you (manage_iam_role = true by default). For stricter control, supply iam_role_arn as shown.
- Update the placeholder account ID, role name, and variables to your values.

### 5) Deploy to AWS

```shell
$ chalice deploy
```

This command:
- Packages your code
- Creates/updates the Lambda function and API Gateway
- Prints the deployed REST API URL

If you use a specific AWS profile or region:

```shell
$ AWS_PROFILE=your-profile 
$ AWS_DEFAULT_REGION=eu-west-1 
$ chalice deploy
```

### 6) Test the deployed API
Example with curl (adjust the path to your route, e.g., /predict):

```shell
$ curl -X POST "[https://xxxxxx.execute-api.eu-west-1.amazonaws.com/api/predict](https://xxxxxx.execute-api.eu-west-1.amazonaws.com/api/predict)"
-H "Content-Type: application/json"
-d '{"data":"0.12, 50.3, 1, 0, 3, ..."}'
```

### 7) Update and redeploy
- Modify your application code/routes.
- Redeploy:

```shell
$ chalice deploy
```

### 8) Clean up
To delete the deployed resources created by Chalice:

```shell
$ chalice delete
```

## Troubleshooting
- AccessDenied for SageMaker InvokeEndpoint:
    - Ensure the Lambda execution role has the sagemaker:InvokeEndpoint permission and, ideally, restrict Resource to your endpoint ARN(s).
- Missing AWS credentials:
    - Run aws configure and verify AWS_PROFILE/AWS_DEFAULT_REGION environment variables if needed.
- Environment variables not visible in Lambda:
    - Confirm they are set under the correct stage in .chalice/config.json and redeploy.
- 4xx/5xx from API Gateway:
    - Check CloudWatch Logs for the Lambda function to identify errors.
    - Validate input payload and required headers.
