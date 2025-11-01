"""Common type definitions for the platform."""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Environment(str, Enum):
    """Deployment environment."""
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class RunStatus(str, Enum):
    """Status of a task or agent run."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(str, Enum):
    """Priority level for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentMetadata(BaseModel):
    """Metadata for an agent."""
    name: str
    domain: str
    capability: str
    version: str = "0.1.0"


class TaskSpec(BaseModel):
    """Specification for a task."""
    task_id: str
    agent_name: str
    priority: TaskPriority = TaskPriority.MEDIUM
    inputs: Dict[str, Any]
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None


class TaskResult(BaseModel):
    """Result from a task execution."""
    task_id: str
    agent_name: str
    status: RunStatus
    outputs: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: Optional[datetime] = None
    cost_gbp: float = 0.0


class DataLineage(BaseModel):
    """Data lineage information."""
    source_uri: str
    target_uri: str
    transformation: str
    agent_name: str
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphState(BaseModel):
    """State passed between agents in LangGraph."""
    task_id: str
    run_id: str
    current_agent: str
    status: RunStatus
    inputs: Dict[str, Any]
    outputs: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    cost_so_far_gbp: float = 0.0
    risk_score: float = 0.0
    lineage: List[DataLineage] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
