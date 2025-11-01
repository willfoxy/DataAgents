# Aurora Energy Platform - Dev Environment

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "aurora-terraform-state-dev"
    key            = "platform/terraform.tfstate"
    region         = "eu-west-2"
    encrypt        = true
    dynamodb_table = "aurora-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "dev"
      Project     = "aurora-energy-platform"
      ManagedBy   = "terraform"
      CostCenter  = "data-analytics"
    }
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "aurora"
}

# S3 buckets
module "s3" {
  source = "../../modules/s3"

  environment  = "dev"
  project_name = var.project_name
}

# DynamoDB tables
module "dynamodb" {
  source = "../../modules/dynamodb"

  environment  = "dev"
  project_name = var.project_name
}

# EventBridge
resource "aws_cloudwatch_event_bus" "platform" {
  name = "${var.project_name}-events-dev"

  tags = {
    Name        = "${var.project_name}-events-dev"
    Environment = "dev"
  }
}

# SNS Topics for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-dev"

  tags = {
    Name        = "${var.project_name}-alerts-dev"
    Environment = "dev"
  }
}

resource "aws_sns_topic" "dq_alerts" {
  name = "${var.project_name}-dq-alerts-dev"

  tags = {
    Name        = "${var.project_name}-dq-alerts-dev"
    Environment = "dev"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "platform" {
  name              = "/aws/aurora-platform/dev"
  retention_in_days = 30

  tags = {
    Name        = "${var.project_name}-logs-dev"
    Environment = "dev"
  }
}

# Outputs
output "data_bucket" {
  value = module.s3.data_bucket_name
}

output "models_bucket" {
  value = module.s3.models_bucket_name
}

output "reports_bucket" {
  value = module.s3.reports_bucket_name
}

output "agent_state_table" {
  value = module.dynamodb.agent_state_table_name
}

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.platform.name
}

output "alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
