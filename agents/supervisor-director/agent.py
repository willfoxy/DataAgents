"""Supervisor Director Agent - central orchestration and task routing."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import json

from libs.common.types import GraphState, RunStatus, TaskPriority
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class SupervisorDirector:
    """
    Supervisor Director Agent.

    Responsibilities:
    - Goal decomposition into subtasks
    - Task routing to specialist agents
    - Arbitration and conflict resolution
    - Safety and policy checks
    - SLA monitoring and enforcement
    - Overall system coordination
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Agent registry with capabilities
        self.agent_registry = {
            "intake-triage": {"domain": "control", "capability": "task_capture"},
            "data-cataloguer": {"domain": "data", "capability": "cataloguing"},
            "data-contracts-quality": {"domain": "data", "capability": "validation"},
            "ingestion-orchestrator": {"domain": "data", "capability": "ingestion"},
            "etl-transformer": {"domain": "data", "capability": "transformation"},
            "feature-store-manager": {"domain": "data", "capability": "feature_engineering"},
            "experiment-planner": {"domain": "model", "capability": "experimentation"},
            "churn-forecast-modeler": {"domain": "model", "capability": "churn_prediction"},
            "acquisition-forecast-modeler": {"domain": "model", "capability": "acquisition_prediction"},
            "load-consumption-forecast": {"domain": "model", "capability": "load_forecasting"},
            "pricing-tariff-optimizer": {"domain": "model", "capability": "pricing_optimization"},
            "portfolio-risk-modeler": {"domain": "model", "capability": "risk_modeling"},
            "trial-design-causal-inference": {"domain": "model", "capability": "causal_inference"},
            "anomaly-fraud-detector": {"domain": "model", "capability": "anomaly_detection"},
            "customer-segmentation-clv": {"domain": "model", "capability": "segmentation"},
            "prompt-model-evaluator": {"domain": "model", "capability": "llm_evaluation"},
            "mlops-deployer": {"domain": "mlops", "capability": "deployment"},
            "monitoring-drift-watcher": {"domain": "mlops", "capability": "monitoring"},
            "crosscloud-trainer": {"domain": "mlops", "capability": "training"},
            "viz-storyteller": {"domain": "governance", "capability": "reporting"},
            "human-loop-coordinator": {"domain": "governance", "capability": "human_review"},
            "compliance-privacy-auditor": {"domain": "governance", "capability": "compliance"},
            "cost-optimizer": {"domain": "governance", "capability": "cost_management"},
            "knowledge-manager": {"domain": "governance", "capability": "knowledge_base"},
        }

    @trace_agent("supervisor-director")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute supervisor orchestration.

        Args:
            state: Current graph state

        Returns:
            Outputs from execution including routing decisions
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="supervisor-director",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting supervisor director", task_id=state.task_id)

        try:
            operation = state.inputs.get("operation", "route")

            if operation == "route":
                outputs = await self._route_task(state)
            elif operation == "decompose":
                outputs = await self._decompose_goal(state)
            elif operation == "arbitrate":
                outputs = await self._arbitrate(state)
            elif operation == "health_check":
                outputs = await self._health_check(state)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Log audit trail
            await self._log_audit(run_id, state, outputs)

            # Track costs
            cost_gbp = 0.5  # Supervisor has minimal compute cost
            self.cost_tracker.record_cost(
                agent_name="supervisor-director",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="orchestration",
                metadata={"operation": operation, "run_id": run_id},
            )

            logger.info(
                "Supervisor director completed",
                task_id=state.task_id,
                operation=operation,
            )

            return outputs

        except Exception as e:
            logger.error(f"Supervisor director failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "supervisor-director",
            }

    async def _route_task(self, state: GraphState) -> Dict[str, Any]:
        """Route task to appropriate agent based on goal."""
        goal = state.inputs.get("goal", "")
        context = state.context

        logger.info("Routing task", goal=goal)

        # Simple rule-based routing (in production, use LLM planner)
        routing_rules = {
            "ingest": "ingestion-orchestrator",
            "transform": "etl-transformer",
            "validate": "data-contracts-quality",
            "train_churn": "churn-forecast-modeler",
            "predict_churn": "churn-forecast-modeler",
            "train_acquisition": "acquisition-forecast-modeler",
            "forecast_load": "load-consumption-forecast",
            "optimize_pricing": "pricing-tariff-optimizer",
            "detect_fraud": "anomaly-fraud-detector",
            "deploy_model": "mlops-deployer",
            "monitor_drift": "monitoring-drift-watcher",
            "generate_report": "viz-storyteller",
        }

        # Extract goal keyword
        goal_lower = goal.lower()
        selected_agent = None
        for keyword, agent in routing_rules.items():
            if keyword in goal_lower:
                selected_agent = agent
                break

        if not selected_agent:
            selected_agent = "intake-triage"  # Default to triage

        # Check safety and cost policies
        policy_check = await self._check_policies(state, selected_agent)

        if not policy_check["allowed"]:
            logger.warning("Policy violation", reason=policy_check["reason"])
            return {
                "status": "blocked",
                "reason": policy_check["reason"],
                "agent": "supervisor-director",
            }

        logger.info("Task routed", target_agent=selected_agent)

        return {
            "status": "success",
            "next_agent": selected_agent,
            "routing_reason": f"Goal '{goal}' matched to {selected_agent}",
            "policy_check": policy_check,
        }

    async def _decompose_goal(self, state: GraphState) -> Dict[str, Any]:
        """Decompose high-level goal into subtasks."""
        goal = state.inputs.get("goal", "")

        logger.info("Decomposing goal", goal=goal)

        # Example decomposition for common workflows
        decompositions = {
            "daily_churn_pipeline": [
                {"agent": "ingestion-orchestrator", "task": "ingest_crm_data"},
                {"agent": "data-contracts-quality", "task": "validate_data"},
                {"agent": "etl-transformer", "task": "transform_to_silver"},
                {"agent": "feature-store-manager", "task": "update_features"},
                {"agent": "churn-forecast-modeler", "task": "predict_churn"},
                {"agent": "viz-storyteller", "task": "generate_churn_report"},
            ],
            "train_new_model": [
                {"agent": "experiment-planner", "task": "design_experiment"},
                {"agent": "feature-store-manager", "task": "prepare_features"},
                {"agent": "crosscloud-trainer", "task": "train_model"},
                {"agent": "prompt-model-evaluator", "task": "evaluate_model"},
                {"agent": "mlops-deployer", "task": "deploy_if_approved"},
            ],
        }

        # Find matching decomposition
        goal_lower = goal.lower()
        subtasks = []
        for key, tasks in decompositions.items():
            if key in goal_lower:
                subtasks = tasks
                break

        if not subtasks:
            # Default: single task to intake-triage
            subtasks = [{"agent": "intake-triage", "task": goal}]

        logger.info("Goal decomposed", num_subtasks=len(subtasks))

        return {
            "status": "success",
            "subtasks": subtasks,
            "decomposition_strategy": "rule_based",
        }

    async def _arbitrate(self, state: GraphState) -> Dict[str, Any]:
        """Arbitrate conflicts between agents or resources."""
        conflict_type = state.inputs.get("conflict_type", "")
        parties = state.inputs.get("parties", [])

        logger.info("Arbitrating conflict", conflict_type=conflict_type, parties=parties)

        # Simple arbitration logic
        if conflict_type == "resource_contention":
            # Prioritize based on task priority
            priority = state.inputs.get("priority", TaskPriority.MEDIUM)
            decision = "allow" if priority in [TaskPriority.HIGH, TaskPriority.CRITICAL] else "defer"
        elif conflict_type == "cost_limit":
            # Check budget
            cost_so_far = state.cost_so_far_gbp
            daily_limit = 150.0  # £150 daily budget
            decision = "allow" if cost_so_far < daily_limit * 0.9 else "deny"
        else:
            decision = "escalate"

        logger.info("Arbitration decision", decision=decision)

        return {
            "status": "success",
            "decision": decision,
            "conflict_type": conflict_type,
        }

    async def _health_check(self, state: GraphState) -> Dict[str, Any]:
        """Perform system health check."""
        logger.info("Performing health check")

        # Check agent availability (simulated)
        agent_health = {
            agent: "healthy" for agent in self.agent_registry.keys()
        }

        # Check cost budget
        cost_status = "ok" if state.cost_so_far_gbp < 135.0 else "warning"

        return {
            "status": "success",
            "agent_health": agent_health,
            "cost_status": cost_status,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _check_policies(
        self,
        state: GraphState,
        target_agent: str
    ) -> Dict[str, Any]:
        """Check safety and cost policies."""
        # Check cost ceiling
        estimated_cost = 5.0  # Estimated cost for the task
        total_cost = state.cost_so_far_gbp + estimated_cost
        daily_limit = 150.0

        if total_cost > daily_limit:
            return {
                "allowed": False,
                "reason": f"Cost ceiling breach: {total_cost:.2f} > {daily_limit}",
            }

        # Check retry limit
        if state.retry_count >= state.max_retries:
            return {
                "allowed": False,
                "reason": f"Max retries exceeded: {state.retry_count}",
            }

        # Check if agent exists
        if target_agent not in self.agent_registry:
            return {
                "allowed": False,
                "reason": f"Unknown agent: {target_agent}",
            }

        return {
            "allowed": True,
            "reason": "All policy checks passed",
        }

    async def _log_audit(
        self,
        run_id: str,
        state: GraphState,
        outputs: Dict[str, Any]
    ) -> None:
        """Log audit trail to S3."""
        audit_record = {
            "run_id": run_id,
            "task_id": state.task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "operation": state.inputs.get("operation", "route"),
            "decision": outputs.get("next_agent") or outputs.get("decision"),
            "cost_so_far": state.cost_so_far_gbp,
            "status": outputs.get("status"),
        }

        # In production: write to S3
        logger.info("Audit logged", audit_record=audit_record)


async def create_supervisor_director() -> SupervisorDirector:
    """Factory function to create supervisor director."""
    return SupervisorDirector()
