"""Experiment Planner Agent - design and plan ML experiments."""

from typing import Dict, Any, List
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class ExperimentPlanner:
    """
    Experiment Planner Agent.

    Responsibilities:
    - Design ML experiments with hyperparameter search spaces
    - Plan A/B tests and trials
    - Recommend model architectures
    - Estimate training costs and duration
    - Generate experiment configs for MLflow
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("experiment-planner")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """Execute experiment planning."""
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="experiment-planner",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting experiment planner", task_id=state.task_id)

        try:
            problem_type = state.inputs.get("problem_type", "binary_classification")
            metric = state.inputs.get("metric", "auc")

            # Design experiment
            experiment_plan = await self._design_experiment(state, problem_type, metric)

            # Track costs
            cost_gbp = 0.2
            self.cost_tracker.record_cost(
                agent_name="experiment-planner",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="planning",
                metadata={"problem_type": problem_type, "run_id": run_id},
            )

            logger.info("Experiment planning completed", task_id=state.task_id)

            return {
                "status": "success",
                "experiment_plan": experiment_plan,
            }

        except Exception as e:
            logger.error(f"Experiment planning failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "experiment-planner",
            }

    async def _design_experiment(
        self,
        state: GraphState,
        problem_type: str,
        metric: str
    ) -> Dict[str, Any]:
        """Design experiment with hyperparameter search."""
        logger.info("Designing experiment", problem_type=problem_type, metric=metric)

        # Recommend algorithms based on problem type
        algorithms = self._recommend_algorithms(problem_type)

        # Define hyperparameter search space
        hyperparam_space = {
            "xgboost": {
                "max_depth": [3, 5, 7, 9],
                "learning_rate": [0.01, 0.05, 0.1],
                "n_estimators": [100, 300, 500],
                "min_child_weight": [1, 3, 5],
            },
            "lightgbm": {
                "num_leaves": [31, 63, 127],
                "learning_rate": [0.01, 0.05, 0.1],
                "n_estimators": [100, 300, 500],
            },
        }

        # Estimate resources
        estimated_trials = 20
        estimated_duration_hours = 3
        estimated_cost_gbp = 25.0

        experiment_plan = {
            "experiment_name": f"{problem_type}_{datetime.utcnow().strftime('%Y%m%d')}",
            "problem_type": problem_type,
            "metric": metric,
            "algorithms": algorithms,
            "hyperparam_space": hyperparam_space,
            "search_strategy": "random_search",
            "num_trials": estimated_trials,
            "cv_folds": 5,
            "estimated_duration_hours": estimated_duration_hours,
            "estimated_cost_gbp": estimated_cost_gbp,
            "mlflow_experiment_name": f"aurora/{problem_type}",
        }

        logger.info("Experiment designed", num_trials=estimated_trials)

        return experiment_plan

    def _recommend_algorithms(self, problem_type: str) -> List[str]:
        """Recommend algorithms based on problem type."""
        recommendations = {
            "binary_classification": ["xgboost", "lightgbm", "random_forest"],
            "regression": ["xgboost", "lightgbm", "linear_regression"],
            "time_series": ["prophet", "lstm", "arima"],
            "clustering": ["kmeans", "dbscan", "gaussian_mixture"],
        }

        return recommendations.get(problem_type, ["xgboost"])


async def create_experiment_planner() -> ExperimentPlanner:
    """Factory function to create experiment planner."""
    return ExperimentPlanner()
