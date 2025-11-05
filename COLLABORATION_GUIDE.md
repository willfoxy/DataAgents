

# Collaboration Layer - User Guide

## Overview

The **Collaboration Layer** enables users to interact with all 25 AI agents through:
- 💬 **Chat Interface** - Natural language task submission
- 🌐 **Web UI** - Browser-based interface
- 🖥️ **CLI Client** - Command-line interaction
- 🔌 **WebSocket** - Real-time status updates
- 📝 **Conversation History** - Multi-turn dialogues
- ✅ **Human-in-the-Loop** - Approval workflows

## Architecture

```
┌──────────────┐
│    User      │
└──────┬───────┘
       │
       ├─── Web Browser (port 8000)
       ├─── CLI Client
       ├─── REST API
       └─── WebSocket (real-time)
       │
┌──────▼───────────────────────────┐
│   Collaboration API (FastAPI)    │
│  - Task submission               │
│  - Conversation management       │
│  - WebSocket connections         │
│  - Agent status tracking         │
└──────┬───────────────────────────┘
       │
┌──────▼───────────────────────────┐
│   Agent Registry + LangGraph     │
│  - 25 AI Agents                  │
│  - Dynamic dispatching           │
│  - Error handling                │
└──────────────────────────────────┘
```

## Quick Start

### 1. Start the Server

```bash
cd /home/user/DataAgents

# Method 1: Using script
./apps/collaboration/start_server.sh

# Method 2: Direct uvicorn
export PYTHONPATH=$PWD
uvicorn apps.collaboration.api:app --reload
```

**Server will start on:** `http://localhost:8000`

### 2. Access Web UI

Open your browser to:
```
http://localhost:8000
```

You'll see:
- Chat interface for submitting tasks
- List of all 25 available agents
- Real-time status updates
- Conversation history

### 3. Use CLI Client

In a new terminal:

```bash
cd /home/user/DataAgents
export PYTHONPATH=$PWD
python apps/collaboration/cli_client.py
```

**CLI Commands:**
- `/agents` - List all agents
- `/status <task_id>` - Get task status
- `/history <conversation_id>` - View conversation
- `/quit` - Exit

## Features

### 1. Natural Language Task Submission

Submit tasks in plain English:

**Example Requests:**
```
"Run the daily churn forecast pipeline"
"Analyze data quality for customer table"
"Train a new acquisition model with recent data"
"Check for fraud in yesterday's transactions"
"Generate cost optimization recommendations"
"Forecast energy load for next 30 days"
```

The system automatically:
1. Parses your request
2. Identifies the right agents
3. Estimates cost and duration
4. Routes to appropriate workflows
5. Provides real-time updates

### 2. Conversation Management

Multi-turn conversations with context:

```
You: "Run churn forecast"
Agent: "I'll run the churn pipeline with 6 agents. Estimated cost: £23.80"

You: "What's the status?"
Agent: "Currently processing features. 65% complete. Cost so far: £12.50"

You: "Show me the results when done"
Agent: "Will generate report and notify you. Report will be at s3://..."
```

### 3. Real-Time Updates

WebSocket provides live updates:
- Agent start/stop
- Progress percentage
- Intermediate outputs
- Cost accumulation
- Errors and warnings

### 4. Human-in-the-Loop Approvals

For critical operations:

```
Agent: "I need approval to deploy the new model to production.
       Changes:
       - New model AUC: 0.84 (previous: 0.82)
       - Deployment strategy: Canary (10% traffic)
       - Estimated cost: £5.00

       Approve? (yes/no)"

You: "yes"

Agent: "Deployment approved. Proceeding with canary deployment..."
```

## REST API Reference

### Endpoints

#### `GET /`
Web UI homepage

**Response:** HTML page

---

#### `GET /agents`
List all 25 agents

**Response:**
```json
[
  {
    "name": "churn-forecast-modeler",
    "domain": "model",
    "capability": "churn_prediction",
    "cost_estimate_gbp": 15.0,
    "avg_duration_seconds": 300
  },
  ...
]
```

---

#### `GET /agents/{agent_name}`
Get agent details

**Response:**
```json
{
  "name": "churn-forecast-modeler",
  "domain": "model",
  "capability": "churn_prediction",
  "cost_estimate_gbp": 15.0,
  "avg_duration_seconds": 300,
  "examples": ["Ask this agent to churn_prediction"]
}
```

