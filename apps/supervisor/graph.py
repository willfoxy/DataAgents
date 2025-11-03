"""LangGraph definition for the 25-agent system."""

from typing import Literal, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from libs.common.types import GraphState, RunStatus
from libs.common.logging import get_logger
from apps.supervisor.supervisor_agent import SupervisorAgent
from apps.supervisor.agent_registry import get_agent_registry
from libs.resilience.self_healing import SelfHealingAgent, RecoveryStrategy

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
        self.agent_registry = get_agent_registry()
        self.self_healer = SelfHealingAgent()
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
        """Execute the routed agent with error handling and retries."""
        next_agent = state.context.get("next_agent", "unknown")

        logger.info(
            f"Executing agent: {next_agent}",
            task_id=state.task_id,
            agent=next_agent,
        )

        try:
            # Get agent from registry
            agent = await self.agent_registry.get_agent(next_agent)

            # Execute agent
            outputs = await agent.execute(state)

            # Check for errors
            if outputs.get("status") == "failed":
                logger.warning(
                    f"Agent {next_agent} failed",
                    error=outputs.get("error"),
                    task_id=state.task_id,
                )

                # Attempt self-healing
                recovery = await self.self_healer.handle_failure(
                    agent_name=next_agent,
                    error=Exception(outputs.get("error", "Unknown error")),
                    context=state,
                )

                # Apply recovery strategy
                if recovery.strategy == RecoveryStrategy.RETRY:
                    logger.info(f"Retrying agent: {next_agent}")
                    state.retry_count += 1
                    if state.retry_count < state.max_retries:
                        outputs = await agent.execute(state)
                    else:
                        outputs["status"] = "failed"
                        outputs["reason"] = "Max retries exceeded"

                elif recovery.strategy == RecoveryStrategy.SKIP:
                    logger.info(f"Skipping agent: {next_agent}")
                    outputs["status"] = "skipped"

                elif recovery.strategy == RecoveryStrategy.FALLBACK:
                    logger.info(f"Using fallback for: {next_agent}")
                    outputs["status"] = "success"
                    outputs["fallback"] = True

            # Store outputs
            state.outputs[next_agent] = outputs

            # Update cost tracking
            agent_cost = outputs.get("cost_gbp", 0.0)
            state.cost_so_far_gbp += agent_cost

            # Update status
            if outputs.get("status") == "success":
                state.status = RunStatus.IN_PROGRESS
            elif outputs.get("status") == "failed":
                state.status = RunStatus.FAILED
                state.errors.append(f"{next_agent}: {outputs.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(
                f"Agent execution failed: {next_agent}",
                error=str(e),
                task_id=state.task_id,
                exc_info=True,
            )

            # Attempt recovery
            recovery = await self.self_healer.handle_failure(
                agent_name=next_agent,
                error=e,
                context=state,
            )

            state.outputs[next_agent] = {
                "status": "failed",
                "error": str(e),
                "agent": next_agent,
                "recovery_attempted": recovery.strategy.value,
            }
            state.status = RunStatus.FAILED
            state.errors.append(f"{next_agent}: {str(e)}")

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

    def get_agent_metadata(self, agent_name: str) -> dict:
        """Get metadata for an agent."""
        return self.agent_registry.get_metadata(agent_name)

    def list_all_agents(self) -> list[str]:
        """List all available agents."""
        return self.agent_registry.list_agents()

    def get_agents_by_domain(self, domain: str) -> list[str]:
        """Get agents by domain."""
        return self.agent_registry.get_agents_by_domain(domain)

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
