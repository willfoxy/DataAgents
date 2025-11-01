"""Supervisor Director Agent - orchestrates the 25-agent graph."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus, TaskSpec, TaskPriority
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client, DynamoDBClient
from libs.cost_meter.tracker import CostTracker, BudgetGuard
from libs.policy_guards.guards import PolicyGuard
from libs.observability.tracing import trace_agent

logger = get_logger(__name__)


class SupervisorAgent:
    """
    Supervisor Director Agent.

    Responsibilities:
    - Goal decomposition
    - Task routing to specialist agents
    - Arbitration and safety checks
    - Cost monitoring
    - SLA enforcement
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.dynamodb = DynamoDBClient()
        self.cost_tracker = CostTracker()
        self.budget_guard = BudgetGuard()
        self.policy_guard = PolicyGuard()

        # Agent routing map
        self.agent_routes = {
            "churn_forecast": "churn-forecast-modeler",
            "acquisition_forecast": "acquisition-forecast-modeler",
            "load_forecast": "load-consumption-forecast",
            "pricing_optimization": "pricing-tariff-optimizer",
            "risk_modeling": "portfolio-risk-modeler",
            "data_quality": "data-contracts-quality",
            "feature_engineering": "feature-store-manager",
            "model_deployment": "mlops-deployer",
            "monitoring": "monitoring-drift-watcher",
            "reporting": "viz-storyteller",
        }

    @trace_agent("supervisor-director")
    async def plan_and_route(
        self,
        task_spec: TaskSpec,
    ) -> GraphState:
        """
        Plan task execution and route to appropriate agents.

        Args:
            task_spec: Task specification

        Returns:
            Initial graph state
        """
        run_id = str(uuid.uuid4())

        bind_context(
            task_id=task_spec.task_id,
            run_id=run_id,
            agent_name="supervisor-director",
        )

        logger.info(
            f"Planning task: {task_spec.task_id}",
            task_id=task_spec.task_id,
            agent=task_spec.agent_name,
            priority=task_spec.priority.value,
        )

        # Safety and policy checks
        allowed, reason = await self._check_safety(task_spec)
        if not allowed:
            logger.error(f"Task rejected: {reason}")
            raise ValueError(f"Task not allowed: {reason}")

        # Decompose goal into subtasks
        subtasks = await self._decompose_goal(task_spec)

        # Create initial graph state
        state = GraphState(
            task_id=task_spec.task_id,
            run_id=run_id,
            current_agent="supervisor-director",
            status=RunStatus.IN_PROGRESS,
            inputs=task_spec.inputs,
            context={
                "priority": task_spec.priority.value,
                "deadline": task_spec.deadline.isoformat() if task_spec.deadline else None,
                "subtasks": subtasks,
            },
        )

        # Persist state
        await self._persist_state(state)

        logger.info(
            f"Task planned with {len(subtasks)} subtasks",
            task_id=task_spec.task_id,
            subtask_count=len(subtasks),
        )

        return state

    async def route_to_agent(
        self,
        state: GraphState,
    ) -> str:
        """
        Route task to next appropriate agent.

        Args:
            state: Current graph state

        Returns:
            Name of next agent
        """
        # Check if we have remaining subtasks
        subtasks = state.context.get("subtasks", [])

        if not subtasks:
            # All subtasks complete
            return "FINISH"

        # Get next subtask
        next_subtask = subtasks[0]
        task_type = next_subtask.get("type")

        # Route based on task type
        next_agent = self.agent_routes.get(task_type, "human-loop-coordinator")

        logger.info(
            f"Routing to {next_agent}",
            task_id=state.task_id,
            next_agent=next_agent,
            task_type=task_type,
        )

        # Update state
        state.current_agent = next_agent

        # Policy check
        allowed, reason = self.policy_guard.check_task_allowed(next_agent, state)
        if not allowed:
            logger.warning(f"Agent {next_agent} blocked: {reason}")
            # Route to human review instead
            return "human-loop-coordinator"

        # Budget check
        can_run, reason = self.budget_guard.check_can_run_task(
            next_agent,
            estimated_cost=5.0,  # Rough estimate
        )

        if not can_run:
            logger.error(f"Budget check failed: {reason}")
            return "PAUSE"

        return next_agent

    async def verify_and_merge(
        self,
        state: GraphState,
        agent_outputs: Dict[str, Any],
    ) -> GraphState:
        """
        Verify agent outputs and merge into state.

        Args:
            state: Current graph state
            agent_outputs: Outputs from agent execution

        Returns:
            Updated graph state
        """
        current_agent = state.current_agent

        logger.info(
            f"Verifying outputs from {current_agent}",
            agent=current_agent,
            task_id=state.task_id,
        )

        # Validate outputs
        try:
            self.policy_guard.validate_outputs(current_agent, agent_outputs)
        except Exception as e:
            logger.error(f"Output validation failed: {e}")
            state.errors.append(f"Validation failed: {str(e)}")
            state.status = RunStatus.FAILED
            return state

        # Merge outputs
        state.outputs.update(agent_outputs)

        # Remove completed subtask
        subtasks = state.context.get("subtasks", [])
        if subtasks:
            completed = subtasks.pop(0)
            state.context["subtasks"] = subtasks
            logger.info(f"Completed subtask: {completed.get('type')}")

        # Update state
        state.updated_at = datetime.utcnow()

        # Persist
        await self._persist_state(state)

        return state

    async def _check_safety(
        self,
        task_spec: TaskSpec,
    ) -> tuple[bool, Optional[str]]:
        """Run safety and compliance checks."""
        # Check daily budget
        if not self.budget_guard.check_daily_budget():
            return False, "Daily budget exceeded"

        # Check task priority vs. system load
        # In production, query metrics to determine load

        return True, None

    async def _decompose_goal(
        self,
        task_spec: TaskSpec,
    ) -> List[Dict[str, Any]]:
        """
        Decompose high-level goal into subtasks.

        This is simplified - in production, use LLM-based planning.
        """
        agent_name = task_spec.agent_name

        # Example decomposition for churn pipeline
        if "churn" in agent_name:
            return [
                {"type": "data_quality", "description": "Validate input data"},
                {"type": "feature_engineering", "description": "Update feature store"},
                {"type": "churn_forecast", "description": "Train/predict churn"},
                {"type": "monitoring", "description": "Check for drift"},
                {"type": "reporting", "description": "Generate report"},
            ]

        # Default: single task
        return [{"type": agent_name, "description": task_spec.inputs.get("description", "")}]

    async def _persist_state(
        self,
        state: GraphState,
    ) -> None:
        """Persist graph state to DynamoDB."""
        table_name = self.config.get_table_name(self.config.dynamodb_state_table)

        item = {
            "task_id": state.task_id,
            "run_id": state.run_id,
            "current_agent": state.current_agent,
            "status": state.status.value,
            "inputs": state.inputs,
            "outputs": state.outputs,
            "context": state.context,
            "cost_so_far_gbp": float(state.cost_so_far_gbp),
            "risk_score": float(state.risk_score),
            "retry_count": state.retry_count,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
        }

        self.dynamodb.put_item(table_name, item)

        # Also log to S3 for audit trail
        audit_key = f"supervisor/{state.run_id}/state_{datetime.utcnow().isoformat()}.json"
        self.s3.write_json(
            data=state.model_dump(mode="json"),
            bucket=self.config.audit_bucket,
            key=audit_key,
        )
