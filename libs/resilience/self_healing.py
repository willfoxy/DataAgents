"""Self-healing agent for automatic error recovery."""

from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

from langchain_anthropic import ChatAnthropic

from libs.common.types import GraphState
from libs.common.logging import get_logger

logger = get_logger(__name__)


class RecoveryStrategy(str, Enum):
    """Recovery strategies."""
    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    SCALE_UP = "scale_up"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    SKIP = "skip"
    ESCALATE = "escalate"


class RecoveryAction(BaseModel):
    """Action to take for recovery."""
    strategy: RecoveryStrategy
    params: Dict[str, Any] = {}
    reason: str
    confidence: float  # 0.0 to 1.0


class ErrorAnalyzer:
    """Analyze errors and determine patterns."""

    def __init__(self) -> None:
        self.error_history: Dict[str, list] = {}

    def record_error(
        self,
        agent_name: str,
        error_type: str,
        error_message: str,
    ) -> None:
        """Record an error occurrence."""

        if agent_name not in self.error_history:
            self.error_history[agent_name] = []

        self.error_history[agent_name].append({
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_error_frequency(
        self,
        agent_name: str,
        error_type: str,
        hours: int = 24,
    ) -> int:
        """Get frequency of specific error type."""

        if agent_name not in self.error_history:
            return 0

        cutoff = datetime.utcnow().timestamp() - (hours * 3600)

        count = sum(
            1 for err in self.error_history[agent_name]
            if err["type"] == error_type
            and datetime.fromisoformat(err["timestamp"]).timestamp() > cutoff
        )

        return count

    def is_recurring_error(
        self,
        agent_name: str,
        error_type: str,
        threshold: int = 3,
    ) -> bool:
        """Check if error is recurring."""
        return self.get_error_frequency(agent_name, error_type) >= threshold


class SelfHealingAgent:
    """
    Self-healing agent that automatically diagnoses and fixes common failures.

    Capabilities:
    - Pattern matching on error types
    - Automatic retries with backoff
    - Resource scaling
    - Rollback on deployment failures
    - LLM-based diagnosis for novel errors
    """

    def __init__(self) -> None:
        self.error_analyzer = ErrorAnalyzer()

        # Initialize LLM for novel error diagnosis
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    async def handle_failure(
        self,
        agent_name: str,
        error: Exception,
        state: GraphState,
    ) -> RecoveryAction:
        """
        Determine recovery strategy for a failure.

        Args:
            agent_name: Name of the failed agent
            error: The exception that occurred
            state: Current graph state

        Returns:
            Recovery action to take
        """

        error_type = type(error).__name__
        error_message = str(error)

        logger.warning(
            f"Handling failure in {agent_name}",
            agent=agent_name,
            error_type=error_type,
            error_message=error_message,
        )

        # Record error for pattern analysis
        self.error_analyzer.record_error(agent_name, error_type, error_message)

        # Check if recurring
        is_recurring = self.error_analyzer.is_recurring_error(agent_name, error_type)

        # Pattern matching on error types
        if "DataQuality" in error_type or "ValidationError" in error_type:
            return await self._recover_data_quality(error_message, state, is_recurring)

        elif "ResourceExhausted" in error_type or "OutOfMemory" in error_type:
            return RecoveryAction(
                strategy=RecoveryStrategy.SCALE_UP,
                params={"instance_type": "ml.m5.2xlarge"},
                reason="Insufficient resources detected, scaling up",
                confidence=0.95,
            )

        elif "Timeout" in error_type:
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                params={"max_retries": 3, "backoff_factor": 2},
                reason="Timeout detected, retrying with backoff",
                confidence=0.90,
            )

        elif "SchemaEvolution" in error_type or "SchemaM" in error_type:
            return await self._handle_schema_evolution(error_message, state)

        elif "ModelNotFound" in error_type:
            return RecoveryAction(
                strategy=RecoveryStrategy.FALLBACK,
                params={"use_previous_model": True},
                reason="Model not found, falling back to previous version",
                confidence=0.85,
            )

        elif "DeploymentFailed" in error_type:
            return RecoveryAction(
                strategy=RecoveryStrategy.ROLLBACK,
                params={"rollback_to": "previous_version"},
                reason="Deployment failed, rolling back",
                confidence=0.98,
            )

        elif "BudgetExceeded" in error_type or "CostCeiling" in error_type:
            return RecoveryAction(
                strategy=RecoveryStrategy.SKIP,
                params={"reason": "budget_exceeded"},
                reason="Budget exceeded, skipping non-critical task",
                confidence=1.0,
            )

        # For novel/unknown errors, use LLM diagnosis
        else:
            return await self._llm_diagnose(agent_name, error, state)

    async def _recover_data_quality(
        self,
        error_message: str,
        state: GraphState,
        is_recurring: bool,
    ) -> RecoveryAction:
        """Handle data quality failures."""

        if is_recurring:
            # Recurring DQ issues need human intervention
            return RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                params={
                    "severity": "P1",
                    "assignee": "data-owner",
                    "message": f"Recurring data quality issue: {error_message}",
                },
                reason="Recurring data quality issue requires human review",
                confidence=1.0,
            )

        # First occurrence: try fallback data
        return RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK,
            params={
                "use_previous_date": True,
                "notify": True,
            },
            reason="Data quality issue, using previous day's data",
            confidence=0.80,
        )

    async def _handle_schema_evolution(
        self,
        error_message: str,
        state: GraphState,
    ) -> RecoveryAction:
        """Handle schema evolution automatically."""

        logger.info("Attempting automatic schema migration")

        # In production: Generate schema migration
        # migration = self._generate_schema_migration(old_schema, new_schema)

        return RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            params={
                "update_schema": True,
                "migration_script": "auto_generated_migration.sql",
            },
            reason="Schema evolution detected, applying migration",
            confidence=0.75,
        )

    async def _llm_diagnose(
        self,
        agent_name: str,
        error: Exception,
        state: GraphState,
    ) -> RecoveryAction:
        """Use LLM to diagnose novel errors."""

        logger.info(f"Using LLM to diagnose error in {agent_name}")

        error_context = {
            "agent_name": agent_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "state_inputs": state.inputs,
            "retry_count": state.retry_count,
            "recent_errors": self.error_analyzer.error_history.get(agent_name, [])[-5:],
        }

        prompt = f"""
You are a self-healing system diagnosing an error in the Aurora Energy platform.

**Error Context:**
{error_context}

**Available Recovery Strategies:**
- RETRY: Simply retry the operation
- RETRY_WITH_BACKOFF: Retry with exponential backoff
- SCALE_UP: Increase resource allocation
- FALLBACK: Use fallback data/model
- ROLLBACK: Revert to previous state
- SKIP: Skip this task
- ESCALATE: Escalate to human

**Your Task:**
1. Analyze the error and context
2. Determine the most appropriate recovery strategy
3. Provide specific parameters for the recovery
4. Explain your reasoning

**Output Format (JSON):**
{{
    "strategy": "RETRY_WITH_BACKOFF",
    "params": {{"max_retries": 3, "backoff_factor": 2}},
    "reason": "Error appears transient, retry likely to succeed",
    "confidence": 0.85
}}
"""

        try:
            response = await self.llm.ainvoke(prompt)

            # Parse JSON response
            import json
            recovery_dict = json.loads(response.content)

            return RecoveryAction(
                strategy=RecoveryStrategy(recovery_dict["strategy"].lower()),
                params=recovery_dict.get("params", {}),
                reason=recovery_dict.get("reason", "LLM-recommended recovery"),
                confidence=recovery_dict.get("confidence", 0.70),
            )

        except Exception as e:
            logger.error(f"LLM diagnosis failed: {e}")

            # Ultimate fallback: escalate
            return RecoveryAction(
                strategy=RecoveryStrategy.ESCALATE,
                params={"severity": "P2"},
                reason=f"Unable to automatically recover from: {error}",
                confidence=1.0,
            )


async def create_self_healing_agent() -> SelfHealingAgent:
    """Factory function to create self-healing agent."""
    return SelfHealingAgent()
