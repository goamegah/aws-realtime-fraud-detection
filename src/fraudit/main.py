#!/usr/bin/env python3
"""
AWS Glue Streaming Job for Fraud Detection
Processes Kinesis stream data and writes to PostgreSQL

This script can run both in AWS Glue environment and locally:
- In AWS Glue: Uses job parameters and AWS Glue context
- Locally: Uses environment variables and standard SparkSession
"""

import sys
import os
import json
import boto3
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.context import SparkContext

# Import local modules
from fraudit.jobs.elt.schema import get_stream_schema
from fraudit.jobs.elt.transform import transform_df
from fraudit.jobs.elt.loader import write_to_postgres
import fraudit.jobs.elt.config as config
from fraudit.utils.create_database_table import create_table_if_not_exists
from fraudit.utils.logging import get_logger

# Constants for local development
LOCAL_KINESIS_CONNECTOR_PATH = os.getenv("KINESIS_CONNECTOR_PATH", "./resources/spark-sql-kinesis_2.12-1.2.0_spark-3.0.jar")

# Check if running in AWS Glue environment
is_glue_env = 'GLUE_SETUP_PATH' in os.environ

# Initialize appropriate context based on environment
if is_glue_env:
    # AWS Glue environment
    from awsglue.transforms import *
    from awsglue.utils import getResolvedOptions
    from awsglue.context import GlueContext
    from awsglue.job import Job
    
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
else:
    # Local environment
    logger = get_logger()
    
    # Create mock args from environment variables
    args = {
        'JOB_NAME': 'local-fraudit-job',
        'postgres_host': os.getenv('POSTGRES_HOST'),
        'postgres_port': os.getenv('POSTGRES_PORT', '5432'),
        'postgres_user': os.getenv('POSTGRES_USER'),
        'postgres_password': os.getenv('POSTGRES_PASSWORD'),
        'postgres_db': os.getenv('POSTGRES_DB'),
        'kinesis_stream': os.getenv('KINESIS_STREAM'),
        'aws_region': os.getenv('AWS_REGION'),
        's3_checkpoint_bucket': 'local-bucket'
    }

def get_postgres_credentials():
    """
    Fetch PostgreSQL credentials from AWS Secrets Manager or job parameters.
    If SECRET_ID is set in the config, it fetches credentials from AWS Secrets Manager.
    Otherwise, it uses the job parameters passed to the Glue job.
    Returns:
        dict: A dictionary containing PostgreSQL credentials.
    """
    global creds
    if hasattr(config, 'SECRET_ID') and config.SECRET_ID:
        logger.info("Fetching PostgreSQL credentials from AWS Secrets Manager...")
        client = boto3.client('secretsmanager', region_name=args['aws_region'])
        secret = client.get_secret_value(SecretId=config.SECRET_ID)
        creds = json.loads(secret['SecretString'])
    elif is_glue_env:
        creds = {
            "username": args['postgres_user'],
            "password": args['postgres_password'],
            "host": args['postgres_host'],
            "port": args['postgres_port'],
            "dbname": args['postgres_db']
        }
    elif config.POSTGRES_USER and config.POSTGRES_PASSWORD and config.POSTGRES_HOST and config.POSTGRES_PORT and config.POSTGRES_DB:
        creds = {
            "username": config.POSTGRES_USER,
            "password": config.POSTGRES_PASSWORD,
            "host": config.POSTGRES_HOST,
            "port": config.POSTGRES_PORT,
            "dbname": config.POSTGRES_DB
        }
    else:
        logger.error("Missing required environment variables for local development")
        logger.error("Please set these variables in your .env file or environment")
        sys.exit(1)
    return creds

