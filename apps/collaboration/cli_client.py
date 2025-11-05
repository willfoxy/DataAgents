#!/usr/bin/env python3
"""
CLI Client for Aurora Energy Agent Collaboration.

Interactive command-line client to chat with agents.
"""

import asyncio
import httpx
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

console = Console()

API_BASE_URL = "http://localhost:8000"


async def list_agents():
    """List all available agents."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/agents")
        agents = response.json()

        table = Table(title="Available Agents (25)")
        table.add_column("Agent", style="cyan")
        table.add_column("Domain", style="magenta")
        table.add_column("Capability", style="green")
        table.add_column("Cost", style="yellow")

        for agent in agents:
            table.add_row(
                agent["name"],
                agent.get("domain", "N/A"),
                agent.get("capability", "N/A"),
                f"£{agent.get('cost_estimate_gbp', 0):.2f}"
            )

        console.print(table)


async def submit_task(message: str):
    """Submit a task to the agents."""
    console.print(f"\n[bold blue]You:[/bold blue] {message}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/tasks",
            json={
                "message": message,
                "priority": "medium",
                "user_id": "cli-user"
            }
        )

        if response.status_code == 200:
            data = response.json()

            console.print(f"\n[bold green]Agent:[/bold green] {data['message']}")
            console.print(f"\n[yellow]Task ID:[/yellow] {data['task_id']}")
            console.print(f"[yellow]Estimated Cost:[/yellow] £{data['estimated_cost_gbp']:.2f}")
            console.print(f"[yellow]Estimated Duration:[/yellow] {data['estimated_duration_seconds']}s")
            console.print(f"[yellow]Agents Involved:[/yellow] {', '.join(data['agents_involved'])}")

            return data['task_id'], data['conversation_id']
        else:
            console.print(f"[red]Error:[/red] {response.text}")
            return None, None


async def get_task_status(task_id: str):
    """Get the status of a task."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/tasks/{task_id}/status")

        if response.status_code == 200:
            status = response.json()

            console.print(Panel(
                f"[bold]{status['agent_name']}[/bold]\n"
                f"Status: {status['status']}\n"
                f"Progress: {status['progress'] * 100:.0f}%\n"
                f"Step: {status['current_step']}\n"
                f"Cost: £{status['cost_so_far_gbp']:.2f}",
                title="Task Status"
            ))
        else:
            console.print(f"[red]Error:[/red] {response.text}")


async def get_conversation(conversation_id: str):
    """Get conversation history."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/conversations/{conversation_id}")

        if response.status_code == 200:
            conv = response.json()

            console.print(Panel(
                f"Conversation: {conv['conversation_id']}\n"
                f"User: {conv['user_id']}\n"
                f"Messages: {len(conv['messages'])}",
                title="Conversation Info"
            ))

            for msg in conv['messages']:
                role = "You" if msg['role'] == 'user' else "Agent"
                console.print(f"\n[bold]{role}:[/bold] {msg['content']}")


async def interactive_chat():
    """Start interactive chat session."""
    console.print(Panel.fit(
        "[bold cyan]Aurora Energy Agent Collaboration[/bold cyan]\n"
        "Chat with 25 AI agents for data analytics, ML, and operations",
        title="Welcome"
    ))

    console.print("\n[yellow]Commands:[/yellow]")
    console.print("  /agents - List all agents")
    console.print("  /status <task_id> - Get task status")
    console.print("  /history <conversation_id> - View conversation")
    console.print("  /quit - Exit")
    console.print()

    conversation_id = None
    task_id = None

    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ").strip()

            if not user_input:
                continue

            if user_input == "/quit":
                console.print("[yellow]Goodbye![/yellow]")
                break

            elif user_input == "/agents":
                await list_agents()

            elif user_input.startswith("/status"):
                parts = user_input.split()
                tid = parts[1] if len(parts) > 1 else task_id
                if tid:
                    await get_task_status(tid)
                else:
                    console.print("[red]No task ID provided or available[/red]")

            elif user_input.startswith("/history"):
                parts = user_input.split()
                cid = parts[1] if len(parts) > 1 else conversation_id
                if cid:
                    await get_conversation(cid)
                else:
                    console.print("[red]No conversation ID provided or available[/red]")

            else:
                # Submit task
                task_id, conversation_id = await submit_task(user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


async def main():
    """Main entry point."""
    # Check if API is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/health", timeout=2.0)
            if response.status_code == 200:
                console.print("[green]✓ Connected to Aurora Energy API[/green]")
            else:
                console.print("[red]✗ API not healthy[/red]")
                return
    except Exception:
        console.print("[red]✗ Cannot connect to API. Is the server running?[/red]")
        console.print(f"[yellow]Start server with: uvicorn apps.collaboration.api:app[/yellow]")
        return

    await interactive_chat()


if __name__ == "__main__":
    asyncio.run(main())
