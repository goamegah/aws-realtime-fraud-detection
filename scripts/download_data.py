import os
import zipfile
import boto3
from dotenv import load_dotenv
from fraudit.definition import DATASET_LOCAL_DIR

# Load environment variables from .env file
load_dotenv()

CONTINUE_SIMULATION = False

if __name__ == "__main__":
    # Example usage of DATASET_DIR
    print(f"Dataset directory is set to: {DATASET_LOCAL_DIR}")

    # Configure environment variables
    aws_region = os.environ.get('AWS_REGION')
    aws_access_key = os.getenv("AWS_ID_ACCESS_KEY")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_bucket = os.getenv("SOLUTIONS_S3_BUCKET")
    s3_prefix = os.getenv("SOLUTION_NAME")

    print(f"aws_region: {aws_region}")
    print(f"aws_access_key: {aws_access_key}")
    print(f"aws_secret_key: {aws_secret_key}")
    print(f"s3_bucket: {s3_bucket}")
    print(f"s3_prefix: {s3_prefix}")

    os.makedirs(DATASET_LOCAL_DIR, exist_ok=True)

    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    # Download file from S3
    s3_key = f"{s3_prefix}/dataset/creditcard.csv.zip"
    local_zip_path = f"{DATASET_LOCAL_DIR}/creditcard.csv.zip"

    print("Downloading...")
    s3_client.download_file(s3_bucket, s3_key, local_zip_path)
    print(f"Download complete: {local_zip_path}")

    # Unzip file to DATASET_PATH
    print("Extracting...")
    with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
        zip_ref.extractall(DATASET_LOCAL_DIR)
    print(f"Files extracted to directory '{DATASET_LOCAL_DIR}'.")

    # (Optional) Remove zip file
    os.remove(local_zip_path)
