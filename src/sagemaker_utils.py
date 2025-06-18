import time
import re
import datetime
import random
import numpy as np
from scipy.stats import poisson
from dotenv import load_dotenv
import os
import boto3
import json

load_dotenv()

SAGEMAKER_ENDPOINT_NAME = os.getenv('SAGEMAKER_ENDPOINT_NAME')  # pas URL ici, mais nom réel de l'endpoint SageMaker
AWS_REGION = os.getenv('AWS_REGION', 'eu-west-1')

# Création du client SageMaker Runtime
sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AWS_REGION)


def generate_metadata():
    millisecond_regex = r'\.\d+'
    timestamp = re.sub(millisecond_regex, '', str(datetime.datetime.now()))
    source = random.choice(['Mobile', 'Web', 'Store'])
    return [timestamp, 'random_id', source]


def get_data_payload(test_array):
    return {
        'data': ','.join(map(str, test_array)),
        'metadata': generate_metadata()
    }


def generate_straffic(X_test):
    while True:
        np.random.shuffle(X_test)
        for example in X_test:
            data_payload = get_data_payload(example)
            invoke_sagemaker_endpoint(data_payload)
            time.sleep(poisson.rvs(1, size=1)[0] + np.random.rand() / 100)


def invoke_sagemaker_endpoint(payload):
    """
    Envoie la requête à un endpoint SageMaker via boto3.
    """
    try:
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )

        result = response['Body'].read().decode('utf-8')
        print(f"Sent payload successfully. Response: {result}")

    except Exception as e:
        print(f"Failed to invoke SageMaker endpoint: {e}")
