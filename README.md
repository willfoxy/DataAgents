# Aurora Energy Agentic Data & Analytics Platform

A production-grade, multi-agent system using LangGraph for orchestration and AWS AgentCore for agent runtimes. This platform autonomously handles data ingestion, model building, evaluation, and deployment for energy retail operations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Supervisor Director                         │
│           (LangGraph Orchestration & Routing)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  ┌─────▼─────┐         ┌─────▼─────┐       ┌──────▼──────┐
  │  Intake   │         │   Data    │       │   Model     │
  │  Agents   │         │  Agents   │       │   Agents    │
  └───────────┘         └───────────┘       └─────────────┘
        │                     │                     │
  ┌─────▼─────────────────────▼─────────────────────▼─────┐
  │                  Data Lake (S3)                        │
  │  Raw (Bronze) → Silver → Gold + Feature Store          │
  └────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  ┌─────▼─────┐         ┌─────▼─────┐       ┌──────▼──────┐
  │ SageMaker │         │Databricks │       │  Azure ML   │
  │  Training │         │   Jobs    │       │Fine-tuning  │
  └───────────┘         └───────────┘       └─────────────┘
```

## Agent Roster (25 Agents)

### Control & Coordination (2)
- **supervisor-director**: Goal decomposition, routing, arbitration
- **intake-triage**: Capture objectives, convert to tasks

### Data Foundation (5)
- **data-cataloguer**: Maintain Glue catalogue, lineage
- **data-contracts-quality**: Enforce contracts, DQ tests
- **ingestion-orchestrator**: Batch/stream ingestion
- **etl-transformer**: Bronze→Silver→Gold transforms
- **feature-store-manager**: Feature views, backfills

### Model Development (10)
- **experiment-planner**: Design experiments, hyperparam search
- **acquisition-forecast-modeler**: Sign-up forecasts
- **churn-forecast-modeler**: Churn prediction & drivers
- **load-consumption-forecast**: Demand forecasts
- **pricing-tariff-optimizer**: Tariff optimisation
- **portfolio-risk-modeler**: Risk & hedging
- **trial-design-causal-inference**: A/B tests, uplift
- **anomaly-fraud-detector**: Fraud detection
- **customer-segmentation-clv**: Personas & CLV
- **prompt-model-evaluator**: LLM/agent evaluation

### MLOps & Monitoring (3)
- **mlops-deployer**: Package & deploy models
- **monitoring-drift-watcher**: Drift detection, retrain triggers
- **crosscloud-trainer**: Multi-cloud training orchestration

### Reporting & Governance (5)
- **viz-storyteller**: Auto-generate reports
- **human-loop-coordinator**: Review routing, feedback
- **compliance-privacy-auditor**: PII scans, audit trails
- **cost-optimizer**: Spend tracking, optimisation
- **knowledge-manager**: RAG index of decisions, playbooks

## Monorepo Structure

```
.
├── agents/                 # 25 specialist agents (LangGraph nodes)
├── libs/                   # Shared libraries
│   ├── common/            # Core utilities
│   ├── data_contracts/    # Data contract schemas
│   ├── observability/     # OpenTelemetry, logging
│   ├── cost_meter/        # Cost tracking
│   ├── policy_guards/     # Safety & compliance
│   └── trainer_backends/  # Cross-cloud training
├── pipelines/             # End-to-end workflows
│   ├── churn/            # Daily churn forecast
│   ├── acquisition/      # Acquisition forecast
│   └── load/             # Load forecast
├── infra/                # Terraform infrastructure
│   └── terraform/
│       ├── modules/      # Reusable modules
│       └── environments/ # Dev/staging/prod
├── apps/                 # Application entry points
├── ops/                  # Operational docs
│   ├── runbooks/
│   ├── playbooks/
│   └── templates/
├── examples/             # Sample datasets & notebooks
│   ├── datasets/
│   └── notebooks/
└── docs/                 # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Terraform 1.5+
- AWS CLI configured
- Docker (for local testing)

