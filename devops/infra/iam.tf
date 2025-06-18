provider "aws" {
  region = "eu-west-1"
}

# 1. Lambda execution role (Chalice uses it behind the scenes)
resource "aws_iam_role" "chalice_lambda_exec_role" {
  name = "ml-inference-api-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect = "Allow",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Action = "sts:AssumeRole"
    }]
  })
}

# 2. Inline policy for Lambda execution
resource "aws_iam_role_policy" "lambda_permissions" {
  name = "ml-inference-api-lambda-policy"
  role = aws_iam_role.chalice_lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:*",
          "sagemaker:InvokeEndpoint",
          "firehose:PutRecord"
        ],
        Resource = "*"
      }
    ]
  })
}

# 3. Policy allowing GetRole + PassRole for the user running 'chalice deploy'
resource "aws_iam_policy" "chalice_deploy_permissions" {
  name = "ChaliceDeployPermissions"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "AllowIAMAccessForChalice",
        Effect = "Allow",
        Action = [
          "iam:GetRole",
          "iam:PassRole"
        ],
        Resource = "*"
      },
      {
        Sid    = "AllowLambdaManagement",
        Effect = "Allow",
        Action = [
          "lambda:*",
          "apigateway:*",
          "cloudformation:*",
          "s3:*",
          "logs:*"
        ],
        Resource = "*"
      }
    ]
  })
}

# 4. Attach the policy to your user
resource "aws_iam_user_policy_attachment" "attach_policy_to_user" {
  user       = "chalice_user"  # replace with your actual IAM username
  policy_arn = aws_iam_policy.chalice_deploy_permissions.arn
}