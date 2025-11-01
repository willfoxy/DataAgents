# Aurora Energy Platform - Architecture

## Overview

The Aurora Energy Platform is a production-grade, multi-agent system built on LangGraph for orchestration and AWS AgentCore for agent runtimes. It autonomously handles data ingestion, model building, evaluation, and deployment for energy retail operations.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          EventBridge (Event Bus)                         │
│                     Tasks, Triggers, Status Updates                      │
└────────────┬─────────────────────────────────────────────────┬───────────┘
             │                                                   │
             ▼                                                   ▼
┌────────────────────────────┐                    ┌──────────────────────┐
│   Supervisor Director      │                    │   Human Review UI    │
│   - Planning               │                    │   - Approval Gates   │
│   - Routing                │◄───────────────────┤   - Feedback Loop    │
│   - Safety Checks          │                    └──────────────────────┘
│   - Cost Gates             │
└────────┬───────────────────┘
         │
         │  LangGraph State Machine
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│                   Specialist Agents (25)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Data Agents  │  │ Model Agents │  │  Ops Agents  │     │
│  │              │  │              │  │              │     │
│  │ - Cataloguer │  │ - Churn      │  │ - Deployer   │     │
│  │ - Quality    │  │ - Acquire    │  │ - Monitor    │     │
│  │ - Ingestion  │  │ - Load       │  │ - Cost Opt   │     │
│  │ - Transform  │  │ - Pricing    │  │ - Compliance │     │
│  │ - Features   │  │ - Risk       │  │ - Knowledge  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│                      Data Platform                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   S3 Lake    │  │ Feature Store│  │   Glue/Lake  │     │
│  │   Bronze     │  │  SageMaker   │  │  Formation   │     │
│  │   Silver     │  │  Databricks  │  │   Catalog    │     │
│  │   Gold       │  │              │  │   Lineage    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  DynamoDB    │  │   MLflow     │  │ OpenSearch   │     │
│  │  State       │  │  Experiment  │  │  Knowledge   │     │
│  │  Tasks       │  │  Registry    │  │  Base        │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────┬───────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────┐
│                  ML Training Backends                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  SageMaker   │  │   Azure ML   │  │ Databricks   │     │
│  │  Training    │  │  Fine-tuning │  │    Jobs      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Supervisor Director
- **Purpose**: Central orchestrator for the 25-agent graph
- **Responsibilities**:
  - Decompose high-level goals into actionable subtasks
  - Route tasks to appropriate specialist agents
  - Enforce safety policies and cost gates
  - Monitor SLAs and trigger alerts
  - Handle failures and retries

### 2. LangGraph State Machine
- **Purpose**: Manage agent execution flow
- **Features**:
  - Checkpointing for fault tolerance
  - Conditional routing based on state
  - Cycle detection and loop prevention
  - State persistence to DynamoDB

### 3. Specialist Agents (25 total)

#### Data Foundation (5 agents)
- `data-cataloguer`: Maintain Glue catalog, schema cards
- `data-contracts-quality`: Enforce contracts, run DQ tests
- `ingestion-orchestrator`: Batch/stream data ingestion
- `etl-transformer`: Bronze→Silver→Gold transformations
- `feature-store-manager`: Feature views, backfills

#### Model Development (10 agents)
- `experiment-planner`: Design experiments, hyperparameter search
- `acquisition-forecast-modeler`: Customer acquisition forecasts
- `churn-forecast-modeler`: Churn prediction & drivers
- `load-consumption-forecast`: Demand forecasting
- `pricing-tariff-optimizer`: Tariff optimization
- `portfolio-risk-modeler`: Risk & hedging models
- `trial-design-causal-inference`: A/B tests, uplift
- `anomaly-fraud-detector`: Fraud detection
- `customer-segmentation-clv`: Personas & CLV
- `prompt-model-evaluator`: LLM/agent evaluation

#### MLOps & Monitoring (3 agents)
- `mlops-deployer`: Package & deploy models
- `monitoring-drift-watcher`: Drift detection
- `crosscloud-trainer`: Multi-cloud training

