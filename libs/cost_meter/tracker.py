"""Cost tracking and estimation."""

from typing import Dict, Optional
from datetime import datetime, timedelta
import boto3
from decimal import Decimal

from libs.common.config import get_config
from libs.common.logging import get_logger
from libs.common.io import DynamoDBClient

logger = get_logger(__name__)


class CostTracker:
    """Track costs per agent and task."""

    def __init__(self) -> None:
        self.config = get_config()
        self.dynamodb = DynamoDBClient()
        self.cost_table = self.config.get_table_name("aurora-costs-{env}")

    def record_cost(
        self,
        agent_name: str,
        task_id: str,
        cost_gbp: float,
        resource_type: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Record cost for an agent task."""
        item = {
            "agent_name": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "cost_gbp": Decimal(str(cost_gbp)),
            "resource_type": resource_type,
            "metadata": metadata or {},
        }
        self.dynamodb.put_item(self.cost_table, item)
        logger.info(
            f"Recorded cost: £{cost_gbp:.2f} for {agent_name}",
            agent_name=agent_name,
            task_id=task_id,
            cost_gbp=cost_gbp,
        )

    def get_agent_spend(
        self,
        agent_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Get total spend for an agent in date range."""
        # In production, this would query DynamoDB or Cost Explorer
        # For now, return a placeholder
        logger.info(f"Getting spend for {agent_name}")
        return 0.0

    def get_daily_spend(self, date: Optional[datetime] = None) -> float:
        """Get total spend for a specific day."""
        if date is None:
            date = datetime.utcnow()

        # In production, query Cost Explorer API
        ce_client = boto3.client("ce", region_name=self.config.aws_region)

        start = date.strftime("%Y-%m-%d")
        end = (date + timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            response = ce_client.get_cost_and_usage(
                TimePeriod={"Start": start, "End": end},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                Filter={
                    "Tags": {
                        "Key": "Project",
                        "Values": ["aurora-energy-platform"],
                    }
                },
            )

            if response["ResultsByTime"]:
                amount = response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"]
                return float(amount)

            return 0.0

        except Exception as e:
            logger.warning(f"Failed to get daily spend: {e}")
            return 0.0


class CostEstimator:
    """Estimate costs for planned tasks."""

    # Cost estimates per resource type (in GBP)
    COST_ESTIMATES = {
        "sagemaker.training.ml.m5.xlarge": 0.28 / 3600,  # per second
        "sagemaker.training.ml.p3.2xlarge": 4.10 / 3600,
        "sagemaker.endpoint.ml.m5.xlarge": 0.28 / 3600,
        "glue.dpu": 0.44 / 3600,
        "lambda.gb_second": 0.0000166667,
        "dynamodb.read_unit": 0.00025 / 3600,
        "dynamodb.write_unit": 0.00125 / 3600,
        "s3.storage_gb_month": 0.023 / 30 / 24,  # per hour
        "s3.get_request": 0.0000004,
        "s3.put_request": 0.000005,
    }

    def estimate_training_cost(
        self,
        instance_type: str,
        duration_seconds: int,
    ) -> float:
        """Estimate cost for a training job."""
        cost_key = f"sagemaker.training.{instance_type}"
        cost_per_second = self.COST_ESTIMATES.get(cost_key, 0.28 / 3600)
        return cost_per_second * duration_seconds

    def estimate_batch_prediction_cost(
        self,
        num_records: int,
        instance_type: str = "ml.m5.xlarge",
    ) -> float:
        """Estimate cost for batch predictions."""
        # Rough estimate: 1000 records per minute on m5.xlarge
        duration_seconds = max(60, num_records / 1000 * 60)
        cost_key = f"sagemaker.training.{instance_type}"
        cost_per_second = self.COST_ESTIMATES.get(cost_key, 0.28 / 3600)
        return cost_per_second * duration_seconds

    def estimate_etl_cost(
        self,
        num_dpus: int,
        duration_seconds: int,
    ) -> float:
        """Estimate cost for Glue ETL job."""
        cost_per_second = self.COST_ESTIMATES["glue.dpu"]
        return cost_per_second * num_dpus * duration_seconds


class BudgetGuard:
    """Enforce budget limits and cost ceilings."""

    def __init__(self) -> None:
        self.config = get_config()
        self.tracker = CostTracker()
        self.estimator = CostEstimator()

    def check_daily_budget(self) -> bool:
        """Check if daily budget has been exceeded."""
        daily_spend = self.tracker.get_daily_spend()
        if daily_spend >= self.config.daily_budget_gbp:
            logger.warning(
                f"Daily budget exceeded: £{daily_spend:.2f} / £{self.config.daily_budget_gbp:.2f}"
            )
            return False
        return True

    def check_task_cost_ceiling(
        self,
        agent_name: str,
        estimated_cost: float,
        ceiling: Optional[float] = None,
    ) -> bool:
        """Check if task estimated cost is within ceiling."""
        ceiling = ceiling or self.config.task_cost_ceiling_gbp

        if estimated_cost > ceiling:
            logger.warning(
                f"Task cost ceiling exceeded for {agent_name}: "
                f"£{estimated_cost:.2f} > £{ceiling:.2f}"
            )
            return False

        return True

    def check_can_run_task(
        self,
        agent_name: str,
        estimated_cost: float,
    ) -> tuple[bool, str]:
        """Check if task can run given budget constraints."""
        if not self.check_daily_budget():
            return False, "Daily budget exceeded"

        if not self.check_task_cost_ceiling(agent_name, estimated_cost):
            return False, f"Task cost ceiling exceeded: £{estimated_cost:.2f}"

        # Check if task would push us over daily budget
        daily_spend = self.tracker.get_daily_spend()
        if daily_spend + estimated_cost > self.config.daily_budget_gbp:
            return (
                False,
                f"Task would exceed daily budget: "
                f"£{daily_spend:.2f} + £{estimated_cost:.2f} > £{self.config.daily_budget_gbp:.2f}",
            )

        return True, "OK"
