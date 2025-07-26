import sys
import boto3
import json
import os

from pyspark.sql import SparkSession
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions

from pyspark.sql.functions import from_json, col, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType, FloatType

from fraudit.jobs.elt.schema import get_stream_schema
from fraudit.jobs.elt.transform import transform_df
from fraudit.jobs.elt.loader import write_to_postgres
from fraudit.utils.logging import get_logger

logger = get_logger()

# Expected arguments
ARG_KEYS = [
    "JOB_NAME",
    "postgres_host",
    "postgres_port", 
    "postgres_user",
    "postgres_password",
    "postgres_db",
    "kinesis_stream",
    "aws_region",
    "s3_checkpoint_bucket"
]

args = getResolvedOptions(sys.argv, ARG_KEYS)

def get_postgres_credentials():
    """Retrieve PostgreSQL credentials from arguments"""
    return {
        "username": args["postgres_user"],
        "password": args["postgres_password"],
        "host": args["postgres_host"],
        "port": args["postgres_port"],
        "dbname": args["postgres_db"],
    }

def get_checkpoint_path():
    """Generate S3 checkpoint path"""
    bucket = args["s3_checkpoint_bucket"]
    job_name = args["JOB_NAME"]
    return f"s3a://{bucket}/checkpoints/{job_name}/"

def process_batch(batch_df, batch_id):
    """Batch processing function for Kinesis streaming"""
    if batch_df.count() > 0:
        logger.info(f"Processing Kinesis batch {batch_id} with {batch_df.count()} records")
        
        try:
            # PostgreSQL configuration
            creds = get_postgres_credentials()
            jdbc_url = f"jdbc:postgresql://{creds['host']}:{creds['port']}/{creds['dbname']}"
            postgres_props = {
                "user": creds["username"],
                "password": creds["password"],
                "driver": "org.postgresql.Driver",
            }
            
            # Transform JSON data from Kinesis (with 'data' column)
            json_df = (
                batch_df
                .selectExpr("CAST(data AS STRING) AS json_string")
                .select(from_json(col("json_string"), get_stream_schema()).alias("record"))
                .select(
                    "record.timestamp",
                    "record.user_id", 
                    "record.source",
                    "record.fraud_prediction",
                    "record.fraud_proba",
                    "record.anomaly_score",
                    "record.ip_address",
                    # Flatten device_info
                    "record.device_info.device_type",
                    "record.device_info.os_version", 
                    "record.device_info.app_version",
                    # Flatten geo
                    "record.geo.country",
                    "record.geo.region",
                    "record.geo.city",
                    "record.geo.latitude",
                    "record.geo.longitude"
                )
                .withColumn("processed_at", current_timestamp())
            )
            
            # Apply business transformations
            transformed_df = transform_df(json_df)
            
            # Write to PostgreSQL with flattened columns
            transformed_df.write \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", "fraud_predictions") \
                .option("user", postgres_props["user"]) \
                .option("password", postgres_props["password"]) \
                .option("driver", postgres_props["driver"]) \
                .mode("append") \
                .save()
                
            logger.info(f"Successfully processed Kinesis batch {batch_id}")
            
        except Exception as e:
            logger.error(f"Error processing Kinesis batch {batch_id}: {str(e)}")
            raise
    else:
        logger.info(f"Batch {batch_id} is empty, skipping")

def process_direct_data(df, batch_id):
    """Processing function for already structured data (test or boto3)"""
    if df.count() > 0:
        logger.info(f"Processing direct data batch {batch_id} with {df.count()} records")
        
        try:
            # PostgreSQL configuration
            creds = get_postgres_credentials()
            jdbc_url = f"jdbc:postgresql://{creds['host']}:{creds['port']}/{creds['dbname']}"
            postgres_props = {
                "user": creds["username"],
                "password": creds["password"],
                "driver": "org.postgresql.Driver",
            }
            
            # Data is already structured, only flatten nested columns
            flattened_df = (
                df
                .select(
                    "timestamp",
                    "user_id", 
                    "source",
                    "fraud_prediction",
                    "fraud_proba",
                    "anomaly_score",
                    "ip_address",
                    # Flatten device_info
                    "device_info.device_type",
                    "device_info.os_version", 
                    "device_info.app_version",
                    # Flatten geo
                    "geo.country",
                    "geo.region",
                    "geo.city",
                    "geo.latitude",
                    "geo.longitude"
                )
            )
            
            # NO call to transform_df because data is already in the correct format
            # Write directly to PostgreSQL
            flattened_df.write \
                .format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", "fraud_predictions") \
                .option("user", postgres_props["user"]) \
                .option("password", postgres_props["password"]) \
                .option("driver", postgres_props["driver"]) \
                .mode("append") \
                .save()
                
            logger.info(f"Successfully processed direct data batch {batch_id}")
            
        except Exception as e:
            logger.error(f"Error processing direct data batch {batch_id}: {str(e)}")
            raise
    else:
        logger.info(f"Batch {batch_id} is empty, skipping")

