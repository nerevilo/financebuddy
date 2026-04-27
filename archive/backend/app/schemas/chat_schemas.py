"""Chat schemas for the AI assistant API."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== Tool Call Schemas ====================

class ToolCallInfo(BaseModel):
    """Information about a tool call made by the assistant."""
    id: str
    name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None


# ==================== Message Schemas ====================

class MessageCreate(BaseModel):
    """Request body for creating a new message."""
    message: str = Field(..., min_length=1, max_length=4000)


class MessageResponse(BaseModel):
    """Response for a single message."""
    id: str
    role: str  # user, assistant, tool, system
    content: str
    tool_calls: Optional[List[ToolCallInfo]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Conversation Schemas ====================

class ConversationCreate(BaseModel):
    """Request body for creating a new conversation."""
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Response for a single conversation."""
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    """Summary of a conversation for list view."""
    id: str
    title: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: Optional[str] = None

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response for listing conversations."""
    conversations: List[ConversationSummary]
    total: int
    has_more: bool


# ==================== Chat API Schemas ====================

class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    """Response for a chat message with AI response."""
    message: MessageResponse
    tool_results: Optional[List[ToolCallInfo]] = None
    conversation_id: str


class ChatStreamEvent(BaseModel):
    """Event for streaming chat responses."""
    type: str  # text, tool_call, tool_result, done, error
    content: Optional[str] = None
    tool_call: Optional[ToolCallInfo] = None
    error: Optional[str] = None
