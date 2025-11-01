# Aurora Energy Platform - Project Summary

## Overview

This repository contains a **production-grade, multi-agent system** for Aurora Energy, a UK energy retailer. The platform autonomously handles data ingestion, model building, evaluation, and deployment using:

- **LangGraph** for agent orchestration
- **AWS AgentCore** for agent runtimes and tools
- **Multi-cloud training** (SageMaker, Azure ML, Databricks)
- **Full observability** (OpenTelemetry, CloudWatch)
- **UK GDPR compliance** built-in

## Key Statistics

- **25 specialist agents** across data, modeling, ops, and governance
- **3 end-to-end pipelines** (churn, acquisition, load forecasting)
- **6 core libraries** (common, observability, cost_meter, policy_guards, trainer_backends)
- **AWS infrastructure** managed via Terraform
- **CI/CD** with GitHub Actions
- **Budget controls**: £150 daily limit with automated gates

## Repository Structure

```
aurora-energy-platform/
├── agents/                      # 25 Agent Implementations
│   ├── 01-25_*_contract.yaml   # YAML contracts for all agents
│   └── churn-forecast-modeler/  # Example agent implementation
│       ├── __init__.py
│       └── agent.py
│
├── apps/                        # Application Entry Points
│   └── supervisor/              # LangGraph orchestration
│       ├── graph.py            # Agent graph definition
│       └── supervisor_agent.py  # Supervisor director
│
├── libs/                        # Shared Libraries
│   ├── common/                  # Core utilities
│   │   ├── config.py           # Configuration management
│   │   ├── io.py               # S3, DynamoDB clients
│   │   ├── logging.py          # Structured logging
│   │   └── types.py            # Common types (GraphState, etc.)
│   ├── observability/           # OpenTelemetry tracing & metrics
│   ├── cost_meter/              # Cost tracking & budget guards
│   ├── policy_guards/           # Safety & compliance checks
│   └── trainer_backends/        # Cross-cloud training (SageMaker, Azure, Databricks)
│
├── pipelines/                   # End-to-End Workflows
│   ├── churn/                   # Daily churn forecast (Day 1 thin slice)
│   ├── acquisition/             # Weekly acquisition forecast
│   └── load/                    # Daily load forecast
│
├── infra/                       # Infrastructure as Code
│   └── terraform/
│       ├── modules/             # Reusable modules (S3, DynamoDB, etc.)
│       │   ├── s3/             # Data lake buckets
│       │   └── dynamodb/       # State tables
│       └── environments/
│           ├── dev/            # Dev environment
│           ├── staging/        # Staging environment
│           └── prod/           # Production environment
│
├── ops/                         # Operational Documentation
│   ├── runbooks/
│   │   ├── incident-response.md
│   │   └── model-rollback.md
│   ├── playbooks/
│   └── templates/
│
├── examples/                    # Examples & Notebooks
│   ├── run_churn_pipeline.py   # Day 1 example script
│   ├── datasets/               # Sample datasets
│   └── notebooks/              # Jupyter notebooks
│
├── tests/                       # Test Suites
│   ├── unit/                   # Unit tests (80%+ coverage target)
│   ├── integration/            # Integration tests
│   ├── e2e/                    # End-to-end tests
│   └── smoke/                  # Smoke tests
│
├── docs/                        # Documentation
│   ├── architecture.md         # Architecture deep dive
│   ├── getting-started.md      # Quick start guide
│   ├── agent-development.md    # Agent development guide
│   └── cost-model.md           # Cost breakdown
│
├── .github/workflows/           # CI/CD
│   ├── ci.yml                  # Lint, test, security scan
│   └── deploy.yml              # Deploy to dev/staging/prod
│
├── Makefile                     # Common tasks
├── pyproject.toml              # Python dependencies & config
├── docker-compose.local.yml    # Local development environment
├── Dockerfile.dev              # Development container
├── .env.example                # Environment configuration template
├── .gitignore                  # Git ignore rules
└── README.md                   # Project README
```

## Day 1 Thin Slice: Daily Churn Forecast

The first production-ready workflow delivers:

### Flow
```
01:00 UTC  → Ingestion (CRM, usage, billing)
02:00 UTC  → ETL (Bronze→Silver→Gold)
03:00 UTC  → Feature Store Update
05:00 UTC  → Churn Prediction (batch)
06:00 UTC  → Drift Detection
07:00 UTC  → Report Generation
07:30 UK   → Report Delivery (SLA) ✓
```

