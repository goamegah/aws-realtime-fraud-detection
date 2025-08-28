resource "aws_glue_job" "fraudit_streaming_job" {
    name     = "fraudit-streaming-job"
    role_arn = aws_iam_role.glue-role.arn
    # Job entrypoint
    command {
        script_location = "s3://${aws_s3_bucket.spark_streaming_bucket.bucket}/spark-jobs/glue_job.py"
        python_version  = "3"
    }

    glue_version = "4.0"
    max_capacity = 2

    default_arguments = {
        "--job-language"                     = "python"
        # Reference to spark jobs packaged(wheel) located in s3
        "--additional-python-modules"        = "s3://${aws_s3_bucket.spark_streaming_bucket.bucket}/wheel/fraudit-0.0.1-py3-none-any.whl"
        "--python-modules-installer-option"  = "--upgrade"
        # reference to spark kinesis connector located in S3
        "--extra-jars"                       = "s3://${aws_s3_bucket.spark_streaming_bucket.bucket}/jars/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar"

        # PostgreSQL variables
        "--postgres_host"                    = aws_db_instance.fraudit_postgres.address
        "--postgres_port"                    = aws_db_instance.fraudit_postgres.port
        "--postgres_user"                    = var.postgres_user
        "--postgres_password"                = var.postgres_password
        "--postgres_db"                      = var.postgres_db

        # Kinesis
        "--kinesis_stream"                   = aws_kinesis_stream.fraud_predictions_stream.name
        "--kinesis_endpoint"                 = "https://kinesis.${var.aws_region}.amazonaws.com"
        "--aws_region"                       = var.aws_region

        # Checkpoint S3 - use this bucket for spark structured streaming checkpointing
        "--s3_checkpoint_bucket"             = aws_s3_bucket.spark_streaming_bucket.bucket

        # Monitoring
        "--enable-continuous-cloudwatch-log" = "true"
        "--enable-job-insights"              = "true"
        "--enable-metrics"                   = "true"
        "--enable-spark-ui"                  = "true"
        "--enable-auto-scaling"              = "true"
    }

    tags = {
        Project     = "fraud-detection"
        Environment = "dev"
    }
}