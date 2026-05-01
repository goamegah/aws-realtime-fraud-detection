variable "aws_region" {
    description = "AWS region to deploy resources into"
    type        = string
    default     = "eu-west-1"
}

variable "postgres_user" {
    description = "Nom d'utilisateur PostgreSQL"
    type        = string
    default     = "postgres_user"
}

variable "postgres_password" {
    description = "Mot de passe PostgreSQL"
    type        = string
    default     = "postgres_password" # change password before deploying
    # sensitive = true
}

variable "postgres_db" {
    description = "Nom de la base PostgreSQL"
    type        = string
    default     = "fraudit_postgres_db"
}

variable "postgres_port" {
    description = "Port PostgreSQL"
    type        = number
    default     = 5432
}


# =======================  EMR Variables =======================

# variable "vpc_id" {
#   description = "VPC ID where EMR cluster will be deployed"
#   type        = string
# }

# variable "subnet_id" {
#   description = "Subnet ID for EMR cluster"
#   type        = string
# }

# variable "emr_master_instance_type" {
#   description = "Instance type for EMR master node"
#   type        = string
#   default     = "m5.xlarge"
# }

# variable "emr_core_instance_type" {
#   description = "Instance type for EMR core nodes"
#   type        = string
#   default     = "m5.xlarge"
# }

# variable "emr_core_instance_count" {
#   description = "Number of EMR core nodes"
#   type        = number
#   default     = 2
# }


# Kinesis stream configuration
variable "kinesis_stream_name" {
    description = "Kinesis Data Stream name for fraud predictions"
    type        = string
    default     = "fraud-predictions-stream"
}

variable "kinesis_shard_count" {
    description = "Number of shards for the Kinesis stream"
    type        = number
    default     = 4
}


# SageMaker variables
variable "sagemaker_notebook_name" {
    description = "Name of the SageMaker Notebook Instance"
    type        = string
    default     = "fraudit-notebook"
}

variable "sagemaker_notebook_instance_type" {
    description = "Instance type for the Notebook"
    type        = string
    default     = "ml.t3.medium"
}

variable "sagemaker_root_volume_size" {
    description = "Root volume size in GB"
    type        = number
    default     = 20
}

variable "sagemaker_subnet_id" {
    description = "Subnet ID to place the notebook in (optional). Leave empty for no VPC attachment."
    type        = string
    default     = ""
}

variable "sagemaker_security_group_ids" {
    description = "Security group IDs for the notebook (optional)"
    type        = list(string)
    default     = []
}

variable "sagemaker_lifecycle_startup_content" {
    description = "Lifecycle configuration script content (optional)"
    type        = string
    default     = "" # Leave empty for no lifecycle configuration
}

variable "region" {
    description = "AWS region"
    type        = string
    default     = "eu-west-1"
}