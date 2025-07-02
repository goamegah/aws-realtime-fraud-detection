# scripts/create_database_table.py

import psycopg2
from psycopg2 import sql

def create_table_if_not_exists(creds):
    """
    Creates the fraud_predictions table if it does not already exist.

    Params:
        creds (dict): Dictionary with keys 'host', 'port', 'dbname', 'username', 'password'
    """
    conn = psycopg2.connect(
        host=creds['host'],
        port=creds['port'],
        dbname=creds['dbname'],
        user=creds['username'],
        password=creds['password']
    )
    cur = conn.cursor()

    ddl = """
    CREATE TABLE IF NOT EXISTS fraud_predictions (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        user_id TEXT NOT NULL,
        source TEXT,
        fraud_prediction INTEGER NOT NULL,
        fraud_proba REAL,
        anomaly_score REAL,
        ip_address TEXT,
        device_type TEXT,
        os_version TEXT,
        app_version TEXT,
        country TEXT,
        region TEXT,
        city TEXT,
        latitude DOUBLE PRECISION,
        longitude DOUBLE PRECISION,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    cur.execute(ddl)
    conn.commit()
    cur.close()
    conn.close()
    print("Table fraud_predictions created or already exists.")


if __name__ == "__main__":
    # debug section to run this script directly
    import os
    from dotenv import load_dotenv

    load_dotenv()

    creds = {
        "host": os.getenv("POSTGRES_HOST"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB"),
        "username": os.getenv("POSTGRES_USER"),
        "password": os.getenv("POSTGRES_PASSWORD")
    }
    create_table_if_not_exists(creds)
