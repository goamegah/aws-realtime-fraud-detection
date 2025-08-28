# Uses AWS default VPC
data "aws_vpc" "default" {
    default = true
}

# Get subnets from default VPC
data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}

# Simplified Security Group for RDS (Internet access for Glue)
resource "aws_security_group" "rds_sg" {
    name        = "fraudit-rds-sg"
    description = "Allow PostgreSQL access"
    vpc_id      = data.aws_vpc.default.id

    # PostgreSQL access from Internet (for Glue without VPC)
    ingress {
        from_port   = var.postgres_port
        to_port     = var.postgres_port
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
        description = "PostgreSQL access for Glue and development"
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "fraudit-rds-sg"
    }
}

# Subnet group for RDS
resource "aws_db_subnet_group" "fraudit_subnet_group" {
    name       = "fraudit-subnet-group"
    subnet_ids = data.aws_subnets.default.ids

    tags = {
        Name = "fraudit-subnet-group"
    }
}

# PostgreSQL RDS Instance
resource "aws_db_instance" "fraudit_postgres" {
    identifier            = "fraudit-postgres-db"
    engine                = "postgres"
    engine_version        = "17.5" # Version supported by AWS RDS
    instance_class        = "db.t3.micro"
    allocated_storage     = 20
    max_allocated_storage = 100
    storage_type          = "gp2"

    db_name  = var.postgres_db
    username = var.postgres_user
    password = var.postgres_password
    port     = var.postgres_port

    # Network configuration
    db_subnet_group_name   = aws_db_subnet_group.fraudit_subnet_group.name
    vpc_security_group_ids = [aws_security_group.rds_sg.id]
    publicly_accessible    = true # Required for access from Glue without VPC

    # Backup configuration
    backup_retention_period = 7
    backup_window           = "03:00-04:00"
    maintenance_window      = "sun:04:00-sun:05:00"

    # Development configuration
    skip_final_snapshot = true
    deletion_protection = false
    apply_immediately   = true

    # Monitoring disabled for simplicity
    performance_insights_enabled = false
    monitoring_interval          = 0

    tags = {
        Name        = "fraudit-postgres"
        Environment = "dev"
        Project     = "fraud-detection"
    }
}
