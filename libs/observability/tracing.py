"""Distributed tracing with OpenTelemetry."""

from typing import Any, Dict, Optional, Callable
from functools import wraps
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

from libs.common.config import get_config
from libs.common.logging import get_logger

logger = get_logger(__name__)


def init_tracing() -> None:
    """Initialize OpenTelemetry tracing."""
    config = get_config()

    resource = Resource.create(
        {
            "service.name": "aurora-energy-platform",
            "service.version": "0.1.0",
            "deployment.environment": config.environment.value,
        }
    )

    provider = TracerProvider(resource=resource)

    if config.otel_exporter_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.otel_exporter_endpoint,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    else:
        logger.warning("OTEL exporter endpoint not configured, traces will not be exported")

    trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def trace_agent(agent_name: str) -> Callable:
    """Decorator to trace agent execution."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(agent_name)
            with tracer.start_as_current_span(
                f"{agent_name}.execute",
                attributes={
                    "agent.name": agent_name,
                },
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("agent.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("agent.status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(agent_name)
            with tracer.start_as_current_span(
                f"{agent_name}.execute",
                attributes={
                    "agent.name": agent_name,
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("agent.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("agent.status", "error")
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        # Detect if function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def trace_task(task_name: str) -> Callable:
    """Decorator to trace individual tasks."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(
                task_name,
                attributes={
                    "task.name": task_name,
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("task.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("task.status", "error")
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator
