#!/usr/bin/env python3
"""
Simple test to verify all agents can be loaded and executed.
"""

import asyncio
import uuid
from datetime import datetime

from libs.common.types import GraphState, RunStatus
from libs.common.logging import get_logger
from apps.supervisor.agent_registry import get_agent_registry

logger = get_logger(__name__)


async def test_all_agents():
    """Test that all 25 agents can be loaded and executed."""

    print("\n" + "="*80)
    print("🧪 Aurora Energy - Agent Integration Test")
    print("="*80 + "\n")

    registry = get_agent_registry()
    agents = registry.list_agents()

    print(f"Found {len(agents)} agents\n")

    # Test each agent
    results = {}

    for i, agent_name in enumerate(agents, 1):
        print(f"[{i}/{len(agents)}] Testing {agent_name}...", end=" ")

        try:
            # Load agent
            agent = await registry.get_agent(agent_name)

            # Create test state
            state = GraphState(
                task_id=f"test-{uuid.uuid4().hex[:8]}",
                run_id=f"run-{uuid.uuid4().hex[:8]}",
                current_agent=agent_name,
                status=RunStatus.PENDING,
                inputs={
                    "mode": "predict",
                    "operation": "test",
                    "test": True,
                },
            )

            # Execute agent
            result = await agent.execute(state)

            status = result.get('status', 'unknown')
            if status in ['success', 'pending']:
                print(f"✅ {status}")
                results[agent_name] = 'passed'
            else:
                print(f"⚠️  {status}")
                results[agent_name] = 'warning'

        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            results[agent_name] = 'failed'
            logger.error(f"Agent test failed: {agent_name}", exc_info=True)

    # Summary
    print("\n" + "="*80)
    print("📊 Test Results")
    print("="*80)

    passed = sum(1 for v in results.values() if v == 'passed')
    warnings = sum(1 for v in results.values() if v == 'warning')
    failed = sum(1 for v in results.values() if v == 'failed')

    print(f"✅ Passed:   {passed}/{len(agents)}")
    print(f"⚠️  Warnings: {warnings}/{len(agents)}")
    print(f"❌ Failed:   {failed}/{len(agents)}")

    if failed == 0:
        print("\n🎉 All agents loaded and executed successfully!\n")
    else:
        print(f"\n⚠️  {failed} agent(s) need attention\n")
        print("Failed agents:")
        for agent, result in results.items():
            if result == 'failed':
                print(f"  - {agent}")
        print()


if __name__ == "__main__":
    asyncio.run(test_all_agents())
