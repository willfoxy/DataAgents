"""SageMaker training backend."""

from typing import Dict, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from libs.trainer_backends.base import TrainerBackend, TrainingConfig, TrainingResult
from libs.common.config import get_config
from libs.common.logging import get_logger

logger = get_logger(__name__)


class SageMakerTrainer(TrainerBackend):
    """SageMaker training backend implementation."""

    def __init__(self) -> None:
        self.config = get_config()
        self.client = boto3.client("sagemaker", region_name=self.config.aws_region)

    def submit_training_job(
        self,
        config: TrainingConfig,
    ) -> str:
        """Submit a SageMaker training job."""
        job_name = f"{config.model_name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        try:
            response = self.client.create_training_job(
                TrainingJobName=job_name,
                RoleArn=self.config.sagemaker_role_arn or "arn:aws:iam::ACCOUNT:role/SageMaker",
                InputDataConfig=[
                    {
                        "ChannelName": "training",
                        "DataSource": {
                            "S3DataSource": {
                                "S3DataType": "S3Prefix",
                                "S3Uri": config.dataset_uri,
                                "S3DataDistributionType": "FullyReplicated",
                            }
                        },
                    }
                ],
                OutputDataConfig={
                    "S3OutputPath": config.output_uri,
                },
                ResourceConfig={
                    "InstanceType": config.instance_type,
                    "InstanceCount": config.instance_count,
                    "VolumeSizeInGB": 30,
                },
                StoppingCondition={
                    "MaxRuntimeInSeconds": config.max_runtime_seconds,
                },
                HyperParameters=config.hyperparameters,
                Tags=[{"Key": k, "Value": v} for k, v in config.tags.items()],
            )

            job_arn = response["TrainingJobArn"]
            logger.info(f"Submitted SageMaker job: {job_name}", job_name=job_name, job_arn=job_arn)
            return job_name

        except ClientError as e:
            logger.error(f"Failed to submit SageMaker job: {e}")
            raise

    def get_job_status(
        self,
        job_id: str,
    ) -> TrainingResult:
        """Get SageMaker training job status."""
        try:
            response = self.client.describe_training_job(TrainingJobName=job_id)

            status = response["TrainingJobStatus"]
            started_at = response["TrainingStartTime"]
            completed_at = response.get("TrainingEndTime")

            # Calculate duration
            if completed_at:
                duration = (completed_at - started_at).total_seconds()
            else:
                duration = (datetime.utcnow() - started_at).total_seconds()

            # Extract metrics
            metrics = {}
            if "FinalMetricDataList" in response:
                for metric in response["FinalMetricDataList"]:
                    metrics[metric["MetricName"]] = metric["Value"]

            # Estimate cost
            cost_gbp = self._calculate_cost(response)

            return TrainingResult(
                job_id=job_id,
                status=status,
                model_uri=response.get("ModelArtifacts", {}).get("S3ModelArtifacts"),
                metrics=metrics,
                cost_gbp=cost_gbp,
                duration_seconds=duration,
                started_at=started_at,
                completed_at=completed_at,
                error_message=response.get("FailureReason"),
            )

        except ClientError as e:
            logger.error(f"Failed to get job status: {e}")
            raise

    def cancel_job(
        self,
        job_id: str,
    ) -> bool:
        """Cancel a SageMaker training job."""
        try:
            self.client.stop_training_job(TrainingJobName=job_id)
            logger.info(f"Cancelled SageMaker job: {job_id}")
            return True
        except ClientError as e:
            logger.error(f"Failed to cancel job: {e}")
            return False

    def estimate_cost(
        self,
        config: TrainingConfig,
    ) -> float:
        """Estimate cost for SageMaker training job."""
        # Simplified cost estimation
        # In production, use AWS Pricing API
        INSTANCE_COSTS_PER_HOUR = {
            "ml.m5.xlarge": 0.28,
            "ml.m5.2xlarge": 0.56,
            "ml.p3.2xlarge": 4.10,
            "ml.p3.8xlarge": 16.40,
        }

        cost_per_hour = INSTANCE_COSTS_PER_HOUR.get(config.instance_type, 0.28)
        hours = config.max_runtime_seconds / 3600
        return cost_per_hour * hours * config.instance_count

    def _calculate_cost(self, job_description: Dict[str, Any]) -> float:
        """Calculate actual cost from job description."""
        # Simplified calculation
        instance_type = job_description["ResourceConfig"]["InstanceType"]
        instance_count = job_description["ResourceConfig"]["InstanceCount"]

        started_at = job_description["TrainingStartTime"]
        ended_at = job_description.get("TrainingEndTime", datetime.utcnow())

        duration_hours = (ended_at - started_at).total_seconds() / 3600

        INSTANCE_COSTS_PER_HOUR = {
            "ml.m5.xlarge": 0.28,
            "ml.m5.2xlarge": 0.56,
            "ml.p3.2xlarge": 4.10,
            "ml.p3.8xlarge": 16.40,
        }

        cost_per_hour = INSTANCE_COSTS_PER_HOUR.get(instance_type, 0.28)
        return cost_per_hour * duration_hours * instance_count