#### Reporting & Governance (5 agents)
- `viz-storyteller`: Auto-generate reports
- `human-loop-coordinator`: Review routing
- `compliance-privacy-auditor`: PII scans, audits
- `cost-optimizer`: Spend tracking
- `knowledge-manager`: RAG index

#### Control (2 agents)
- `supervisor-director`: Orchestration
- `intake-triage`: Task capture

### 4. Data Platform

#### S3 Data Lake
- **Bronze**: Raw ingested data
- **Silver**: Cleansed, deduplicated
- **Gold**: Business-ready aggregates
- **Models**: Trained model artifacts
- **Reports**: Generated reports, dashboards
- **Audit**: Immutable audit trail (7-year retention)

#### Feature Store
- **Primary**: SageMaker Feature Store
- **Secondary**: Databricks Feature Store
- **Capabilities**: Online/offline features, backfills

#### Metadata & Catalog
- **Glue Catalog**: Schema registry
- **Lake Formation**: Fine-grained access control
- **Lineage**: End-to-end data provenance

### 5. Observability

#### Tracing
- OpenTelemetry for distributed tracing
- Export to CloudWatch/Jaeger
- Trace ID propagation across agents

#### Metrics
- Prometheus/CloudWatch
- Per-agent cost meters
- Model performance metrics
- Data quality scores

#### Logging
- Structured JSON logs (structlog)
- Centralized in CloudWatch Logs
- 30-day retention (dev), 365-day (prod)

## Data Flow: Daily Churn Forecast

```
01:00 UTC - Ingestion
    ↓
02:00 UTC - ETL (Bronze→Silver→Gold)
    ↓
03:00 UTC - Feature Store Update
    ↓
05:00 UTC - Churn Prediction
    ↓
06:00 UTC - Drift Detection
    ↓
07:00 UTC - Report Generation
    ↓
07:30 UK  - Report Delivery (SLA)
```

## Security & Compliance

### UK GDPR Compliance
- PII detection on ingress
- Data minimization enforced
- Line-level lineage tracking
- 7-year audit trail
- Right to erasure support

### Access Control
- IAM least-privilege roles
- Lake Formation column-level security
- VPC endpoints for private access
- KMS encryption at rest
- TLS in transit

### Safety Gates
- Human approval for high-risk changes
- Cost ceilings per agent/task
- Policy violation halts
- Automated rollback on failure

## Cost Management

### Budget Controls
- Daily budget: £150
- Per-agent cost tracking
- Real-time spend alerts at 80%, 90%, 100%
- Automatic pause on budget breach

### Optimization
- Spot instances for training
- Autoscale down off-hours
- DynamoDB on-demand pricing
- S3 Intelligent-Tiering

## Disaster Recovery

### Backup Strategy
- S3 versioning enabled
- DynamoDB PITR enabled
- Cross-region replication for critical data
- Model artifacts retained for 90 days

### Recovery Procedures
- RPO: 1 hour (data)
- RTO: 4 hours (full system)
- Automated state recovery from checkpoints
- One-click model rollback

## Deployment

### Environments
- **Dev**: Continuous deployment from main branch
- **Staging**: Manual promotion, full integration tests
- **Prod**: Manual promotion with approval gates

### CI/CD Pipeline
1. PR: Lint, test, security scan
2. Merge: Deploy to dev
3. Staging: Promote with smoke tests
4. Prod: Promote with human approval

## Monitoring & Alerts

### SLOs
- 99% successful DAG runs
- Model report by 07:30 UK daily
- <1% missing features
- <5min P95 latency (per 1K records)

### Alerting
- PagerDuty integration
- Slack notifications
- Escalation policies
- Runbook links in alerts

## Future Enhancements

1. **Phase 2**: Cross-cloud fine-tuning (Azure ML, Databricks)
2. **Phase 3**: Real-time streaming features
3. **Phase 4**: Autonomous decision-making with guardrails
4. **Phase 5**: Multi-tenant support
