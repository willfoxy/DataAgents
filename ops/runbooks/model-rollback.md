## Model Rollback Runbook

### When to Rollback

- Metrics regressed beyond threshold (>5% drop in AUC)
- Drift detected and confirmed
- Predictions showing anomalies
- Customer complaints about recommendations
- Failed canary deployment

### Pre-requisites

- MLflow tracking enabled
- Model versions tagged in registry
- Previous version still available
- Rollback approval (if prod)

### Rollback Process

#### 1. Identify Target Version

```bash
# List recent model versions
mlflow models search --name churn-forecast --order-by "creation_time DESC"

# Check metrics for previous version
mlflow runs describe --run-id RUN_ID
```

#### 2. Execute Rollback

```bash
# Set environment
export ENV=prod
export MODEL=churn
export TARGET_VERSION=previous  # or specific version number

# Execute rollback
make rollback-model MODEL=$MODEL ENV=$ENV VERSION=$TARGET_VERSION
```

#### 3. Verify Rollback

```bash
# Check deployed version
aws sagemaker describe-endpoint --endpoint-name aurora-churn-prod

# Run smoke test
pytest tests/smoke/test_churn_endpoint.py -v

# Check predictions
make run-pipeline PIPELINE=churn ENV=prod --dry-run
```

#### 4. Monitor

```bash
# Watch metrics for 1 hour
make metrics ENV=prod

# Check CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace Aurora/Models \
  --metric-name PredictionLatency \
  --dimensions Name=Model,Value=churn \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

#### 5. Document

Create incident report with:
- Reason for rollback
- Target version selected
- Verification results
- Follow-up actions

### Emergency Rollback (< 5 minutes)

For critical issues:

```bash
# Quick rollback script
./scripts/emergency_rollback.sh churn prod previous
```

This will:
1. Load previous model version from registry
2. Update endpoint with zero-downtime
3. Send notifications
4. Create audit log
