import os
from threading import Thread
import pandas as pd
import numpy as np
import zipfile
from sklearn.model_selection import train_test_split
import boto3
from dotenv import load_dotenv
from definition import DATASET_LOCAL_DIR
from utils import generate_data

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

CONTINUE_SIMULATION = False

if __name__ == "__main__":
    # Example usage of DATASET_DIR
    print(f"Dataset directory is set to: {DATASET_LOCAL_DIR}")

    # Configuration des variables d'environnement
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

    # Initialisation du client S3
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        region_name=aws_region
    )

    # Download file from S3
    s3_key = f"{s3_prefix}/dataset/creditcard.csv.zip"
    local_zip_path = f"{DATASET_LOCAL_DIR}/creditcard.csv.zip"

    print("Téléchargement en cours...")
    s3_client.download_file(s3_bucket, s3_key, local_zip_path)
    print(f"Téléchargement terminé : {local_zip_path}")

    # Unzip file to DATASET_PATH
    print("Décompression...")
    with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
        zip_ref.extractall(DATASET_LOCAL_DIR)
    print(f"Fichiers extraits dans le dossier '{DATASET_LOCAL_DIR}'.")

    # (Optionnal) Remove zip file
    os.remove(local_zip_path)

    data = pd.read_csv(f"{DATASET_LOCAL_DIR}/creditcard.csv", delimiter=',')

    nonfrauds, frauds = data.groupby('Class').size()
    print('Number of frauds: ', frauds)
    print('Number of non-frauds: ', nonfrauds)
    print('Percentage of fradulent data:', 100.*frauds/(frauds + nonfrauds))

    feature_columns = data.columns[:-1]
    label_column = data.columns[-1]

    features = data[feature_columns].values.astype('float32')
    labels = (data[label_column].values).astype('float32')

    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.1, random_state=42
    )

    print(f"X_test: {X_test[0]}")
    if CONTINUE_SIMULATION:
        thread = Thread(target = generate_data, args=[np.copy(X_test)])
        thread.start()
    else:
        # one simulation at a time
        generate_data(np.copy(X_test), max_requests=100)  # Adjust max_requests as needed



