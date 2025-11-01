"""LangGraph definition for the 25-agent system."""

from typing import Literal, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from libs.common.types import GraphState, RunStatus
from libs.common.logging import get_logger
from apps.supervisor.supervisor_agent import SupervisorAgent

logger = get_logger(__name__)


class AgentGraph:
    """
    LangGraph orchestration for the 25-agent system.

    Flow:
    1. Supervisor plans and decomposes task
    2. Supervisor routes to specialist agent
    3. Agent executes
    4. Supervisor verifies outputs
    5. Repeat until complete or failed
    """

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""

        # Define the graph
        workflow = StateGraph(GraphState)

        # Add nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("route", self._route_node)
        workflow.add_node("execute_agent", self._execute_agent_node)
        workflow.add_node("verify", self._verify_node)

        # Define edges
        workflow.set_entry_point("supervisor")

        # Supervisor -> Route
        workflow.add_edge("supervisor", "route")

        # Route -> Execute or END
        workflow.add_conditional_edges(
            "route",
            self._should_continue,
            {
                "execute": "execute_agent",
                "finish": END,
            },
        )

        # Execute -> Verify
        workflow.add_edge("execute_agent", "verify")

        # Verify -> Route (loop)
        workflow.add_edge("verify", "route")

        # Compile with checkpointing
        memory = SqliteSaver.from_conn_string(":memory:")
        return workflow.compile(checkpointer=memory)

    async def _supervisor_node(
        self,
        state: GraphState,
    ) -> GraphState:
        """Supervisor planning node."""
        logger.info("Supervisor planning", task_id=state.task_id)

        # Supervisor has already planned, just pass through
        # In a real implementation, this could do additional planning
        return state

    async def _route_node(
        self,
        state: GraphState,
    ) -> GraphState:
        """Route to next agent."""
        logger.info("Routing to next agent", task_id=state.task_id)

        next_agent = await self.supervisor.route_to_agent(state)

        # Update context with next agent
        state.context["next_agent"] = next_agent

        return state

    async def _execute_agent_node(
        self,
        state: GraphState,
    ) -> GraphState:
        """Execute the routed agent."""
        next_agent = state.context.get("next_agent", "unknown")

        logger.info(
            f"Executing agent: {next_agent}",
            task_id=state.task_id,
            agent=next_agent,
        )

        # In production, this would dynamically dispatch to the actual agent
        # For now, simulate execution
        outputs = await self._simulate_agent_execution(next_agent, state)

        state.outputs[next_agent] = outputs

        return state

    async def _verify_node(
        self,
        state: GraphState,
    ) -> GraphState:
        """Verify agent outputs."""
        next_agent = state.context.get("next_agent", "unknown")

        logger.info(
            f"Verifying outputs from: {next_agent}",
            task_id=state.task_id,
            agent=next_agent,
        )

        # Get agent outputs
        agent_outputs = state.outputs.get(next_agent, {})

        # Verify and merge
        state = await self.supervisor.verify_and_merge(state, agent_outputs)

        return state

    def _should_continue(
        self,
        state: GraphState,
    ) -> Literal["execute", "finish"]:
        """Determine if we should continue or finish."""
        next_agent = state.context.get("next_agent")

        if next_agent == "FINISH" or state.status == RunStatus.FAILED:
            return "finish"

        if next_agent == "PAUSE":
            # In production, persist state and exit gracefully
            logger.info("Pausing execution", task_id=state.task_id)
            return "finish"

        return "execute"

    async def _simulate_agent_execution(
        self,
        agent_name: str,
        state: GraphState,
    ) -> dict:
        """
        Simulate agent execution.

        In production, this would:
        1. Load agent implementation
        2. Execute agent with state
        3. Return outputs
        """
        logger.info(f"Simulating {agent_name} execution")

        # Placeholder outputs
        outputs = {
            "status": "success",
            "timestamp": state.updated_at.isoformat(),
            "agent": agent_name,
        }

        # Simulate specific agent outputs
        if agent_name == "churn-forecast-modeler":
            outputs.update(
                {
                    "predictions_uri": f"s3://aurora-data-dev/gold/customers/predictions/churn/20250101/",
                    "model_uri": f"s3://aurora-models-dev/churn/run-123/model.tar.gz",
                    "metrics": {"auc": 0.82, "calibration_error": 0.015},
                }
            )
        elif agent_name == "data-contracts-quality":
            outputs.update(
                {
                    "validation_passed": True,
                    "checks_run": 15,
                    "checks_passed": 15,
                }
            )

        return outputs

    async def run(
        self,
        initial_state: GraphState,
    ) -> GraphState:
        """
        Run the graph with initial state.

        Args:
            initial_state: Initial graph state

        Returns:
            Final graph state
        """
        logger.info(
            "Starting graph execution",
            task_id=initial_state.task_id,
            run_id=initial_state.run_id,
        )

        config = {"configurable": {"thread_id": initial_state.run_id}}

        # Execute graph
        final_state = None
        async for state in self.graph.astream(initial_state, config=config):
            final_state = state
            logger.debug("Graph state update", state=state)

        logger.info(
            "Graph execution complete",
            task_id=initial_state.task_id,
            status=final_state.get("status") if final_state else "unknown",
        )

        return final_state


def create_agent_graph() -> AgentGraph:
    """Factory function to create agent graph."""
    return AgentGraph()