### Installation

```bash
# Install dependencies
make install

# Configure AWS credentials
aws configure

# Deploy infrastructure (dev environment)
make infra-plan ENV=dev
make infra-apply ENV=dev
```

### Run Local E2E Test

```bash
# Run local churn pipeline with synthetic data
make local-e2e

# Run in AWS (small dataset)
make test-e2e ENV=dev
```

### Deploy Production

```bash
# Plan production deployment
make infra-plan ENV=prod

# Apply (requires approval)
make infra-apply ENV=prod

# Deploy agents
make deploy-agents ENV=prod
```

## Day 1 Thin Slice: Daily Churn Forecast

The first production workflow delivers:

1. **Daily ingestion**: CRM data, usage, billing events
2. **Feature engineering**: Automated feature store updates
3. **Model training**: Weekly retraining with hyperparameter tuning
4. **Batch prediction**: Daily churn scores by 07:30 UK time
5. **Report generation**: HTML report with SHAP explanations
6. **Human review gate**: Promotion requires approval if metrics regress

### Run Churn Pipeline

```bash
# Trigger manually
make run-pipeline PIPELINE=churn

# View status
make pipeline-status PIPELINE=churn

# View latest report
make view-report PIPELINE=churn
```

## Security & Compliance

- **UK GDPR & Data Protection Act 2018** compliant
- **PII minimisation**: Automatic detection and masking
- **Line-level lineage**: Full data provenance tracking
- **Secrets management**: AWS Secrets Manager
- **Lake Formation**: Fine-grained data access policies
- **Encryption**: KMS at rest, TLS in transit

## Observability

- **Traces**: OpenTelemetry to CloudWatch/Jaeger
- **Logs**: Structured JSON logs with trace IDs
- **Metrics**: Prometheus/CloudWatch dashboards
- **Drift monitoring**: Automated data & model drift detection
- **Alerts**: PagerDuty integration for SLA breaches

## Cost Controls

- **Daily budget**: £150 across all pipelines
- **Per-agent meters**: Track costs by agent
- **Autoscaling**: Off-hours scale-down
- **Spot instances**: For non-critical training
- **Budget alarms**: CloudWatch alarms at 80%, 90%, 100%

## SLOs

- 99% successful DAG runs
- Model reports by 07:30 Europe/London daily
- <1% missing features in feature store
- <5 minute P95 latency for batch scoring (per 1K records)

## Development Workflow

### Adding a New Agent

```bash
# Generate agent scaffold
make new-agent NAME=my-new-agent

# Implement agent logic
# Edit agents/my-new-agent/agent.py

# Add tests
# Edit agents/my-new-agent/test_agent.py

# Run tests
make test-agent AGENT=my-new-agent

# Add to graph
# Edit apps/supervisor/graph.py
```

### Adding a New Pipeline

```bash
# Generate pipeline scaffold
make new-pipeline NAME=my-pipeline

# Implement pipeline steps
# Edit pipelines/my-pipeline/pipeline.py

# Add tests
make test-pipeline PIPELINE=my-pipeline
```

## CI/CD

GitHub Actions workflows:

- **PR checks**: Lint, type-check, unit tests, security scans
- **Infra plan**: Terraform plan on PR
- **Dev deploy**: Auto-deploy to dev on merge to main
- **Staging**: Manual promotion with approval
- **Production**: Manual promotion with approval + review

## Documentation

- [Architecture Deep Dive](docs/architecture.md)
- [Agent Development Guide](docs/agent-development.md)
- [Runbook: Incident Response](ops/runbooks/incident-response.md)
- [Runbook: Model Rollback](ops/runbooks/model-rollback.md)
- [Cost Model](docs/cost-model.md)
- [Data Protection Impact Assessment](ops/templates/dpia-template.md)

## Support

- Issues: GitHub Issues
- On-call: PagerDuty rotation
- Runbooks: `ops/runbooks/`

## License

Proprietary - Aurora Energy Ltd.
