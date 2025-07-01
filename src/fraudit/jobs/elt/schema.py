# fraudit/jobs/elt/schema.py

from pyspark.sql.types import *

def get_stream_schema():
    return StructType([
        StructField("timestamp", StringType()),
        StructField("user_id", StringType()),
        StructField("source", StringType()),
        StructField("fraud_prediction", IntegerType()),
        StructField("fraud_proba", FloatType()),
        StructField("anomaly_score", FloatType()),
        StructField("ip_address", StringType()),
        StructField("device_info", StructType([
            StructField("device_type", StringType()),
            StructField("os_version", StringType()),
            StructField("app_version", StringType())
        ])),
        StructField("geo", StructType([
            StructField("country", StringType()),
            StructField("region", StringType()),
            StructField("city", StringType()),
            StructField("latitude", DoubleType()),
            StructField("longitude", DoubleType())
        ]))
    ])
