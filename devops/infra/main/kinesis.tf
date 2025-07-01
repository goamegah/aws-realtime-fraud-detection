resource "aws_kinesis_stream" "fraud_predictions_stream" {
    name             = "fraud-predictions-stream"
    shard_count      = 1
    retention_period = 24 # in hours
    tags = {
        Environment = "dev"
        Project     = "fraud-detection"
    }
}