import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.domain.notebook import ChatSession, Note, Notebook, Source
from open_notebook.exceptions import (
    NotFoundError,
)
from open_notebook.graphs.chat import graph as chat_graph

router = APIRouter()


# Request/Response models
class CreateSessionRequest(BaseModel):
    notebook_id: int = Field(..., description="Notebook ID to create session for")
    title: Optional[str] = Field(None, description="Optional session title")
    model_override: Optional[str] = Field(
        None, description="Optional model override for this session"
    )


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = Field(None, description="New session title")
    model_override: Optional[str] = Field(
        None, description="Model override for this session"
    )


class ChatMessage(BaseModel):
    id: str = Field(..., description="Message ID")
    type: str = Field(..., description="Message type (human|ai)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = Field(None, description="Message timestamp")


class ChatSessionResponse(BaseModel):
    id: int = Field(..., description="Session ID")
    title: str = Field(..., description="Session title")
    notebook_id: Optional[int] = Field(None, description="Notebook ID")
    created: str = Field(..., description="Creation timestamp")
    updated: str = Field(..., description="Last update timestamp")
    message_count: Optional[int] = Field(
        None, description="Number of messages in session"
    )
    model_override: Optional[str] = Field(
        None, description="Model override for this session"
    )


class ChatSessionWithMessagesResponse(ChatSessionResponse):
    messages: List[ChatMessage] = Field(
        default_factory=list, description="Session messages"
    )


class ExecuteChatRequest(BaseModel):
    session_id: int = Field(..., description="Chat session ID")
    message: str = Field(..., description="User message content")
    context: Dict[str, Any] = Field(
        ..., description="Chat context with sources and notes"
    )
    model_override: Optional[str] = Field(
        None, description="Optional model override for this message"
    )


class ExecuteChatResponse(BaseModel):
    session_id: int = Field(..., description="Session ID")
    messages: List[ChatMessage] = Field(..., description="Updated message list")


class BuildContextRequest(BaseModel):
    notebook_id: int = Field(..., description="Notebook ID")
    context_config: Dict[str, Any] = Field(..., description="Context configuration")


class BuildContextResponse(BaseModel):
    context: Dict[str, Any] = Field(..., description="Built context data")
    token_count: int = Field(..., description="Estimated token count")
    char_count: int = Field(..., description="Character count")


class SuccessResponse(BaseModel):
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")


@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
async def get_sessions(notebook_id: int = Query(..., description="Notebook ID")):
    """Get all chat sessions for a notebook."""
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        sessions = await notebook.get_chat_sessions()

        return [
            ChatSessionResponse(
                id=session.id,
                title=session.title or "Untitled Session",
                notebook_id=notebook_id,
                created=str(session.created),
                updated=str(session.updated),
                model_override=session.model_override,
            )
            for session in sessions
        ]
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching chat sessions")


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_session(request: CreateSessionRequest):
    """Create a new chat session."""
    try:
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        session = ChatSession(
            title=request.title or f"Chat Session {asyncio.get_event_loop().time():.0f}",
            model_override=request.model_override,
            notebook_id=request.notebook_id,
        )
        await session.save()

        return ChatSessionResponse(
            id=session.id,
            title=session.title or "",
            notebook_id=request.notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            model_override=session.model_override,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating chat session")


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionWithMessagesResponse)
async def get_session(session_id: int):
    """Get a specific session with its messages."""
    try:
        session = await ChatSession.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        thread_state = chat_graph.get_state(
            config=RunnableConfig(configurable={"thread_id": str(session_id)})
        )

        messages: list[ChatMessage] = []
        if thread_state and thread_state.values and "messages" in thread_state.values:
            for msg in thread_state.values["messages"]:
                messages.append(
                    ChatMessage(
                        id=getattr(msg, "id", f"msg_{len(messages)}"),
                        type=msg.type,
                        content=msg.content,
                    )
                )

        return ChatSessionWithMessagesResponse(
            id=session.id,
            title=session.title or "Untitled Session",
            notebook_id=session.notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            message_count=len(messages),
            messages=messages,
            model_override=session.model_override,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error fetching session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching session")


@router.put("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(session_id: int, request: UpdateSessionRequest):
    """Update session title."""
    try:
        session = await ChatSession.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(session, key, value)
        await session.save()

        return ChatSessionResponse(
            id=session.id,
            title=session.title or "",
            notebook_id=session.notebook_id,
            created=str(session.created),
            updated=str(session.updated),
            model_override=session.model_override,
        )
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating session")


@router.delete("/chat/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: int):
    """Delete a chat session."""
    try:
        session = await ChatSession.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await session.delete()
        return SuccessResponse(success=True, message="Session deleted successfully")
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting session")


@router.post("/chat/execute", response_model=ExecuteChatResponse)
async def execute_chat(request: ExecuteChatRequest):
    """Execute a chat request and get AI response."""
    try:
        session = await ChatSession.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        model_override = request.model_override or session.model_override

        current_state = chat_graph.get_state(
            config=RunnableConfig(configurable={"thread_id": str(request.session_id)})
        )

        state_values = current_state.values if current_state else {}
        state_values["messages"] = state_values.get("messages", [])
        state_values["context"] = request.context
        state_values["model_override"] = model_override

        from langchain_core.messages import HumanMessage
        state_values["messages"].append(HumanMessage(content=request.message))

        result = chat_graph.invoke(
            input=state_values,
            config=RunnableConfig(
                configurable={
                    "thread_id": str(request.session_id),
                    "model_id": model_override,
                }
            ),
        )

        await session.save()

        messages: list[ChatMessage] = []
        for msg in result.get("messages", []):
            messages.append(
                ChatMessage(
                    id=getattr(msg, "id", f"msg_{len(messages)}"),
                    type=msg.type,
                    content=msg.content,
                )
            )

        return ExecuteChatResponse(session_id=request.session_id, messages=messages)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error executing chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error executing chat")


@router.post("/chat/context", response_model=BuildContextResponse)
async def build_context(request: BuildContextRequest):
    """Build context for a notebook based on context configuration."""
    try:
        notebook = await Notebook.get(request.notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        context_data: dict[str, list[dict[str, str]]] = {"sources": [], "notes": []}
        total_content = ""

        if request.context_config:
            for source_id_str, status in request.context_config.get("sources", {}).items():
                if "not in" in status: continue
                try:
                    source = await Source.get(int(source_id_str))
                    if "insights" in status:
                        context_data["sources"].append(await source.get_context(context_size="short"))
                    elif "full content" in status:
                        context_data["sources"].append(await source.get_context(context_size="long"))
                except Exception as e:
                    logger.warning(f"Error processing source {source_id_str}: {e}")

            for note_id_str, status in request.context_config.get("notes", {}).items():
                if "not in" in status: continue
                try:
                    note = await Note.get(int(note_id_str))
                    if "full content" in status:
                        context_data["notes"].append(note.get_context(context_size="long"))
                except Exception as e:
                    logger.warning(f"Error processing note {note_id_str}: {e}")
        else:
            sources = await notebook.get_sources()
            for source in sources:
                context_data["sources"].append(await source.get_context(context_size="short"))
            notes = await notebook.get_notes()
            for note in notes:
                context_data["notes"].append(note.get_context(context_size="short"))
        
        total_content = str(context_data)
        char_count = len(total_content)
        from open_notebook.utils import token_count
        estimated_tokens = token_count(total_content)

        return BuildContextResponse(
            context=context_data, token_count=estimated_tokens, char_count=char_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building context: {str(e)}")
        raise HTTPException(status_code=500, detail="Error building context")
