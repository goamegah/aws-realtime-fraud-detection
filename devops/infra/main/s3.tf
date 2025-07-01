# === S3 Bucket for Fraud Data Storage ===
resource "aws_s3_bucket" "fraud_data_bucket" {
    bucket        = "credit-card-fraud-detection-data-bucket"
    force_destroy = true

    tags = {
        Environment = "dev"
        Project     = "fraud-detection"
    }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_bucket_lifecycle" {
    bucket = aws_s3_bucket.fraud_data_bucket.id

    rule {
        id     = "expire-old-data"
        status = "Enabled"

        filter {
            prefix = ""
        }

        expiration {
            days = 90
        }
    }
}


## === S3 Bucket for Fraud EMR Logs ===
# resource "aws_s3_bucket" "fraud_logs_bucket" {
#   bucket        = "fraud-detection-emr-logs-bucket"
#   force_destroy = true

#   tags = {
#     Project     = "fraud-detection"
#     Environment = "dev"
#   }
# }



# === S3 Bucket for Fraud Predictions ===
# resource "aws_s3_bucket" "fraud_predictions_bucket" {
#     bucket        = "credit-card-fraud-detection-predictions-bucket"
#     force_destroy = true

#     tags = {
#         Environment = "dev"
#         Project     = "fraud-detection"
#     }
# }

# resource "aws_s3_bucket_lifecycle_configuration" "fraud_lifecycle" {
#     bucket = aws_s3_bucket.fraud_predictions_bucket.id

#     rule {
#         id     = "delete-old-objects"
#         status = "Enabled"

#         filter {
#             prefix = ""
#         }

#         expiration {
#             days = 30
#         }
#     }
# }


# === S3 Bucket for athena queries ===
# resource "aws_s3_bucket" "athena_queries_bucket" {
#     bucket        = "credit-card-fraud-detection-athena-queries-bucket"
#     force_destroy = true
#     tags = {
#         Environment = "dev"
#         Project     = "fraud-detection"
#     }
# }
# resource "aws_s3_bucket_lifecycle_configuration" "athena_queries_lifecycle" {
#     bucket = aws_s3_bucket.athena_queries_bucket.id

#     rule {
#         id     = "expire-old-athena-queries"
#         status = "Enabled"

#         filter {
#             prefix = ""
#         }

#         expiration {
#             days = 180
#         }
#     }
# }
