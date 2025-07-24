# Utilise le VPC par défaut AWS
data "aws_vpc" "default" {
    default = true
}

# Récupérer les subnets du VPC par défaut
data "aws_subnets" "default" {
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.default.id]
    }
}

# Security Group simplifié pour RDS (accès depuis Internet pour Glue)
resource "aws_security_group" "rds_sg" {
    name        = "fraudit-rds-sg"
    description = "Allow PostgreSQL access"
    vpc_id      = data.aws_vpc.default.id

    # Accès PostgreSQL depuis Internet (pour Glue sans VPC)
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

# Groupe de sous-réseaux pour RDS
resource "aws_db_subnet_group" "fraudit_subnet_group" {
    name       = "fraudit-subnet-group"
    subnet_ids = data.aws_subnets.default.ids

    tags = {
        Name = "fraudit-subnet-group"
    }
}

# Instance PostgreSQL RDS
resource "aws_db_instance" "fraudit_postgres" {
    identifier            = "fraudit-postgres-db"
    engine                = "postgres"
    engine_version        = "17.5"  # Version supportée par AWS RDS
    instance_class        = "db.t3.micro"
    allocated_storage     = 20
    max_allocated_storage = 100
    storage_type          = "gp2"

    db_name               = var.postgres_db
    username              = var.postgres_user
    password              = var.postgres_password
    port                  = var.postgres_port

    # Configuration réseau
    db_subnet_group_name   = aws_db_subnet_group.fraudit_subnet_group.name
    vpc_security_group_ids = [aws_security_group.rds_sg.id]
    publicly_accessible    = true  # Nécessaire pour l'accès depuis Glue sans VPC

    # Configuration de sauvegarde
    backup_retention_period = 7
    backup_window          = "03:00-04:00"
    maintenance_window     = "sun:04:00-sun:05:00"

    # Configuration pour le développement
    skip_final_snapshot   = true
    deletion_protection   = false
    apply_immediately     = true

    # Monitoring désactivé pour simplifier
    performance_insights_enabled = false
    monitoring_interval          = 0

    tags = {
        Name        = "fraudit-postgres"
        Environment = "dev"
        Project     = "fraud-detection"
    }
}