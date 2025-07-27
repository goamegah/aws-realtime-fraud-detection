# fraudit/jobs/elt/schema.py

from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, FloatType

def get_stream_schema():
    """
    Returns the schema for the Kinesis stream JSON data.
    This matches the actual JSON structure from your Kinesis stream.
    """
    return StructType([
        StructField("timestamp", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("source", StringType(), True),
        StructField("fraud_prediction", IntegerType(), True),
        StructField("fraud_proba", FloatType(), True),
        StructField("anomaly_score", FloatType(), True),
        StructField("ip_address", StringType(), True),
        StructField("device_info", StructType([
            StructField("device_type", StringType(), True),
            StructField("os_version", StringType(), True),
            StructField("app_version", StringType(), True)
        ]), True),
        StructField("geo", StructType([
            StructField("country", StringType(), True),
            StructField("region", StringType(), True),
            StructField("city", StringType(), True),
            StructField("latitude", DoubleType(), True),
            StructField("longitude", DoubleType(), True)
        ]), True)
    ])