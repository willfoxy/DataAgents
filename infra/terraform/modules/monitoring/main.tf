# CloudWatch Dashboards and Alarms

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "aurora"
}

# Main platform dashboard
resource "aws_cloudwatch_dashboard" "platform" {
  dashboard_name = "${var.project_name}-platform-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Platform", "AgentExecutions", { stat = "Sum", label = "Total Executions" }],
            [".", "AgentSuccesses", { stat = "Sum", label = "Successful" }],
            [".", "AgentFailures", { stat = "Sum", label = "Failed" }],
          ]
          period = 300
          stat   = "Sum"
          region = "eu-west-2"
          title  = "Agent Execution Status"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Platform", "DailyCostGBP", { stat = "Sum" }],
          ]
          period = 86400
          stat   = "Sum"
          region = "eu-west-2"
          title  = "Daily Cost (GBP)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Platform", "TaskLatencyMs", { stat = "Average", label = "P50" }],
            ["...", { stat = "p95", label = "P95" }],
            ["...", { stat = "p99", label = "P99" }],
          ]
          period = 300
          region = "eu-west-2"
          title  = "Task Latency"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Models", "ChurnAUC", { stat = "Average", label = "Churn Model AUC" }],
            ["Aurora/Models", "AcquisitionMAPE", { stat = "Average", label = "Acquisition MAPE" }],
            ["Aurora/Models", "LoadMAPE", { stat = "Average", label = "Load MAPE" }],
          ]
          period = 3600
          region = "eu-west-2"
          title  = "Model Performance"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/DataQuality", "ValidationsPassed", { stat = "Sum", label = "Passed" }],
            [".", "ValidationsFailed", { stat = "Sum", label = "Failed" }],
          ]
          period = 3600
          region = "eu-west-2"
          title  = "Data Quality Checks"
        }
      },
      {
        type = "log"
        properties = {
          query   = <<-EOT
            SOURCE '/aws/aurora-platform/${var.environment}'
            | fields @timestamp, level, agent_name, @message
            | filter level = 'ERROR'
            | sort @timestamp desc
            | limit 20
          EOT
          region  = "eu-west-2"
          title   = "Recent Errors"
        }
      },
    ]
  })
}

# Cost monitoring dashboard
resource "aws_cloudwatch_dashboard" "costs" {
  dashboard_name = "${var.project_name}-costs-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Costs", "AgentCost", { stat = "Sum", label = "Per Agent" }],
            ["Aurora/Costs", "InfrastructureCost", { stat = "Sum", label = "Infrastructure" }],
            ["Aurora/Costs", "TotalCost", { stat = "Sum", label = "Total" }],
          ]
          period = 86400
          stat   = "Sum"
          region = "eu-west-2"
          title  = "Daily Cost Breakdown"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Costs", "BudgetUtilization", { stat = "Maximum" }],
          ]
          period = 3600
          stat   = "Maximum"
          region = "eu-west-2"
          title  = "Budget Utilization (%)"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
          annotations = {
            horizontal = [
              {
                value = 80
                label = "Warning"
                color = "#ff9900"
              },
              {
                value = 90
                label = "Critical"
                color = "#d13212"
              }
            ]
          }
        }
      },
    ]
  })
}

# Model performance dashboard
resource "aws_cloudwatch_dashboard" "models" {
  dashboard_name = "${var.project_name}-models-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Models", "ChurnAUC", { stat = "Average" }],
            ["Aurora/Models", "ChurnCalibrationError", { stat = "Average" }],
          ]
          period = 3600
          region = "eu-west-2"
          title  = "Churn Model Metrics"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Drift", "DataDriftPSI", { stat = "Maximum", label = "Max PSI" }],
            [".", "ModelDriftAUCDrop", { stat = "Maximum", label = "AUC Drop %" }],
          ]
          period = 3600
          region = "eu-west-2"
          title  = "Drift Metrics"
          annotations = {
            horizontal = [
              {
                value = 0.2
                label = "PSI Threshold"
                color = "#d13212"
              }
            ]
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Aurora/Models", "PredictionLatencyMs", { stat = "Average", label = "P50" }],
            ["...", { stat = "p95", label = "P95" }],
          ]
          period = 300
          region = "eu-west-2"
          title  = "Prediction Latency"
        }
      },
    ]
  })
}

# Budget alarms
resource "aws_cloudwatch_metric_alarm" "budget_80" {
  alarm_name          = "${var.project_name}-budget-80pct-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BudgetUtilization"
  namespace           = "Aurora/Costs"
  period              = 3600
  statistic           = "Maximum"
  threshold           = 80
  alarm_description   = "Budget utilization exceeded 80%"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.budget_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "budget_90" {
  alarm_name          = "${var.project_name}-budget-90pct-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BudgetUtilization"
  namespace           = "Aurora/Costs"
  period              = 3600
  statistic           = "Maximum"
  threshold           = 90
  alarm_description   = "Budget utilization exceeded 90% - CRITICAL"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.budget_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "budget_100" {
  alarm_name          = "${var.project_name}-budget-100pct-${var.environment}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "BudgetUtilization"
  namespace           = "Aurora/Costs"
  period              = 3600
  statistic           = "Maximum"
  threshold           = 100
  alarm_description   = "Budget exceeded - EMERGENCY"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.budget_alerts.arn]
}

# Model performance alarms
resource "aws_cloudwatch_metric_alarm" "churn_auc_low" {
  alarm_name          = "${var.project_name}-churn-auc-low-${var.environment}"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ChurnAUC"
  namespace           = "Aurora/Models"
  period              = 3600
  statistic           = "Average"
  threshold           = 0.78
  alarm_description   = "Churn model AUC below threshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.model_alerts.arn]
}

# Drift detection alarms
resource "aws_cloudwatch_metric_alarm" "data_drift" {
  alarm_name          = "${var.project_name}-data-drift-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DataDriftPSI"
  namespace           = "Aurora/Drift"
  period              = 3600
  statistic           = "Maximum"
  threshold           = 0.2
  alarm_description   = "Data drift detected (PSI > 0.2)"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.drift_alerts.arn]
}

# SNS topics for alerts
resource "aws_sns_topic" "budget_alerts" {
  name = "${var.project_name}-budget-alerts-${var.environment}"
}

resource "aws_sns_topic" "model_alerts" {
  name = "${var.project_name}-model-alerts-${var.environment}"
}

resource "aws_sns_topic" "drift_alerts" {
  name = "${var.project_name}-drift-alerts-${var.environment}"
}

# Outputs
output "platform_dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=eu-west-2#dashboards:name=${aws_cloudwatch_dashboard.platform.dashboard_name}"
}

output "costs_dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=eu-west-2#dashboards:name=${aws_cloudwatch_dashboard.costs.dashboard_name}"
}

output "models_dashboard_url" {
  value = "https://console.aws.amazon.com/cloudwatch/home?region=eu-west-2#dashboards:name=${aws_cloudwatch_dashboard.models.dashboard_name}"
}

output "budget_alerts_topic_arn" {
  value = aws_sns_topic.budget_alerts.arn
}

output "model_alerts_topic_arn" {
  value = aws_sns_topic.model_alerts.arn
}

output "drift_alerts_topic_arn" {
  value = aws_sns_topic.drift_alerts.arn
}
