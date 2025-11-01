"""Monitoring & Drift Watcher - Detect data/model drift and performance decay."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import numpy as np
import pandas as pd

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class MonitoringDriftWatcher:
    """
    Monitoring & Drift Watcher Agent.

    Responsibilities:
    - Detect data drift (PSI, KS test, etc.)
    - Detect model drift (performance decay)
    - Detect concept drift
    - Alert on anomalies
    - Trigger retraining when necessary
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Drift detection thresholds
        self.psi_threshold = 0.2  # Population Stability Index
        self.ks_threshold = 0.3   # Kolmogorov-Smirnov
        self.performance_threshold = 0.10  # 10% performance drop

    @trace_agent("monitoring-drift-watcher")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Execute drift monitoring.

        Args:
            state: Current graph state

        Returns:
            Drift detection results
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="monitoring-drift-watcher",
            task_id=state.task_id,
            run_id=run_id,
        )

        model_name = state.inputs.get("model_name", "churn")

        logger.info(
            f"Starting drift monitoring for: {model_name}",
            task_id=state.task_id,
        )

        try:
            # Detect different types of drift
            data_drift = await self._detect_data_drift(state.inputs)
            model_drift = await self._detect_model_drift(state.inputs)
            concept_drift = await self._detect_concept_drift(state.inputs)

            # Aggregate drift signals
            drift_detected = (
                data_drift["drift_detected"]
                or model_drift["drift_detected"]
                or concept_drift["drift_detected"]
            )

            # Determine action
            action = await self._determine_action(
                data_drift,
                model_drift,
                concept_drift,
            )

            # Persist drift report
            report_uri = await self._persist_drift_report(
                model_name=model_name,
                data_drift=data_drift,
                model_drift=model_drift,
                concept_drift=concept_drift,
                action=action,
                run_id=run_id,
            )

            # Send alerts if drift detected
            if drift_detected:
                await self._send_alerts(model_name, action, report_uri)

            # Track costs
            cost_gbp = 1.0
            self.cost_tracker.record_cost(
                agent_name="monitoring-drift-watcher",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="computation",
                metadata={"model": model_name, "run_id": run_id},
            )

            logger.info(
                "Drift monitoring completed",
                task_id=state.task_id,
                model=model_name,
                drift_detected=drift_detected,
                action=action,
            )

            return {
                "status": "success",
                "model_name": model_name,
                "drift_detected": drift_detected,
                "data_drift": data_drift,
                "model_drift": model_drift,
                "concept_drift": concept_drift,
                "action": action,
                "report_uri": report_uri,
                "cost_gbp": cost_gbp,
            }

        except Exception as e:
            logger.error(f"Drift monitoring failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "model_name": model_name,
                "agent": "monitoring-drift-watcher",
            }

    async def _detect_data_drift(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Detect data drift using PSI and KS tests."""

        logger.info("Detecting data drift")

        # In production:
        # 1. Load reference (training) data
        # 2. Load current (production) data
        # 3. Calculate PSI for each feature
        # 4. Run KS test for numerical features

        # from evidently.test_suite import TestSuite
        # from evidently.test_preset import DataDriftTestPreset
        #
        # test_suite = TestSuite(tests=[DataDriftTestPreset()])
        # test_suite.run(reference_data=reference_df, current_data=current_df)

        # Simulate drift detection
        features_analyzed = 50
        features_with_drift = 3

        psi_scores = {
            f"feature_{i}": np.random.uniform(0, 0.3)
            for i in range(features_analyzed)
        }

        # Check which features exceed threshold
        drift_features = [
            f for f, score in psi_scores.items()
            if score > self.psi_threshold
        ]

        drift_detected = len(drift_features) > 0

        return {
            "drift_detected": drift_detected,
            "features_analyzed": features_analyzed,
            "features_with_drift": len(drift_features),
            "drift_features": drift_features[:10],  # Top 10
            "max_psi": max(psi_scores.values()),
            "mean_psi": np.mean(list(psi_scores.values())),
            "drift_severity": "high" if len(drift_features) > 5 else "medium" if len(drift_features) > 0 else "none",
        }

    async def _detect_model_drift(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Detect model performance drift."""

        logger.info("Detecting model drift")

        # In production:
        # 1. Load baseline metrics (from MLflow)
        # 2. Calculate current metrics on recent predictions
        # 3. Compare and calculate drift

        # Simulate
        baseline_auc = 0.82
        current_auc = 0.78  # 4.8% drop
        baseline_calibration = 0.015
        current_calibration = 0.022  # Worse calibration

        auc_drop = baseline_auc - current_auc
        auc_drop_pct = (auc_drop / baseline_auc) * 100

        drift_detected = auc_drop_pct > (self.performance_threshold * 100)

        return {
            "drift_detected": drift_detected,
            "baseline_auc": baseline_auc,
            "current_auc": current_auc,
            "auc_drop_pct": auc_drop_pct,
            "baseline_calibration": baseline_calibration,
            "current_calibration": current_calibration,
            "drift_severity": "high" if auc_drop_pct > 10 else "medium" if auc_drop_pct > 5 else "none",
        }

    async def _detect_concept_drift(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Detect concept drift (relationship changes)."""

        logger.info("Detecting concept drift")

        # In production:
        # 1. Analyze prediction residuals over time
        # 2. Check if feature importances have changed
        # 3. Look for non-stationarity in error patterns

        # Simulate
        residual_trend = 0.08  # 8% upward trend in errors
        feature_importance_shift = 0.15  # 15% change in top features

        drift_detected = residual_trend > 0.05 or feature_importance_shift > 0.10

        return {
            "drift_detected": drift_detected,
            "residual_trend": residual_trend,
            "feature_importance_shift": feature_importance_shift,
            "drift_severity": "high" if drift_detected else "none",
        }

    async def _determine_action(
        self,
        data_drift: Dict[str, Any],
        model_drift: Dict[str, Any],
        concept_drift: Dict[str, Any],
    ) -> str:
        """Determine what action to take based on drift signals."""

        # Combine severity scores
        severities = [
            data_drift.get("drift_severity", "none"),
            model_drift.get("drift_severity", "none"),
            concept_drift.get("drift_severity", "none"),
        ]

        if "high" in severities:
            # Multiple high severity drifts or concept drift
            if concept_drift["drift_detected"]:
                return "emergency_retrain"
            else:
                return "trigger_retrain"

        elif "medium" in severities:
            return "schedule_review"

        else:
            return "monitor"

    async def _persist_drift_report(
        self,
        model_name: str,
        data_drift: Dict[str, Any],
        model_drift: Dict[str, Any],
        concept_drift: Dict[str, Any],
        action: str,
        run_id: str,
    ) -> str:
        """Persist drift report to S3."""

        ds = datetime.utcnow().strftime("%Y%m%d")
        key = f"drift/reports/{model_name}/{ds}/{run_id}/drift_report.json"

        report = {
            "model_name": model_name,
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "data_drift": data_drift,
            "model_drift": model_drift,
            "concept_drift": concept_drift,
            "action": action,
        }

        report_uri = self.s3.write_json(
            data=report,
            bucket=self.config.reports_bucket,
            key=key,
        )

        return report_uri

    async def _send_alerts(
        self,
        model_name: str,
        action: str,
        report_uri: str,
    ) -> None:
        """Send alerts for drift detection."""

        logger.warning(
            f"Drift detected for {model_name}, action: {action}",
            model=model_name,
            action=action,
            report=report_uri,
        )

        # In production:
        # 1. Send SNS notification
        # 2. Post to Slack
        # 3. Create PagerDuty incident if emergency
        # 4. Update dashboard

        if action == "emergency_retrain":
            severity = "P1"
        elif action == "trigger_retrain":
            severity = "P2"
        else:
            severity = "P3"

        logger.info(f"Alert sent: {severity} - {action}")


async def create_monitoring_drift_watcher() -> MonitoringDriftWatcher:
    """Factory function to create drift watcher."""
    return MonitoringDriftWatcher()
