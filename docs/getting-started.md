# Getting Started with Aurora Energy Platform

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Terraform 1.5+
- AWS CLI configured
- Git

## Quick Start

### 1. Clone and Install

```bash
# Clone repository
git clone https://github.com/auroraenergy/dataagents.git
cd dataagents

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make install
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your AWS configuration
vim .env
```

### 3. Run Local Development Environment

```bash
# Start local services (LocalStack, MLflow, etc.)
make local-setup

# This starts:
# - LocalStack (AWS services) on port 4566
# - MLflow Tracking Server on port 5000
# - PostgreSQL on port 5432
# - Jupyter Lab on port 8888
```

### 4. Run Example Pipeline

```bash
# Run the daily churn forecast pipeline (simulated)
python examples/run_churn_pipeline.py
```

Expected output:
```
================================================================================
Aurora Energy Platform - Daily Churn Forecast Pipeline
================================================================================
Task ID: 123e4567-e89b-12d3-a456-426614174000
Priority: high
Environment: dev

================================================================================
Phase 1: Planning & Task Decomposition
================================================================================
Run ID: 789e4567-e89b-12d3-a456-426614174999
Subtasks: 5
  1. data_quality: Validate input data
  2. feature_engineering: Update feature store
  3. churn_forecast: Train/predict churn
  4. monitoring: Check for drift
  5. reporting: Generate report

================================================================================
Phase 2: Agent Orchestration
================================================================================
Supervisor planning task_id=123e4567-e89b-12d3-a456-426614174000
Routing to next agent task_id=123e4567-e89b-12d3-a456-426614174000 next_agent=data-contracts-quality
Executing agent: data-contracts-quality
...

================================================================================
Key Results
================================================================================
Predictions: s3://aurora-data-dev/gold/customers/predictions/churn/20250101/
Report: s3://aurora-reports-dev/churn/20250101/index.html

Metrics:
  num_predictions: 50000
  high_risk_count: 2500
  prediction_time_seconds: 120

Total cost: £8.00

================================================================================
Pipeline completed successfully!
================================================================================
```

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run specific test suite
make test-unit
make test-integration

# Run tests for specific agent
make test-agent AGENT=churn-forecast-modeler
```

### Linting and Formatting

```bash
# Run linting
make lint

# Auto-format code
make format
```

### Adding a New Agent

```bash
# Generate agent scaffold
make new-agent NAME=my-new-agent

# This creates:
# - agents/my-new-agent/
#   - __init__.py
#   - agent.py
#   - contract.yaml
#   - test_agent.py
```

Edit the generated files:

1. **contract.yaml**: Define inputs, outputs, tools, KPIs
2. **agent.py**: Implement agent logic
3. **test_agent.py**: Write unit tests

Register in the supervisor:

```python
# In apps/supervisor/supervisor_agent.py
self.agent_routes["my_task"] = "my-new-agent"
```

### Running Individual Agents

```python
# In Python
from agents.churn_forecast_modeler import ChurnForecastModeler
from libs.common.types import GraphState

modeler = ChurnForecastModeler()
state = GraphState(...)
result = await modeler.execute(state)
```

## Deploying to AWS

### 1. Initialize Terraform State

```bash
# Create S3 bucket for Terraform state (one-time)
aws s3 mb s3://aurora-terraform-state-dev --region eu-west-2

# Create DynamoDB table for state locking (one-time)
aws dynamodb create-table \
  --table-name aurora-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-2
```

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
make infra-init ENV=dev

# Plan changes
make infra-plan ENV=dev

# Apply (after reviewing plan)
make infra-apply ENV=dev
```

### 3. Deploy Agents

```bash
# Build and deploy agents
make deploy ENV=dev
```

### 4. Verify Deployment

```bash
# Check infrastructure outputs
make infra-output ENV=dev

# Run smoke tests
make test-e2e ENV=dev
```

## Monitoring and Observability

### View Logs

```bash
# Tail logs for specific agent
make logs AGENT=churn-forecast-modeler ENV=dev

# View all recent logs
aws logs tail /aws/aurora-platform/dev --since 1h --follow
```

### Check Metrics

```bash
# Open CloudWatch dashboard
make metrics ENV=dev

# View cost report
make cost-report ENV=dev --days 7
```

### MLflow UI

```bash
# Start MLflow UI (local)
make mlflow-ui

# Open browser to http://localhost:5000
```

## Troubleshooting

### Issue: Import errors

**Solution:**
```bash
# Ensure package is installed in editable mode
pip install -e .

# Verify PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: AWS credentials not working

**Solution:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Configure if needed
aws configure
```

### Issue: LocalStack services not accessible

**Solution:**
```bash
# Check LocalStack is running
docker ps | grep localstack

# Restart if needed
docker-compose -f docker-compose.local.yml restart localstack

# Create required resources
aws --endpoint-url=http://localhost:4566 s3 mb s3://aurora-data-dev
```

### Issue: Tests failing

**Solution:**
```bash
# Install test dependencies
pip install -e ".[dev,test]"

# Run with verbose output
pytest -vv -s

# Run specific test
pytest tests/unit/test_supervisor.py::TestSupervisorAgent::test_plan_and_route -v
```

## Next Steps

1. **Explore the codebase:**
   - Read [Architecture Documentation](./architecture.md)
   - Review agent contracts in `agents/*/contract.yaml`
   - Check out example notebooks in `examples/notebooks/`

2. **Run the full churn pipeline:**
   - Deploy infrastructure: `make infra-apply ENV=dev`
   - Trigger pipeline: `make run-pipeline PIPELINE=churn ENV=dev`
   - View report: `make view-report PIPELINE=churn ENV=dev`

3. **Customize for your use case:**
   - Add new agents for your domain
   - Modify agent contracts
   - Adjust cost ceilings and SLOs
   - Configure alerts and dashboards

4. **Set up CI/CD:**
   - Configure GitHub Actions secrets
   - Set up environments (dev, staging, prod)
   - Configure approval gates

## Support

- **Documentation:** `docs/`
- **Runbooks:** `ops/runbooks/`
- **Issues:** GitHub Issues
- **Slack:** #aurora-platform

## Additional Resources

- [Agent Development Guide](./agent-development.md)
- [Cost Model](./cost-model.md)
- [Security & Compliance](./security-compliance.md)
- [API Reference](./api-reference.md)
