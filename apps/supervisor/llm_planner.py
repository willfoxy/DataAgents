"""LLM-powered planning for the supervisor agent."""

from typing import Dict, Any, List
import json

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from libs.common.types import TaskSpec, TaskPriority
from libs.common.config import get_config
from libs.common.logging import get_logger

logger = get_logger(__name__)


class SubTask(BaseModel):
    """A subtask in the execution plan."""
    agent: str = Field(description="Name of the agent to execute this subtask")
    description: str = Field(description="Description of what this subtask does")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Inputs for this subtask")
    depends_on: List[str] = Field(default_factory=list, description="Agent names this depends on")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")


class ExecutionPlan(BaseModel):
    """Complete execution plan."""
    goal: str = Field(description="High-level goal")
    subtasks: List[SubTask] = Field(description="List of subtasks to execute")
    estimated_cost_gbp: float = Field(description="Estimated total cost in GBP")
    estimated_duration_minutes: int = Field(description="Estimated duration in minutes")
    risk_factors: List[str] = Field(default_factory=list, description="Potential risk factors")


class LLMPlanner:
    """
    LLM-powered planner using Claude for intelligent task decomposition.

    This replaces hard-coded task decomposition with dynamic, context-aware planning.
    """

    def __init__(self) -> None:
        self.config = get_config()

        # Initialize Claude
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0.0,  # Deterministic for planning
            max_tokens=4000,
        )

        # Agent capabilities registry
        self.agent_capabilities = self._load_agent_capabilities()

        # Output parser
        self.parser = PydanticOutputParser(pydantic_object=ExecutionPlan)

    def _load_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Load agent capabilities from contracts."""

        # In production, parse YAML contracts
        # For now, return simplified registry

        return {
            "data-contracts-quality": {
                "domain": "data",
                "capability": "Validate data quality using Great Expectations",
                "typical_duration": "5-10 minutes",
                "typical_cost": "£0.5",
            },
            "feature-store-manager": {
                "domain": "data",
                "capability": "Manage features in SageMaker Feature Store",
                "typical_duration": "10-20 minutes",
                "typical_cost": "£2",
            },
            "churn-forecast-modeler": {
                "domain": "model",
                "capability": "Train and predict customer churn",
                "typical_duration": "30-60 minutes (training), 5-10 minutes (prediction)",
                "typical_cost": "£15 (training), £3 (prediction)",
            },
            "mlops-deployer": {
                "domain": "mlops",
                "capability": "Deploy models with canary/blue-green strategies",
                "typical_duration": "20-40 minutes",
                "typical_cost": "£8",
            },
            "monitoring-drift-watcher": {
                "domain": "mlops",
                "capability": "Detect data and model drift",
                "typical_duration": "5-15 minutes",
                "typical_cost": "£1",
            },
            "viz-storyteller": {
                "domain": "reporting",
                "capability": "Generate automated HTML reports with visualizations",
                "typical_duration": "3-5 minutes",
                "typical_cost": "£0.5",
            },
            "etl-transformer": {
                "domain": "data",
                "capability": "Transform data through bronze/silver/gold layers",
                "typical_duration": "15-30 minutes",
                "typical_cost": "£5",
            },
            "ingestion-orchestrator": {
                "domain": "data",
                "capability": "Ingest data from various sources",
                "typical_duration": "10-20 minutes",
                "typical_cost": "£3",
            },
        }

    async def plan(
        self,
        task_spec: TaskSpec,
        context: Dict[str, Any],
    ) -> ExecutionPlan:
        """
        Generate execution plan using LLM.

        Args:
            task_spec: Task specification
            context: Additional context (system state, constraints, etc.)

        Returns:
            Execution plan with subtasks
        """

        logger.info(f"Generating LLM-powered plan for: {task_spec.agent_name}")

        # Build prompt
        prompt = self._build_planning_prompt(task_spec, context)

        # Get plan from Claude
        try:
            response = await self.llm.ainvoke(prompt)

            # Parse response
            plan = self.parser.parse(response.content)

            logger.info(
                f"Plan generated with {len(plan.subtasks)} subtasks",
                goal=plan.goal,
                estimated_cost=plan.estimated_cost_gbp,
                estimated_duration=plan.estimated_duration_minutes,
            )

            return plan

        except Exception as e:
            logger.error(f"LLM planning failed: {e}, falling back to rule-based")
            # Fallback to rule-based planning
            return self._fallback_plan(task_spec)

    def _build_planning_prompt(
        self,
        task_spec: TaskSpec,
        context: Dict[str, Any],
    ) -> str:
        """Build the planning prompt for Claude."""

        agent_descriptions = "\n".join([
            f"- **{name}** ({info['domain']}): {info['capability']} | "
            f"Duration: {info['typical_duration']} | Cost: {info['typical_cost']}"
            for name, info in self.agent_capabilities.items()
        ])

        current_time = context.get("current_time", "2025-01-01 10:00 UK")
        budget_remaining = context.get("budget_remaining_gbp", 50.0)
        system_load = context.get("system_load", "normal")

        prompt = f"""
