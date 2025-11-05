# Collaboration Layer

User-facing collaboration interface for the Aurora Energy Agent Platform.

## Features

- 💬 **Chat Interface** - Natural language task submission
- 🌐 **Web UI** - Interactive browser interface
- 🖥️ **CLI Client** - Command-line interaction
- 🔌 **WebSocket** - Real-time status updates
- 📝 **Conversation History** - Multi-turn dialogues
- ✅ **Human-in-the-Loop** - Approval workflows

## Quick Start

```bash
# Start server
./start_server.sh

# Or directly
uvicorn apps.collaboration.api:app --reload

# Open browser
open http://localhost:8000

# Or use CLI
python cli_client.py
```

## Components

### `api.py`
FastAPI application with:
- REST endpoints for task submission
- WebSocket for real-time updates
- Built-in web UI
- Agent integration

### `conversation.py`
Conversation management:
- Multi-turn dialogue tracking
- Context preservation
- History storage

### `websocket.py`
WebSocket connection manager:
- Multiple concurrent connections
- Broadcast to all clients
- Per-user messaging

### `cli_client.py`
Interactive CLI client:
- Chat with agents
- View agent list
- Track task status
- Browse conversation history

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI homepage |
| GET | `/agents` | List all 25 agents |
| GET | `/agents/{name}` | Get agent details |
| POST | `/tasks` | Submit new task |
| GET | `/tasks/{id}/status` | Get task status |
| POST | `/tasks/{id}/approve` | Approve/reject task |
| GET | `/conversations/{id}` | Get conversation |
| GET | `/health` | Health check |
| WS | `/ws` | WebSocket connection |

## Usage Examples

### Submit Task via API

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/tasks",
        json={"message": "Run churn forecast", "user_id": "alice"}
    )
    print(response.json())
```

### WebSocket Listener

```python
import websockets

async with websockets.connect("ws://localhost:8000/ws") as ws:
    async for message in ws:
        print(f"Update: {message}")
```

### CLI Client

```bash
$ python cli_client.py

You: Run the daily churn forecast pipeline
Agent: I'll coordinate 6 agents. Estimated cost: £23.80

You: /status
Agent: Currently processing features. 65% complete.
```

## Configuration

Set via environment variables:

```bash
export API_HOST="0.0.0.0"
export API_PORT="8000"
export DAILY_BUDGET_GBP="150.0"
```

## Documentation

See [COLLABORATION_GUIDE.md](../../COLLABORATION_GUIDE.md) for complete documentation.

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run with auto-reload
uvicorn apps.collaboration.api:app --reload --log-level debug

# Run tests
pytest apps/collaboration/
```

## Production Deployment

```bash
# With gunicorn
gunicorn apps.collaboration.api:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## Architecture

```
User → Web UI/CLI → FastAPI → Agent Registry → 25 Agents
                       ↓
                   WebSocket
                       ↓
                Real-time Updates
```

## License

Proprietary - Aurora Energy Ltd.
