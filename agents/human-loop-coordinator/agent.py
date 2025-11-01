"""Human Loop Coordinator Agent - manage human review and approval workflows."""

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


class HumanLoopCoordinator:
    """
    Human Loop Coordinator Agent.

    Responsibilities:
    - Route tasks requiring human review
    - Manage approval workflows
    - Collect and incorporate human feedback
    - Track review SLAs
    - Escalate blocked tasks
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("human-loop-coordinator")
    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute human loop coordination."""
        run_id = str(uuid.uuid4())
        bind_context(agent_name="human-loop-coordinator", task_id=state.task_id, run_id=run_id)
        logger.info("Starting human loop coordinator", task_id=state.task_id)

        try:
            operation = state.inputs.get("operation", "request_review")

            if operation == "request_review":
                outputs = await self._request_review(state)
            elif operation == "process_feedback":
                outputs = await self._process_feedback(state)
            else:
                outputs = await self._check_status(state)

            self.cost_tracker.record_cost(
                agent_name="human-loop-coordinator",
                task_id=state.task_id,
                cost_gbp=0.1,
                resource_type="coordination",
                metadata={"operation": operation, "run_id": run_id},
            )

            return outputs

        except Exception as e:
            logger.error(f"Human loop coordination failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "agent": "human-loop-coordinator"}

    async def _request_review(self, state: GraphState) -> Dict[str, Any]:
        """Request human review."""
        logger.info("Requesting human review")

        review_type = state.inputs.get("review_type", "model_approval")
        priority = state.inputs.get("priority", "medium")

        review_request = {
            "review_id": f"rev-{uuid.uuid4().hex[:8]}",
            "type": review_type,
            "priority": priority,
            "reviewer": "data-science-team",
            "sla_hours": 24 if priority == "high" else 72,
            "status": "pending",
            "context": state.inputs.get("context", {}),
        }

        # In production: send to review queue (SQS, Jira, etc.)
        logger.info("Review requested", review_id=review_request["review_id"])

        return {"status": "success", "review_request": review_request}

    async def _process_feedback(self, state: GraphState) -> Dict[str, Any]:
        """Process human feedback."""
        logger.info("Processing feedback")

        feedback = state.inputs.get("feedback", {})
        decision = feedback.get("decision", "approved")

        processed_feedback = {
            "decision": decision,
            "comments": feedback.get("comments", ""),
            "processed_at": datetime.utcnow().isoformat(),
            "next_action": "proceed" if decision == "approved" else "revise",
        }

        logger.info("Feedback processed", decision=decision)

        return {"status": "success", "feedback": processed_feedback}

    async def _check_status(self, state: GraphState) -> Dict[str, Any]:
        """Check review status."""
        review_id = state.inputs.get("review_id")
        logger.info("Checking review status", review_id=review_id)

        # Simulate status check
        status = {
            "review_id": review_id,
            "status": "in_progress",
            "assigned_to": "reviewer@aurora.com",
            "time_remaining_hours": 18,
        }

        return {"status": "success", "review_status": status}


async def create_human_loop_coordinator() -> HumanLoopCoordinator:
    """Factory function to create human loop coordinator."""
    return HumanLoopCoordinator()
