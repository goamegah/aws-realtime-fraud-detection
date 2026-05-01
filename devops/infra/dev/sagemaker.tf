# SageMaker Notebook (always created)

resource "aws_iam_role" "sagemaker_execution_role" {
  name = "fraudit-sagemaker-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = { Service = "sagemaker.amazonaws.com" },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Policy AWS gérée — couvre tout SageMaker sans surprises
resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# Policy custom — accès à tes buckets S3 spécifiques
resource "aws_iam_role_policy" "sagemaker_s3_policy" {
  name = "fraudit-sagemaker-s3-access"
  role = aws_iam_role.sagemaker_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        Resource = [
          "${aws_s3_bucket.fraud_data_bucket.arn}",
          "${aws_s3_bucket.fraud_data_bucket.arn}/*",
          "${aws_s3_bucket.fraud_streaming_bucket.arn}",
          "${aws_s3_bucket.fraud_streaming_bucket.arn}/*",
          "${aws_s3_bucket.fraud_ml_bucket.arn}",
          "${aws_s3_bucket.fraud_ml_bucket.arn}/*"
        ]
      }
    ]
  })
}

# Lifecycle configuration
resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "fraudit_nb_lifecycle" {
  count = var.sagemaker_lifecycle_startup_content != "" ? 1 : 0
  name  = "fraudit-notebook-lifecycle"

  on_start = base64encode(<<-EOF
    #!/bin/bash
    set -e
    aws s3 sync s3://${aws_s3_bucket.fraud_ml_bucket.bucket}/notebooks/ /home/ec2-user/SageMaker/ --delete 2>/dev/null || true
    chown -R ec2-user:ec2-user /home/ec2-user/SageMaker/
  EOF
  )
}

# Notebook instance
resource "aws_sagemaker_notebook_instance" "fraudit_notebook" {
  name          = var.sagemaker_notebook_name
  instance_type = var.sagemaker_notebook_instance_type
  role_arn      = aws_iam_role.sagemaker_execution_role.arn
  volume_size   = var.sagemaker_root_volume_size

  subnet_id       = var.sagemaker_subnet_id != "" ? var.sagemaker_subnet_id : null
  security_groups = length(var.sagemaker_security_group_ids) > 0 ? var.sagemaker_security_group_ids : null
  lifecycle_config_name = var.sagemaker_lifecycle_startup_content != "" ? aws_sagemaker_notebook_instance_lifecycle_configuration.fraudit_nb_lifecycle[0].name : null

  tags = {
    Project     = "fraud-detection"
    Environment = "dev"
  }
}