# SageMaker Notebook (always created)

# Variables expected in variables.tf:
# - sagemaker_notebook_instance_type: string
# - sagemaker_notebook_name: string
# - sagemaker_root_volume_size: number
# - sagemaker_subnet_id: string (optional)
# - sagemaker_security_group_ids: list(string) (optional)
# - sagemaker_lifecycle_startup_content: string (optional)

resource "aws_iam_role" "sagemaker_execution_role" {
  name = "fraudit-sagemaker-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect    = "Allow",
        Principal = { Service = "sagemaker.amazonaws.com" },
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "sagemaker_policy" {
  name = "fraudit-sagemaker-access"
  role = aws_iam_role.sagemaker_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ],
        Resource = [
          "${aws_s3_bucket.fraud_data_bucket.arn}",
          "${aws_s3_bucket.fraud_data_bucket.arn}/*",
          "${aws_s3_bucket.fraud_streaming_bucket.arn}",
          "${aws_s3_bucket.fraud_streaming_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      }
    ]
  })
}

# Lifecycle configuration améliorée avec votre script
resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "fraudit_nb_lifecycle" {
  count = var.sagemaker_lifecycle_startup_content != "" ? 1 : 0
  name  = "fraudit-notebook-lifecycle"

  on_start = base64encode(<<-EOF
    #!/bin/bash
    set -e

    # Logging détaillé
    exec > >(tee /var/log/sagemaker-startup.log) 2>&1
    echo "$(date): Starting SageMaker setup for fraudit project"

    SAGEMAKER_HOME="/home/ec2-user/SageMaker"
    REPO_URL="https://github.com/goamegah/aws-realtime-fraud-detection.git"

    # Attendre que SageMaker soit complètement prêt
    echo "$(date): Waiting for SageMaker to be ready..."
    sleep 30

    # Vérifier que git est disponible
    if ! command -v git &> /dev/null; then
        echo "$(date): Installing git..."
        yum update -y
        yum install -y git
    fi

    # Créer et naviguer vers le répertoire SageMaker
    mkdir -p $SAGEMAKER_HOME
    cd $SAGEMAKER_HOME

    # Nettoyer les anciens clones
    echo "$(date): Cleaning up previous installations..."
    rm -rf aws-realtime-fraud-detection

    echo "$(date): Cloning repository from $REPO_URL..."

    # Clone avec retry et gestion d'erreurs
    RETRY_COUNT=0
    MAX_RETRIES=3

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if git clone --depth=1 --filter=blob:none --sparse $REPO_URL; then
            echo "$(date): Repository cloned successfully"
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            echo "$(date): Clone attempt $RETRY_COUNT failed"
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo "$(date): Retrying in 10 seconds..."
                sleep 10
                rm -rf aws-realtime-fraud-detection
            else
                echo "$(date): ERROR: Failed to clone repository after $MAX_RETRIES attempts"
                exit 1
            fi
        fi
    done

    # Configuration du sparse checkout
    cd aws-realtime-fraud-detection
    echo "$(date): Configuring sparse checkout for sagemaker directory..."

    if git sparse-checkout set sagemaker; then
        echo "$(date): Sparse checkout configured"
    else
        echo "$(date): Warning: Sparse checkout failed, using full repository"
    fi

    if git checkout main; then
        echo "$(date): Checked out main branch"
    else
        echo "$(date): Warning: Could not checkout main branch"
    fi

    # Déplacer les fichiers du répertoire sagemaker
    echo "$(date): Moving sagemaker files to $SAGEMAKER_HOME..."
    if [ -d "sagemaker" ] && [ "$(ls -A sagemaker 2>/dev/null)" ]; then
        mv sagemaker/* $SAGEMAKER_HOME/
        echo "$(date): Files moved successfully"
    else
        echo "$(date): Warning: sagemaker directory is empty or doesn't exist"
        echo "$(date): Available directories: $(ls -la)"
    fi

    echo "$(date): Installing Python packages..."

    # Installation dans l'environnement conda de SageMaker avec gestion d'erreurs
    sudo -u ec2-user -i <<'USEREOF'
    set -e

    # Activer l'environnement conda approprié
    source /home/ec2-user/anaconda3/bin/activate JupyterSystemEnv

    echo "Active conda environment: $CONDA_DEFAULT_ENV"
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"

    # Mise à jour de pip
    pip install --upgrade pip

    # Installation des packages avec timeout et retry
    echo "Installing essential packages..."
    pip install --no-cache-dir --timeout=300 --retries=3 \
        pandas numpy matplotlib seaborn scikit-learn \
        boto3 psycopg2-binary sqlalchemy plotly \
        jupyter-dash ipywidgets

    # Vérification des installations
    echo "Verifying installations..."
    python -c "import pandas, numpy, matplotlib, seaborn, sklearn, boto3; print('All packages imported successfully')"

    echo "Python packages installed successfully"
USEREOF

    # Log de fin et changement de propriétaire
    echo "Setup completed at $(date)" > $SAGEMAKER_HOME/setup.log
    echo "Repository: $REPO_URL" >> $SAGEMAKER_HOME/setup.log
    echo "Python packages: pandas, numpy, matplotlib, seaborn, scikit-learn, boto3, psycopg2-binary, sqlalchemy, plotly" >> $SAGEMAKER_HOME/setup.log

    # S'assurer que ec2-user possède tous les fichiers
    chown -R ec2-user:ec2-user $SAGEMAKER_HOME

    # Permissions correctes pour les scripts
    find $SAGEMAKER_HOME -name "*.sh" -exec chmod +x {} \;
    find $SAGEMAKER_HOME -name "*.py" -exec chmod +r {} \;

    echo "$(date): SageMaker setup completed successfully!"
    echo "$(date): Logs available at /var/log/sagemaker-startup.log"
    echo "$(date): Setup summary available at $SAGEMAKER_HOME/setup.log"
  EOF
  )
}

# Notebook instance
resource "aws_sagemaker_notebook_instance" "fraudit_notebook" {
  name          = var.sagemaker_notebook_name
  instance_type = var.sagemaker_notebook_instance_type
  role_arn      = aws_iam_role.sagemaker_execution_role.arn
  volume_size   = var.sagemaker_root_volume_size

  # Conditionnel pour subnet
  subnet_id = var.sagemaker_subnet_id != "" ? var.sagemaker_subnet_id : null

  # Conditionnel pour security groups
  security_groups = length(var.sagemaker_security_group_ids) > 0 ? var.sagemaker_security_group_ids : null

  # Conditionnel pour lifecycle config
  lifecycle_config_name = var.sagemaker_lifecycle_startup_content != "" ? aws_sagemaker_notebook_instance_lifecycle_configuration.fraudit_nb_lifecycle[0].name : null

  tags = {
    Project     = "fraud-detection"
    Environment = "dev"
  }
}