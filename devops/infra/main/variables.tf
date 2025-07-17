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
