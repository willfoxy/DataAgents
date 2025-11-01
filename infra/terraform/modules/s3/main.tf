# S3 buckets for data lake

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "aurora"
}

# Data bucket (raw, silver, gold layers)
resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}"

  tags = {
    Name        = "${var.project_name}-data-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Models bucket
resource "aws_s3_bucket" "models" {
  bucket = "${var.project_name}-models-${var.environment}"

  tags = {
    Name        = "${var.project_name}-models-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Reports bucket
resource "aws_s3_bucket" "reports" {
  bucket = "${var.project_name}-reports-${var.environment}"

  tags = {
    Name        = "${var.project_name}-reports-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Config bucket
resource "aws_s3_bucket" "config" {
  bucket = "${var.project_name}-config-${var.environment}"

  tags = {
    Name        = "${var.project_name}-config-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Audit bucket (immutable, lifecycle)
resource "aws_s3_bucket" "audit" {
  bucket = "${var.project_name}-audit-${var.environment}"

  tags = {
    Name        = "${var.project_name}-audit-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "audit" {
  bucket = aws_s3_bucket.audit.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audit" {
  bucket = aws_s3_bucket.audit.id

  rule {
    id     = "retain-7-years"
    status = "Enabled"

    expiration {
      days = 2555 # 7 years for UK GDPR compliance
    }
  }
}

# Metadata bucket
resource "aws_s3_bucket" "metadata" {
  bucket = "${var.project_name}-metadata-${var.environment}"

  tags = {
    Name        = "${var.project_name}-metadata-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs
output "data_bucket_name" {
  value = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  value = aws_s3_bucket.data.arn
}

output "models_bucket_name" {
  value = aws_s3_bucket.models.id
}

output "models_bucket_arn" {
  value = aws_s3_bucket.models.arn
}

output "reports_bucket_name" {
  value = aws_s3_bucket.reports.id
}

output "config_bucket_name" {
  value = aws_s3_bucket.config.id
}

output "audit_bucket_name" {
  value = aws_s3_bucket.audit.id
}

output "metadata_bucket_name" {
  value = aws_s3_bucket.metadata.id
}
