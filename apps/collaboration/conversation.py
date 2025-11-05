"""
Conversation Manager - Track user-agent conversations.

Manages conversation history, context, and multi-turn interactions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from libs.common.logging import get_logger

logger = get_logger(__name__)


class Message(BaseModel):
    """A message in a conversation."""
    message_id: str
    role: str  # "user" or "assistant" or "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """A conversation between user and agents."""
    conversation_id: str
    user_id: str
    messages: List[Message] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # active, paused, completed


class ConversationManager:
    """
    Manages conversations between users and agents.

    Features:
    - Multi-turn conversation tracking
    - Context preservation across messages
    - Conversation history storage
    - User session management
    """

    def __init__(self):
        # In-memory storage (in production, use database)
        self.conversations: Dict[str, Conversation] = {}
        self.user_conversations: Dict[str, List[str]] = {}

    def create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            context=initial_context or {},
        )

        self.conversations[conversation_id] = conversation

        # Track user's conversations
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = []
        self.user_conversations[user_id].append(conversation_id)

        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.conversations.get(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """Add a message to a conversation."""
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        message = Message(
            message_id=f"msg-{len(conversation.messages) + 1}",
            role=role,
            content=content,
            metadata=metadata or {}
        )

        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()

        logger.info(
            f"Added {role} message to conversation {conversation_id}",
            message_length=len(content)
        )

        return message

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get messages from a conversation."""
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            return []

        messages = conversation.messages

        if limit:
            messages = messages[-limit:]

        return messages

    def get_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation context."""
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            return {}

        return conversation.context

    def update_context(
        self,
        conversation_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """Update conversation context."""
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        conversation.context.update(updates)
        conversation.updated_at = datetime.utcnow()

        logger.info(f"Updated context for conversation {conversation_id}")

    def get_user_conversations(self, user_id: str) -> List[Conversation]:
        """Get all conversations for a user."""
        conversation_ids = self.user_conversations.get(user_id, [])
        return [
            self.conversations[cid]
            for cid in conversation_ids
            if cid in self.conversations
        ]

    def end_conversation(self, conversation_id: str) -> None:
        """Mark a conversation as completed."""
        conversation = self.conversations.get(conversation_id)

        if conversation:
            conversation.status = "completed"
            conversation.updated_at = datetime.utcnow()
            logger.info(f"Ended conversation {conversation_id}")

    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get a summary of the conversation."""
        conversation = self.conversations.get(conversation_id)

        if not conversation:
            return {}

        return {
            "conversation_id": conversation_id,
            "user_id": conversation.user_id,
            "message_count": len(conversation.messages),
            "status": conversation.status,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "duration_seconds": (conversation.updated_at - conversation.created_at).total_seconds(),
            "active_task": conversation.context.get("active_task"),
        }
