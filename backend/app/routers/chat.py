"""
Chat Router - Agentic Chatbot API

Handles conversation management and message processing with Claude/Gemini.
"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
import json

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.rate_limiter import limiter
from ..models import User
from ..schemas.chat_schemas import (
    ConversationResponse,
    ConversationSummary,
    ConversationListResponse,
    ChatRequest,
    ChatResponse,
    MessageResponse,
    ToolCallInfo
)
from ..services.chat_service import ChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _format_conversation_summary(conv) -> ConversationSummary:
    """Format a conversation for list view."""
    # Get last message preview if exists
    last_message_preview = None
    if conv.messages:
        last_msg = conv.messages[-1] if conv.messages else None
        if last_msg:
            last_message_preview = last_msg.content[:100] + ("..." if len(last_msg.content) > 100 else "")

    return ConversationSummary(
        id=conv.id,
        title=conv.title,
        status=conv.status,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        last_message_preview=last_message_preview
    )


def _format_message(msg) -> MessageResponse:
    """Format a message for response."""
    tool_calls = None
    if msg.tool_calls:
        try:
            tc_data = json.loads(msg.tool_calls)
            tool_calls = [
                ToolCallInfo(
                    id=tc.get("id", ""),
                    name=tc.get("name", ""),
                    arguments=tc.get("arguments", {}),
                    result=tc.get("result")
                )
                for tc in tc_data
            ]
        except json.JSONDecodeError:
            pass

    return MessageResponse(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        tool_calls=tool_calls,
        created_at=msg.created_at
    )


def _format_conversation_with_messages(conv) -> ConversationResponse:
    """Format a conversation with all its messages."""
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        status=conv.status,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=conv.message_count,
        messages=[_format_message(msg) for msg in conv.messages]
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List user's conversations, most recent first.

    - limit: Maximum number of conversations to return (default 20, max 100)
    - offset: Number of conversations to skip for pagination
    - status: Filter by status (active, archived)
    """
    chat_service = ChatService(db, current_user.id)
    conversations, total = chat_service.get_conversations(limit, offset, status)

    return ConversationListResponse(
        conversations=[_format_conversation_summary(c) for c in conversations],
        total=total,
        has_more=(offset + limit) < total
    )


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new conversation."""
    chat_service = ChatService(db, current_user.id)
    conversation = await chat_service.create_conversation()

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        status=conversation.status,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count,
        messages=[]
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a conversation with all messages.

    Returns the full conversation including all message history.
    """
    chat_service = ChatService(db, current_user.id)
    conversation = chat_service.get_conversation_with_messages(conversation_id)

    return _format_conversation_with_messages(conversation)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Archive a conversation.

    Soft deletes the conversation by setting status to 'archived'.
    """
    chat_service = ChatService(db, current_user.id)
    chat_service.archive_conversation(conversation_id)

    return {"status": "archived", "conversation_id": conversation_id}


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    conversation_id: str,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message and get AI response.

    This is the main chat endpoint that:
    1. Saves the user message to the conversation
    2. Invokes Claude (or Gemini fallback) with available tools
    3. Executes any tool calls (searching transactions, etc.)
    4. Returns the final AI response

    The AI has access to tools for:
    - Searching transactions
    - Getting spending summaries
    - Checking spending pace
    - Viewing goals
    - Updating transaction tags
    - Analyzing unusual transactions
    - Comparing spending periods
    """
    chat_service = ChatService(db, current_user.id)
    response = await chat_service.process_message(conversation_id, chat_request.message)

    # Format tool_calls if present
    tool_results = None
    if response.get("tool_results"):
        tool_results = [
            ToolCallInfo(
                id=tc.get("id", ""),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
                result=tc.get("result")
            )
            for tc in response["tool_results"]
        ]

    return ChatResponse(
        message=MessageResponse(
            id=response["message"]["id"],
            role=response["message"]["role"],
            content=response["message"]["content"],
            tool_calls=tool_results,
            created_at=response["message"]["created_at"]
        ),
        tool_results=tool_results,
        conversation_id=response["conversation_id"]
    )
