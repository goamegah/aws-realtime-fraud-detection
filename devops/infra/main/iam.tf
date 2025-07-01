# =================== Rôle Lambda (Chalice) =====================
resource "aws_iam_role" "chalice_lambda_exec_role" {
    name = "ml-inference-api-lambda-exec-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17",
        Statement = [
            {
                Effect = "Allow",
                Principal = { Service = "lambda.amazonaws.com" },
                Action = "sts:AssumeRole"
            }
        ]
    })
}

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
                    "kinesis:PutRecord"
                ],
                Resource = "*"
                # Resource: "${aws_kinesis_stream.fraud_predictions_stream.arn}"
            }
        ]
    })
}

# # ============ Glue IAM Role and Policy  ===========
# data "aws_iam_policy_document" "glue_assume_role_policy_document" {
#     statement {
#         actions = ["sts:AssumeRole"]
#         principals {
#             type        = "Service"
#             identifiers = ["glue.amazonaws.com"]
#         }
#     }
# }
# data "aws_iam_policy_document" "glue_role_policy_document" {
#     statement {
#         sid     = "S3Access"
#         actions = [
#             "s3:GetObject",
#             "s3:PutObject",
#             "s3:ListBucket"
#         ]
#         resources = [
#             "${aws_s3_bucket.fraud_data_bucket.arn}",
#             "${aws_s3_bucket.fraud_data_bucket.arn}/*"
#         ]
#         effect = "Allow"
#     }

#     statement {
#         sid     = "KinesisAccess"
#         actions = [
#             "kinesis:GetRecords",
#             "kinesis:GetShardIterator",
#             "kinesis:DescribeStream",
#             "kinesis:ListStreams"
#         ]
#         resources = [
#             aws_kinesis_stream.fraud_predictions_stream.arn
#         ]
#         effect = "Allow"
#     }

#     statement {
#         sid     = "SecretsManagerAccess"
#         actions = [
#             "secretsmanager:GetSecretValue"
#         ]
#         resources = [
#             aws_secretsmanager_secret.rds_credentials.arn
#         ]
#         effect = "Allow"
#     }

#     statement {
#         sid     = "CloudWatchAndLogs"
#         actions = [
#             "logs:CreateLogGroup",
#             "logs:CreateLogStream",
#             "logs:PutLogEvents",
#             "cloudwatch:PutMetricData"
#         ]
#         resources = ["*"]
#         effect = "Allow"
#     }
# }
# resource "aws_iam_policy" "glue_policy" {
#     name   = "glue_policy"
#     path   = "/"
#     policy = data.aws_iam_policy_document.glue_role_policy_document.json
# }
# resource "aws_iam_role" "glue-role" {
#     name               = "glue_role"
#     assume_role_policy = data.aws_iam_policy_document.glue_assume_role_policy_document.json
# }
# resource "aws_iam_role_policy_attachment" "glue_policy_attachment" {
#     role       = aws_iam_role.glue-role.name
#     policy_arn = aws_iam_policy.glue_policy.arn
# }