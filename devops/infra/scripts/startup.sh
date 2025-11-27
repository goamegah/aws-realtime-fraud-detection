#!/bin/bash
set -e

SAGEMAKER_HOME="/home/ec2-user/SageMaker"
REPO_URL="https://github.com/goamegah/aws-realtime-fraud-detection.git"

cd $SAGEMAKER_HOME

rm -rf aws-realtime-fraud-detection

git clone --depth=1 --filter=blob:none --sparse $REPO_URL
cd aws-realtime-fraud-detection
git sparse-checkout set sagemaker
git checkout main

mv sagemaker/* $SAGEMAKER_HOME/
cd $SAGEMAKER_HOME
rm -rf aws-realtime-fraud-detection

mkdir -p {data,models,outputs,scripts}

pip install --no-cache-dir pandas numpy matplotlib seaborn scikit-learn

echo "Setup completed at $(date)" > setup.log
chown -R ec2-user:ec2-user $SAGEMAKER_HOME