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
BASE_DELAY = 1  # in seconds
API_URL = os.getenv("CHALICE_API_URL")  # e.g.: https://xxxxxx.execute-api.eu-west-1.amazonaws.com/api
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
    user_id = f"user_{random.randint(1000, 9999)}"
    source = random.choice(['Mobile', 'Web', 'Store'])

    device_info = {
        "device_type": random.choice(["iOS", "Android", "Windows", "macOS", "Linux"]),
        "os_version": random.choice(["14.4", "11.2", "10.15", "12", "22.04"]),
        "app_version": f"v{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
    }

    ip_address = f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}"

    geo = random.choice([
        {"country": "FR", "region": "Île-de-France", "city": "Paris", "latitude": 48.8566, "longitude": 2.3522},
        {"country": "US", "region": "California", "city": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
        {"country": "IN", "region": "Maharashtra", "city": "Mumbai", "latitude": 19.076, "longitude": 72.8777},
        {"country": "BR", "region": "São Paulo", "city": "São Paulo", "latitude": -23.5505, "longitude": -46.6333}
    ])

    return {
        "timestamp": timestamp,
        "user_id": user_id,
        "source": source,
        "device_info": device_info,
        "ip_address": ip_address,
        "geo": geo
    }

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
            logger.info("Response received: %s", response.json())
            return
        except requests.exceptions.RequestException as e:
            logger.warning("Attempt %d failed: %s", attempt, e)

            if attempt == MAX_RETRIES:
                logger.error("All attempts failed. Giving up.")
                raise RuntimeError("All attempts to call the API have failed.")

            backoff = BASE_DELAY * (2 ** (attempt - 1))
            jitter = min(1, 0.1 * backoff) * (0.5 - np.random.rand())
            delay = max(0.1, backoff + jitter)

            logger.info("Retrying in %.2f seconds...", delay)
            time.sleep(delay)



def generate_data(X_test, max_requests=None):
    request_count = 0
    while True:
        np.random.shuffle(X_test)
        for example in X_test:
            if max_requests is not None and request_count >= max_requests:
                logger.info(f"Limit reached: {request_count} requests sent.")
                return

            payload = get_data_payload(example)
            try:
                invoke_chalice_api(payload)
            except RuntimeError as e:
                logger.error("Fatal API call error: %s", e)
                return  # or `continue` to ignore the error

            # Simulate realistic delay: average wait time between 3 and 6 seconds, with some variation
            base_wait = poisson.rvs(mu=10)  # average ~10 sec (you can adjust)
            jitter = np.random.uniform(0.5, 1.5)  # variation between 0.5 and 1.5 sec
            wait = base_wait + jitter

            logger.debug(f"Pause before next send: {wait:.2f} seconds")
            time.sleep(wait)

            request_count += 1