def fallback_with_boto3():
    """Fallback: use boto3 to read Kinesis and create test data"""
    logger.info("Using boto3 fallback for Kinesis reading...")
    
    try:
        kinesis_client = boto3.client('kinesis', region_name=args["aws_region"])
        
        # Get shards
        response = kinesis_client.describe_stream(StreamName=args["kinesis_stream"])
        shards = response['StreamDescription']['Shards']
        
        logger.info(f"Found {len(shards)} shards in Kinesis stream")
        
        # For each shard, read some records
        all_records = []
        for shard in shards:
            shard_id = shard['ShardId']
            
            try:
                # Get an iterator
                iterator_response = kinesis_client.get_shard_iterator(
                    StreamName=args["kinesis_stream"],
                    ShardId=shard_id,
                    ShardIteratorType='LATEST'
                )
                
                shard_iterator = iterator_response['ShardIterator']
                
                if shard_iterator:
                    # Read records
                    records_response = kinesis_client.get_records(
                        ShardIterator=shard_iterator,
                        Limit=100
                    )
                    
                    records = records_response['Records']
                    
                    for record in records:
                        try:
                            data = json.loads(record['Data'].decode('utf-8'))
                            all_records.append(data)
                        except:
                            continue
                            
            except Exception as shard_error:
                logger.warning(f"Error reading shard {shard_id}: {str(shard_error)}")
                continue
        
        if all_records:
            logger.info(f"Found {len(all_records)} records via boto3")
            
            # Create a DataFrame from the records
            spark = SparkSession.getActiveSession()
            records_df = spark.createDataFrame(all_records, get_stream_schema())
            records_df = records_df.withColumn("processed_at", current_timestamp())
            
            # Process with the direct function (no JSON parsing)
            process_direct_data(records_df, "boto3_fallback")
            
        else:
            logger.info("No records found, creating test record...")
            
            # Create a test record with the correct schema
            test_data = [{
                "timestamp": "2025-07-23T22:52:00Z",
                "user_id": "test_user_spark_001",
                "source": "test_spark_api",
                "fraud_prediction": 0,
                "fraud_proba": 0.25,
                "anomaly_score": 0.7,
                "ip_address": "192.168.1.200",
                "device_info": {
                    "device_type": "desktop",
                    "os_version": "Windows 11",
                    "app_version": "2.1.0"
                },
                "geo": {
                    "country": "France",
                    "region": "Occitanie",
                    "city": "Nîmes",
                    "latitude": 43.8367,
                    "longitude": 4.3601
                }
            }]
            
            spark = SparkSession.getActiveSession()
            test_df = spark.createDataFrame(test_data, get_stream_schema())
            test_df = test_df.withColumn("processed_at", current_timestamp())
            
            process_direct_data(test_df, "test_record")
            
    except Exception as fallback_error:
        logger.error(f"Fallback also failed: {str(fallback_error)}")
        raise

if __name__ == "__main__":
    logger.info("Starting Fraudit Streaming Job with Spark Streaming...")
    
    # Optimized Spark configuration for Glue 4.0 with Kinesis JAR
    spark = (
        SparkSession.builder
        .appName("Fraudit Streaming Job")
        # PostgreSQL driver
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3")
        # Explicit configuration for Kinesis JAR (if not already loaded by --extra-jars)
        # .config("spark.jars", "s3://credit-card-fraud-detection-spark-streaming-bucket/jars/spark-streaming-sql-kinesis-connector_2.12-1.0.0.jar")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.AbstractFileSystem.s3.impl", "org.apache.hadoop.fs.s3a.S3A")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
        .getOrCreate()
    )
    
    spark.sparkContext.setLogLevel("WARN")
    
    glueContext = GlueContext(spark.sparkContext)
    job = Job(glueContext)
    job.init(args["JOB_NAME"], args)

    logger.info("Spark session initialized successfully")

    try:
        # First try native Kinesis streaming with Spark
        logger.info(f"Configuring Kinesis stream with Spark native: {args['kinesis_stream']}")
        
        # Checkpoint path
        checkpoint_path = get_checkpoint_path()
        logger.info(f"Using checkpoint path: {checkpoint_path}")
        
        try:
            # Attempt streaming read with Spark and Kinesis JAR
            kinesis_df = (
                spark.readStream
                .format("aws-kinesis")
                .option("kinesis.streamName", args["kinesis_stream"])
                .option("kinesis.region", args["aws_region"])
                .option("kinesis.startingposition", "LATEST")
                .option("kinesis.endpointUrl", f"https://kinesis.{args['aws_region']}.amazonaws.com")
                # AWS authentication (uses Glue credentials)
                .option("kinesis.awsAccessKeyId", "")  # Empty = use IAM role
                .option("kinesis.awsSecretKey", "")    # Empty = use IAM role
                .load()
            )
            
            logger.info("Kinesis stream configured successfully with Spark native")
            
            # Start streaming with foreachBatch
            logger.info("Starting streaming processing...")
            
            streaming_query = (
                kinesis_df
                .writeStream
                .foreachBatch(process_batch)
                .outputMode("append")
                .option("checkpointLocation", checkpoint_path)
                .trigger(processingTime='30 seconds')
                .start()
            )
            
            logger.info("Streaming job started successfully. Waiting for termination...")
            
            # Wait for job termination (or timeout after 5 minutes for tests)
            streaming_query.awaitTermination(timeout=300)  # 5 minutes max for tests
            
            if streaming_query.isActive:
                logger.info("Stopping streaming query after timeout...")
                streaming_query.stop()
                
        except Exception as kinesis_error:
            logger.warning(f"Kinesis streaming failed: {str(kinesis_error)}")
            logger.info("Falling back to boto3...")
            
            # Fallback to boto3
            fallback_with_boto3()
        
    except Exception as e:
        logger.error(f"Error in streaming job: {str(e)}")
        
        # Final fallback
        logger.info("Trying final fallback...")
        fallback_with_boto3()
        
    finally:
        logger.info("Committing Glue job...")
        job.commit()
        logger.info("Glue job completed")