---

#### `POST /tasks`
Submit a new task

**Request:**
```json
{
  "message": "Run the daily churn forecast pipeline",
  "priority": "medium",
  "context": {},
  "user_id": "alice"
}
```

**Response:**
```json
{
  "task_id": "task-abc123",
  "conversation_id": "conv-xyz789",
  "message": "I'll coordinate 6 agents to complete this task",
  "estimated_cost_gbp": 23.80,
  "estimated_duration_seconds": 780,
  "agents_involved": [
    "ingestion-orchestrator",
    "data-contracts-quality",
    "etl-transformer",
    "feature-store-manager",
    "churn-forecast-modeler",
    "viz-storyteller"
  ],
  "status": "queued"
}
```

---

#### `GET /conversations/{conversation_id}`
Get conversation history

**Response:**
```json
{
  "conversation_id": "conv-xyz789",
  "user_id": "alice",
  "messages": [
    {
      "message_id": "msg-1",
      "role": "user",
      "content": "Run the daily churn forecast pipeline",
      "timestamp": "2025-11-05T10:30:00Z",
      "metadata": {}
    },
    {
      "message_id": "msg-2",
      "role": "assistant",
      "content": "I'll coordinate 6 agents...",
      "timestamp": "2025-11-05T10:30:01Z",
      "metadata": {
        "task_id": "task-abc123"
      }
    }
  ],
  "created_at": "2025-11-05T10:30:00Z",
  "updated_at": "2025-11-05T10:30:01Z"
}
```

---

#### `GET /tasks/{task_id}/status`
Get task execution status

**Response:**
```json
{
  "agent_name": "churn-forecast-modeler",
  "status": "in_progress",
  "progress": 0.65,
  "current_step": "Generating predictions",
  "outputs": {
    "records_processed": 35000,
    "records_total": 50000
  },
  "cost_so_far_gbp": 12.50
}
```

---

#### `POST /tasks/{task_id}/approve`
Approve or reject a task

**Request:**
```json
{
  "task_id": "task-abc123",
  "decision": "approved",
  "comments": "Looks good, proceed"
}
```

**Response:**
```json
{
  "task_id": "task-abc123",
  "decision": "approved",
  "message": "Task approved. Agents will proceed."
}
```

---

#### `GET /health`
Health check

**Response:**
```json
{
  "status": "healthy",
  "agents_available": 25,
  "active_conversations": 3,
  "timestamp": "2025-11-05T10:30:00Z"
}
```

---

#### `WS /ws`
WebSocket for real-time updates

**Message Types:**

**Connection:**
```json
{
  "type": "connection",
  "message": "Connected to Aurora Energy Agent Platform",
  "total_connections": 1
}
```

**Agent Update:**
```json
{
  "type": "agent_update",
  "task_id": "task-abc123",
  "agent_name": "churn-forecast-modeler",
  "status": "in_progress",
  "message": "Processing features...",
  "timestamp": "2025-11-05T10:30:05Z"
}
```

**Task Complete:**
```json
{
  "type": "task_complete",
  "task_id": "task-abc123",
  "status": "success",
  "cost_gbp": 23.80,
  "outputs": {...}
}
```

## Example Workflows

### Workflow 1: Daily Churn Forecast

```bash
# Start server
./apps/collaboration/start_server.sh

# In browser: http://localhost:8000
# Type: "Run the daily churn forecast pipeline"
```

**Expected Flow:**
1. ✅ Intake triage parses request
2. ✅ Supervisor decomposes into 6 subtasks
3. ✅ Agents execute in sequence:
   - Ingestion orchestrator (£2.00)
   - Data contracts quality (£1.00)
   - ETL transformer (£3.00)
   - Feature store manager (£2.00)
   - Churn forecast modeler (£15.00)
   - Viz storyteller (£0.80)
4. ✅ Total cost: £23.80
5. ✅ Report generated and URL provided

### Workflow 2: Ask About Agent Capabilities

```bash
# CLI client
python apps/collaboration/cli_client.py

> /agents
# Shows table of all 25 agents

> What agents can help with customer retention?
# Agent responds with recommendations
```

### Workflow 3: Human Approval

```bash
> Train and deploy a new churn model

Agent: "I need approval to deploy to production.
        New model metrics: AUC=0.84
        Current model: AUC=0.82
        Approve?"

> yes

Agent: "Approved! Deploying with canary strategy..."
```

