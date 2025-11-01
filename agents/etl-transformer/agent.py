"""ETL Transformer Agent - Bronze to Silver to Gold transformations."""

from typing import Dict, Any
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus, DataLineage
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class ETLTransformer:
    """
    ETL Transformer Agent.

    Responsibilities:
    - Transform Bronze (raw) to Silver (cleansed)
    - Transform Silver to Gold (curated/aggregated)
    - Handle data quality transformations
    - Apply business logic
    - Track transformation lineage
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("etl-transformer")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """Execute ETL transformation."""
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="etl-transformer",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting ETL transformer", task_id=state.task_id)

        try:
            transformation_type = state.inputs.get("transformation", "bronze_to_silver")

            if transformation_type == "bronze_to_silver":
                outputs = await self._transform_bronze_to_silver(state)
            elif transformation_type == "silver_to_gold":
                outputs = await self._transform_silver_to_gold(state)
            else:
                raise ValueError(f"Unknown transformation: {transformation_type}")

            # Track costs
            cost_gbp = 3.0
            self.cost_tracker.record_cost(
                agent_name="etl-transformer",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="glue.job",
                metadata={"transformation": transformation_type, "run_id": run_id},
            )

            logger.info("ETL transformation completed", task_id=state.task_id)

            return outputs

        except Exception as e:
            logger.error(f"ETL transformation failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "etl-transformer",
            }

    async def _transform_bronze_to_silver(self, state: GraphState) -> Dict[str, Any]:
        """Transform Bronze to Silver."""
        logger.info("Transforming Bronze to Silver")

        table = state.inputs.get("table", "customers")
        ds = datetime.utcnow().strftime("%Y%m%d")

        source_uri = f"s3://{self.config.data_bucket}/bronze/{table}/ds={ds}/"
        target_uri = f"s3://{self.config.data_bucket}/silver/{table}/ds={ds}/"

        # In production: PySpark transformations
        # - Deduplicate
        # - Validate schema
        # - Clean data (nulls, formats)
        # - Hash PII fields
        # - Apply business rules

        transformations_applied = [
            "deduplicate_by_primary_key",
            "hash_pii_fields",
            "validate_email_format",
            "standardize_dates",
            "remove_test_accounts",
        ]

        records_in = 50000
        records_out = 48500  # Some removed

        lineage = DataLineage(
            source_uri=source_uri,
            target_uri=target_uri,
            transformation="bronze_to_silver",
            agent_name="etl-transformer",
            run_id=state.run_id,
            metadata={
                "records_in": records_in,
                "records_out": records_out,
                "transformations": transformations_applied,
            },
        )

        logger.info("Bronze to Silver complete", records_out=records_out)

        return {
            "status": "success",
            "transformation": "bronze_to_silver",
            "source_uri": source_uri,
            "target_uri": target_uri,
            "records_in": records_in,
            "records_out": records_out,
            "transformations": transformations_applied,
            "lineage": lineage.model_dump(),
        }

    async def _transform_silver_to_gold(self, state: GraphState) -> Dict[str, Any]:
        """Transform Silver to Gold."""
        logger.info("Transforming Silver to Gold")

        table = state.inputs.get("table", "customers")
        ds = datetime.utcnow().strftime("%Y%m%d")

        source_uri = f"s3://{self.config.data_bucket}/silver/{table}/ds={ds}/"
        target_uri = f"s3://{self.config.data_bucket}/gold/{table}/ds={ds}/"

        # In production: PySpark aggregations
        # - Join with other tables
        # - Calculate metrics
        # - Create summary tables
        # - Apply business logic

        aggregations_applied = [
            "calculate_customer_lifetime_value",
            "aggregate_monthly_usage",
            "compute_churn_labels",
            "join_with_contracts",
        ]

        records_out = 48500

        lineage = DataLineage(
            source_uri=source_uri,
            target_uri=target_uri,
            transformation="silver_to_gold",
            agent_name="etl-transformer",
            run_id=state.run_id,
            metadata={
                "records_out": records_out,
                "aggregations": aggregations_applied,
            },
        )

        logger.info("Silver to Gold complete", records_out=records_out)

        return {
            "status": "success",
            "transformation": "silver_to_gold",
            "source_uri": source_uri,
            "target_uri": target_uri,
            "records_out": records_out,
            "aggregations": aggregations_applied,
            "lineage": lineage.model_dump(),
        }


async def create_etl_transformer() -> ETLTransformer:
    """Factory function to create ETL transformer."""
    return ETLTransformer()
