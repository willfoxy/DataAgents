"""Base classes for training backends."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration for a training job."""
    model_name: str
    dataset_uri: str
    output_uri: str
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    instance_type: str = "ml.m5.xlarge"
    instance_count: int = 1
    max_runtime_seconds: int = 3600
    tags: Dict[str, str] = Field(default_factory=dict)


class TrainingResult(BaseModel):
    """Result from a training job."""
    job_id: str
    status: str  # "InProgress", "Completed", "Failed", "Stopped"
    model_uri: Optional[str] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    cost_gbp: float = 0.0
    duration_seconds: float = 0.0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TrainerBackend(ABC):
    """Abstract base class for training backends."""

    @abstractmethod
    def submit_training_job(
        self,
        config: TrainingConfig,
    ) -> str:
        """Submit a training job and return job ID."""
        pass

    @abstractmethod
    def get_job_status(
        self,
        job_id: str,
    ) -> TrainingResult:
        """Get status of a training job."""
        pass

    @abstractmethod
    def cancel_job(
        self,
        job_id: str,
    ) -> bool:
        """Cancel a running training job."""
        pass

    @abstractmethod
    def estimate_cost(
        self,
        config: TrainingConfig,
    ) -> float:
        """Estimate cost for training job in GBP."""
        pass
