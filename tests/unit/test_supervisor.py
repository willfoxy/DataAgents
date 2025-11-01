"""Unit tests for Supervisor Agent."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from apps.supervisor.supervisor_agent import SupervisorAgent
from libs.common.types import TaskSpec, TaskPriority, GraphState, RunStatus


@pytest.fixture
def supervisor():
    """Create supervisor instance."""
    return SupervisorAgent()


@pytest.fixture
def task_spec():
    """Create sample task spec."""
    return TaskSpec(
        task_id="test-task-123",
        agent_name="churn-forecast-modeler",
        priority=TaskPriority.HIGH,
        inputs={
            "mode": "predict",
            "date": "2025-01-01",
        },
    )


@pytest.fixture
def graph_state():
    """Create sample graph state."""
    return GraphState(
        task_id="test-task-123",
        run_id="run-456",
        current_agent="supervisor-director",
        status=RunStatus.IN_PROGRESS,
        inputs={"mode": "predict"},
        context={"subtasks": [{"type": "churn_forecast"}]},
    )


class TestSupervisorAgent:
    """Test suite for Supervisor Agent."""

    @pytest.mark.asyncio
    async def test_plan_and_route(self, supervisor, task_spec):
        """Test task planning and routing."""
        # Mock dependencies
        with patch.object(supervisor, "_check_safety", return_value=(True, None)):
            with patch.object(supervisor, "_persist_state", new_callable=AsyncMock):
                # Execute
                state = await supervisor.plan_and_route(task_spec)

                # Assert
                assert state.task_id == task_spec.task_id
                assert state.status == RunStatus.IN_PROGRESS
                assert "subtasks" in state.context
                assert len(state.context["subtasks"]) > 0

    @pytest.mark.asyncio
    async def test_route_to_agent_with_subtasks(self, supervisor, graph_state):
        """Test routing when subtasks exist."""
        # Execute
        next_agent = await supervisor.route_to_agent(graph_state)

        # Assert
        assert next_agent in supervisor.agent_routes.values()
        assert graph_state.current_agent == next_agent

    @pytest.mark.asyncio
    async def test_route_to_finish_when_no_subtasks(self, supervisor, graph_state):
        """Test routing when all subtasks complete."""
        # Setup - no subtasks
        graph_state.context["subtasks"] = []

        # Execute
        next_agent = await supervisor.route_to_agent(graph_state)

        # Assert
        assert next_agent == "FINISH"

    @pytest.mark.asyncio
    async def test_verify_and_merge(self, supervisor, graph_state):
        """Test output verification and merging."""
        agent_outputs = {
            "status": "success",
            "predictions_uri": "s3://bucket/predictions/",
            "metrics": {"auc": 0.82},
        }

        with patch.object(supervisor, "_persist_state", new_callable=AsyncMock):
            # Execute
            updated_state = await supervisor.verify_and_merge(graph_state, agent_outputs)

            # Assert
            assert updated_state.outputs == agent_outputs
            assert len(updated_state.context["subtasks"]) == 0  # Subtask removed

    @pytest.mark.asyncio
    async def test_safety_check_budget_exceeded(self, supervisor, task_spec):
        """Test safety check fails when budget exceeded."""
        with patch.object(
            supervisor.budget_guard, "check_daily_budget", return_value=False
        ):
            # Execute
            allowed, reason = await supervisor._check_safety(task_spec)

            # Assert
            assert not allowed
            assert "budget" in reason.lower()

    @pytest.mark.asyncio
    async def test_decompose_goal_for_churn(self, supervisor, task_spec):
        """Test goal decomposition for churn task."""
        # Execute
        subtasks = await supervisor._decompose_goal(task_spec)

        # Assert
        assert len(subtasks) > 0
        task_types = [st["type"] for st in subtasks]
        assert "churn_forecast" in task_types
        assert "data_quality" in task_types

    @pytest.mark.asyncio
    async def test_persist_state(self, supervisor, graph_state):
        """Test state persistence."""
        with patch.object(supervisor.dynamodb, "put_item") as mock_put:
            with patch.object(supervisor.s3, "write_json"):
                # Execute
                await supervisor._persist_state(graph_state)

                # Assert
                mock_put.assert_called_once()
                args, kwargs = mock_put.call_args
                assert args[1]["task_id"] == graph_state.task_id
