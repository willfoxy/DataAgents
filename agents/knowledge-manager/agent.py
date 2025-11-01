"""Knowledge Manager Agent - maintain knowledge base with RAG index."""

from typing import Dict, Any, List
from datetime import datetime
import uuid

from libs.common.types import GraphState
from libs.common.config import get_config
from libs.common.logging import get_logger, bind_context
from libs.common.io import S3Client
from libs.observability.tracing import trace_agent
from libs.cost_meter.tracker import CostTracker

logger = get_logger(__name__)


class KnowledgeManager:
    """
    Knowledge Manager Agent.

    Responsibilities:
    - Maintain knowledge base of decisions, playbooks, runbooks
    - Build and update RAG index for semantic search
    - Capture agent learnings and best practices
    - Provide context retrieval for other agents
    - Track knowledge gaps and recommendations
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.s3 = S3Client()
        self.cost_tracker = CostTracker()

    @trace_agent("knowledge-manager")
    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """Execute knowledge management."""
        run_id = str(uuid.uuid4())
        bind_context(agent_name="knowledge-manager", task_id=state.task_id, run_id=run_id)
        logger.info("Starting knowledge manager", task_id=state.task_id)

        try:
            operation = state.inputs.get("operation", "search")

            if operation == "index":
                outputs = await self._index_knowledge(state)
            elif operation == "search":
                outputs = await self._search_knowledge(state)
            else:
                outputs = await self._update_knowledge(state)

            self.cost_tracker.record_cost(
                agent_name="knowledge-manager",
                task_id=state.task_id,
                cost_gbp=0.3,
                resource_type="opensearch",
                metadata={"operation": operation, "run_id": run_id},
            )

            return outputs

        except Exception as e:
            logger.error(f"Knowledge management failed: {e}", exc_info=True)
            return {"status": "failed", "error": str(e), "agent": "knowledge-manager"}

    async def _index_knowledge(self, state: GraphState) -> Dict[str, Any]:
        """Index new knowledge."""
        logger.info("Indexing knowledge")

        document = state.inputs.get("document", {})
        doc_type = state.inputs.get("doc_type", "playbook")

        # In production: use OpenSearch or vector database
        indexed_doc = {
            "doc_id": f"doc-{uuid.uuid4().hex[:8]}",
            "type": doc_type,
            "title": document.get("title"),
            "content": document.get("content"),
            "tags": document.get("tags", []),
            "indexed_at": datetime.utcnow().isoformat(),
        }

        logger.info("Knowledge indexed", doc_id=indexed_doc["doc_id"])

        return {
            "status": "success",
            "indexed_doc": indexed_doc,
        }

    async def _search_knowledge(self, state: GraphState) -> Dict[str, Any]:
        """Search knowledge base."""
        logger.info("Searching knowledge")

        query = state.inputs.get("query", "")
        top_k = state.inputs.get("top_k", 5)

        # In production: semantic search with embeddings
        results = [
            {
                "doc_id": "doc-abc123",
                "title": "Churn Model Deployment Playbook",
                "excerpt": "Steps to deploy churn model with canary strategy...",
                "relevance_score": 0.92,
            },
            {
                "doc_id": "doc-def456",
                "title": "Model Rollback Runbook",
                "excerpt": "Emergency procedure to rollback a deployed model...",
                "relevance_score": 0.85,
            },
        ]

        logger.info("Knowledge search complete", num_results=len(results))

        return {
            "status": "success",
            "query": query,
            "results": results[:top_k],
        }

    async def _update_knowledge(self, state: GraphState) -> Dict[str, Any]:
        """Update knowledge base with learnings."""
        logger.info("Updating knowledge")

        learning = state.inputs.get("learning", {})

        # In production: add to knowledge base
        knowledge_entry = {
            "entry_id": f"entry-{uuid.uuid4().hex[:8]}",
            "agent": learning.get("agent"),
            "decision": learning.get("decision"),
            "outcome": learning.get("outcome"),
            "lesson": learning.get("lesson"),
            "created_at": datetime.utcnow().isoformat(),
        }

        logger.info("Knowledge updated", entry_id=knowledge_entry["entry_id"])

        return {
            "status": "success",
            "knowledge_entry": knowledge_entry,
        }


async def create_knowledge_manager() -> KnowledgeManager:
    """Factory function to create knowledge manager."""
    return KnowledgeManager()
