"""
FastAPI Application for User-Agent Collaboration.

Features:
- Task submission via natural language
- Real-time status updates via WebSocket
- Conversation history tracking
- Human-in-the-loop approvals
- Agent recommendations
- Cost visibility
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from libs.common.types import GraphState, RunStatus, TaskPriority
from libs.common.logging import get_logger
from apps.supervisor.agent_registry import get_agent_registry
from apps.supervisor.graph import create_agent_graph
from apps.collaboration.conversation import ConversationManager, Message, Conversation
from apps.collaboration.websocket import ConnectionManager

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Aurora Energy Agent Collaboration",
    description="Interactive platform for collaborating with AI agents",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
conversation_manager = ConversationManager()
connection_manager = ConnectionManager()
agent_registry = get_agent_registry()


# Request/Response Models
class TaskRequest(BaseModel):
    """User task request."""
    message: str = Field(..., description="Natural language task description")
    priority: str = Field(default="medium", description="Task priority: low, medium, high, critical")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_id: str = Field(default="anonymous", description="User identifier")


class TaskResponse(BaseModel):
    """Task submission response."""
    task_id: str
    conversation_id: str
    message: str
    estimated_cost_gbp: float
    estimated_duration_seconds: int
    agents_involved: List[str]
    status: str


class ConversationResponse(BaseModel):
    """Conversation response."""
    conversation_id: str
    user_id: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str


class AgentStatusResponse(BaseModel):
    """Agent status response."""
    agent_name: str
    status: str
    progress: float
    current_step: str
    outputs: Dict[str, Any]
    cost_so_far_gbp: float


class ApprovalRequest(BaseModel):
    """Human approval request."""
    task_id: str
    decision: str = Field(..., description="approved or rejected")
    comments: Optional[str] = None


# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the web UI."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aurora Energy - Agent Collaboration</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #2c3e50; }
            .chat-container { border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0; }
            .message { margin: 10px 0; padding: 10px; border-radius: 4px; }
            .user-message { background: #e3f2fd; text-align: right; }
            .agent-message { background: #f5f5f5; }
            #messageInput { width: 70%; padding: 10px; margin-right: 10px; }
            #sendBtn { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer; }
            #sendBtn:hover { background: #1976d2; }
            .agent-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
            .agent-card { border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #fafafa; }
            .status { margin-top: 20px; padding: 10px; background: #fff3cd; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🚀 Aurora Energy - Agent Collaboration Platform</h1>
        <p>Interact with 25 AI agents for data analytics, ML, and operations.</p>

        <div class="chat-container">
            <h2>💬 Chat with Agents</h2>
            <div id="messages"></div>
            <div style="margin-top: 20px;">
                <input type="text" id="messageInput" placeholder="Ask agents to do something... (e.g., 'Run churn forecast pipeline')" />
                <button id="sendBtn" onclick="sendMessage()">Send</button>
            </div>
            <div id="status" class="status" style="display: none;"></div>
        </div>

        <div>
            <h2>📦 Available Agents (25)</h2>
            <div id="agentList" class="agent-list"></div>
        </div>

        <script>
            let ws = null;
            let conversationId = null;

            // Connect to WebSocket
            function connectWebSocket() {
                ws = new WebSocket(`ws://${window.location.host}/ws`);

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };

                ws.onclose = function() {
                    console.log('WebSocket closed, reconnecting...');
                    setTimeout(connectWebSocket, 3000);
                };
            }

            // Load agents
            async function loadAgents() {
                const response = await fetch('/agents');
                const agents = await response.json();

                const agentList = document.getElementById('agentList');
                agentList.innerHTML = agents.map(agent => `
                    <div class="agent-card">
                        <strong>${agent.name}</strong><br>
                        <small>${agent.capability}</small><br>
                        <small>£${agent.cost_estimate_gbp}</small>
                    </div>
                `).join('');
            }

            // Send message
            async function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();

                if (!message) return;

                // Add user message to UI
                addMessage('user', message);
                input.value = '';

                // Show status
                const status = document.getElementById('status');
                status.style.display = 'block';
                status.innerHTML = '🔄 Processing your request...';

                try {
                    const response = await fetch('/tasks', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: message,
                            priority: 'medium',
                            user_id: 'web-user'
                        })
                    });

                    const data = await response.json();
                    conversationId = data.conversation_id;

                    // Add agent response
                    addMessage('agent', data.message);
                    status.innerHTML = `✅ Task submitted! Estimated cost: £${data.estimated_cost_gbp}<br>Agents: ${data.agents_involved.join(', ')}`;

                } catch (error) {
                    status.innerHTML = '❌ Error: ' + error.message;
                }
            }

            // Add message to UI
            function addMessage(sender, text) {
                const messages = document.getElementById('messages');
                const div = document.createElement('div');
                div.className = `message ${sender}-message`;
                div.innerHTML = `<strong>${sender === 'user' ? 'You' : '🤖 Agent'}:</strong> ${text}`;
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }

            // Handle WebSocket message
            function handleMessage(data) {
                if (data.type === 'agent_update') {
                    addMessage('agent', `${data.agent_name}: ${data.status} - ${data.message}`);
                } else if (data.type === 'task_complete') {
                    addMessage('agent', `✅ Task completed! Total cost: £${data.cost_gbp}`);
                    document.getElementById('status').innerHTML = '✅ Task completed successfully!';
                }
            }

            // Allow Enter key to send
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') sendMessage();
            });

            // Initialize
            connectWebSocket();
            loadAgents();
        </script>
    </body>
    </html>
    """


