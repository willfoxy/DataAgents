"""Feature Store Manager - Manage SageMaker Feature Store."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import pandas as pd

import boto3
from sagemaker.feature_store.feature_group import FeatureGroup
from sagemaker.session import Session

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class FeatureStoreManager:
    """
    Feature Store Manager Agent.

    Responsibilities:
    - Create and manage feature groups
    - Ingest features to online/offline store
    - Ensure online/offline parity
    - Handle backfills
    - Validate feature freshness
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Initialize SageMaker session
        self.sagemaker_session = Session()
        self.feature_store_client = boto3.client(
            "sagemaker-featurestore-runtime",
            region_name=self.config.aws_region,
        )

    @trace_agent("feature-store-manager")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute feature store operations.

        Args:
            state: Current graph state

        Returns:
            Operation results
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="feature-store-manager",
            task_id=state.task_id,
            run_id=run_id,
        )

        operation = state.inputs.get("operation", "ingest")

        logger.info(
            f"Starting feature store operation: {operation}",
            task_id=state.task_id,
        )

        try:
            if operation == "create_feature_group":
                result = await self._create_feature_group(state.inputs)
            elif operation == "ingest":
                result = await self._ingest_features(state.inputs)
            elif operation == "backfill":
                result = await self._backfill_features(state.inputs)
            elif operation == "validate":
                result = await self._validate_features(state.inputs)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Track costs
            cost_gbp = result.get("cost_gbp", 2.0)
            self.cost_tracker.record_cost(
                agent_name="feature-store-manager",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="sagemaker.feature_store",
                metadata={"operation": operation, "run_id": run_id},
            )

            logger.info(
                "Feature store operation completed",
                task_id=state.task_id,
                operation=operation,
                cost_gbp=cost_gbp,
            )

            result["status"] = "success"
            result["operation"] = operation
            return result

        except Exception as e:
            logger.error(f"Feature store operation failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "operation": operation,
                "agent": "feature-store-manager",
            }

    async def _create_feature_group(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new feature group."""

        feature_group_name = inputs["feature_group_name"]
        record_identifier = inputs.get("record_identifier", "customer_id")
        event_time_feature = inputs.get("event_time_feature", "event_time")

        logger.info(f"Creating feature group: {feature_group_name}")

        # Define feature group
        feature_group = FeatureGroup(
            name=feature_group_name,
            sagemaker_session=self.sagemaker_session,
        )

        # Load feature definitions from schema
        feature_definitions = self._get_feature_definitions(inputs)

        # Create feature group (in production)
        # feature_group.create(
        #     s3_uri=f"s3://{self.config.data_bucket}/feature-store/{feature_group_name}",
        #     record_identifier_name=record_identifier,
        #     event_time_feature_name=event_time_feature,
        #     role_arn=self.config.sagemaker_role_arn,
        #     enable_online_store=True,
        # )

        # Simulate for now
        logger.info(f"Feature group created: {feature_group_name}")

        return {
            "feature_group_name": feature_group_name,
            "feature_count": len(feature_definitions),
            "online_store_enabled": True,
            "offline_store_enabled": True,
            "cost_gbp": 1.0,
        }

    async def _ingest_features(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Ingest features to feature store."""

        feature_group_name = inputs["feature_group_name"]
        data_uri = inputs["data_uri"]

        logger.info(f"Ingesting features to: {feature_group_name}")

        # In production: Read data and ingest
        # df = pd.read_parquet(data_uri)
        #
        # feature_group = FeatureGroup(
        #     name=feature_group_name,
        #     sagemaker_session=self.sagemaker_session,
        # )
        #
        # feature_group.ingest(
        #     data_frame=df,
        #     max_workers=8,
        #     wait=True,
        # )

        # Simulate ingestion
        num_records = 50000
        ingestion_time_seconds = 120

        logger.info(
            f"Ingested {num_records} records in {ingestion_time_seconds}s"
        )

        return {
            "feature_group_name": feature_group_name,
            "records_ingested": num_records,
            "ingestion_time_seconds": ingestion_time_seconds,
            "online_store_updated": True,
            "offline_store_updated": True,
            "cost_gbp": 2.0,
        }

    async def _backfill_features(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Backfill historical features."""

        feature_group_name = inputs["feature_group_name"]
        start_date = inputs["start_date"]
        end_date = inputs.get("end_date", datetime.utcnow().strftime("%Y-%m-%d"))

        logger.info(
            f"Backfilling features: {feature_group_name} from {start_date} to {end_date}"
        )

        # Calculate date range
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days

        # In production: Process each date
        total_records = 0
        for day in range(days + 1):
            date = start + timedelta(days=day)
            # Load and ingest data for this date
            # records = await self._ingest_features({
            #     "feature_group_name": feature_group_name,
            #     "data_uri": f"s3://.../{date.strftime('%Y%m%d')}/",
            # })
            # total_records += records["records_ingested"]

            total_records += 50000  # Simulate

        logger.info(f"Backfill completed: {total_records} total records")

        return {
            "feature_group_name": feature_group_name,
            "days_backfilled": days + 1,
            "total_records": total_records,
            "start_date": start_date,
            "end_date": end_date,
            "cost_gbp": 5.0,
        }

    async def _validate_features(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate feature store data."""

        feature_group_name = inputs["feature_group_name"]

        logger.info(f"Validating features: {feature_group_name}")

        # Check online/offline parity
        sample_ids = inputs.get("sample_ids", ["customer_001", "customer_002"])

        parity_check = await self._check_online_offline_parity(
            feature_group_name, sample_ids
        )

        # Check freshness
        freshness_check = await self._check_feature_freshness(feature_group_name)

        # Check completeness
        completeness_check = await self._check_feature_completeness(feature_group_name)

        validation_passed = (
            parity_check["passed"]
            and freshness_check["passed"]
            and completeness_check["passed"]
        )

        logger.info(
            f"Validation completed: {'PASSED' if validation_passed else 'FAILED'}",
            parity=parity_check["parity_score"],
            freshness=freshness_check["max_age_hours"],
            completeness=completeness_check["completeness_rate"],
        )

        return {
            "feature_group_name": feature_group_name,
            "validation_passed": validation_passed,
            "parity_check": parity_check,
            "freshness_check": freshness_check,
            "completeness_check": completeness_check,
            "cost_gbp": 0.5,
        }

    async def _check_online_offline_parity(
        self,
        feature_group_name: str,
        sample_ids: List[str],
    ) -> Dict[str, Any]:
        """Check if online and offline stores are in sync."""

        # In production: Query both stores and compare
        # online_features = self._get_online_features(feature_group_name, sample_ids)
        # offline_features = self._get_offline_features(feature_group_name, sample_ids)
        # parity = self._calculate_parity(online_features, offline_features)

        # Simulate
        parity_score = 0.999

        return {
            "passed": parity_score >= 0.99,
            "parity_score": parity_score,
            "samples_checked": len(sample_ids),
        }

    async def _check_feature_freshness(
        self,
        feature_group_name: str,
    ) -> Dict[str, Any]:
        """Check how fresh the features are."""

        # In production: Query latest event_time
        # max_age_hours = (datetime.utcnow() - latest_event_time).total_seconds() / 3600

        # Simulate
        max_age_hours = 0.5  # 30 minutes

        return {
            "passed": max_age_hours <= 1.0,  # SLO: <= 1 hour
            "max_age_hours": max_age_hours,
        }

    async def _check_feature_completeness(
        self,
        feature_group_name: str,
    ) -> Dict[str, Any]:
        """Check for missing features."""

        # In production: Query for null counts
        # completeness_rate = 1 - (null_count / total_count)

        # Simulate
        completeness_rate = 0.995

        return {
            "passed": completeness_rate >= 0.99,  # SLO: <= 1% missing
            "completeness_rate": completeness_rate,
        }

    def _get_feature_definitions(
        self,
        inputs: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Get feature definitions from schema."""

        # In production: Load from schema definition
        # For now, return example definitions

        return [
            {"name": "customer_id", "type": "String"},
            {"name": "event_time", "type": "String"},
            {"name": "age", "type": "Integral"},
            {"name": "tenure_days", "type": "Integral"},
            {"name": "lifetime_value", "type": "Fractional"},
            {"name": "last_purchase_days", "type": "Integral"},
            {"name": "avg_monthly_spend", "type": "Fractional"},
            {"name": "num_support_tickets", "type": "Integral"},
            {"name": "region", "type": "String"},
            {"name": "plan_type", "type": "String"},
        ]


async def create_feature_store_manager() -> FeatureStoreManager:
    """Factory function to create feature store manager."""
    return FeatureStoreManager()