### Components
1. **data-contracts-quality**: Validate input data
2. **feature-store-manager**: Update features
3. **churn-forecast-modeler**: Train/predict
4. **monitoring-drift-watcher**: Check drift
5. **viz-storyteller**: Generate HTML report
6. **human-loop-coordinator**: Review gate (if metrics regress)

### Outputs
- Churn predictions: `s3://aurora-data-prod/gold/customers/predictions/churn/YYYYMMDD/`
- SHAP explanations: `s3://aurora-reports-prod/churn/YYYYMMDD/shap/`
- HTML report: `s3://aurora-reports-prod/churn/YYYYMMDD/index.html`
- MLflow run: `mlflow://aurora-mlflow/churn/run-{id}`

### KPIs
- AUC >= 0.78
- Calibration error <= 0.02
- Report by 07:30 UK time
- Cost <= £5/day

## Agent Roster (25 Agents)

### Control & Coordination (2)
1. **supervisor-director**: Goal decomposition, routing, arbitration
2. **intake-triage**: Task capture from tickets/prompts

### Data Foundation (5)
3. **data-cataloguer**: Glue catalog, schema cards, lineage
4. **data-contracts-quality**: Enforce contracts, DQ tests
5. **ingestion-orchestrator**: Batch/stream ingestion
6. **etl-transformer**: Bronze→Silver→Gold
7. **feature-store-manager**: Feature views, backfills

### Model Development (10)
8. **experiment-planner**: Experiment design, hyperparameter search
9. **acquisition-forecast-modeler**: Sign-up forecasts
10. **churn-forecast-modeler**: Churn prediction & drivers
11. **load-consumption-forecast**: Demand forecasts
12. **pricing-tariff-optimizer**: Tariff optimization
13. **portfolio-risk-modeler**: Risk & hedging
14. **trial-design-causal-inference**: A/B tests, uplift
15. **anomaly-fraud-detector**: Fraud detection
16. **customer-segmentation-clv**: Personas & CLV
17. **prompt-model-evaluator**: LLM/agent evaluation

### MLOps & Monitoring (3)
18. **mlops-deployer**: Package & deploy models
19. **monitoring-drift-watcher**: Drift detection, retrain triggers
25. **crosscloud-trainer**: Multi-cloud training orchestration

### Reporting & Governance (5)
20. **viz-storyteller**: Auto-generate reports
21. **human-loop-coordinator**: Review routing, feedback
22. **compliance-privacy-auditor**: PII scans, audit trails
23. **cost-optimizer**: Spend tracking, optimization
24. **knowledge-manager**: RAG index of decisions

## Core Libraries

### libs/common
- **config.py**: Pydantic-based configuration
- **io.py**: S3 and DynamoDB clients
- **logging.py**: Structured logging with structlog
- **types.py**: GraphState, TaskSpec, RunStatus, etc.

### libs/observability
- **tracing.py**: OpenTelemetry distributed tracing
- **metrics.py**: Prometheus/CloudWatch metrics

### libs/cost_meter
- **tracker.py**: Per-agent cost tracking
- Budget guards with automated circuit breakers

### libs/policy_guards
- **guards.py**: Safety checks (PII detection, data size limits)
- Compliance checks (UK GDPR, data retention)

### libs/trainer_backends
- **base.py**: Abstract trainer interface
- **sagemaker.py**: SageMaker training implementation
- **azure.py**: Azure ML training (stub)
- **databricks.py**: Databricks training (stub)

## Infrastructure (Terraform)

### AWS Resources Created
- **S3 Buckets**: data, models, reports, config, audit, metadata
- **DynamoDB Tables**: agent-state, tasks, approvals
- **EventBridge**: Event bus for task triggers
- **SNS Topics**: alerts, dq-alerts
- **CloudWatch**: Log groups, dashboards, alarms
- **SageMaker**: Feature Store, training jobs, endpoints
- **Glue**: Data Catalog
- **Lake Formation**: Fine-grained access control

### Multi-Environment Support
- **Dev**: Auto-deploy from main branch
- **Staging**: Manual promotion with tests
- **Prod**: Manual promotion with approval

## CI/CD Pipeline

