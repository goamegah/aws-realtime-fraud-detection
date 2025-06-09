import time
import re
import datetime
import random
import requests
import numpy as np
from scipy.stats import poisson
from dotenv import load_dotenv
import os

load_dotenv()

FASTAPI_URL = os.getenv('FASTAPI_URL')


def generate_metadata():
    """
    Génère des métadonnées pour la requête HTTP : une source aléatoire et un timestamp.
    """
    millisecond_regex = r'\.\d+'
    timestamp = re.sub(millisecond_regex, '', str(datetime.datetime.now()))
    source = random.choice(['Mobile', 'Web', 'Store'])
    result = [timestamp, 'random_id', source]
    return result


def get_data_payload(test_array):
    return {
        'data': ','.join(map(str, test_array)),
        'metadata': generate_metadata()
    }


def generate_traffic(X_test):
    """
    Utilise un tableau de features comme entrée pour simuler du trafic.
    """
    while True:
        np.random.shuffle(X_test)
        for example in X_test:
            data_payload = get_data_payload(example)
            invoke_endpoint(data_payload)
            time.sleep(poisson.rvs(1, size=1)[0] + np.random.rand() / 100)


def invoke_endpoint(payload):
    """
    Envoie les données à l'API FastAPI (remplace API Gateway).
    """
    try:
        response = requests.post(FASTAPI_URL, json=payload)
        response.raise_for_status()
        
        print(f"Sent payload successfully: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send payload: {e}")
