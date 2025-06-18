output "lambda_exec_role_arn" {
  description = "ARN du rôle IAM utilisé par Chalice pour exécuter les fonctions Lambda"
  value       = aws_iam_role.chalice_lambda_exec_role.arn
}
