"""
Chat Service - Agentic LLM Orchestration

Manages conversation flow with Claude (primary) and Gemini (fallback).
Implements tool calling for financial queries and actions.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from ..core.config import get_settings
from ..models.models import Conversation, Message, generate_uuid
from .chat_tools import ChatToolExecutor, TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

# Claude API (primary)
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    anthropic = None

# Gemini API (fallback)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class ChatService:
    """
    Orchestrates chat interactions with LLM providers.

    Features:
    - Claude as primary LLM with tool use
    - Gemini as fallback
    - Conversation context management
    - Tool execution pipeline
    """

    SYSTEM_PROMPT = """You are Ledgi, a helpful and knowledgeable personal finance assistant. You help users understand and manage their spending, track their financial goals, and make better financial decisions.

You have access to the user's financial data through tools. When users ask about their spending, transactions, or finances, USE THE TOOLS to get real data - don't make up numbers.

Guidelines:
- Be concise but helpful. Use bullet points for clarity when listing multiple items.
- Always use real data from tools - never fabricate financial information.
- When showing transaction data, format amounts as currency ($X.XX).
- If you modify anything (like tags), confirm the action was successful.
- Be encouraging about financial progress, but honest about overspending.
- For vague questions, ask clarifying questions to provide better answers.
- When you don't have enough information, use tools to gather data first.
- Keep responses focused and actionable.