## Python Client Example

```python
import asyncio
import httpx

async def run_churn_pipeline():
    async with httpx.AsyncClient() as client:
        # Submit task
        response = await client.post(
            "http://localhost:8000/tasks",
            json={
                "message": "Run the daily churn forecast pipeline",
                "priority": "high",
                "user_id": "alice"
            }
        )

        data = response.json()
        task_id = data['task_id']

        print(f"Task submitted: {task_id}")
        print(f"Estimated cost: £{data['estimated_cost_gbp']}")
        print(f"Agents: {', '.join(data['agents_involved'])}")

        # Poll for status
        while True:
            status_response = await client.get(
                f"http://localhost:8000/tasks/{task_id}/status"
            )

            status = status_response.json()
            print(f"Progress: {status['progress']*100:.0f}%")

            if status['status'] in ['completed', 'failed']:
                break

            await asyncio.sleep(5)

asyncio.run(run_churn_pipeline())
```

## WebSocket Client Example

```python
import asyncio
import websockets
import json

async def listen_to_updates():
    uri = "ws://localhost:8000/ws"

    async with websockets.connect(uri) as websocket:
        print("Connected to WebSocket")

        async for message in websocket:
            data = json.loads(message)
            print(f"Update: {data}")

            if data.get('type') == 'task_complete':
                print(f"Task completed! Cost: £{data['cost_gbp']}")
                break

asyncio.run(listen_to_updates())
```

## Configuration

### Environment Variables

```bash
# API settings
export API_HOST="0.0.0.0"
export API_PORT="8000"

# CORS settings (for web UI)
export CORS_ORIGINS="*"

# Agent settings
export AGENT_TIMEOUT_SECONDS="300"
export MAX_CONCURRENT_TASKS="10"

# Cost limits
export DAILY_BUDGET_GBP="150.0"
export COST_ALERT_THRESHOLD="0.8"
```

### Start with Custom Port

```bash
uvicorn apps.collaboration.api:app --host 0.0.0.0 --port 9000
```

## Deployment

### Development

```bash
# Local development with auto-reload
uvicorn apps.collaboration.api:app --reload --log-level debug
```

### Production

```bash
# Production with multiple workers
gunicorn apps.collaboration.api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -e .

EXPOSE 8000

CMD ["uvicorn", "apps.collaboration.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t aurora-collaboration .
docker run -p 8000:8000 aurora-collaboration
```

## Monitoring

### Metrics

- Active conversations
- Tasks per minute
- Agent utilization
- Response times
- Error rates
- Cost tracking

### Logs

All requests logged with:
- User ID
- Task ID
- Conversation ID
- Timestamp
- Duration
- Status

```bash
# View logs
tail -f logs/collaboration.log
```

## Troubleshooting

### Server won't start

```bash
# Check port availability
lsof -i :8000

# Kill existing process
kill -9 $(lsof -t -i:8000)

# Check Python path
echo $PYTHONPATH
```

### WebSocket connection fails

```bash
# Test WebSocket
wscat -c ws://localhost:8000/ws

# Check firewall
sudo ufw status
```

### Agents not responding

```bash
# Check agent registry
python -c "from apps.supervisor.agent_registry import get_agent_registry; print(get_agent_registry().list_agents())"

# Verify all 25 agents
python examples/simple_agent_test.py
```

## Security

### Authentication (TODO)

For production, add authentication:

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/tasks")
async def submit_task(
    request: TaskRequest,
    token: str = Depends(security)
):
    # Verify token
    user = verify_token(token)
    ...
```

### Rate Limiting (TODO)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/tasks")
@limiter.limit("10/minute")
async def submit_task(...):
    ...
```

## Summary

The Collaboration Layer provides:

✅ **Natural Language Interface** - Chat with agents in plain English
✅ **Web UI** - Browser-based interaction
✅ **CLI Client** - Command-line tool
✅ **REST API** - Programmatic access
✅ **WebSocket** - Real-time updates
✅ **Conversation History** - Multi-turn dialogues
✅ **Human Approvals** - Review and approve critical tasks
✅ **Cost Visibility** - Real-time cost tracking
✅ **25 Agents** - Full agent roster available

**The platform is now fully interactive!** 🚀
