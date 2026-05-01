resource "aws_kinesis_stream" "fraud_predictions_stream" {
    name             = var.kinesis_stream_name
    shard_count      = var.kinesis_shard_count
    retention_period = 24 # in hours
    tags = {
        Environment = "dev"
        Project     = "fraud-detection"
    }
}