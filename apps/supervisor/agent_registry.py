"""Agent Registry - centralized registry of all 25 agents."""

from typing import Dict, Any, Protocol
from libs.common.types import GraphState
from libs.common.logging import get_logger

# Import all agents
from agents.supervisor_director import create_supervisor_director
from agents.intake_triage import create_intake_triage
from agents.data_cataloguer import create_data_cataloguer
from agents.data_contracts_quality import create_data_contracts_quality_agent
from agents.ingestion_orchestrator import create_ingestion_orchestrator
from agents.etl_transformer import create_etl_transformer
from agents.feature_store_manager import create_feature_store_manager
from agents.experiment_planner import create_experiment_planner
from agents.churn_forecast_modeler import create_churn_modeler
from agents.acquisition_forecast_modeler import create_acquisition_modeler
from agents.load_consumption_forecast import create_load_forecast
from agents.pricing_tariff_optimizer import create_pricing_optimizer
from agents.portfolio_risk_modeler import create_risk_modeler
from agents.trial_design_causal_inference import create_trial_designer
from agents.anomaly_fraud_detector import create_fraud_detector
from agents.customer_segmentation_clv import create_segmentation_agent
from agents.prompt_model_evaluator import create_evaluator
from agents.mlops_deployer import create_mlops_deployer
from agents.monitoring_drift_watcher import create_drift_watcher
from agents.crosscloud_trainer import create_crosscloud_trainer
from agents.viz_storyteller import create_viz_storyteller
from agents.human_loop_coordinator import create_human_loop_coordinator
from agents.compliance_privacy_auditor import create_compliance_auditor
from agents.cost_optimizer import create_cost_optimizer
from agents.knowledge_manager import create_knowledge_manager

logger = get_logger(__name__)


