# resource "aws_secretsmanager_secret" "rds_credentials" {
#     name        = "fraudit-postgres-credentials-"
#     description = "Credentials PostgreSQL pour Glue"
# }

# resource "aws_secretsmanager_secret_version" "rds_credentials_version" {
#     secret_id = aws_secretsmanager_secret.rds_credentials.id

#     secret_string = jsonencode({
#         username = var.postgres_user
#         password = var.postgres_password
#         host     = aws_db_instance.fraudit_postgres.address
#         port     = var.postgres_port
#         dbname   = var.postgres_db
#     })
# }
