import os
import requests
import datetime
import random
import time
import logging
import numpy as np
from dotenv import load_dotenv
from scipy.stats import poisson
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

MAX_RETRIES = 5
BASE_DELAY = 1  # en secondes
API_URL = os.getenv("CHALICE_API_URL")  # ex: https://xxxxxx.execute-api.eu-west-1.amazonaws.com/api
print(f"API URL: {API_URL}")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console_handler)


def generate_metadata():
    timestamp = datetime.datetime.now().replace(microsecond=0).isoformat()
    source = random.choice(['Mobile', 'Web', 'Store'])
    return [timestamp, 'random_id', source]


def get_data_payload(test_array):
    return {
        'data': ','.join(map(str, test_array)),
        'metadata': generate_metadata()
    }


def invoke_chalice_api(payload):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Réponse reçue : %s", response.json())
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Tentative %d échouée : %s", attempt, e)

            if attempt == MAX_RETRIES:
                logger.error("Toutes les tentatives ont échoué. Abandon.")
                raise RuntimeError("Toutes les tentatives d'appel à l'API ont échoué.")

            backoff = BASE_DELAY * (2 ** (attempt - 1))
            jitter = min(1, 0.1 * backoff) * (0.5 - np.random.rand())
            delay = max(0.1, backoff + jitter)

            logger.info("Nouvelle tentative dans %.2f secondes...", delay)
            time.sleep(delay)


def generate_data(X_test, max_requests=None):
    request_count = 0
    while True:
        np.random.shuffle(X_test)
        for example in X_test:
            if max_requests is not None and request_count >= max_requests:
                logger.info(f"Limite atteinte : {request_count} requêtes envoyées.")
                return
            payload = get_data_payload(example)
            try:
                invoke_chalice_api(payload)
            except RuntimeError as e:
                logger.error("Erreur fatale d'appel API : %s", e)
                return  # ou `continue` si tu veux ignorer l’échec
            wait = poisson.rvs(1) + np.random.rand() / 100
            time.sleep(wait)
            request_count += 1