class Agent(Protocol):
    """Protocol for agent interface."""

    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute agent with state."""
        ...


class AgentRegistry:
    """
    Central registry of all 25 agents.

    Manages agent lifecycle:
    - Lazy loading of agents
    - Agent metadata and capabilities
    - Dynamic dispatching
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._agent_factories = {
            # Control & Coordination
            "supervisor-director": create_supervisor_director,
            "intake-triage": create_intake_triage,

            # Data Foundation
            "data-cataloguer": create_data_cataloguer,
            "data-contracts-quality": create_data_contracts_quality_agent,
            "ingestion-orchestrator": create_ingestion_orchestrator,
            "etl-transformer": create_etl_transformer,
            "feature-store-manager": create_feature_store_manager,

            # Model Development
            "experiment-planner": create_experiment_planner,
            "churn-forecast-modeler": create_churn_modeler,
            "acquisition-forecast-modeler": create_acquisition_modeler,
            "load-consumption-forecast": create_load_forecast,
            "pricing-tariff-optimizer": create_pricing_optimizer,
            "portfolio-risk-modeler": create_risk_modeler,
            "trial-design-causal-inference": create_trial_designer,
            "anomaly-fraud-detector": create_fraud_detector,
            "customer-segmentation-clv": create_segmentation_agent,
            "prompt-model-evaluator": create_evaluator,

            # MLOps & Monitoring
            "mlops-deployer": create_mlops_deployer,
            "monitoring-drift-watcher": create_drift_watcher,
            "crosscloud-trainer": create_crosscloud_trainer,

            # Reporting & Governance
            "viz-storyteller": create_viz_storyteller,
            "human-loop-coordinator": create_human_loop_coordinator,
            "compliance-privacy-auditor": create_compliance_auditor,
            "cost-optimizer": create_cost_optimizer,
            "knowledge-manager": create_knowledge_manager,
        }

        # Agent metadata
        self._agent_metadata = {
            "supervisor-director": {
                "domain": "control",
                "capability": "orchestration",
                "cost_estimate_gbp": 0.5,
                "avg_duration_seconds": 10,
            },
            "intake-triage": {
                "domain": "control",
                "capability": "task_capture",
                "cost_estimate_gbp": 0.1,
                "avg_duration_seconds": 5,
            },
            "data-cataloguer": {
                "domain": "data",
                "capability": "cataloguing",
                "cost_estimate_gbp": 0.5,
                "avg_duration_seconds": 30,
            },
            "data-contracts-quality": {
                "domain": "data",
                "capability": "validation",
                "cost_estimate_gbp": 1.0,
                "avg_duration_seconds": 60,
            },
            "ingestion-orchestrator": {
                "domain": "data",
                "capability": "ingestion",
                "cost_estimate_gbp": 2.0,
                "avg_duration_seconds": 120,
            },
            "etl-transformer": {
                "domain": "data",
                "capability": "transformation",
                "cost_estimate_gbp": 3.0,
                "avg_duration_seconds": 180,
            },
            "feature-store-manager": {
                "domain": "data",
                "capability": "feature_engineering",
                "cost_estimate_gbp": 2.0,
                "avg_duration_seconds": 90,
            },
            "experiment-planner": {
                "domain": "model",
                "capability": "experimentation",
                "cost_estimate_gbp": 0.2,
                "avg_duration_seconds": 15,
            },
            "churn-forecast-modeler": {
                "domain": "model",
                "capability": "churn_prediction",
                "cost_estimate_gbp": 15.0,
                "avg_duration_seconds": 300,
            },
            "acquisition-forecast-modeler": {
                "domain": "model",
                "capability": "acquisition_prediction",
                "cost_estimate_gbp": 12.0,
                "avg_duration_seconds": 240,
            },
            "load-consumption-forecast": {
                "domain": "model",
                "capability": "load_forecasting",
                "cost_estimate_gbp": 18.0,
                "avg_duration_seconds": 360,
            },
            "pricing-tariff-optimizer": {
                "domain": "model",
                "capability": "pricing_optimization",
                "cost_estimate_gbp": 1.5,
                "avg_duration_seconds": 30,
            },
            "portfolio-risk-modeler": {
                "domain": "model",
                "capability": "risk_modeling",
                "cost_estimate_gbp": 3.0,
                "avg_duration_seconds": 60,
            },
            "trial-design-causal-inference": {
                "domain": "model",
                "capability": "causal_inference",
                "cost_estimate_gbp": 1.0,
                "avg_duration_seconds": 20,
            },
            "anomaly-fraud-detector": {
                "domain": "model",
                "capability": "anomaly_detection",
                "cost_estimate_gbp": 2.5,
                "avg_duration_seconds": 90,
            },
            "customer-segmentation-clv": {
                "domain": "model",
                "capability": "segmentation",
                "cost_estimate_gbp": 4.0,
                "avg_duration_seconds": 120,
            },
            "prompt-model-evaluator": {
                "domain": "model",
                "capability": "llm_evaluation",
                "cost_estimate_gbp": 1.5,
                "avg_duration_seconds": 45,
            },
            "mlops-deployer": {
                "domain": "mlops",
                "capability": "deployment",
                "cost_estimate_gbp": 1.0,
                "avg_duration_seconds": 180,
            },
            "monitoring-drift-watcher": {
                "domain": "mlops",
                "capability": "monitoring",
                "cost_estimate_gbp": 1.5,
                "avg_duration_seconds": 60,
            },
            "crosscloud-trainer": {
                "domain": "mlops",
                "capability": "training",
                "cost_estimate_gbp": 15.0,
                "avg_duration_seconds": 2700,
            },
            "viz-storyteller": {
                "domain": "governance",
                "capability": "reporting",
                "cost_estimate_gbp": 0.8,
                "avg_duration_seconds": 90,
            },
            "human-loop-coordinator": {
                "domain": "governance",
                "capability": "human_review",
                "cost_estimate_gbp": 0.1,
                "avg_duration_seconds": 5,
            },
            "compliance-privacy-auditor": {
                "domain": "governance",
                "capability": "compliance",
                "cost_estimate_gbp": 0.5,
                "avg_duration_seconds": 30,
            },
            "cost-optimizer": {
                "domain": "governance",
                "capability": "cost_management",
                "cost_estimate_gbp": 0.2,
                "avg_duration_seconds": 15,
            },
            "knowledge-manager": {
                "domain": "governance",
                "capability": "knowledge_base",
                "cost_estimate_gbp": 0.3,
                "avg_duration_seconds": 20,
            },
        }

    async def get_agent(self, agent_name: str) -> Any:
        """
        Get agent instance (lazy loading).

        Args:
            agent_name: Name of the agent

        Returns:
            Agent instance

        Raises:
            ValueError: If agent not found
        """
        if agent_name not in self._agent_factories:
            raise ValueError(f"Unknown agent: {agent_name}")

        # Lazy load agent if not already loaded
        if agent_name not in self._agents:
            logger.info(f"Loading agent: {agent_name}")
            factory = self._agent_factories[agent_name]
            self._agents[agent_name] = await factory()

        return self._agents[agent_name]

    def get_metadata(self, agent_name: str) -> Dict[str, Any]:
        """Get agent metadata."""
        return self._agent_metadata.get(agent_name, {})

    def list_agents(self) -> list[str]:
        """List all registered agents."""
        return list(self._agent_factories.keys())

    def get_agents_by_domain(self, domain: str) -> list[str]:
        """Get all agents in a domain."""
        return [
            name for name, meta in self._agent_metadata.items()
            if meta.get("domain") == domain
        ]

    def get_agents_by_capability(self, capability: str) -> list[str]:
        """Get all agents with a capability."""
        return [
            name for name, meta in self._agent_metadata.items()
            if meta.get("capability") == capability
        ]


# Global registry instance
_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Get global agent registry instance."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
