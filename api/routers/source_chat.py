import asyncio
import json
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from loguru import logger
from pydantic import BaseModel, Field

from open_notebook.domain.notebook import ChatSession, Source
from open_notebook.exceptions import NotFoundError
from open_notebook.graphs.source_chat import source_chat_graph

router = APIRouter()

# ... (Pydantic models will need to be updated to use int for IDs)

class CreateSourceChatSessionRequest(BaseModel):
    title: Optional[str] = Field(None, description="Optional session title")
    model_override: Optional[str] = Field(None, description="Optional model override")

# ... (Other models updated similarly)


@router.post("/sources/{source_id}/chat/sessions", response_model=SourceChatSessionResponse)
async def create_source_chat_session(
    request: CreateSourceChatSessionRequest,
    source_id: int = Path(..., description="Source ID"),
):
    """Create a new chat session for a source."""
    try:
        source = await Source.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        session = ChatSession(
            title=request.title or f"Source Chat {asyncio.get_event_loop().time():.0f}",
            model_override=request.model_override,
            source_id=source_id,
        )
        await session.save()

        return SourceChatSessionResponse(**session.model_dump())
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")
    except Exception as e:
        logger.error(f"Error creating source chat session: {e}")
        raise HTTPException(status_code=500, detail="Error creating source chat session")


@router.get("/sources/{source_id}/chat/sessions", response_model=List[SourceChatSessionResponse])
async def get_source_chat_sessions(source_id: int = Path(..., description="Source ID")):
    """Get all chat sessions for a source."""
    try:
        sessions = await repo_query("chat_session", filters={"source_id": source_id})
        return [SourceChatSessionResponse(**s) for s in sessions]
    except Exception as e:
        logger.error(f"Error fetching source chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Error fetching source chat sessions")


@router.get("/sources/{source_id}/chat/sessions/{session_id}", response_model=SourceChatSessionWithMessagesResponse)
async def get_source_chat_session(
    source_id: int = Path(..., description="Source ID"),
    session_id: int = Path(..., description="Session ID"),
):
    """Get a specific source chat session with its messages."""
    try:
        session = await ChatSession.get(session_id)
        if not session or session.source_id != source_id:
            raise HTTPException(status_code=404, detail="Session not found for this source")

        # ... (rest of the logic remains similar, using integer IDs)
        
        return SourceChatSessionWithMessagesResponse(**session.model_dump(), messages=[]) # Placeholder
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Error fetching source chat session: {e}")
        raise HTTPException(status_code=500, detail="Error fetching source chat session")

# ... (Other endpoints need to be refactored in a similar way)
