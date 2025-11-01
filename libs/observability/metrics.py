"""Metrics collection with OpenTelemetry."""

from enum import Enum
from typing import Dict, Any
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

from libs.common.config import get_config
from libs.common.logging import get_logger

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


def init_metrics() -> None:
    """Initialize OpenTelemetry metrics."""
    config = get_config()

    resource = Resource.create(
        {
            "service.name": "aurora-energy-platform",
            "service.version": "0.1.0",
            "deployment.environment": config.environment.value,
        }
    )

    if config.otel_exporter_endpoint:
        exporter = OTLPMetricExporter(
            endpoint=config.otel_exporter_endpoint,
            insecure=True,
        )
        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)
        provider = MeterProvider(resource=resource, metric_readers=[reader])
    else:
        logger.warning("OTEL exporter endpoint not configured, metrics will not be exported")
        provider = MeterProvider(resource=resource)

    metrics.set_meter_provider(provider)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance."""
    return metrics.get_meter(name)


def record_metric(
    meter_name: str,
    metric_name: str,
    value: float,
    metric_type: MetricType = MetricType.COUNTER,
    attributes: Dict[str, Any] = None,
) -> None:
    """Record a metric value."""
    meter = get_meter(meter_name)
    attributes = attributes or {}

    if metric_type == MetricType.COUNTER:
        counter = meter.create_counter(metric_name)
        counter.add(value, attributes)
    elif metric_type == MetricType.GAUGE:
        gauge = meter.create_gauge(metric_name)
        gauge.set(value, attributes)
    elif metric_type == MetricType.HISTOGRAM:
        histogram = meter.create_histogram(metric_name)
        histogram.record(value, attributes)
