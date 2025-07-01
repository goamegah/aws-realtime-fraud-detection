# resource "aws_glue_job" "fraudit_streaming_job" {
#     name     = "fraudit-streaming-job"
#     role_arn = aws_iam_role.glue-role.arn

#     command {
#         script_location = "s3://${aws_s3_bucket.fraud_data_bucket.bucket}/spark-jobs/glue_job.py"
#         python_version  = "3"
#     }

#     glue_version      = "4.0"
#     number_of_workers = 2
#     worker_type       = "G.1X" # plus optimisé pour Spark que "Standard"

#     default_arguments = {
#         "--job-language"                     = "python"
#         "--additional-python-modules"        = "s3://${aws_s3_bucket.fraud_data_bucket.bucket}/wheel/fraudit-0.0.1-py3-none-any.whl"
#         "--python-modules-installer-option"  = "--upgrade"

#         # Tes paramètres métiers
#         "--kinesis_stream"                   = aws_kinesis_stream.fraud_predictions_stream.name
#         "--secrets_manager_id"               = aws_secretsmanager_secret.rds_credentials.name
#         "--aws_region"                       = var.aws_region

#         # Logs & monitoring
#         "--enable-continuous-cloudwatch-log" = "true"
#         "--enable-job-insights"              = "true"
#         "--enable-metrics"                   = "true"
#         "--enable-spark-ui"                  = "true"
#     }

#     tags = {
#         Project     = "fraud-detection"
#         Environment = "dev"
#     }
# }