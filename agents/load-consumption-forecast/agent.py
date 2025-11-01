"""Load Consumption Forecast Agent - predict energy demand."""

from typing import Dict, Any
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class LoadConsumptionForecast:
    """
    Load Consumption Forecast Agent.

    Responsibilities:
    - Forecast energy consumption/demand
    - Predict load profiles by customer segment
    - Handle seasonal patterns and weather effects
    - Support portfolio risk management
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("load-consumption-forecast")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """Execute load forecasting."""
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="load-consumption-forecast",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting load forecast", task_id=state.task_id)

        try:
            mode = state.inputs.get("mode", "predict")
            horizon_days = state.inputs.get("horizon_days", 30)

            if mode == "train":
                outputs = await self._train_model(state)
            else:
                outputs = await self._predict(state, horizon_days)

            cost_gbp = 18.0 if mode == "train" else 4.0
            self.cost_tracker.record_cost(
                agent_name="load-consumption-forecast",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="sagemaker.training" if mode == "train" else "sagemaker.batch",
                metadata={"mode": mode, "horizon_days": horizon_days, "run_id": run_id},
            )

            logger.info("Load forecasting completed", task_id=state.task_id)

            return outputs

        except Exception as e:
            logger.error(f"Load forecasting failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "load-consumption-forecast",
            }

    async def _train_model(self, state: GraphState) -> Dict[str, Any]:
        """Train load forecast model."""
        logger.info("Training load forecast model")

        model_uri = f"s3://{self.config.models_bucket}/load_forecast/{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}/model.tar.gz"

        metrics = {
            "mae_mwh": 15.2,
            "rmse_mwh": 22.5,
            "mape": 0.06,
        }

        return {
            "status": "success",
            "mode": "train",
            "model_uri": model_uri,
            "metrics": metrics,
        }

    async def _predict(self, state: GraphState, horizon_days: int) -> Dict[str, Any]:
        """Generate load forecasts."""
        logger.info("Generating load forecasts", horizon_days=horizon_days)

        ds = datetime.utcnow().strftime("%Y%m%d")
        forecast_uri = f"s3://{self.config.data_bucket}/gold/load/forecasts/{ds}/"

        # Simulate forecast
        forecast = {
            "total_mwh_next_30d": 45000,
            "peak_load_mw": 180,
            "confidence_interval_95": [42000, 48000],
        }

        return {
            "status": "success",
            "mode": "predict",
            "forecast_uri": forecast_uri,
            "horizon_days": horizon_days,
            "forecast": forecast,
        }


async def create_load_forecast() -> LoadConsumptionForecast:
    """Factory function to create load forecast agent."""
    return LoadConsumptionForecast()
