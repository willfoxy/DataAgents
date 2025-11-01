"""Viz Storyteller - Auto-generate reports and storyboards."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from pathlib import Path

from jinja2 import Template, Environment, FileSystemLoader
import matplotlib.pyplot as plt
import seaborn as sns

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class VizStoryteller:
    """
    Viz Storyteller Agent.

    Responsibilities:
    - Auto-generate HTML/PDF reports
    - Create visualizations (charts, plots)
    - Answer "What changed?" and "So what?"
    - Deliver insights with context
    - Send notifications (Slack, Teams, Email)
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

        # Set plot style
        sns.set_style("whitegrid")
        plt.rcParams["figure.figsize"] = (12, 6)

        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

    @trace_agent("viz-storyteller")
    async def execute(
        self,
        state: GraphState,
    ) -> Dict[str, Any]:
        """
        Generate report.

        Args:
            state: Current graph state

        Returns:
            Report generation results
        """
        run_id = str(uuid.uuid4())

        bind_context(
            agent_name="viz-storyteller",
            task_id=state.task_id,
            run_id=run_id,
        )

        report_type = state.inputs.get("report_type", "churn")

        logger.info(
            f"Starting report generation: {report_type}",
            task_id=state.task_id,
        )

        try:
            # Generate report based on type
            if report_type == "churn":
                report = await self._generate_churn_report(state.inputs)
            elif report_type == "drift":
                report = await self._generate_drift_report(state.inputs)
            elif report_type == "model_performance":
                report = await self._generate_model_performance_report(state.inputs)
            else:
                report = await self._generate_generic_report(state.inputs)

            # Persist report
            report_uri = await self._persist_report(report, report_type, run_id)

            # Send notifications
            await self._send_notifications(report_type, report_uri, report["summary"])

            # Track costs
            cost_gbp = 0.5
            self.cost_tracker.record_cost(
                agent_name="viz-storyteller",
                task_id=state.task_id,
                cost_gbp=cost_gbp,
                resource_type="computation",
                metadata={"report_type": report_type, "run_id": run_id},
            )

            logger.info(
                "Report generation completed",
                task_id=state.task_id,
                report_type=report_type,
                report_uri=report_uri,
            )

            return {
                "status": "success",
                "report_type": report_type,
                "report_uri": report_uri,
                "summary": report["summary"],
                "insights": report.get("insights", []),
                "cost_gbp": cost_gbp,
            }

        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "report_type": report_type,
                "agent": "viz-storyteller",
            }

    async def _generate_churn_report(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate churn forecast report."""

        logger.info("Generating churn report")

        # Load data (in production, from S3/MLflow)
        data = await self._load_churn_data(inputs)

        # Create visualizations
        charts = []

        # 1. Churn rate over time
        chart_uri = await self._create_churn_trend_chart(data)
        charts.append({"title": "Churn Rate Trend", "uri": chart_uri})

        # 2. Feature importance
        chart_uri = await self._create_feature_importance_chart(data)
        charts.append({"title": "Top Churn Drivers", "uri": chart_uri})

        # 3. Segmentation analysis
        chart_uri = await self._create_segment_analysis_chart(data)
        charts.append({"title": "Churn by Segment", "uri": chart_uri})

        # Generate insights
        insights = await self._generate_churn_insights(data)

        # Render HTML template
        template = self.jinja_env.get_template("churn_report.html")
        html_content = template.render(
            title="Daily Churn Forecast Report",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            summary=self._create_churn_summary(data),
            charts=charts,
            insights=insights,
            metrics=data.get("metrics", {}),
        )

        return {
            "html_content": html_content,
            "summary": self._create_churn_summary(data),
            "insights": insights,
            "charts": charts,
        }

    async def _generate_drift_report(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate drift monitoring report."""

        logger.info("Generating drift report")

        # Load drift data
        drift_data = inputs.get("drift_results", {})

        # Create visualizations
        charts = []

        # 1. PSI scores by feature
        chart_uri = await self._create_drift_chart(drift_data)
        charts.append({"title": "Feature Drift Scores", "uri": chart_uri})

        # Generate insights
        insights = [
            f"Data drift detected in {drift_data.get('features_with_drift', 0)} features",
            f"Model performance dropped by {drift_data.get('auc_drop_pct', 0):.1f}%",
            f"Recommended action: {drift_data.get('action', 'monitor')}",
        ]

        # Render HTML template
        template = self.jinja_env.get_template("drift_report.html")
        html_content = template.render(
            title="Drift Monitoring Report",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            summary="Drift analysis summary",
            charts=charts,
            insights=insights,
            drift_data=drift_data,
        )

        return {
            "html_content": html_content,
            "summary": "Drift detected",
            "insights": insights,
            "charts": charts,
        }

    async def _generate_model_performance_report(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate model performance report."""

        logger.info("Generating model performance report")

        # Load performance metrics
        metrics = inputs.get("metrics", {})

        # Create visualizations
        charts = []

        # ROC curve
        chart_uri = await self._create_roc_curve(metrics)
        charts.append({"title": "ROC Curve", "uri": chart_uri})

        # Calibration plot
        chart_uri = await self._create_calibration_plot(metrics)
        charts.append({"title": "Calibration Plot", "uri": chart_uri})

        insights = [
            f"AUC: {metrics.get('auc', 0):.3f}",
            f"Calibration error: {metrics.get('calibration_error', 0):.3f}",
            f"F1 Score: {metrics.get('f1', 0):.3f}",
        ]

        template = self.jinja_env.get_template("model_performance_report.html")
        html_content = template.render(
            title="Model Performance Report",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            summary="Performance metrics summary",
            charts=charts,
            insights=insights,
            metrics=metrics,
        )

        return {
            "html_content": html_content,
            "summary": "Model performance analysis",
            "insights": insights,
            "charts": charts,
        }

    async def _generate_generic_report(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate generic report."""

        return {
            "html_content": "<html><body><h1>Generic Report</h1></body></html>",
            "summary": "Generic report",
            "insights": [],
            "charts": [],
        }

    async def _load_churn_data(
        self,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Load churn data and metrics."""

        # In production: Load from S3/MLflow

        return {
            "predictions_count": 50000,
            "high_risk_count": 2500,
            "churn_rate": 0.05,
            "metrics": {
                "auc": 0.82,
                "precision": 0.75,
                "recall": 0.68,
                "f1": 0.71,
                "calibration_error": 0.015,
            },
            "feature_importance": {
                "tenure_days": 0.25,
                "support_tickets": 0.20,
                "price_increase": 0.18,
                "competitor_offers": 0.15,
                "usage_drop": 0.12,
            },
        }

    async def _create_churn_trend_chart(
        self,
        data: Dict[str, Any],
    ) -> str:
        """Create churn rate trend chart."""

        # Simulate time series data
        import numpy as np

        dates = [datetime.utcnow() - timedelta(days=i) for i in range(30, 0, -1)]
        churn_rates = np.random.uniform(0.04, 0.06, 30)

        plt.figure(figsize=(12, 6))
        plt.plot(dates, churn_rates, marker="o", linewidth=2)
        plt.title("Churn Rate - Last 30 Days", fontsize=16, fontweight="bold")
        plt.xlabel("Date")
        plt.ylabel("Churn Rate")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        # Save to temp file (in production: upload to S3)
        chart_path = f"/tmp/churn_trend_{uuid.uuid4()}.png"
        plt.savefig(chart_path, dpi=100, bbox_inches="tight")
        plt.close()

        # In production: Upload to S3 and return URI
        chart_uri = f"s3://{self.config.reports_bucket}/charts/churn_trend.png"

        return chart_uri

    async def _create_feature_importance_chart(
        self,
        data: Dict[str, Any],
    ) -> str:
        """Create feature importance chart."""

        feature_importance = data.get("feature_importance", {})

        plt.figure(figsize=(10, 6))
        features = list(feature_importance.keys())
        importances = list(feature_importance.values())

        plt.barh(features, importances, color="steelblue")
        plt.title("Top Churn Drivers", fontsize=16, fontweight="bold")
        plt.xlabel("Importance")
        plt.tight_layout()

        chart_path = f"/tmp/feature_importance_{uuid.uuid4()}.png"
        plt.savefig(chart_path, dpi=100, bbox_inches="tight")
        plt.close()

        chart_uri = f"s3://{self.config.reports_bucket}/charts/feature_importance.png"

        return chart_uri

    async def _create_segment_analysis_chart(
        self,
        data: Dict[str, Any],
    ) -> str:
        """Create segment analysis chart."""

        # Simulate segment data
        segments = ["Premium", "Standard", "Basic"]
        churn_rates = [0.03, 0.05, 0.08]

        plt.figure(figsize=(8, 6))
        plt.bar(segments, churn_rates, color=["#2ecc71", "#f39c12", "#e74c3c"])
        plt.title("Churn Rate by Segment", fontsize=16, fontweight="bold")
        plt.ylabel("Churn Rate")
        plt.tight_layout()

        chart_path = f"/tmp/segment_analysis_{uuid.uuid4()}.png"
        plt.savefig(chart_path, dpi=100, bbox_inches="tight")
        plt.close()

        chart_uri = f"s3://{self.config.reports_bucket}/charts/segment_analysis.png"

        return chart_uri

    async def _create_drift_chart(self, drift_data: Dict[str, Any]) -> str:
        """Create drift visualization."""
        chart_uri = f"s3://{self.config.reports_bucket}/charts/drift_scores.png"
        return chart_uri

    async def _create_roc_curve(self, metrics: Dict[str, Any]) -> str:
        """Create ROC curve."""
        chart_uri = f"s3://{self.config.reports_bucket}/charts/roc_curve.png"
        return chart_uri

    async def _create_calibration_plot(self, metrics: Dict[str, Any]) -> str:
        """Create calibration plot."""
        chart_uri = f"s3://{self.config.reports_bucket}/charts/calibration.png"
        return chart_uri

    async def _generate_churn_insights(
        self,
        data: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable insights from churn data."""

        insights = []

        # High risk customers
        high_risk_pct = (data["high_risk_count"] / data["predictions_count"]) * 100
        insights.append(
            f"🔴 {high_risk_pct:.1f}% of customers ({data['high_risk_count']:,}) are at high risk of churning"
        )

        # Top driver
        top_feature = max(data["feature_importance"].items(), key=lambda x: x[1])
        insights.append(
            f"📊 Top churn driver: {top_feature[0].replace('_', ' ').title()} "
            f"({top_feature[1]*100:.0f}% importance)"
        )

        # Model performance
        auc = data["metrics"]["auc"]
        if auc >= 0.80:
            insights.append(f"✅ Model performance is strong (AUC: {auc:.3f})")
        else:
            insights.append(f"⚠️ Model performance needs attention (AUC: {auc:.3f})")

        # Recommendations
        insights.append(
            "💡 Recommended action: Proactive outreach to high-risk customers with retention offers"
        )

        return insights

    def _create_churn_summary(self, data: Dict[str, Any]) -> str:
        """Create executive summary."""

        return f"""
        Analyzed {data['predictions_count']:,} customers with the daily churn forecast model.
        Identified {data['high_risk_count']:,} customers at high risk of churning in the next 30 days.
        Model performance: AUC {data['metrics']['auc']:.3f}, Calibration error {data['metrics']['calibration_error']:.3f}.
        """

    async def _persist_report(
        self,
        report: Dict[str, Any],
        report_type: str,
        run_id: str,
    ) -> str:
        """Persist report to S3."""

        ds = datetime.utcnow().strftime("%Y%m%d")
        key = f"reports/{report_type}/{ds}/{run_id}/index.html"

        html_content = report["html_content"]

        report_uri = self.s3.write_text(
            content=html_content,
            bucket=self.config.reports_bucket,
            key=key,
            content_type="text/html",
        )

        return report_uri

    async def _send_notifications(
        self,
        report_type: str,
        report_uri: str,
        summary: str,
    ) -> None:
        """Send notifications about new report."""

        logger.info(
            f"Sending notifications for {report_type} report",
            report_uri=report_uri,
        )

        # In production:
        # 1. Post to Slack
        # 2. Send email
        # 3. Post to Teams
        # 4. Update dashboard


async def create_viz_storyteller() -> VizStoryteller:
    """Factory function to create viz storyteller."""
    return VizStoryteller()
