# fraudit/main.py

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
import boto3
import json
from dotenv import load_dotenv

from fraudit.definition import KINESIS_CONNECTOR_PATH, CHECKPOINT_PATH
from fraudit.jobs.elt.schema import get_stream_schema
from fraudit.jobs.elt.transform import transform_df
from fraudit.jobs.elt.loader import write_to_postgres
import fraudit.jobs.elt.config as config
from fraudit.utils.db_utils import create_table_if_not_exists

# Charger .env localement
load_dotenv()


def get_postgres_credentials():
    """
    Récupère les credentials PostgreSQL depuis Secrets Manager si SECRET_ID défini,
    sinon fallback sur les variables d'environnement locales.
    """
    if config.SECRET_ID:
        print(" -> Fetching PostgreSQL credentials from AWS Secrets Manager...")
        client = boto3.client('secretsmanager', region_name=config.AWS_REGION)
        secret = client.get_secret_value(SecretId=config.SECRET_ID)
        creds = json.loads(secret['SecretString'])
    else:
        creds = {
            "username": config.POSTGRES_USER,
            "password": config.POSTGRES_PASSWORD,
            "host": config.POSTGRES_HOST,
            "port": config.POSTGRES_PORT,
            "dbname": config.POSTGRES_DB
        }
    return creds


def main():
    # Credentials
    creds = get_postgres_credentials()

    # Create table if it does not exist
    create_table_if_not_exists(creds)

    jdbc_url = f"jdbc:postgresql://{creds['host']}:{creds['port']}/{creds['dbname']}"
    props = {
        "user": creds['username'],
        "password": creds['password'],
        "driver": "org.postgresql.Driver"
    }

    # SparkSession with Kinesis connector
    print("-> Initializing SparkSession with Kinesis connector...")

    spark = (
        SparkSession.builder
        .appName("Fraudit Streaming Job")
        .config("spark.jars", KINESIS_CONNECTOR_PATH)
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3")
        .getOrCreate()
    )

    print(f"-> Kinesis connector jar loaded from: {KINESIS_CONNECTOR_PATH}")

    # Check important variables
    print("=== Configuration ===:")
    print("AWS_ACCESS_KEY_ID:", config.AWS_ID_ACCESS_KEY)
    print("AWS_SECRET_ACCESS_KEY:", config.AWS_SECRET_ACCESS_KEY)
    print("KINESIS_STREAM:", config.KINESIS_STREAM)
    print("AWS_REGION:", config.AWS_REGION)
    print("KINESIS_ENDPOINT:", config.KINESIS_ENDPOINT)
    print("PostgreSQL JDBC URL:", jdbc_url)
    print("PostgreSQL Properties:", props)
    print("Checkpoint Path:", CHECKPOINT_PATH)
    print("\n... Démarrage du job de streaming...\n")

    # reading Kinesis stream
    raw_df = (
        spark
        .readStream
        .format("aws-kinesis")
        .option("kinesis.streamName", config.KINESIS_STREAM)
        .option("kinesis.region", config.AWS_REGION)
        .option("kinesis.awsAccessKeyId", config.AWS_ID_ACCESS_KEY)
        .option("kinesis.awsSecretKey", config.AWS_SECRET_ACCESS_KEY)
        .option("kinesis.startingposition", "LATEST")
        .option("kinesis.endpointUrl", config.KINESIS_ENDPOINT)
        .load()
    )

    # JSON parsing with structured schema
    print("-> Parsing JSON data from Kinesis stream...")

    json_df = (
        raw_df
        .selectExpr("CAST(data AS STRING) AS json_string")
        .select(from_json(col("json_string"), get_stream_schema()).alias("record"))
        .select("record.*")
    )

    # Business transformation
    print("-> Transforming data...")

    transformed_df = transform_df(json_df)

    # Writing to PostgreSQL in streaming mode
    print("-> Writing transformed data to PostgreSQL...")

    query = write_to_postgres(transformed_df, jdbc_url, props, checkpoint_path=CHECKPOINT_PATH)
    query.awaitTermination()


if __name__ == "__main__":
    main()