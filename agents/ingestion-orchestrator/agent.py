"""Ingestion Orchestrator Agent - orchestrate batch and stream data ingestion."""

from typing import Dict, Any, List
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus, DataLineage
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class IngestionOrchestrator:
    """
    Ingestion Orchestrator Agent.

    Responsibilities:
    - Orchestrate batch data ingestion from CRM, billing, smart meters
    - Handle streaming data from Kinesis/Kafka
    - Manage incremental loads
    - Track ingestion lineage
    - Handle schema evolution
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("ingestion-orchestrator")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """Execute ingestion orchestration."""
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="ingestion-orchestrator",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting ingestion orchestrator", task_id=state.task_id)

        try:
            mode = state.inputs.get("mode", "batch")  # batch or stream
            source = state.inputs.get("source", "crm")

            if mode == "batch":
                outputs = await self._ingest_batch(state, source)
            else:
                outputs = await self._ingest_stream(state, source)

            # Track costs
            cost_gbp = 2.0
            self.cost_tracker.record_cost(
                agent_name="ingestion-orchestrator",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="glue.job",
                metadata={"mode": mode, "source": source, "run_id": run_id},
            )

            logger.info("Ingestion completed", task_id=state.task_id, mode=mode)

            return outputs

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "ingestion-orchestrator",
            }

    async def _ingest_batch(self, state: GraphState, source: str) -> Dict[str, Any]:
        """Ingest batch data."""
        logger.info("Ingesting batch data", source=source)

        ds = datetime.utcnow().strftime("%Y%m%d")
        target_uri = f"s3://{self.config.data_bucket}/bronze/{source}/ds={ds}/"

        # Simulate batch ingestion
        # In production: use Glue jobs, EMR, or custom PySpark

        ingested_records = 50000
        bytes_written = 5242880

        # Create lineage record
        lineage = DataLineage(
            source_uri=f"api://{source}/export",
            target_uri=target_uri,
            transformation="batch_copy",
            agent_name="ingestion-orchestrator",
            run_id=state.run_id,
            metadata={
                "records": ingested_records,
                "bytes": bytes_written,
            },
        )

        logger.info("Batch ingestion complete", records=ingested_records)

        return {
            "status": "success",
            "mode": "batch",
            "source": source,
            "target_uri": target_uri,
            "records_ingested": ingested_records,
            "bytes_written": bytes_written,
            "lineage": lineage.model_dump(),
        }

    async def _ingest_stream(self, state: GraphState, source: str) -> Dict[str, Any]:
        """Ingest streaming data."""
        logger.info("Ingesting stream data", source=source)

        # Simulate stream ingestion
        # In production: Kinesis Data Firehose, Kafka Connect

        records_processed = 1000
        checkpoint_sequence = "49590338271490256608559692538361571095921575989136588898"

        logger.info("Stream ingestion complete", records=records_processed)

        return {
            "status": "success",
            "mode": "stream",
            "source": source,
            "records_processed": records_processed,
            "checkpoint_sequence": checkpoint_sequence,
        }


async def create_ingestion_orchestrator() -> IngestionOrchestrator:
    """Factory function to create ingestion orchestrator."""
    return IngestionOrchestrator()
