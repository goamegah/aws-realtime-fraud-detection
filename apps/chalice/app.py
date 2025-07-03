import os
import json
import logging
import boto3
from chalice import Chalice, BadRequestError

app = Chalice(app_name='ml-inference-api')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

STREAM_NAME = os.environ.get('stream_name')
SOLUTION_PREFIX = os.environ.get('solution_prefix', 'fraud-detection')
AWS_REGION = os.environ.get('aws_region', 'eu-west-1')

sagemaker_runtime = boto3.client('sagemaker-runtime', region_name=AWS_REGION)
kinesis = boto3.client('kinesis', region_name=AWS_REGION)
# firehose = boto3.client('firehose', region_name=AWS_REGION)


@app.route('/predict', methods=['POST'])
def predict():
    event = app.current_request.json_body

    metadata = event.get('metadata')
    data_payload = event.get('data')

    if not metadata or not data_payload:
        raise BadRequestError("Requête invalide : champ 'metadata' ou 'data' manquant.")

    anomaly = get_anomaly_prediction(data_payload)
    fraud = get_fraud_prediction(data_payload)

    output = {
        "anomaly_detector": anomaly,
        "fraud_classifier": fraud
    }

    store_data_prediction(output, metadata)

    return output


def get_anomaly_prediction(data):
    endpoint = f"{SOLUTION_PREFIX}-rcf-endpoint"
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint,
        ContentType='text/csv',
        Body=data
    )
    body = response['Body'].read().decode()
    anomaly_score = json.loads(body)["scores"][0]["score"]
    logger.info(f"Anomaly score: {anomaly_score}")
    return {"score": anomaly_score}


def get_fraud_prediction(data, threshold=0.5):
    endpoint = f"{SOLUTION_PREFIX}-xgb-endpoint"
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint,
        ContentType='text/csv',
        Body=data
    )
    body = response['Body'].read().decode()
    pred_proba = json.loads(body)
    prediction = 1 if pred_proba >= threshold else 0
    logger.info(f"Fraud prediction: {prediction} (proba: {pred_proba})")
    return {"pred_proba": pred_proba, "prediction": prediction}


def store_data_prediction(output, metadata):
    # extract metadata
    timestamp = metadata["timestamp"]
    user_id = metadata["user_id"]
    source = metadata["source"]
    device_info = metadata.get("device_info", {})
    ip_address = metadata.get("ip_address")
    geo = metadata.get("geo", {})

    fraud_pred = output["fraud_classifier"]["prediction"]
    pred_proba = output["fraud_classifier"]["pred_proba"]
    anomaly_score = output["anomaly_detector"]["score"]

    record_data = {
        "timestamp": timestamp,
        "user_id": user_id,
        "source": source,
        "fraud_prediction": fraud_pred,
        "fraud_proba": pred_proba,
        "anomaly_score": anomaly_score,
        "device_info": device_info,
        "ip_address": ip_address,
        "geo": geo
    }

    response = kinesis.put_record(
        StreamName=STREAM_NAME,
        Data=json.dumps(record_data),
        PartitionKey=user_id  # partitioning by user_id
    )
    logger.info("Logged to Kinesis Stream: %s", response)