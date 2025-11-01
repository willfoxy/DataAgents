"""MLOps Deployer - Deploy models with canary/blue-green strategies."""

from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import time

import boto3
import mlflow

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class MLOpsDeployer:
    """
    MLOps Deployer Agent.

    Responsibilities:
    - Package and deploy models to production
    - Execute canary/blue-green rollouts
    - Monitor deployment health
    - Automatic rollback on failure
    - Zero-downtime deployments
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        self.sagemaker = boto3.client("sagemaker", region_name=self.config.aws_region)
        mlflow.set_tracking_uri(self.config.mlflow_tracking_uri)

    @trace_agent("mlops-deployer")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute model deployment.

        Args:
            state: Current graph state

        Returns:
            Deployment results
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="mlops-deployer",
            task_id=state.task_id,
            run_id=run_id,
        )

        deployment_strategy = state.inputs.get("strategy", "canary")
        model_name = state.inputs["model_name"]

        logger.info(
            f"Starting model deployment: {model_name}",
            task_id=state.task_id,
            strategy=deployment_strategy,
        )

        try:
            if deployment_strategy == "canary":
                result = await self._deploy_canary(state.inputs)
            elif deployment_strategy == "blue_green":
                result = await self._deploy_blue_green(state.inputs)
            elif deployment_strategy == "direct":
                result = await self._deploy_direct(state.inputs)
            else:
                raise ValueError(f"Unknown strategy: {deployment_strategy}")

            # Track costs
            cost_gbp = result.get("cost_gbp", 5.0)
            self.cost_tracker.record_cost(
                agent_name="mlops-deployer",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="sagemaker.endpoint",
                metadata={
                    "model": model_name,
                    "strategy": deployment_strategy,
                    "run_id": run_id,
                },
            )

            logger.info(
                "Model deployment completed",
                task_id=state.task_id,
                model=model_name,
                strategy=deployment_strategy,
                endpoint=result.get("endpoint_name"),
            )

            result["status"] = "success"
            result["strategy"] = deployment_strategy
            return result

        except Exception as e:
            logger.error(f"Model deployment failed: {e}", exc_info=True)

            # Attempt automatic rollback
            if deployment_strategy in ["canary", "blue_green"]:
                await self._rollback_deployment(model_name)

            return {
                "status": "failed",
                "error": str(e),
                "model": model_name,
                "strategy": deployment_strategy,
                "agent": "mlops-deployer",
            }

    async def _deploy_canary(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deploy with canary strategy."""

        model_name = inputs["model_name"]
        model_uri = inputs["model_uri"]
        canary_traffic = inputs.get("canary_traffic", 0.1)  # 10% to canary
        monitoring_duration_minutes = inputs.get("monitoring_duration_minutes", 30)

        logger.info(
            f"Starting canary deployment: {model_name}",
            canary_traffic=canary_traffic,
            monitoring_duration=monitoring_duration_minutes,
        )

        # Step 1: Create model in SageMaker
        model_version = await self._create_sagemaker_model(model_name, model_uri)

        # Step 2: Create endpoint config with two variants
        endpoint_config_name = await self._create_canary_endpoint_config(
            model_name,
            model_version,
            canary_traffic,
        )

        # Step 3: Update or create endpoint
        endpoint_name = f"aurora-{model_name}-{self.config.environment.value}"
        endpoint_exists = await self._endpoint_exists(endpoint_name)

        if endpoint_exists:
            await self._update_endpoint(endpoint_name, endpoint_config_name)
        else:
            await self._create_endpoint(endpoint_name, endpoint_config_name)

        # Step 4: Monitor canary metrics
        logger.info(f"Monitoring canary for {monitoring_duration_minutes} minutes")
        canary_healthy = await self._monitor_canary(
            endpoint_name,
            duration_minutes=monitoring_duration_minutes,
        )

        # Step 5: Promote or rollback
        if canary_healthy:
            logger.info("Canary healthy, promoting to 100% traffic")
            await self._promote_canary(endpoint_name, model_version)
            deployment_status = "promoted"
        else:
            logger.error("Canary unhealthy, rolling back")
            await self._rollback_deployment(model_name)
            deployment_status = "rolled_back"

        return {
            "model_name": model_name,
            "model_version": model_version,
            "endpoint_name": endpoint_name,
            "deployment_status": deployment_status,
            "canary_healthy": canary_healthy,
            "cost_gbp": 8.0,
        }

    async def _deploy_blue_green(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Deploy with blue-green strategy."""

        model_name = inputs["model_name"]
        model_uri = inputs["model_uri"]

        logger.info(f"Starting blue-green deployment: {model_name}")

        # Step 1: Create green environment
        model_version = await self._create_sagemaker_model(model_name, model_uri)
        green_endpoint = f"aurora-{model_name}-green-{self.config.environment.value}"

        # Step 2: Deploy to green
        endpoint_config = await self._create_endpoint_config(model_name, model_version)
        await self._create_endpoint(green_endpoint, endpoint_config)

        # Step 3: Run smoke tests on green
        smoke_tests_passed = await self._run_smoke_tests(green_endpoint)

        if not smoke_tests_passed:
            logger.error("Smoke tests failed on green environment")
            await self._delete_endpoint(green_endpoint)
            raise ValueError("Smoke tests failed")

        # Step 4: Switch traffic (update DNS/load balancer)
        blue_endpoint = f"aurora-{model_name}-{self.config.environment.value}"
        await self._switch_traffic(blue_endpoint, green_endpoint)

        # Step 5: Keep blue for rollback window
        logger.info("Blue environment kept for rollback (24h window)")

        return {
            "model_name": model_name,
            "model_version": model_version,
            "green_endpoint": green_endpoint,
            "blue_endpoint": blue_endpoint,
            "smoke_tests_passed": smoke_tests_passed,
            "cost_gbp": 10.0,
        }

    async def _deploy_direct(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Direct deployment (no canary)."""

        model_name = inputs["model_name"]
        model_uri = inputs["model_uri"]

        logger.info(f"Starting direct deployment: {model_name}")

        model_version = await self._create_sagemaker_model(model_name, model_uri)
        endpoint_config = await self._create_endpoint_config(model_name, model_version)

        endpoint_name = f"aurora-{model_name}-{self.config.environment.value}"
        endpoint_exists = await self._endpoint_exists(endpoint_name)

        if endpoint_exists:
            await self._update_endpoint(endpoint_name, endpoint_config)
        else:
            await self._create_endpoint(endpoint_name, endpoint_config)

        return {
            "model_name": model_name,
            "model_version": model_version,
            "endpoint_name": endpoint_name,
            "cost_gbp": 5.0,
        }

    async def _create_sagemaker_model(
        self,
        model_name: str,
        model_uri: str,
    ) -> str:
        """Create SageMaker model."""

        version = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        model_version = f"{model_name}-{version}"

        logger.info(f"Creating SageMaker model: {model_version}")

        # In production:
        # self.sagemaker.create_model(
        #     ModelName=model_version,
        #     PrimaryContainer={
        #         "Image": self._get_inference_image(),
        #         "ModelDataUrl": model_uri,
        #     },
        #     ExecutionRoleArn=self.config.sagemaker_role_arn,
        # )

        return model_version

    async def _create_canary_endpoint_config(
        self,
        model_name: str,
        canary_model_version: str,
        canary_traffic: float,
    ) -> str:
        """Create endpoint config with canary variant."""

        config_name = f"{model_name}-canary-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"Creating canary endpoint config: {config_name}")

        # In production:
        # self.sagemaker.create_endpoint_config(
        #     EndpointConfigName=config_name,
        #     ProductionVariants=[
        #         {
        #             "VariantName": "production",
        #             "ModelName": f"{model_name}-current",
        #             "InitialInstanceCount": 2,
        #             "InstanceType": "ml.m5.xlarge",
        #             "InitialVariantWeight": 1 - canary_traffic,
        #         },
        #         {
        #             "VariantName": "canary",
        #             "ModelName": canary_model_version,
        #             "InitialInstanceCount": 1,
        #             "InstanceType": "ml.m5.xlarge",
        #             "InitialVariantWeight": canary_traffic,
        #         },
        #     ],
        # )

        return config_name

    async def _create_endpoint_config(
        self,
        model_name: str,
        model_version: str,
    ) -> str:
        """Create standard endpoint config."""

        config_name = f"{model_name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"Creating endpoint config: {config_name}")

        return config_name

    async def _endpoint_exists(self, endpoint_name: str) -> bool:
        """Check if endpoint exists."""
        # In production: check SageMaker
        return False  # Simulate new deployment

    async def _create_endpoint(
        self,
        endpoint_name: str,
        endpoint_config_name: str,
    ) -> None:
        """Create SageMaker endpoint."""
        logger.info(f"Creating endpoint: {endpoint_name}")

    async def _update_endpoint(
        self,
        endpoint_name: str,
        endpoint_config_name: str,
    ) -> None:
        """Update existing endpoint."""
        logger.info(f"Updating endpoint: {endpoint_name}")

    async def _monitor_canary(
        self,
        endpoint_name: str,
        duration_minutes: int,
    ) -> bool:
        """Monitor canary metrics."""

        logger.info(f"Monitoring canary metrics for {duration_minutes} minutes")

        # In production: Query CloudWatch metrics
        # - Latency
        # - Error rate
        # - Model performance metrics

        # Simulate monitoring
        # In real scenario, we'd wait and check metrics periodically

        # Simulate: 95% chance canary is healthy
        import random
        return random.random() > 0.05

    async def _promote_canary(
        self,
        endpoint_name: str,
        model_version: str,
    ) -> None:
        """Promote canary to 100% traffic."""

        logger.info(f"Promoting canary to 100% traffic: {endpoint_name}")

        # Update endpoint config to remove canary variant
        # and give all traffic to new model

    async def _rollback_deployment(self, model_name: str) -> None:
        """Rollback to previous deployment."""

        logger.error(f"Rolling back deployment: {model_name}")

        # Revert to previous endpoint configuration

    async def _run_smoke_tests(self, endpoint_name: str) -> bool:
        """Run smoke tests on endpoint."""

        logger.info(f"Running smoke tests on: {endpoint_name}")

        # In production: Send test requests and validate responses

        return True  # Simulate passing tests

    async def _switch_traffic(
        self,
        blue_endpoint: str,
        green_endpoint: str,
    ) -> None:
        """Switch traffic from blue to green."""

        logger.info(f"Switching traffic: {blue_endpoint} -> {green_endpoint}")

        # Update load balancer / DNS / alias

    async def _delete_endpoint(self, endpoint_name: str) -> None:
        """Delete SageMaker endpoint."""

        logger.info(f"Deleting endpoint: {endpoint_name}")


async def create_mlops_deployer() -> MLOpsDeployer:
    """Factory function to create MLOps deployer."""
    return MLOpsDeployer()
