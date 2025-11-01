# DynamoDB tables for state and metadata

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "aurora"
}

# Agent state table
resource "aws_dynamodb_table" "agent_state" {
  name           = "${var.project_name}-agent-state-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "task_id"
  range_key      = "run_id"

  attribute {
    name = "task_id"
    type = "S"
  }

  attribute {
    name = "run_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "task_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-agent-state-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Tasks table
resource "aws_dynamodb_table" "tasks" {
  name           = "${var.project_name}-tasks-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "task_id"

  attribute {
    name = "task_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-tasks-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Approvals table (for human-in-the-loop)
resource "aws_dynamodb_table" "approvals" {
  name           = "${var.project_name}-approvals-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "approval_id"

  attribute {
    name = "approval_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-approvals-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Outputs
output "agent_state_table_name" {
  value = aws_dynamodb_table.agent_state.name
}

output "agent_state_table_arn" {
  value = aws_dynamodb_table.agent_state.arn
}

output "tasks_table_name" {
  value = aws_dynamodb_table.tasks.name
}

output "approvals_table_name" {
  value = aws_dynamodb_table.approvals.name
}
