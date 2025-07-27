# fraudit/jobs/elt/transform.py

from pyspark.sql.functions import col, when, regexp_replace, upper, trim
from pyspark.sql.types import TimestampType

def transform_df(df):
    """
    Apply business transformations to the fraud detection data.
    
    Args:
        df: Spark DataFrame with flattened columns (not nested)
        
    Returns:
        Transformed Spark DataFrame
    """
    
    # Convert timestamp string to proper timestamp type
    df = df.withColumn("timestamp", col("timestamp").cast(TimestampType()))
    
    # Data quality transformations
    transformed_df = df.select(
        col("timestamp"),
        col("user_id"),
        col("source"),
        col("fraud_prediction"),
        col("fraud_proba"),
        col("anomaly_score"),
        col("ip_address"),
        # Device info columns (already flattened)
        col("device_type"),
        col("os_version"),
        col("app_version"),
        # Geo columns (already flattened)
        upper(trim(col("country"))).alias("country"),  # Standardize country codes
        trim(col("region")).alias("region"),
        trim(col("city")).alias("city"),
        col("latitude"),
        col("longitude"),
        col("processed_at")
    ).where(
        # Basic data quality filters
        col("user_id").isNotNull() & 
        col("timestamp").isNotNull() & 
        col("fraud_prediction").isNotNull()
    )
    
    return transformed_df