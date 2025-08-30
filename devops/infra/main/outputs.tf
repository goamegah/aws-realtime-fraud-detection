output "lambda_exec_role_arn" {
    description = "ARN du rôle IAM utilisé par Chalice pour Lambda"
    value       = aws_iam_role.chalice_lambda_exec_role.arn
}

output "kinesis_stream_name" {
    value = aws_kinesis_stream.fraud_predictions_stream.name
}

output "kinesis_stream_arn" {
    value = aws_kinesis_stream.fraud_predictions_stream.arn
}

output "rds_postgres_endpoint" {
    description = "Endpoint (host) de l'instance RDS PostgreSQL"
    value       = aws_db_instance.fraudit_postgres.address
}

output "rds_postgres_port" {
    description = "Port de l'instance RDS PostgreSQL"
    value       = aws_db_instance.fraudit_postgres.port
}

output "spark_streaming_bucket_name" {
    description = "Bucket used to store wheel, jars, and glue job script"
    value = aws_s3_bucket.spark_streaming_bucket.bucket
}

output "fraud_data_bucket" {
    value = aws_s3_bucket.fraud_data_bucket.bucket
    description = "Bucket used to store credit card fraud dataset"
}

##  =============================
# output "s3_bucket_name" {
#   description = "Name of the S3 bucket for prediction results" 
#   value       = aws_s3_bucket.fraud_predictions_bucket.bucket
# }

# output "glue_database_name" {
#   description = "Name of the Glue database"
#   value       = aws_glue_catalog_database.fraud_db.name
# }

# output "glue_crawler_name" {
#   description = "Name of the Glue crawler for JSON files"
#   value       = aws_glue_crawler.fraud_json_crawler.name
# }

# output "firehose_stream_name" {
#   description = "Name of the Kinesis Firehose stream for predictions"
#   value       = aws_kinesis_firehose_delivery_stream.fraud_predictions_stream.name
# }