@app.get("/agents")
async def list_agents():
    """List all available agents."""
    agents = agent_registry.list_agents()

    return [
        {
            "name": agent,
            **agent_registry.get_metadata(agent)
        }
        for agent in agents
    ]


@app.get("/agents/{agent_name}")
async def get_agent_info(agent_name: str):
    """Get detailed information about an agent."""
    try:
        metadata = agent_registry.get_metadata(agent_name)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        return {
            "name": agent_name,
            **metadata,
            "examples": [
                f"Ask this agent to {metadata.get('capability', 'perform its task')}"
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/tasks", response_model=TaskResponse)
async def submit_task(request: TaskRequest):
    """
    Submit a task in natural language.

    Examples:
    - "Run the daily churn forecast pipeline"
    - "Analyze data quality for customer table"
    - "Train a new acquisition model"
    """
    logger.info(f"Task request from {request.user_id}: {request.message}")

    # Create or get conversation
    conversation_id = str(uuid.uuid4())
    conversation = conversation_manager.create_conversation(
        conversation_id=conversation_id,
        user_id=request.user_id
    )

    # Add user message
    conversation_manager.add_message(
        conversation_id=conversation_id,
        role="user",
        content=request.message,
        metadata=request.context
    )

    # Parse task using intake-triage agent
    try:
        from agents.intake_triage import create_intake_triage

        triage_agent = await create_intake_triage()

        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # Create state for triage
        triage_state = GraphState(
            task_id=task_id,
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            current_agent="intake-triage",
            status=RunStatus.PENDING,
            inputs={
                "request": request.message,
                "source": "collaboration_api",
                "justification": "User-submitted task",
                "priority": request.priority,
                "estimated_cost_gbp": 30.0,  # Default estimate
            },
            context={
                "user_id": request.user_id,
                "conversation_id": conversation_id,
                "user_active_tasks": 1,
                "budget_remaining_gbp": 150.0,
            }
        )

        # Execute triage
        triage_result = await triage_agent.execute(triage_state)

        if triage_result.get("status") == "success":
            parsed_goal = triage_result.get("parsed_goal", {})
            task_type = parsed_goal.get("task", "unknown")

            # Estimate agents involved
            agents_map = {
                "daily_churn_pipeline": ["ingestion-orchestrator", "data-contracts-quality", "etl-transformer", "feature-store-manager", "churn-forecast-modeler", "viz-storyteller"],
                "forecast_load": ["ingestion-orchestrator", "load-consumption-forecast", "viz-storyteller"],
                "train_acquisition": ["experiment-planner", "acquisition-forecast-modeler", "mlops-deployer"],
                "detect_fraud": ["anomaly-fraud-detector", "viz-storyteller"],
            }

            agents_involved = agents_map.get(task_type, ["supervisor-director", "intake-triage"])

            # Calculate cost estimate
            total_cost = sum(
                agent_registry.get_metadata(agent).get("cost_estimate_gbp", 0)
                for agent in agents_involved
            )

            # Calculate duration estimate
            total_duration = sum(
                agent_registry.get_metadata(agent).get("avg_duration_seconds", 0)
                for agent in agents_involved
            )

            # Add agent response
            response_message = f"I'll help you with that! I've parsed your request as: '{task_type}'. I'll coordinate {len(agents_involved)} agents to complete this task."

            conversation_manager.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_message,
                metadata={
                    "task_id": task_id,
                    "parsed_goal": parsed_goal,
                    "agents_involved": agents_involved,
                }
            )

            # Store task in conversation context
            conversation_manager.conversations[conversation_id].context["active_task"] = {
                "task_id": task_id,
                "agents_involved": agents_involved,
                "status": "queued"
            }

            return TaskResponse(
                task_id=task_id,
                conversation_id=conversation_id,
                message=response_message,
                estimated_cost_gbp=round(total_cost, 2),
                estimated_duration_seconds=int(total_duration),
                agents_involved=agents_involved,
                status="queued"
            )

        elif triage_result.get("status") == "clarification_needed":
            # Need more info from user
            questions = triage_result.get("questions", [])
            response_message = "I need some clarification:\n" + "\n".join(f"- {q}" for q in questions)

            conversation_manager.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_message,
                metadata={"clarification_needed": True}
            )

            return TaskResponse(
                task_id=task_id,
                conversation_id=conversation_id,
                message=response_message,
                estimated_cost_gbp=0.0,
                estimated_duration_seconds=0,
                agents_involved=["intake-triage"],
                status="clarification_needed"
            )

        else:
            # Request rejected
            reason = triage_result.get("reason", "Unknown reason")
            response_message = f"I cannot process this request: {reason}"

            conversation_manager.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response_message,
                metadata={"rejected": True, "reason": reason}
            )

            raise HTTPException(status_code=400, detail=response_message)

    except Exception as e:
        logger.error(f"Task submission failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """Get conversation history."""
    conversation = conversation_manager.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse(
        conversation_id=conversation.conversation_id,
        user_id=conversation.user_id,
        messages=[msg.model_dump() for msg in conversation.messages],
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat()
    )


@app.get("/tasks/{task_id}/status", response_model=AgentStatusResponse)
async def get_task_status(task_id: str):
    """Get current status of a task."""
    # In production, query from database or state store
    # For now, return mock status

    return AgentStatusResponse(
        agent_name="churn-forecast-modeler",
        status="in_progress",
        progress=0.65,
        current_step="Generating predictions",
        outputs={
            "records_processed": 35000,
            "records_total": 50000,
        },
        cost_so_far_gbp=12.50
    )


@app.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, approval: ApprovalRequest):
    """Approve or reject a task requiring human review."""
    logger.info(f"Task {task_id} decision: {approval.decision}")

    # In production, update task state and resume execution

    return {
        "task_id": task_id,
        "decision": approval.decision,
        "message": f"Task {approval.decision}. Agents will {'proceed' if approval.decision == 'approved' else 'halt'}."
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await connection_manager.connect(websocket)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()

            # Echo back (in production, this would trigger agent actions)
            await connection_manager.send_personal_message(
                {"type": "ack", "message": f"Received: {data}"},
                websocket
            )

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agents_available": len(agent_registry.list_agents()),
        "active_conversations": len(conversation_manager.conversations),
        "timestamp": datetime.utcnow().isoformat()
    }


# Utility function to broadcast agent updates
async def broadcast_agent_update(task_id: str, agent_name: str, status: str, message: str):
    """Broadcast agent status update to all connected clients."""
    await connection_manager.broadcast({
        "type": "agent_update",
        "task_id": task_id,
        "agent_name": agent_name,
        "status": status,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