You are the supervisor of the Aurora Energy agentic data & analytics platform.
Your job is to decompose high-level goals into a sequence of agent tasks.

**Available Agents:**
{agent_descriptions}

**Current System State:**
- Current time: {current_time}
- Budget remaining today: £{budget_remaining:.2f}
- System load: {system_load}
- Environment: {self.config.environment.value}

**User Goal:**
Agent: {task_spec.agent_name}
Priority: {task_spec.priority.value}
Inputs: {json.dumps(task_spec.inputs, indent=2)}
Deadline: {task_spec.deadline.isoformat() if task_spec.deadline else "None"}

**Your Task:**
Generate an execution plan that:
1. Decomposes the goal into concrete subtasks
2. Assigns each subtask to the appropriate agent
3. Respects dependencies between tasks
4. Optimizes for cost and time
5. Includes error handling strategies

**Constraints:**
- Total cost must be <= £{budget_remaining:.2f}
- If goal involves a model, it must follow: data validation → feature prep → model execution → drift check → reporting
- High priority tasks get more resources
- Include human approval for production deployments

**Output Format:**
{self.parser.get_format_instructions()}

Generate the plan now.
"""

        return prompt

    def _fallback_plan(self, task_spec: TaskSpec) -> ExecutionPlan:
        """Fallback to rule-based planning if LLM fails."""

        logger.info("Using rule-based fallback planning")

        agent_name = task_spec.agent_name

        # Simple rule-based decomposition
        if "churn" in agent_name:
            subtasks = [
                SubTask(
                    agent="data-contracts-quality",
                    description="Validate input data quality",
                    inputs={"dataset_uri": "s3://aurora-data-dev/gold/customers/"},
                    depends_on=[],
                ),
                SubTask(
                    agent="feature-store-manager",
                    description="Update feature store",
                    inputs={"operation": "ingest"},
                    depends_on=["data-contracts-quality"],
                ),
                SubTask(
                    agent="churn-forecast-modeler",
                    description="Generate churn predictions",
                    inputs={"mode": "predict"},
                    depends_on=["feature-store-manager"],
                ),
                SubTask(
                    agent="monitoring-drift-watcher",
                    description="Check for drift",
                    inputs={"model_name": "churn"},
                    depends_on=["churn-forecast-modeler"],
                ),
                SubTask(
                    agent="viz-storyteller",
                    description="Generate report",
                    inputs={"report_type": "churn"},
                    depends_on=["churn-forecast-modeler", "monitoring-drift-watcher"],
                ),
            ]
        else:
            # Default: single task
            subtasks = [
                SubTask(
                    agent=agent_name,
                    description=f"Execute {agent_name}",
                    inputs=task_spec.inputs,
                    depends_on=[],
                )
            ]

        return ExecutionPlan(
            goal=f"Execute {agent_name}",
            subtasks=subtasks,
            estimated_cost_gbp=10.0,
            estimated_duration_minutes=30,
            risk_factors=["Rule-based fallback used"],
        )


async def create_llm_planner() -> LLMPlanner:
    """Factory function to create LLM planner."""
    return LLMPlanner()
