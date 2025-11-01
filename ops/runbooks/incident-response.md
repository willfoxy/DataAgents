# Incident Response Runbook

## Severity Levels

- **P0 (Critical)**: System down, data breach, regulatory violation
- **P1 (High)**: SLA breach, model failure, pipeline failure
- **P2 (Medium)**: Performance degradation, non-critical failures
- **P3 (Low)**: Minor issues, scheduled maintenance

## Incident Response Process

### 1. Detection & Alerting

**Symptoms:**
- CloudWatch alarm fired
- PagerDuty notification
- Slack alert
- Manual report

**First Actions:**
1. Acknowledge incident in PagerDuty
2. Create incident channel in Slack: `#incident-YYYYMMDD-description`
3. Assign incident commander
4. Start incident log

### 2. Assessment

**Questions to answer:**
- What is the impact? (users, systems, data)
- What is the severity?
- When did it start?
- Is it still ongoing?

**Check:**
```bash
# Check system health
make metrics ENV=prod

# Check recent deployments
git log --oneline -10

# Check agent status
aws dynamodb scan \
  --table-name aurora-agent-state-prod \
  --filter-expression "status = :status" \
  --expression-attribute-values '{":status":{"S":"FAILED"}}'
```

### 3. Mitigation

#### Pipeline Failure

**Symptoms:**
- Task stuck in IN_PROGRESS
- Multiple retries exhausted
- Data quality check failed

**Actions:**
```bash
# Check task status
make pipeline-status PIPELINE=churn ENV=prod

# View logs
make logs AGENT=churn-forecast-modeler ENV=prod

# Retry manually
aws dynamodb update-item \
  --table-name aurora-tasks-prod \
  --key '{"task_id": {"S": "TASK_ID"}}' \
  --update-expression "SET #status = :status, retry_count = :zero" \
  --expression-attribute-names '{"#status": "status"}' \
  --expression-attribute-values '{":status": {"S": "PENDING"}, ":zero": {"N": "0"}}'
```

#### Model Performance Degradation

**Symptoms:**
- Drift alert fired
- Metrics below threshold
- Predictions look wrong

**Actions:**
```bash
# Check drift report
aws s3 cp s3://aurora-reports-prod/drift/$(date +%Y%m%d)/ . --recursive

# Rollback to previous model
make rollback-model MODEL=churn ENV=prod

# Trigger manual review
aws sns publish \
  --topic-arn arn:aws:sns:eu-west-2:ACCOUNT:aurora-alerts-prod \
  --subject "Manual review required: churn model" \
  --message "Model rolled back due to drift. Review required."
```

#### Budget Overrun

**Symptoms:**
- Budget alert at 100%
- Tasks being paused
- Cost alarm fired

**Actions:**
```bash
# Check current spend
make cost-report ENV=prod

# Identify high-cost agents
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=TAG,Key=agent_name

# Pause non-critical agents
# Edit config to disable auto-retrain, reduce frequency
```

#### Data Quality Issue

**Symptoms:**
- GE validation failed
- Missing data
- Schema mismatch

**Actions:**
```bash
# Check data quality dashboard
aws cloudwatch get-dashboard --dashboard-name aurora-dq-dashboard

# Review validation results
aws s3 cp s3://aurora-quality-prod/results/$(date +%Y%m%d)/ . --recursive

# Quarantine bad data
aws s3 mv s3://aurora-data-prod/gold/customers/features/$(date +%Y%m%d)/ \
          s3://aurora-data-prod/quarantine/$(date +%Y%m%d)/ --recursive

# Notify data owner
# Halt downstream pipelines
```

### 4. Communication

**Internal:**
- Update incident channel every 30 minutes
- Tag relevant teams
- Post-incident review scheduled

**External (if needed):**
- Customer notification via status page
- Regulatory notification (data breach)
- Press release (major outage)

### 5. Resolution

**Verify:**
- Issue no longer occurring
- Monitoring shows green
- Smoke tests pass

**Document:**
```bash
# Create post-incident report
cp ops/templates/pir-template.md ops/reports/pir-$(date +%Y%m%d)-description.md

# Fill in:
# - Timeline
# - Root cause
# - Action items
# - Lessons learned
```

### 6. Follow-up

- Schedule PIR meeting (within 48 hours)
- Create tickets for action items
- Update runbooks with learnings
- Implement preventive measures

## Common Issues

### Issue: SLA Miss (Report not delivered by 07:30)

**Diagnosis:**
```bash
# Check pipeline status
make pipeline-status PIPELINE=churn ENV=prod

# Check agent logs
make logs AGENT=churn-forecast-modeler ENV=prod | grep ERROR
```

**Resolution:**
1. Identify bottleneck (ingestion, ETL, training, reporting)
2. If recoverable, trigger manual run
3. If not recoverable, send notification with delay estimate
4. Post-mortem to identify root cause

### Issue: PII Detected in Outputs

**Severity:** P0 - Stop everything

**Actions:**
1. **Immediate halt:**
   ```bash
   # Halt all pipelines
   aws events disable-rule --name aurora-*-trigger --region eu-west-2
   ```

2. **Quarantine data:**
   ```bash
   # Move to quarantine
   aws s3 mv s3://aurora-data-prod/gold/ s3://aurora-quarantine-prod/$(date +%Y%m%d%H%M%S)/ --recursive
   ```

3. **Notify:**
   - Data Protection Officer
   - Legal team
   - Affected individuals (if GDPR breach)

4. **Investigation:**
   - How did PII bypass checks?
   - What data is affected?
   - Who had access?

5. **Remediation:**
   - Fix PII detection logic
   - Implement additional guards
   - Enhanced logging
   - Re-train team

### Issue: Model Serving Endpoint Down

**Diagnosis:**
```bash
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name aurora-churn-prod

# Check endpoint logs
aws logs tail /aws/sagemaker/Endpoints/aurora-churn-prod --follow
```

**Resolution:**
```bash
# Rollback to previous version
aws sagemaker update-endpoint \
  --endpoint-name aurora-churn-prod \
  --endpoint-config-name aurora-churn-prod-previous

# Or create new endpoint
make deploy-model MODEL=churn ENV=prod VERSION=previous
```

## Escalation

- **P0:** Immediately escalate to CTO
- **P1:** Escalate if not resolved in 2 hours
- **P2:** Escalate if not resolved in 24 hours
- **P3:** Standard process

## On-call Rotation

- **Primary:** Platform Team rotation (weekly)
- **Secondary:** Data Science Team
- **Escalation:** Engineering Manager

## Useful Commands

```bash
# Tail all logs
make logs ENV=prod

# Check all agent status
aws dynamodb scan --table-name aurora-agent-state-prod

# Check costs
make cost-report ENV=prod --days 7

# Check data quality
aws s3 ls s3://aurora-quality-prod/results/$(date +%Y%m%d)/

# Trigger manual pipeline
make run-pipeline PIPELINE=churn ENV=prod

# View recent changes
git log --since="24 hours ago" --oneline

# Check CloudWatch alarms
aws cloudwatch describe-alarms --state-value ALARM
```

## Post-Incident Review Template

See: `ops/templates/pir-template.md`
