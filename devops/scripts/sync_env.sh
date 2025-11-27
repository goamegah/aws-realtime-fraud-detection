#!/usr/bin/env bash
# Sync .env with Terraform outputs
# Usage: ./devops/scripts/sync_env.sh [--create]
#   --create: Create .env from .env.example if it doesn't exist

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TF_DIR="${ROOT_DIR}/devops/infra/main"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE="${ROOT_DIR}/.env.example"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if terraform is available
if ! command -v terraform &> /dev/null; then
    log_error "terraform command not found. Please install Terraform."
    exit 1
fi

# Check if we're in a valid terraform directory
if [ ! -f "${TF_DIR}/terraform.tfstate" ]; then
    log_error "No terraform.tfstate found in ${TF_DIR}. Run 'make tf.apply' first."
    exit 1
fi

# Create .env from example if requested and file doesn't exist
if [[ "${1:-}" == "--create" ]] && [ ! -f "${ENV_FILE}" ]; then
    if [ -f "${ENV_EXAMPLE}" ]; then
        cp "${ENV_EXAMPLE}" "${ENV_FILE}"
        log_info "Created ${ENV_FILE} from ${ENV_EXAMPLE}"
    else
        log_error "No ${ENV_EXAMPLE} found to create .env"
        exit 1
    fi
fi

# Check if .env exists
if [ ! -f "${ENV_FILE}" ]; then
    log_error ".env file not found. Run 'make env' or use --create flag."
    exit 1
fi

log_info "Fetching Terraform outputs from ${TF_DIR}..."

# Get terraform outputs as JSON
cd "${TF_DIR}"
TF_OUTPUT=$(terraform output -json 2>/dev/null) || {
    log_error "Failed to get Terraform outputs. Make sure 'terraform apply' has been run."
    exit 1
}

# Extract values using jq or python
if command -v jq &> /dev/null; then
    SPARK_BUCKET=$(echo "$TF_OUTPUT" | jq -r '.spark_streaming_bucket_name.value // empty')
    DATA_BUCKET=$(echo "$TF_OUTPUT" | jq -r '.fraud_data_bucket_name.value // empty')
    KINESIS_STREAM=$(echo "$TF_OUTPUT" | jq -r '.kinesis_stream_name.value // empty')
    POSTGRES_HOST=$(echo "$TF_OUTPUT" | jq -r '.rds_postgres_endpoint.value // empty')
    POSTGRES_PORT=$(echo "$TF_OUTPUT" | jq -r '.rds_postgres_port.value // empty')
else
    # Fallback to Python if jq not available
    read_tf_output() {
        python3 -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('$1', {}).get('value', ''))" <<< "$TF_OUTPUT"
    }
    SPARK_BUCKET=$(read_tf_output "spark_streaming_bucket_name")
    DATA_BUCKET=$(read_tf_output "fraud_data_bucket_name")
    KINESIS_STREAM=$(read_tf_output "kinesis_stream_name")
    POSTGRES_HOST=$(read_tf_output "rds_postgres_endpoint")
    POSTGRES_PORT=$(read_tf_output "rds_postgres_port")
fi

# Function to update a variable in .env
update_env_var() {
    local var_name="$1"
    local new_value="$2"
    
    if [ -z "$new_value" ]; then
        log_warn "Skipping ${var_name}: no value from Terraform"
        return
    fi
    
    if grep -q "^${var_name}=" "${ENV_FILE}"; then
        # Variable exists, update it
        sed -i "s|^${var_name}=.*|${var_name}=\"${new_value}\"|" "${ENV_FILE}"
        log_info "Updated ${var_name}=${new_value}"
    else
        # Variable doesn't exist, append it
        echo "${var_name}=\"${new_value}\"" >> "${ENV_FILE}"
        log_info "Added ${var_name}=${new_value}"
    fi
}

log_info "Updating .env with Terraform outputs..."

# Update .env variables
update_env_var "SPARK_SOLUTION_S3_BUCKET" "$SPARK_BUCKET"
update_env_var "SOLUTIONS_S3_BUCKET" "$DATA_BUCKET"
update_env_var "KINESIS_STREAM" "$KINESIS_STREAM"
update_env_var "stream_name" "$KINESIS_STREAM"
update_env_var "POSTGRES_HOST" "$POSTGRES_HOST"
update_env_var "POSTGRES_PORT" "$POSTGRES_PORT"

log_info "Done! .env synced with Terraform outputs."
log_warn "Remember: AWS credentials should be in ~/.aws/credentials, not in .env"

# Show summary
echo ""
echo "=== Summary ==="
echo "SPARK_SOLUTION_S3_BUCKET: ${SPARK_BUCKET:-<not set>}"
echo "SOLUTIONS_S3_BUCKET:      ${DATA_BUCKET:-<not set>}"
echo "KINESIS_STREAM:           ${KINESIS_STREAM:-<not set>}"
echo "POSTGRES_HOST:            ${POSTGRES_HOST:-<not set>}"
echo "POSTGRES_PORT:            ${POSTGRES_PORT:-<not set>}"
