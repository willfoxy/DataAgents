#!/usr/bin/env python3
"""
Example: Run the daily churn forecast pipeline.

This demonstrates the Day 1 "thin slice" that delivers:
1. Data quality validation
2. Feature store updates
3. Churn prediction
4. Drift detection
5. Report generation
"""

import asyncio
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus, TaskSpec, TaskPriority
from libs.common.config import get_config
from libs.common.logging import setup_logging, get_logger
from apps.supervisor.supervisor_agent import SupervisorAgent
from apps.supervisor.graph import create_agent_graph

setup_logging()
logger = get_logger(__name__)


async def main():
    """Run the churn forecast pipeline."""
    config = get_config()

    logger.info("=" * 80)
    logger.info("Aurora Energy Platform - Daily Churn Forecast Pipeline")
    logger.info("=" * 80)

    # Create task specification
    task_spec = TaskSpec(
        task_id=str(uuid.uuid4()),
        agent_name="churn-forecast-modeler",
        priority=TaskPriority.HIGH,
        inputs={
            "mode": "predict",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "description": "Daily churn forecast and reporting",
        },
        config={
            "model_version": "latest",
            "generate_shap": True,
            "generate_report": True,
        },
    )

    logger.info(f"Task ID: {task_spec.task_id}")
    logger.info(f"Priority: {task_spec.priority.value}")
    logger.info(f"Environment: {config.environment.value}")

    # Initialize supervisor
    supervisor = SupervisorAgent()

    # Plan and create initial state
    logger.info("\n" + "=" * 80)
    logger.info("Phase 1: Planning & Task Decomposition")
    logger.info("=" * 80)
    initial_state = await supervisor.plan_and_route(task_spec)

    logger.info(f"Run ID: {initial_state.run_id}")
    logger.info(f"Subtasks: {len(initial_state.context.get('subtasks', []))}")

    for i, subtask in enumerate(initial_state.context.get("subtasks", []), 1):
        logger.info(f"  {i}. {subtask.get('type')}: {subtask.get('description')}")

    # Create and execute graph
    logger.info("\n" + "=" * 80)
    logger.info("Phase 2: Agent Orchestration")
    logger.info("=" * 80)

    agent_graph = create_agent_graph()

    try:
        # Run graph
        final_state = await agent_graph.run(initial_state)

        logger.info("\n" + "=" * 80)
        logger.info("Phase 3: Results")
        logger.info("=" * 80)

        if final_state:
            status = final_state.get("status", "unknown")
            logger.info(f"Status: {status}")

            # Display outputs
            outputs = final_state.get("outputs", {})
            logger.info(f"\nOutputs from {len(outputs)} agents:")

            for agent_name, agent_output in outputs.items():
                logger.info(f"\n  {agent_name}:")
                for key, value in agent_output.items():
                    logger.info(f"    {key}: {value}")

            # Display costs
            cost = final_state.get("cost_so_far_gbp", 0.0)
            logger.info(f"\nTotal cost: £{cost:.2f}")

            # Display key metrics
            logger.info("\n" + "=" * 80)
            logger.info("Key Results")
            logger.info("=" * 80)

            churn_output = outputs.get("churn-forecast-modeler", {})
            if churn_output:
                predictions_uri = churn_output.get("predictions_uri", "N/A")
                report_uri = churn_output.get("report_uri", "N/A")

                logger.info(f"Predictions: {predictions_uri}")
                logger.info(f"Report: {report_uri}")

                metrics = churn_output.get("metrics", {})
                if metrics:
                    logger.info("\nMetrics:")
                    for metric_name, metric_value in metrics.items():
                        logger.info(f"  {metric_name}: {metric_value}")

            logger.info("\n" + "=" * 80)
            logger.info("Pipeline completed successfully!")
            logger.info("=" * 80)

        else:
            logger.error("Pipeline failed - no final state returned")

    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
