# fraudit/jobs/elt/transform.py

from pyspark.sql.functions import col

def transform_df(df):
    return df.select(
        col("timestamp").cast("timestamp"),
        col("user_id"),
        col("source"),
        col("fraud_prediction").cast("int"),
        col("fraud_proba").cast("float"),
        col("anomaly_score").cast("float"),
        col("ip_address"),
        col("device_info.device_type").alias("device_type"),
        col("device_info.os_version").alias("os_version"),
        col("device_info.app_version").alias("app_version"),
        col("geo.country").alias("country"),
        col("geo.region").alias("region"),
        col("geo.city").alias("city"),
        col("geo.latitude").cast("double").alias("latitude"),
        col("geo.longitude").cast("double").alias("longitude")
    )
