"""Cost Optimizer Agent - track spending and optimize costs."""

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


class CostOptimizer:
    """
    Cost Optimizer Agent.

    Responsibilities:
    - Track spending across all agents and infrastructure
    - Identify cost optimization opportunities
    - Recommend resource right-sizing
    - Alert on budget breaches
    - Generate cost reports and forecasts
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()
        self.daily_budget_gbp = 150.0

    @trace_agent("cost-optimizer")
    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute cost optimization."""
        run_id = str(uuid.uuid4())
        bind_context(agent_name="cost-optimizer", task_id=state.task_id, run_id=run_id)
        logger.info("Starting cost optimizer", task_id=state.task_id)

        try:
            operation = state.inputs.get("operation", "analyze")

            if operation == "analyze":
                outputs = await self._analyze_costs(state)
            elif operation == "recommend":
                outputs = await self._recommend_optimizations(state)
            else:
                outputs = await self._forecast_costs(state)

            self.cost_tracker.record_cost(
                agent_name="cost-optimizer",
                task_id=state.task_id,
                cost_gbp=0.2,
                resource_type="analysis",
                metadata={"operation": operation, "run_id": run_id},
            )

            return outputs

        except Exception as e:
            logger.error(f"Cost optimization failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "agent": "cost-optimizer"}

    async def _analyze_costs(self, state: GraphState) -> Dict[str, Any]:
        """Analyze current costs."""
        logger.info("Analyzing costs")

        # In production: query CostTracker, CloudWatch, Cost Explorer
        cost_breakdown = {
            "total_today_gbp": 87.50,
            "by_agent": {
                "churn-forecast-modeler": 15.0,
                "crosscloud-trainer": 12.0,
                "feature-store-manager": 8.5,
                "mlops-deployer": 6.0,
                "ingestion-orchestrator": 5.0,
                "other": 41.0,
            },
            "by_resource_type": {
                "sagemaker.training": 25.0,
                "sagemaker.batch": 12.0,
                "glue.job": 10.0,
                "lambda": 3.5,
                "s3": 2.0,
                "other": 35.0,
            },
            "budget_utilization": 0.583,  # 58.3%
        }

        logger.info("Cost analysis complete", total_today=cost_breakdown["total_today_gbp"])

        return {
            "status": "success",
            "cost_breakdown": cost_breakdown,
            "alert_level": "ok" if cost_breakdown["budget_utilization"] < 0.8 else "warning",
        }

    async def _recommend_optimizations(self, state: GraphState) -> Dict[str, Any]:
        """Recommend cost optimizations."""
        logger.info("Recommending optimizations")

        recommendations = [
            {
                "area": "training",
                "recommendation": "Use spot instances for non-critical training jobs",
                "potential_savings_gbp": 5.0,
                "priority": "high",
            },
            {
                "area": "storage",
                "recommendation": "Archive bronze data older than 90 days to Glacier",
                "potential_savings_gbp": 2.0,
                "priority": "medium",
            },
            {
                "area": "compute",
                "recommendation": "Scale down SageMaker endpoints during off-hours",
                "potential_savings_gbp": 3.0,
                "priority": "medium",
            },
        ]

        total_potential_savings = sum(r["potential_savings_gbp"] for r in recommendations)

        logger.info("Recommendations generated", num_recommendations=len(recommendations))

        return {
            "status": "success",
            "recommendations": recommendations,
            "total_potential_savings_gbp": total_potential_savings,
        }

    async def _forecast_costs(self, state: GraphState) -> Dict[str, Any]:
        """Forecast future costs."""
        logger.info("Forecasting costs")

        forecast_days = state.inputs.get("forecast_days", 30)

        forecast = {
            "forecast_days": forecast_days,
            "projected_total_gbp": forecast_days * 90.0,  # £90/day average
            "confidence_interval_95": [forecast_days * 75.0, forecast_days * 105.0],
            "trend": "stable",
        }

        logger.info("Cost forecast complete", projected_total=forecast["projected_total_gbp"])

        return {
            "status": "success",
            "forecast": forecast,
        }


async def create_cost_optimizer() -> CostOptimizer:
    """Factory function to create cost optimizer."""
    return CostOptimizer()
