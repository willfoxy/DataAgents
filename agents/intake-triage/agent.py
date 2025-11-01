"""Intake Triage Agent - capture and convert objectives into task specs."""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import re

from libs.common.types import GraphState, RunStatus, TaskPriority, TaskSpec
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class IntakeTriage:
    """
    Intake Triage Agent.

    Responsibilities:
    - Capture objectives from tickets, prompts, KPI dashboards
    - Convert high-level goals into actionable task specs
    - Validate requests against policies
    - Request clarification for ambiguous requests
    - Reject invalid requests with clear reasons
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Goal patterns for common requests
        self.goal_patterns = {
            r"reduce churn( by (\d+)%)?": {
                "task": "daily_churn_pipeline",
                "goal_type": "churn_reduction",
            },
            r"forecast (load|demand|consumption)": {
                "task": "forecast_load",
                "goal_type": "load_forecasting",
            },
            r"optimize (pricing|tariff)": {
                "task": "optimize_pricing",
                "goal_type": "pricing_optimization",
            },
            r"detect (fraud|anomaly)": {
                "task": "detect_fraud",
                "goal_type": "fraud_detection",
            },
            r"predict (customer )?acquisition": {
                "task": "train_acquisition",
                "goal_type": "acquisition_forecasting",
            },
            r"segment customers": {
                "task": "customer_segmentation",
                "goal_type": "segmentation",
            },
            r"model (portfolio )?risk": {
                "task": "model_portfolio_risk",
                "goal_type": "risk_modeling",
            },
        }

    @trace_agent("intake-triage")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute intake triage.

        Args:
            state: Current graph state

        Returns:
            Outputs from triage including task spec or rejection reason
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="intake-triage",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting intake triage", task_id=state.task_id)

        try:
            request_text = state.inputs.get("request", "")
            source = state.inputs.get("source", "prompt")  # jira, prompt, kpi_dashboard

            # Parse the request
            parsed_goal = await self._parse_request(request_text)

            if not parsed_goal:
                # Ambiguous request - needs clarification
                return await self._request_clarification(state, request_text)

            # Validate the request
            validation = await self._validate_request(state, parsed_goal)

            if not validation["valid"]:
                # Reject with reason
                return await self._reject_request(state, validation["reason"])

            # Create task spec
            task_spec = await self._create_task_spec(state, parsed_goal)

            # Track costs
            cost_gbp = 0.1  # Minimal cost for triage
            self.cost_tracker.record_cost(
                agent_name="intake-triage",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="nlp_processing",
                metadata={"source": source, "run_id": run_id},
            )

            logger.info(
                "Intake triage completed",
                task_id=state.task_id,
                task_type=parsed_goal["task"],
            )

            return {
                "status": "success",
                "task_spec": task_spec.model_dump(),
                "parsed_goal": parsed_goal,
                "source": source,
            }

        except Exception as e:
            logger.error(f"Intake triage failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "intake-triage",
            }

    async def _parse_request(self, request_text: str) -> Optional[Dict[str, Any]]:
        """Parse request text to extract goal."""
        request_lower = request_text.lower()

        # Try to match against known patterns
        for pattern, goal_info in self.goal_patterns.items():
            match = re.search(pattern, request_lower)
            if match:
                parsed = {
                    "task": goal_info["task"],
                    "goal_type": goal_info["goal_type"],
                    "original_text": request_text,
                }

                # Extract numeric targets if present
                if match.groups():
                    for group in match.groups():
                        if group and group.isdigit():
                            parsed["target_value"] = int(group)

                logger.info("Request parsed", parsed_goal=parsed)
                return parsed

        # If no pattern matched, return None (ambiguous)
        logger.warning("Unable to parse request", request_text=request_text)
        return None

    async def _validate_request(
        self,
        state: GraphState,
        parsed_goal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate request against policies."""
        # Check if business justification is provided
        if "justification" not in state.inputs:
            return {
                "valid": False,
                "reason": "Missing business justification",
            }

        # Check estimated cost
        estimated_cost = state.inputs.get("estimated_cost_gbp", 0.0)
        if estimated_cost > 50.0:  # £50 per task limit
            return {
                "valid": False,
                "reason": f"Estimated cost {estimated_cost} exceeds limit of £50",
            }

        # Check concurrent tasks (simulated)
        # In production, query DynamoDB for active tasks by user
        concurrent_tasks = state.context.get("user_active_tasks", 0)
        if concurrent_tasks >= 5:
            return {
                "valid": False,
                "reason": "Maximum concurrent tasks (5) reached",
            }

        return {
            "valid": True,
            "reason": "All validations passed",
        }

    async def _create_task_spec(
        self,
        state: GraphState,
        parsed_goal: Dict[str, Any]
    ) -> TaskSpec:
        """Create task specification."""
        # Determine priority
        priority_str = state.inputs.get("priority", "medium")
        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }
        priority = priority_map.get(priority_str, TaskPriority.MEDIUM)

        # Set deadline
        deadline_hours = {
            TaskPriority.CRITICAL: 4,
            TaskPriority.HIGH: 24,
            TaskPriority.MEDIUM: 72,
            TaskPriority.LOW: 168,  # 1 week
        }
        deadline = datetime.utcnow() + timedelta(hours=deadline_hours[priority])

        task_spec = TaskSpec(
            task_id=state.task_id,
            agent_name="supervisor-director",  # Route to supervisor
            priority=priority,
            inputs={
                "operation": "decompose",
                "goal": parsed_goal["task"],
                "goal_type": parsed_goal["goal_type"],
                "original_request": parsed_goal["original_text"],
                "target_value": parsed_goal.get("target_value"),
            },
            deadline=deadline,
        )

        logger.info("Task spec created", task_id=task_spec.task_id, priority=priority)
        return task_spec

    async def _request_clarification(
        self,
        state: GraphState,
        request_text: str
    ) -> Dict[str, Any]:
        """Request clarification for ambiguous request."""
        logger.info("Requesting clarification", request_text=request_text)

        clarification_questions = [
            "What is the specific business objective? (e.g., reduce churn, forecast load, optimize pricing)",
            "What is the target metric or KPI?",
            "What is the desired timeline?",
            "Is there a specific dataset or customer segment to focus on?",
        ]

        return {
            "status": "clarification_needed",
            "request_text": request_text,
            "questions": clarification_questions,
            "assign_to": "human-loop-coordinator",
        }

    async def _reject_request(
        self,
        state: GraphState,
        reason: str
    ) -> Dict[str, Any]:
        """Reject request with reason."""
        logger.warning("Request rejected", reason=reason, task_id=state.task_id)

        # Log rejection to S3 (in production)
        rejection_record = {
            "task_id": state.task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "request": state.inputs.get("request"),
            "reason": reason,
            "source": state.inputs.get("source"),
        }

        # In production: write to S3 rejected bucket
        logger.info("Rejection logged", rejection_record=rejection_record)

        return {
            "status": "rejected",
            "reason": reason,
            "rejection_record": rejection_record,
        }


async def create_intake_triage() -> IntakeTriage:
    """Factory function to create intake triage agent."""
    return IntakeTriage()
