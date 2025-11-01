"""Azure ML training backend (stub implementation)."""

from datetime import datetime
from libs.trainer_backends.base import TrainerBackend, TrainingConfig, TrainingResult
from libs.common.logging import get_logger

logger = get_logger(__name__)


class AzureMLTrainer(TrainerBackend):
    """Azure ML training backend implementation."""

    def __init__(self) -> None:
        logger.info("Initialized Azure ML trainer")
        # In production: initialize Azure ML client
        # from azure.ai.ml import MLClient
        # from azure.identity import DefaultAzureCredential

    def submit_training_job(
        self,
        config: TrainingConfig,
    ) -> str:
        """Submit Azure ML training job."""
        job_name = f"{config.model_name}-azure-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Submitting Azure ML job: {job_name}")

        # In production: submit to Azure ML
        # command_job = command(...)
        # returned_job = ml_client.jobs.create_or_update(command_job)

        return job_name

    def get_job_status(
        self,
        job_id: str,
    ) -> TrainingResult:
        """Get Azure ML job status."""
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
        """Cancel Azure ML job."""
        logger.info(f"Cancelling Azure ML job: {job_id}")
        return True

    def estimate_cost(
        self,
        config: TrainingConfig,
    ) -> float:
        """Estimate Azure ML training cost."""
        # Simplified estimation
        return 0.30 * (config.max_runtime_seconds / 3600) * config.instance_count