def main():
    # Credentials
    creds = get_postgres_credentials()

    # Create table if it does not exist
    # create_table_if_not_exists(creds)

    jdbc_url = f"jdbc:postgresql://{creds['host']}:{creds['port']}/{creds['dbname']}"
    props = {
        "user": creds['username'],
        "password": creds['password'],
        "driver": "org.postgresql.Driver",
        "stringtype": "unspecified"
    }

    # Initialize or get SparkSession based on environment
    if not is_glue_env:
        logger.info("Initializing local SparkSession with Kinesis connector...")
        
        # For local development, create a new SparkSession
        spark = (
            SparkSession.builder
            .appName("Fraudit Streaming Job")
            .config("spark.jars", LOCAL_KINESIS_CONNECTOR_PATH)
            .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3")
            .master("local[*]")  # Use all available cores
            .getOrCreate()
        )
        
        logger.info(f"Kinesis connector jar loaded from: {LOCAL_KINESIS_CONNECTOR_PATH}")
    else:
        # In Glue environment, spark is already initialized
        logger.info("Using AWS Glue SparkSession")
    
    # Use config.CHECKPOINT_PATH which is already defined in config.py
    checkpoint_path = config.CHECKPOINT_PATH
    
    # Check important variables
    logger.info("=== Configuration ===")
    logger.info(f"AWS_ACCESS_KEY_ID: {'*' * 8}")
    logger.info(f"AWS_SECRET_ACCESS_KEY: {'*' * 8}")
    logger.info(f"KINESIS_STREAM: {config.KINESIS_STREAM}")
    logger.info(f"AWS_REGION: {config.AWS_REGION}")
    logger.info(f"KINESIS_ENDPOINT: {config.KINESIS_ENDPOINT}")
    logger.info(f"PostgreSQL JDBC URL: jdbc:postgresql://{creds['host']}:{creds['port']}/{creds['dbname']}")
    logger.info(f"PostgreSQL Properties: {{'user': '{props['user']}', 'password': '{props["password"]}', 'driver': '{props['driver']}'}}")
    logger.info(f"Checkpoint Path: {checkpoint_path}")
    logger.info("Starting streaming job...")

    # Reading Kinesis stream
    logger.info(f"Reading from Kinesis stream: {config.KINESIS_STREAM}")
    
    # Configure Kinesis stream reader with appropriate options
    kinesis_options = {
        "kinesis.streamName": config.KINESIS_STREAM,
        "kinesis.region": config.AWS_REGION,
        "kinesis.awsAccessKeyId": config.AWS_ID_ACCESS_KEY,
        "kinesis.awsSecretKey": config.AWS_SECRET_ACCESS_KEY,
        "kinesis.startingposition": "LATEST",  # or "TRIM_HORIZON" for all data
        "kinesis.endpointUrl": config.KINESIS_ENDPOINT
    }
    
    # For local development, add additional options if needed
    if not is_glue_env:
        # You can add local-specific options here if needed
        pass
    
    # Create the streaming DataFrame
    raw_df = (
        spark
        .readStream
        .format("aws-kinesis")
        .options(**kinesis_options)
        .load()
    )

    # JSON parsing with structured schema
    logger.info("Parsing JSON data from Kinesis stream...")

    json_df = (
        raw_df
        .selectExpr("CAST(data AS STRING) AS json_string")
        .select(from_json(col("json_string"), get_stream_schema()).alias("record"))
        .select("record.*")
    )

    # Business transformation
    logger.info("Transforming data...")

    transformed_df = transform_df(json_df)

    # Writing to PostgreSQL in streaming mode
    logger.info("Writing transformed data to PostgreSQL...")

    query = write_to_postgres(transformed_df, jdbc_url, props, checkpoint_path=checkpoint_path)
    
    # In local mode, provide more information about the streaming query
    if not is_glue_env:
        logger.info(f"Streaming query started with ID: {query.id}")
        logger.info(f"Streaming query name: {query.name}")
        logger.info("Waiting for query termination...")
    
    # Wait for the query to terminate
    query.awaitTermination()


if __name__ == "__main__":
    try:
        logger.info("Starting Fraudit streaming job...")
        if is_glue_env:
            logger.info("Running in AWS Glue environment")
        else:
            logger.info("Running in local environment")
            
            # Check if required environment variables are set
            required_vars = [
                'POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB',
                'KINESIS_STREAM', 'AWS_REGION', 'AWS_ID_ACCESS_KEY', 'AWS_SECRET_ACCESS_KEY'
            ]
            
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            if missing_vars:
                logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                logger.error("Please set these variables in your .env file or environment")
                sys.exit(1)
                
            # Check if Kinesis connector jar exists
            if not os.path.exists(LOCAL_KINESIS_CONNECTOR_PATH):
                logger.warning(f"Kinesis connector jar not found at: {LOCAL_KINESIS_CONNECTOR_PATH}")
                logger.warning("Please download it or set KINESIS_CONNECTOR_PATH environment variable")
        
        # Run the main function
        main()
    except Exception as e:
        logger.error(f"Error in Fraudit streaming job: {str(e)}", exc_info=True)
        sys.exit(1)
