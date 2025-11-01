"""Policy guards and safety checks."""

from typing import Any, Dict, List, Optional
from enum import Enum
import re

from libs.common.config import get_config
from libs.common.logging import get_logger
from libs.common.types import GraphState

logger = get_logger(__name__)


class Severity(str, Enum):
    """Violation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PolicyViolation(Exception):
    """Exception raised when a policy is violated."""

    def __init__(
        self,
        message: str,
        policy_name: str,
        severity: Severity = Severity.ERROR,
    ):
        self.message = message
        self.policy_name = policy_name
        self.severity = severity
        super().__init__(message)


class SafetyCheck:
    """Safety checks for agent operations."""

    @staticmethod
    def check_no_pii_in_data(data: Dict[str, Any]) -> bool:
        """Check if data contains potential PII."""
        # Simplified PII detection - in production use Presidio or similar
        pii_patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN/NI pattern
        ]

        data_str = str(data)
        for pattern in pii_patterns:
            if re.search(pattern, data_str):
                logger.warning("Potential PII detected in data")
                return False

        return True

    @staticmethod
    def check_data_size_limits(
        data: Any,
        max_size_mb: float = 100.0,
    ) -> bool:
        """Check if data size is within limits."""
        import sys

        size_mb = sys.getsizeof(data) / (1024 * 1024)
        if size_mb > max_size_mb:
            logger.warning(f"Data size {size_mb:.2f}MB exceeds limit {max_size_mb}MB")
            return False
        return True

    @staticmethod
    def check_file_path_safe(path: str) -> bool:
        """Check if file path is safe (no path traversal)."""
        if ".." in path or path.startswith("/"):
            logger.warning(f"Unsafe file path detected: {path}")
            return False
        return True


class ComplianceCheck:
    """Compliance checks for GDPR, DPA 2018, etc."""

    @staticmethod
    def check_data_retention(
        data_type: str,
        retention_days: int,
    ) -> bool:
        """Check if retention period complies with policy."""
        # UK GDPR retention limits
        MAX_RETENTION = {
            "customer_data": 2555,  # 7 years
            "transaction_data": 2555,  # 7 years
            "model_predictions": 365,  # 1 year
            "audit_logs": 2555,  # 7 years
            "temp_data": 90,  # 90 days
        }

        max_days = MAX_RETENTION.get(data_type, 365)
        if retention_days > max_days:
            logger.warning(
                f"Retention period {retention_days} days exceeds limit "
                f"{max_days} days for {data_type}"
            )
            return False

        return True

    @staticmethod
    def check_data_minimisation(
        required_fields: List[str],
        requested_fields: List[str],
    ) -> bool:
        """Check data minimisation principle (only collect what's needed)."""
        extra_fields = set(requested_fields) - set(required_fields)
        if extra_fields:
            logger.warning(f"Unnecessary fields requested: {extra_fields}")
            return False
        return True

    @staticmethod
    def check_lawful_basis(
        purpose: str,
        data_subject_consent: bool = False,
    ) -> bool:
        """Check if there's a lawful basis for processing."""
        # Simplified check - in production, integrate with consent management
        LEGITIMATE_PURPOSES = [
            "contract_fulfillment",
            "legal_obligation",
            "legitimate_interest",
            "consent",
        ]

        if purpose not in LEGITIMATE_PURPOSES and not data_subject_consent:
            logger.warning(f"No lawful basis for purpose: {purpose}")
            return False

        return True


class PolicyGuard:
    """Main policy guard for enforcing rules."""

    def __init__(self) -> None:
        self.config = get_config()
        self.safety = SafetyCheck()
        self.compliance = ComplianceCheck()

    def check_task_allowed(
        self,
        agent_name: str,
        state: GraphState,
    ) -> tuple[bool, Optional[str]]:
        """Check if task is allowed to proceed."""
        checks = [
            self._check_cost_limits(agent_name, state),
            self._check_retry_limits(state),
            self._check_environment_constraints(agent_name),
        ]

        for allowed, reason in checks:
            if not allowed:
                return False, reason

        return True, None

    def _check_cost_limits(
        self,
        agent_name: str,
        state: GraphState,
    ) -> tuple[bool, Optional[str]]:
        """Check if cost limits are respected."""
        if not self.config.enable_cost_gates:
            return True, None

        if state.cost_so_far_gbp > self.config.daily_budget_gbp:
            return False, f"Daily budget exceeded: £{state.cost_so_far_gbp:.2f}"

        return True, None

    def _check_retry_limits(
        self,
        state: GraphState,
    ) -> tuple[bool, Optional[str]]:
        """Check if retry limits are respected."""
        if state.retry_count >= state.max_retries:
            return False, f"Max retries exceeded: {state.retry_count}/{state.max_retries}"

        return True, None

    def _check_environment_constraints(
        self,
        agent_name: str,
    ) -> tuple[bool, Optional[str]]:
        """Check environment-specific constraints."""
        # In production, check if agent is allowed to run in current environment
        HIGH_RISK_AGENTS = [
            "pricing-tariff-optimizer",
            "portfolio-risk-modeler",
            "mlops-deployer",
        ]

        if (
            agent_name in HIGH_RISK_AGENTS
            and self.config.environment.value == "prod"
            and self.config.enable_human_approval
        ):
            return False, f"{agent_name} requires human approval in production"

        return True, None

    def validate_outputs(
        self,
        agent_name: str,
        outputs: Dict[str, Any],
    ) -> bool:
        """Validate agent outputs before persisting."""
        # Check for PII
        if not self.safety.check_no_pii_in_data(outputs):
            raise PolicyViolation(
                "PII detected in outputs",
                policy_name="no_pii_in_outputs",
                severity=Severity.CRITICAL,
            )

        # Check data size
        if not self.safety.check_data_size_limits(outputs):
            logger.warning(f"Output size warning for {agent_name}")

        return True