Available capabilities:
- Search transactions by merchant, description, date range, or category
- Get spending summaries by category or time period
- Check budget pace and spending velocity
- View and track financial goals
- Update transaction tags for better organization
- Analyze unusual spending patterns
- Compare spending between time periods"""

    MAX_CONTEXT_MESSAGES = 20  # Keep last N messages for context
    MAX_TOOL_ITERATIONS = 5   # Max tool call loops per message

    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
        self.settings = get_settings()
        self.tool_executor = ChatToolExecutor(db, user_id)

        # Initialize Claude client
        self.claude_client = None
        if CLAUDE_AVAILABLE and self.settings.anthropic_api_key:
            self.claude_client = anthropic.Anthropic(
                api_key=self.settings.anthropic_api_key,
                timeout=30.0,
            )
            logger.info("Claude client initialized successfully")
        else:
            logger.warning(f"Claude not available: CLAUDE_AVAILABLE={CLAUDE_AVAILABLE}, has_key={bool(self.settings.anthropic_api_key)}")

        # Initialize Gemini
        self.gemini_model = None
        if GEMINI_AVAILABLE and self.settings.gemini_api_key:
            genai.configure(api_key=self.settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info("Gemini client initialized successfully")
        else:
            logger.warning(f"Gemini not available: GEMINI_AVAILABLE={GEMINI_AVAILABLE}, has_key={bool(self.settings.gemini_api_key)}")

    def _get_conversation(self, conversation_id: str) -> Conversation:
        """Get and verify conversation ownership."""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == self.user_id
        ).first()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return conversation

    def _save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict]] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None
    ) -> Message:
        """Save a message to the database."""
        message = Message(
            id=generate_uuid(),
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def _build_context(self, conversation_id: str) -> List[Dict]:
        """Build conversation context from message history."""
        messages = self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(self.MAX_CONTEXT_MESSAGES).all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        context = []
        for msg in messages:
            if msg.role == "user":
                context.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                # Check if this message had tool calls
                if msg.tool_calls:
                    tool_calls = json.loads(msg.tool_calls)
                    # Build content with text and tool_use blocks
                    content_blocks = []
                    if msg.content:
                        content_blocks.append({"type": "text", "text": msg.content})
                    for tc in tool_calls:
                        content_blocks.append({
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["arguments"]
                        })
                    context.append({"role": "assistant", "content": content_blocks})

                    # Add tool results
                    for tc in tool_calls:
                        if tc.get("result"):
                            context.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tc["id"],
                                    "content": json.dumps(tc["result"])
                                }]
                            })
                else:
                    context.append({"role": "assistant", "content": msg.content})

        return context

    def _update_conversation_meta(
        self,
        conversation: Conversation,
        response: Dict,
        user_message: str
    ):
        """Update conversation metadata after processing."""
        conversation.updated_at = datetime.now(timezone.utc)
        conversation.last_message_at = datetime.now(timezone.utc)
        conversation.message_count += 2  # User + assistant messages

        if response.get("tool_results"):
            conversation.tool_calls_count += len(response["tool_results"])

        if response.get("tokens"):
            conversation.total_tokens += response["tokens"]

        if response.get("provider"):
            conversation.llm_provider = response["provider"]

        # Auto-generate title from first message
        if not conversation.title and user_message:
            # Take first 50 chars of first user message as title
            conversation.title = user_message[:50] + ("..." if len(user_message) > 50 else "")

        self.db.commit()

    async def process_message(
        self,
        conversation_id: str,
        user_message: str
    ) -> Dict:
        """
        Process a user message and return AI response.

        Flow:
        1. Validate conversation ownership
        2. Save user message
        3. Build context from conversation history
        4. Call LLM with tools
        5. Execute any tool calls
        6. Return final response
        """
        # Verify conversation belongs to user
        conversation = self._get_conversation(conversation_id)

        # Save user message
        self._save_message(conversation_id, "user", user_message)

        # Build conversation context (last N messages)
        context = self._build_context(conversation_id)

        # Try Claude first, then Gemini
        if self.claude_client:
            logger.info(f"Processing message with Claude, context size: {len(context)}")
            try:
                response = await self._process_with_claude(context)
                logger.info(f"Claude response received: {len(response.get('content', ''))} chars")
            except Exception as e:
                logger.error(f"Claude API error: {e}")
                if self.gemini_model:
                    logger.info("Falling back to Gemini")
                    response = await self._process_with_gemini(context, user_message)
                else:
                    raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
        elif self.gemini_model:
            logger.info(f"Processing message with Gemini (no Claude available)")
            response = await self._process_with_gemini(context, user_message)
        else:
            logger.error("No LLM provider available")
            raise HTTPException(status_code=500, detail="No LLM provider available. Please configure ANTHROPIC_API_KEY or GEMINI_API_KEY.")

        # Save assistant response
        assistant_message = self._save_message(
            conversation_id,
            "assistant",
            response["content"],
            tool_calls=response.get("tool_results"),
            input_tokens=response.get("input_tokens"),
            output_tokens=response.get("output_tokens")
        )

        # Update conversation metadata
        self._update_conversation_meta(conversation, response, user_message)

        # Format response for API
        return {
            "message": {
                "id": assistant_message.id,
                "role": assistant_message.role,
                "content": assistant_message.content,
                "tool_calls": response.get("tool_results"),
                "created_at": assistant_message.created_at.isoformat()
            },
            "tool_results": response.get("tool_results"),
            "conversation_id": conversation_id
        }

    async def _process_with_claude(self, context: List[Dict]) -> Dict:
        """Process message using Claude with tool calling."""

        # Convert tools to Claude format
        tools = self._get_claude_tools()

        messages = context.copy()
        tool_results = []

        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                tools=tools,
                messages=messages
            )

            # Check if we need to execute tools
            if response.stop_reason == "tool_use":
                # Execute each tool call
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

                # Add assistant's response with tool calls to messages
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools and collect results
                tool_result_content = []
                for tool_block in tool_use_blocks:
                    result = await self.tool_executor.execute(
                        tool_block.name,
                        tool_block.input
                    )
                    tool_results.append({
                        "id": tool_block.id,
                        "name": tool_block.name,
                        "arguments": tool_block.input,
                        "result": result
                    })

                    tool_result_content.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": json.dumps(result)
                    })

                # Add tool results to messages
                messages.append({
                    "role": "user",
                    "content": tool_result_content
                })
            else:
                # Final response - extract text
                text_content = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_content += block.text

                return {
                    "content": text_content,
                    "tool_results": tool_results if tool_results else None,
                    "provider": "claude",
                    "tokens": response.usage.input_tokens + response.usage.output_tokens,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }

        # If we hit max iterations, return what we have
        return {
            "content": "I processed your request but reached the maximum number of operations. Please try a more specific question.",
            "tool_results": tool_results if tool_results else None,
            "provider": "claude"
        }

    async def _process_with_gemini(self, context: List[Dict], user_message: str) -> Dict:
        """Process message using Gemini with tool calling support."""

        # Convert tools to Gemini format
        gemini_tools = self._get_gemini_tools()

        # Build conversation history for Gemini
        gemini_history = []
        for msg in context[:-1]:  # Exclude the last user message (we'll send it separately)
            role = msg["role"]
            content = msg["content"]

            if role == "user":
                if isinstance(content, list):
                    # Handle tool results
                    parts = []
                    for item in content:
                        if item.get("type") == "tool_result":
                            parts.append({"function_response": {
                                "name": "tool_result",
                                "response": {"result": item.get("content", "")}
                            }})
                    if parts:
                        gemini_history.append({"role": "user", "parts": parts})
                else:
                    gemini_history.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                if isinstance(content, str):
                    gemini_history.append({"role": "model", "parts": [content]})

        tool_results = []

        try:
            # Create chat with tools
            chat = self.gemini_model.start_chat(history=gemini_history)

            for _ in range(self.MAX_TOOL_ITERATIONS):
                response = chat.send_message(
                    user_message if not tool_results else "Please continue with the tool results.",
                    tools=gemini_tools
                )

                # Check for function calls
                function_calls = []
                text_parts = []

                for part in response.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_calls.append(part.function_call)
                    elif hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)

                if function_calls:
                    # Execute function calls
                    function_responses = []
                    for fc in function_calls:
                        tool_name = fc.name
                        tool_args = dict(fc.args) if fc.args else {}

                        logger.info(f"Gemini calling tool: {tool_name} with args: {tool_args}")

                        result = await self.tool_executor.execute(tool_name, tool_args)
                        tool_results.append({
                            "id": f"gemini-{tool_name}-{len(tool_results)}",
                            "name": tool_name,
                            "arguments": tool_args,
                            "result": result
                        })

                        function_responses.append({
                            "function_response": {
                                "name": tool_name,
                                "response": {"result": json.dumps(result)}
                            }
                        })

                    # Send function responses back to Gemini
                    response = chat.send_message(function_responses)

                    # Check if this response has more function calls or is final
                    has_more_calls = any(
                        hasattr(part, 'function_call') and part.function_call
                        for part in response.parts
                    )

                    if not has_more_calls:
                        # Final response
                        final_text = ""
                        for part in response.parts:
                            if hasattr(part, 'text') and part.text:
                                final_text += part.text

                        return {
                            "content": final_text,
                            "tool_results": tool_results if tool_results else None,
                            "provider": "gemini"
                        }
                else:
                    # No function calls, return text response
                    return {
                        "content": "".join(text_parts),
                        "tool_results": tool_results if tool_results else None,
                        "provider": "gemini"
                    }

            # Max iterations reached
            return {
                "content": "I processed your request but reached the maximum number of operations.",
                "tool_results": tool_results if tool_results else None,
                "provider": "gemini"
            }

        except Exception as e:
            logger.error(f"Gemini error: {e}")
            # Fallback to simple prompt without tools
            try:
                prompt = f"{self.SYSTEM_PROMPT}\n\nUser: {user_message}\n\nAssistant:"
                response = self.gemini_model.generate_content(prompt)
                return {
                    "content": response.text,
                    "tool_results": None,
                    "provider": "gemini"
                }
            except Exception as e2:
                return {
                    "content": "I apologize, but I encountered an error processing your request. Please try again.",
                    "tool_results": None,
                    "provider": "gemini",
                    "error": str(e2)
                }

    def _get_claude_tools(self) -> List[Dict]:
        """Convert tool definitions to Claude format."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["input_schema"]
            }
            for tool in TOOL_DEFINITIONS
        ]

    def _get_gemini_tools(self) -> List:
        """Convert tool definitions to Gemini format."""
        function_declarations = []

        for tool in TOOL_DEFINITIONS:
            # Convert JSON Schema to Gemini format
            schema = tool["input_schema"]
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            gemini_params = {
                "type": "object",
                "properties": {},
                "required": required
            }

            for prop_name, prop_def in properties.items():
                param_type = prop_def.get("type", "string")
                gemini_type = {
                    "string": "STRING",
                    "integer": "INTEGER",
                    "number": "NUMBER",
                    "boolean": "BOOLEAN",
                    "array": "ARRAY",
                    "object": "OBJECT"
                }.get(param_type, "STRING")

                gemini_params["properties"][prop_name] = {
                    "type": gemini_type,
                    "description": prop_def.get("description", "")
                }

                # Handle enum
                if "enum" in prop_def:
                    gemini_params["properties"][prop_name]["enum"] = prop_def["enum"]

            function_declarations.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": gemini_params
            })

        return [{"function_declarations": function_declarations}]

    async def create_conversation(self) -> Conversation:
        """Create a new conversation for the user."""
        conversation = Conversation(
            id=generate_uuid(),
            user_id=self.user_id,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversations(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None
    ) -> tuple[List[Conversation], int]:
        """Get user's conversations with pagination."""
        query = self.db.query(Conversation).filter(
            Conversation.user_id == self.user_id
        )

        if status:
            query = query.filter(Conversation.status == status)

        total = query.count()
        conversations = query.order_by(
            Conversation.updated_at.desc()
        ).offset(offset).limit(limit).all()

        return conversations, total

    def get_conversation_with_messages(self, conversation_id: str) -> Conversation:
        """Get a conversation with all its messages."""
        conversation = self._get_conversation(conversation_id)
        # Messages are loaded via relationship
        return conversation

    def archive_conversation(self, conversation_id: str) -> Conversation:
        """Archive (soft delete) a conversation."""
        conversation = self._get_conversation(conversation_id)
        conversation.status = "archived"
        self.db.commit()
        return conversation