### PR Workflow (`.github/workflows/ci.yml`)
1. **Lint**: ruff check
2. **Type check**: mypy (strict mode)
3. **Format check**: ruff format
4. **Unit tests**: pytest with coverage
5. **Security scan**: bandit, safety
6. **Terraform validate**: fmt + validate

### Deploy Workflow (`.github/workflows/deploy.yml`)
1. **Deploy infrastructure**: Terraform apply
2. **Deploy agents**: Package & upload to AWS
3. **Smoke tests**: Basic health checks

## Security & Compliance

### UK GDPR Compliance
- ✅ PII detection on ingress
- ✅ Data minimization enforced
- ✅ Line-level lineage tracking
- ✅ 7-year audit trail (immutable)
- ✅ Right to erasure support
- ✅ Lawful basis checks

### Security Controls
- IAM least-privilege roles
- VPC endpoints for private access
- KMS encryption at rest
- TLS in transit
- Secrets in AWS Secrets Manager
- Fine-grained Lake Formation policies

## Observability

### Tracing
- OpenTelemetry spans for all agent executions
- Trace ID propagation across services
- Export to CloudWatch/Jaeger

### Metrics
- Per-agent execution time, cost, success rate
- Model performance (AUC, calibration, drift)
- Data quality scores
- Budget utilization

### Logging
- Structured JSON logs with trace IDs
- Centralized in CloudWatch Logs
- Retention: 30 days (dev), 365 days (prod)

### Dashboards
- CloudWatch: System health, costs, SLAs
- MLflow: Experiment tracking, model registry
- Custom: Drift detection, data quality

## Cost Management

### Budget Controls
- **Daily limit**: £150
- **Alerts**: 80%, 90%, 100% thresholds
- **Automatic actions**: Pause non-critical at 90%, halt all at 100%

### Per-Agent Tracking
- Cost meter tracks every agent execution
- Attributed to: agent name, task ID, resource type
- Historical trends in CloudWatch

### Optimization
- Spot instances for training (non-critical)
- Autoscale down off-hours
- DynamoDB on-demand (cost-effective for variable load)
- S3 Intelligent-Tiering

## SLOs

| Metric | Target | Window |
|--------|--------|--------|
| DAG success rate | >= 99% | 30d |
| Churn report delivery | 07:30 UK | daily |
| Missing features | <= 1% | 24h |
| P95 prediction latency | <= 5min/1K records | 7d |

## Quick Start

```bash
# 1. Install
make install

# 2. Configure
cp .env.example .env
# Edit .env

# 3. Start local services
make local-setup

# 4. Run example
python examples/run_churn_pipeline.py

# 5. Deploy to AWS
make infra-plan ENV=dev
make infra-apply ENV=dev
make deploy ENV=dev
```

## Testing

```bash
# Run all tests
make test

# Run specific suites
make test-unit
make test-integration
make test-e2e ENV=dev

# Run with coverage
pytest --cov --cov-report=html
```

## Key Files to Review

1. **Core orchestration**: `apps/supervisor/graph.py`
2. **Supervisor agent**: `apps/supervisor/supervisor_agent.py`
3. **Example agent**: `agents/churn-forecast-modeler/agent.py`
4. **Agent contracts**: `agents/*_contract.yaml`
5. **Graph state**: `libs/common/types.py`
6. **Infrastructure**: `infra/terraform/environments/dev/main.tf`
7. **Example pipeline**: `examples/run_churn_pipeline.py`

## Next Steps

1. ✅ **Phase 1 (Current)**: Day 1 thin slice (churn forecast)
2. **Phase 2**: Remaining 24 agent implementations
3. **Phase 3**: Cross-cloud fine-tuning (Azure ML, Databricks)
4. **Phase 4**: Real-time streaming features
5. **Phase 5**: Autonomous decision-making with guardrails

## Documentation

- [Architecture Deep Dive](docs/architecture.md)
- [Getting Started Guide](docs/getting-started.md)
- [Incident Response Runbook](ops/runbooks/incident-response.md)
- [Model Rollback Procedure](ops/runbooks/model-rollback.md)

## Support

- **Issues**: GitHub Issues
- **On-call**: PagerDuty rotation
- **Runbooks**: `ops/runbooks/`
- **Slack**: #aurora-platform

---

**Built with**: Python 3.11, LangGraph, AWS AgentCore, Terraform, GitHub Actions

**License**: Proprietary - Aurora Energy Ltd.
