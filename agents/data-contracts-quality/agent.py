"""Data Contracts & Quality Agent - Enforce data contracts and run DQ tests."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from great_expectations.core import ExpectationSuite, ExpectationConfiguration
from great_expectations.data_context import DataContext
from great_expectations.checkpoint import Checkpoint

from libs.common.types import GraphState, RunStatus
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class DataContractsQualityAgent:
    """
    Data Contracts & Quality Agent.

    Responsibilities:
    - Define and enforce data contracts
    - Run Great Expectations validation suites
    - Alert on SLA breaches and data quality issues
    - Block downstream pipelines on critical failures
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Initialize Great Expectations context
        self.ge_context = self._init_ge_context()

    def _init_ge_context(self) -> DataContext:
        """Initialize Great Expectations data context."""
        # In production, this would load from GE config
        # For now, create in-memory context
        try:
            context = DataContext()
        except:
            # Create minimal context if none exists
            logger.info("Creating new GE context")
            context = DataContext.create()

        return context

    @trace_agent("data-contracts-quality")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute data quality validation.

        Args:
            state: Current graph state

        Returns:
            Validation results
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="data-contracts-quality",
            task_id=state.task_id,
            run_id=run_id,
        )

        logger.info("Starting data quality validation", task_id=state.task_id)

        try:
            # Get dataset to validate
            dataset_uri = state.inputs.get("dataset_uri")
            contract_name = state.inputs.get("contract_name", "default")

            # Load or create expectation suite
            suite = await self._get_or_create_suite(contract_name)

            # Run validation
            results = await self._run_validation(dataset_uri, suite)

            # Analyze results
            validation_passed = results["success"]

            # Handle failures
            if not validation_passed:
                await self._handle_validation_failure(results, state)

            # Persist results
            results_uri = await self._persist_results(results, run_id)

            # Track costs
            cost_gbp = 0.5  # Data quality checks are cheap
            self.cost_tracker.record_cost(
                agent_name="data-contracts-quality",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="glue.dpu",
                metadata={"contract": contract_name, "run_id": run_id},
            )

            logger.info(
                "Data quality validation completed",
                task_id=state.task_id,
                validation_passed=validation_passed,
                checks_run=results["statistics"]["evaluated_expectations"],
                checks_passed=results["statistics"]["successful_expectations"],
            )

            return {
                "status": "success" if validation_passed else "failed",
                "validation_passed": validation_passed,
                "results_uri": results_uri,
                "checks_run": results["statistics"]["evaluated_expectations"],
                "checks_passed": results["statistics"]["successful_expectations"],
                "success_rate": results["statistics"]["success_percent"] / 100.0,
                "cost_gbp": cost_gbp,
            }

        except Exception as e:
            logger.error(f"Data quality validation failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "agent": "data-contracts-quality",
            }

    async def _get_or_create_suite(self, contract_name: str) -> ExpectationSuite:
        """Get existing suite or create new one."""
        suite_name = f"{contract_name}_suite"

        try:
            suite = self.ge_context.get_expectation_suite(suite_name)
            logger.info(f"Loaded existing suite: {suite_name}")
        except:
            # Create new suite
            logger.info(f"Creating new suite: {suite_name}")
            suite = self._create_default_suite(suite_name, contract_name)

        return suite

    def _create_default_suite(
        self,
        suite_name: str,
        contract_name: str,
    ) -> ExpectationSuite:
        """Create default expectation suite based on contract."""

        suite = self.ge_context.create_expectation_suite(
            expectation_suite_name=suite_name,
            overwrite_existing=True,
        )

        # Add common expectations based on contract type
        if "customer" in contract_name.lower():
            expectations = [
                # Core identity
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_not_be_null",
                    kwargs={"column": "customer_id"},
                ),
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_be_unique",
                    kwargs={"column": "customer_id"},
                ),
                # Data quality
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_be_between",
                    kwargs={"column": "age", "min_value": 18, "max_value": 120},
                ),
                ExpectationConfiguration(
                    expectation_type="expect_column_values_to_match_regex",
                    kwargs={"column": "email", "regex": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"},
                ),
            ]
        else:
            # Generic expectations
            expectations = [
                ExpectationConfiguration(
                    expectation_type="expect_table_row_count_to_be_between",
                    kwargs={"min_value": 1, "max_value": 10000000},
                ),
            ]

        for expectation in expectations:
            suite.add_expectation(expectation)

        self.ge_context.save_expectation_suite(suite)

        return suite

    async def _run_validation(
        self,
        dataset_uri: str,
        suite: ExpectationSuite,
    ) -> Dict[str, Any]:
        """Run validation against dataset."""

        # In production, would connect to actual data source
        # For now, simulate validation results

        logger.info(f"Running validation on {dataset_uri}")

        # Create batch request (in production)
        # batch_request = {
        #     "datasource_name": "s3_datasource",
        #     "data_connector_name": "default_data_connector",
        #     "data_asset_name": dataset_uri,
        # }

        # Simulate results
        total_expectations = len(suite.expectations)
        successful_expectations = int(total_expectations * 0.95)  # 95% pass rate

        results = {
            "success": successful_expectations == total_expectations,
            "statistics": {
                "evaluated_expectations": total_expectations,
                "successful_expectations": successful_expectations,
                "unsuccessful_expectations": total_expectations - successful_expectations,
                "success_percent": (successful_expectations / total_expectations) * 100,
            },
            "results": [],
            "evaluation_parameters": {},
            "meta": {
                "great_expectations_version": "0.18.0",
                "run_id": str(uuid.uuid4()),
                "run_time": datetime.utcnow().isoformat(),
            },
        }

        return results

    async def _handle_validation_failure(
        self,
        results: Dict[str, Any],
        state: GraphState,
    ) -> None:
        """Handle validation failures."""

        failed_expectations = results["statistics"]["unsuccessful_expectations"]

        logger.error(
            f"Data quality validation failed: {failed_expectations} checks failed",
            task_id=state.task_id,
        )

        # In production:
        # 1. Send SNS alert
        # 2. Update DynamoDB to block downstream
        # 3. Create Jira ticket
        # 4. Notify data owner

        # Add error to state
        state.errors.append(
            f"Data quality validation failed: {failed_expectations} checks failed"
        )

    async def _persist_results(
        self,
        results: Dict[str, Any],
        run_id: str,
    ) -> str:
        """Persist validation results to S3."""

        ds = datetime.utcnow().strftime("%Y%m%d")
        key = f"quality/results/{ds}/{run_id}/validation_results.json"

        results_uri = self.s3.write_json(
            data=results,
            bucket=self.config.data_bucket,
            key=key,
        )

        return results_uri


async def create_data_contracts_quality_agent() -> DataContractsQualityAgent:
    """Factory function to create data contracts quality agent."""
    return DataContractsQualityAgent()
