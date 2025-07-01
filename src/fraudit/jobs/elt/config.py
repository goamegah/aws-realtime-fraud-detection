
# fraudit/jobs/elt/config.py
import os
from dotenv import load_dotenv

load_dotenv()

KINESIS_STREAM = os.environ.get("KINESIS_STREAM")
AWS_REGION = os.environ.get("AWS_REGION")
SECRET_ID = os.environ.get("SECRETS_MANAGER_ID")  # Optionnel, utilisé en prod
KINESIS_ENDPOINT = f"https://kinesis.{AWS_REGION}.amazonaws.com"


AWS_ID_ACCESS_KEY = os.environ.get("AWS_ID_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# Local fallback for PostgreSQL
POSTGRES_USER = os.environ.get("POSTGRES_USER")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB")

CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", "/tmp/fraudit-checkpoint")
