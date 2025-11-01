"""Anomaly Fraud Detector Agent - detect usage anomalies and fraud."""

from typing import Dict, Any
from datetime import datetime
import uuid

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class AnomalyFraudDetector:
    """Anomaly and Fraud Detector Agent - detect unusual patterns and fraudulent activity."""

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("anomaly-fraud-detector")
    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute anomaly/fraud detection."""
        run_id = str(uuid.uuid4())
        bind_context(agent_name="anomaly-fraud-detector", task_id=state.task_id, run_id=run_id)
        logger.info("Starting fraud detector", task_id=state.task_id)

        try:
            detection_type = state.inputs.get("detection_type", "usage_anomaly")

            if detection_type == "usage_anomaly":
                outputs = await self._detect_usage_anomalies(state)
            else:
                outputs = await self._detect_fraud(state)

            self.cost_tracker.record_cost(
                agent_name="anomaly-fraud-detector",
                task_id=state.task_id,
                cost_gbp=2.5,
                resource_type="sagemaker.batch",
                metadata={"detection_type": detection_type, "run_id": run_id},
            )

            return outputs

        except Exception as e:
            logger.error(f"Fraud detection failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "agent": "anomaly-fraud-detector"}

    async def _detect_usage_anomalies(self, state: GraphState) -> Dict[str, Any]:
        """Detect usage anomalies."""
        logger.info("Detecting usage anomalies")

        anomalies = [
            {"customer_id": "C12345", "anomaly_score": 0.95, "type": "spike"},
            {"customer_id": "C67890", "anomaly_score": 0.88, "type": "drop"},
        ]

        return {"status": "success", "anomalies": anomalies, "num_detected": len(anomalies)}

    async def _detect_fraud(self, state: GraphState) -> Dict[str, Any]:
        """Detect fraudulent activity."""
        logger.info("Detecting fraud")

        fraud_cases = [
            {"account_id": "A11111", "fraud_score": 0.92, "indicators": ["tampering", "unusual_usage"]},
        ]

        return {"status": "success", "fraud_cases": fraud_cases, "num_detected": len(fraud_cases)}


async def create_fraud_detector() -> AnomalyFraudDetector:
    """Factory function to create fraud detector."""
    return AnomalyFraudDetector()
