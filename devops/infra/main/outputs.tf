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

##  ==============================

# output "rds_endpoint" {
#   description = "Adresse de la base PostgreSQL"
#   value       = aws_db_instance.fraudit_postgres.address
# }

# output "rds_secret_name" {
#   description = "Nom du secret PostgreSQL"
#   value       = aws_secretsmanager_secret.rds_credentials.name
# }


##  =============================

# output "s3_bucket_name" {
#   description = "Nom du bucket S3 pour les résultats de prédictions"
#   value       = aws_s3_bucket.fraud_predictions_bucket.bucket
# }

# output "glue_database_name" {
#   description = "Nom de la base de données Glue"
#   value       = aws_glue_catalog_database.fraud_db.name
# }

# output "glue_crawler_name" {
#   description = "Nom du crawler Glue pour les fichiers JSON"
#   value       = aws_glue_crawler.fraud_json_crawler.name
# }

# output "firehose_stream_name" {
#   description = "Nom du flux Kinesis Firehose pour les prédictions"
#   value       = aws_kinesis_firehose_delivery_stream.fraud_predictions_stream.name
# }