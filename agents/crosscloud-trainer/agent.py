"""Crosscloud Trainer Agent - orchestrate training across AWS, Azure, Databricks."""

from typing import Dict, Any
from datetime import datetime
import uuid

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker
from libs.trainer_backends import SageMakerBackend, AzureMLBackend, DatabricksBackend

logger = get_logger(__name__)


class CrosscloudTrainer:
    """
    Crosscloud Trainer Agent.

    Responsibilities:
    - Orchestrate training across AWS SageMaker, Azure ML, Databricks
    - Select optimal backend based on cost and performance
    - Handle data transfer between clouds
    - Track multi-cloud training jobs
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Initialize backends
        self.backends = {
            "sagemaker": SageMakerBackend(),
            "azure": AzureMLBackend(),
            "databricks": DatabricksBackend(),
        }

    @trace_agent("crosscloud-trainer")
    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute cross-cloud training."""
        run_id = str(uuid.uuid4())
        bind_context(agent_name="crosscloud-trainer", task_id=state.task_id, run_id=run_id)
        logger.info("Starting crosscloud trainer", task_id=state.task_id)

        try:
            backend = state.inputs.get("backend", "auto")

            # Auto-select backend if needed
            if backend == "auto":
                backend = await self._select_backend(state)

            # Train on selected backend
            training_result = await self._train(state, backend)

            self.cost_tracker.record_cost(
                agent_name="crosscloud-trainer",
                task_id=state.task_id,
                cost_gbp=training_result["cost_gbp"],
                resource_type=f"{backend}.training",
                metadata={"backend": backend, "run_id": run_id},
            )

            return {
                "status": "success",
                "backend": backend,
                "training_result": training_result,
            }

        except Exception as e:
            logger.error(f"Crosscloud training failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "agent": "crosscloud-trainer"}

    async def _select_backend(self, state: GraphState) -> str:
        """Select optimal backend based on cost and availability."""
        logger.info("Auto-selecting backend")

        # Simple cost-based selection
        backend_costs = {
            "sagemaker": 15.0,
            "databricks": 12.0,
            "azure": 14.0,
        }

        # Check budget constraints
        budget_remaining = 150.0 - state.cost_so_far_gbp

        for backend, cost in sorted(backend_costs.items(), key=lambda x: x[1]):
            if cost <= budget_remaining:
                logger.info("Backend selected", backend=backend, cost=cost)
                return backend

        return "sagemaker"  # Fallback

    async def _train(self, state: GraphState, backend: str) -> Dict[str, Any]:
        """Train model on selected backend."""
        logger.info("Training model", backend=backend)

        backend_handler = self.backends[backend]

        # In production: call actual backend
        # result = await backend_handler.train(
        #     training_job_name=f"aurora-{state.task_id}",
        #     algorithm="xgboost",
        #     hyperparameters={...},
        #     data_uri=state.inputs.get("data_uri"),
        # )

        # Simulate training
        training_result = {
            "job_id": f"{backend}-job-{uuid.uuid4().hex[:8]}",
            "status": "completed",
            "model_uri": f"{backend}://models/aurora/model-{datetime.utcnow().strftime('%Y%m%d')}",
            "metrics": {"auc": 0.84, "precision": 0.78},
            "duration_minutes": 45,
            "cost_gbp": 12.0 if backend == "databricks" else 15.0,
        }

        logger.info("Training completed", backend=backend, job_id=training_result["job_id"])

        return training_result


async def create_crosscloud_trainer() -> CrosscloudTrainer:
    """Factory function to create crosscloud trainer."""
    return CrosscloudTrainer()
