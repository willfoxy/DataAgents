"""Databricks training backend (stub implementation)."""

from datetime import datetime
from libs.trainer_backends.base import TrainerBackend, TrainingConfig, TrainingResult
from libs.common.logging import get_logger

logger = get_logger(__name__)


class DatabricksTrainer(TrainerBackend):
    """Databricks training backend implementation."""

    def __init__(self) -> None:
        logger.info("Initialized Databricks trainer")
        # In production: initialize Databricks client
        # from databricks.sdk import WorkspaceClient

    def submit_training_job(
        self,
        config: TrainingConfig,
    ) -> str:
        """Submit Databricks training job."""
        job_name = f"{config.model_name}-dbx-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Submitting Databricks job: {job_name}")

        # In production: submit to Databricks Jobs API
        # w = WorkspaceClient()
        # run = w.jobs.submit(...)

        return job_name

    def get_job_status(
        self,
        job_id: str,
    ) -> TrainingResult:
        """Get Databricks job status."""
        # Stub implementation
        return TrainingResult(
            job_id=job_id,
            status="Completed",
            started_at=datetime.utcnow(),
        )

    def cancel_job(
        self,
        job_id: str,
    ) -> bool:
        """Cancel Databricks job."""
        logger.info(f"Cancelling Databricks job: {job_id}")
        return True

    def estimate_cost(
        self,
        config: TrainingConfig,
    ) -> float:
        """Estimate Databricks training cost."""
        # Simplified estimation (DBU pricing)
        dbu_cost = 0.22  # per DBU-hour
        dbus_per_node = 0.75
        return dbu_cost * dbus_per_node * (config.max_runtime_seconds / 3600) * config.instance_count
