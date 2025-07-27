#!/usr/bin/env python3

"""
AWS Glue Streaming Job for Fraud Detection
Processes Kinesis stream data and writes to PostgreSQL
"""

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

from pyspark.sql.functions import from_json, col, current_timestamp, upper, trim
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    TimestampType, IntegerType, FloatType
)

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
logger = glueContext.get_logger()

# Get job parameters
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'postgres_host',
    'postgres_port',
    'postgres_user', 
    'postgres_password',
    'postgres_db',
    'kinesis_stream',
    'aws_region',
    's3_checkpoint_bucket'
])

# Initialize Glue job
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

def get_kinesis_schema():
    """Define the schema for Kinesis JSON data"""
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

def transform_data(df):
    """Apply business transformations to the data"""
    return df.select(
        col("timestamp").cast(TimestampType()).alias("timestamp"),
        col("user_id"),
        col("source"),
        col("fraud_prediction"),
        col("fraud_proba"),
        col("anomaly_score"),
        col("ip_address"),
        col("device_type"),
        col("os_version"),
        col("app_version"),
        upper(trim(col("country"))).alias("country"),
        trim(col("region")).alias("region"),
        trim(col("city")).alias("city"),
        col("latitude"),
        col("longitude"),
        # Add processed_at timestamp here instead of expecting it
        current_timestamp().alias("processed_at")
    ).where(
        col("user_id").isNotNull() & 
        col("timestamp").isNotNull() & 
        col("fraud_prediction").isNotNull()
    )

def write_to_postgres(df, batch_id):
    """Write DataFrame to PostgreSQL"""
    if df.count() > 0:
        logger.info(f"Processing batch {batch_id} with {df.count()} records")
        
        # PostgreSQL JDBC URL and properties
        jdbc_url = f"jdbc:postgresql://{args['postgres_host']}:{args['postgres_port']}/{args['postgres_db']}"
        postgres_props = {
            "user": args["postgres_user"],
            "password": args["postgres_password"],
            "driver": "org.postgresql.Driver",
            "stringtype": "unspecified"
        }
        
        # Write to PostgreSQL
        df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "fraud_predictions") \
            .option("user", postgres_props["user"]) \
            .option("password", postgres_props["password"]) \
            .option("driver", postgres_props["driver"]) \
            .option("stringtype", postgres_props["stringtype"]) \
            .mode("append") \
            .save()
            
        logger.info(f"Successfully wrote batch {batch_id} to PostgreSQL")

def process_kinesis_batch(batch_df, batch_id):
    """Process each batch from Kinesis stream"""
    if batch_df.count() > 0:
        logger.info(f"Processing batch {batch_id} with {batch_df.count()} records")
        
        # Parse JSON from Kinesis data field
        parsed_df = (
            batch_df
            .selectExpr("CAST(data AS STRING) AS json_string")
            .select(from_json(col("json_string"), get_kinesis_schema()).alias("record"))
            .select(
                col("record.timestamp").alias("timestamp"),
                col("record.user_id").alias("user_id"),
                col("record.source").alias("source"),
                col("record.fraud_prediction").alias("fraud_prediction"),
                col("record.fraud_proba").alias("fraud_proba"),
                col("record.anomaly_score").alias("anomaly_score"),
                col("record.ip_address").alias("ip_address"),
                # Flatten device_info
                col("record.device_info.device_type").alias("device_type"),
                col("record.device_info.os_version").alias("os_version"),
                col("record.device_info.app_version").alias("app_version"),
                # Flatten geo
                col("record.geo.country").alias("country"),
                col("record.geo.region").alias("region"),
                col("record.geo.city").alias("city"),
                col("record.geo.latitude").alias("latitude"),
                col("record.geo.longitude").alias("longitude")
            )
            #.withColumn("processed_at", current_timestamp())
        )
        
        # Apply transformations
        transformed_df = transform_data(parsed_df)
        
        # Write to PostgreSQL
        write_to_postgres(transformed_df, batch_id)
        
    else:
        logger.info(f"Batch {batch_id} is empty, skipping")

def main():
    """Main execution function"""
    logger.info("Starting Fraud Detection Streaming Job")
    
    # Configure checkpoint location
    checkpoint_location = f"s3a://{args['s3_checkpoint_bucket']}/checkpoints/{args['JOB_NAME']}/"
    logger.info(f"Using checkpoint location: {checkpoint_location}")
    
    # Read from Kinesis stream
    kinesis_df = (
        spark.readStream
        .format("aws-kinesis")
        .option("kinesis.streamName", args["kinesis_stream"])
        .option("kinesis.region", args["aws_region"])
        .option("kinesis.startingposition", "TRIM_HORIZON")  # Start from the latest data
        .option("kinesis.endpointUrl", f"https://kinesis.{args['aws_region']}.amazonaws.com")
        .load()
    )
    
    logger.info("Successfully configured Kinesis stream reader")
    
    # Start streaming query
    query = (
        kinesis_df
        .writeStream
        .foreachBatch(process_kinesis_batch)
        .outputMode("append")
        .option("checkpointLocation", checkpoint_location)
        .trigger(processingTime='30 seconds')
        .start()
    )
    
    logger.info("Streaming query started successfully")
    
    # Wait for termination
    query.awaitTermination()

if __name__ == "__main__":
    main()
    job.commit()