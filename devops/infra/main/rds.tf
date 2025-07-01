# Utilise le VPC par défaut AWS
data "aws_vpc" "default" {
    default = true
}

# Security Group pour autoriser l'accès PostgreSQL
resource "aws_security_group" "rds_sg" {
    name        = "fraudit-rds-sg"
    description = "Allow PostgreSQL access"
    vpc_id      = data.aws_vpc.default.id

    ingress {
        from_port   = var.postgres_port
        to_port     = var.postgres_port
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"] # /!\ à restreindre en prod (ex: CIDR Glue uniquement)
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

# Instance PostgreSQL RDS
resource "aws_db_instance" "fraudit_postgres" {
    identifier            = "fraudit-postgres-db"
    engine                = "postgres"
    engine_version        = "17.5"
    instance_class        = "db.t3.micro"
    allocated_storage     = 20
    max_allocated_storage = 100
    storage_type          = "gp2"

    db_name               = var.postgres_db
    username              = var.postgres_user
    password              = var.postgres_password
    port                  = var.postgres_port

    publicly_accessible   = true
    skip_final_snapshot   = true
    deletion_protection   = false
    apply_immediately     = true

    vpc_security_group_ids = [aws_security_group.rds_sg.id]

    tags = {
        Name        = "fraudit-postgres"
        Environment = "dev"
        Project     = "fraud-detection"
    }
}
