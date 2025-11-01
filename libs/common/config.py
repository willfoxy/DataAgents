"""Configuration management."""

import os
from typing import Optional
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

from libs.common.types import Environment


class Config(BaseSettings):
    """Application configuration."""

    # Environment
    environment: Environment = Field(
        default=Environment.DEV,
        validation_alias="ENV"
    )

    # AWS Configuration
    aws_region: str = Field(default="eu-west-2")
    aws_account_id: Optional[str] = Field(default=None)

    # S3 Buckets
    s3_data_bucket: str = Field(default="aurora-data-{env}")
    s3_models_bucket: str = Field(default="aurora-models-{env}")
    s3_reports_bucket: str = Field(default="aurora-reports-{env}")
    s3_config_bucket: str = Field(default="aurora-config-{env}")
    s3_audit_bucket: str = Field(default="aurora-audit-{env}")
    s3_metadata_bucket: str = Field(default="aurora-metadata-{env}")

    # DynamoDB Tables
    dynamodb_state_table: str = Field(default="aurora-agent-state-{env}")
    dynamodb_tasks_table: str = Field(default="aurora-tasks-{env}")
    dynamodb_approvals_table: str = Field(default="aurora-approvals-{env}")

    # EventBridge
    event_bus_name: str = Field(default="aurora-events-{env}")

    # SageMaker
    sagemaker_role_arn: Optional[str] = None
    feature_store_prefix: str = Field(default="aurora-feature-store-{env}")

    # MLflow
    mlflow_tracking_uri: str = Field(default="http://localhost:5000")
    mlflow_experiment_prefix: str = Field(default="aurora")

    # OpenSearch
    opensearch_endpoint: Optional[str] = None
    opensearch_index_prefix: str = Field(default="aurora")

    # Cost Controls
    daily_budget_gbp: float = Field(default=150.0)
    task_cost_ceiling_gbp: float = Field(default=50.0)

    # Timeouts
    default_task_timeout_seconds: int = Field(default=3600)

    # Observability
    log_level: str = Field(default="INFO")
    otel_exporter_endpoint: Optional[str] = None

    # Timezone
    timezone: str = Field(default="Europe/London")

    # Feature flags
    enable_auto_retrain: bool = Field(default=True)
    enable_human_approval: bool = Field(default=True)
    enable_cost_gates: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_bucket_name(self, bucket_template: str) -> str:
        """Resolve bucket name with environment."""
        return bucket_template.format(env=self.environment.value)

    def get_table_name(self, table_template: str) -> str:
        """Resolve DynamoDB table name with environment."""
        return table_template.format(env=self.environment.value)

    @property
    def data_bucket(self) -> str:
        return self.get_bucket_name(self.s3_data_bucket)

    @property
    def models_bucket(self) -> str:
        return self.get_bucket_name(self.s3_models_bucket)

    @property
    def reports_bucket(self) -> str:
        return self.get_bucket_name(self.s3_reports_bucket)

    @property
    def config_bucket(self) -> str:
        return self.get_bucket_name(self.s3_config_bucket)

    @property
    def audit_bucket(self) -> str:
        return self.get_bucket_name(self.s3_audit_bucket)

    @property
    def metadata_bucket(self) -> str:
        return self.get_bucket_name(self.s3_metadata_bucket)


@lru_cache()
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config()
