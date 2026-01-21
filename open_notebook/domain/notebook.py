import asyncio
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Literal, Optional

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from open_notebook.ai.models import model_manager
from open_notebook.database.repository import repo_create, repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError
from open_notebook.utils import split_text


class Notebook(ObjectModel):
    table_name: ClassVar[str] = "notebook"
    name: str
    description: str
    archived: Optional[bool] = False

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise InvalidInputError("Notebook name cannot be empty")
        return v

    async def get_sources(self) -> List["Source"]:
        try:
            # Assuming a one-to-many relationship with a notebook_id foreign key in the source table
            srcs = await repo_query("source", filters={"notebook_id": self.id})
            return [Source(**src) for src in srcs]
        except Exception as e:
            logger.error(f"Error fetching sources for notebook {self.id}: {str(e)}")
            raise DatabaseOperationError(e)

    async def get_notes(self) -> List["Note"]:
        try:
            # Assuming a one-to-many relationship with a notebook_id foreign key in the note table
            notes = await repo_query("note", filters={"notebook_id": self.id})
            return [Note(**note) for note in notes]
        except Exception as e:
            logger.error(f"Error fetching notes for notebook {self.id}: {str(e)}")
            raise DatabaseOperationError(e)

    async def get_chat_sessions(self) -> List["ChatSession"]:
        try:
            # Assuming a one-to-many relationship with a notebook_id foreign key in the chat_session table
            sessions = await repo_query("chat_session", filters={"notebook_id": self.id})
            return [ChatSession(**session) for session in sessions]
        except Exception as e:
            logger.error(
                f"Error fetching chat sessions for notebook {self.id}: {str(e)}"
            )
            raise DatabaseOperationError(e)


class Asset(BaseModel):
    file_path: Optional[str] = None
    url: Optional[str] = None


class SourceEmbedding(ObjectModel):
    table_name: ClassVar[str] = "source_embedding"
    source_id: int
    content: str
    embedding: List[float]


class SourceInsight(ObjectModel):
    table_name: ClassVar[str] = "source_insight"
    source_id: int
    insight_type: str
    content: str

    async def get_source(self) -> "Source":
        return await Source.get(self.source_id)

    async def save_as_note(self, notebook_id: Optional[int] = None) -> Any:
        source = await self.get_source()
        note = Note(
            title=f"{self.insight_type} from source {source.title}",
            content=self.content,
            notebook_id=notebook_id,
        )
        await note.save()
        return note


class Source(ObjectModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    table_name: ClassVar[str] = "source"
    notebook_id: int
    asset: Optional[Asset] = None
    title: Optional[str] = None
    topics: Optional[List[str]] = Field(default_factory=list)
    full_text: Optional[str] = None
    processing_status: Optional[str] = "pending"


    async def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        insights_list = await self.get_insights()
        insights = [insight.model_dump() for insight in insights_list]
        if context_size == "long":
            return dict(
                id=self.id,
                title=self.title,
                insights=insights,
                full_text=self.full_text,
            )
        else:
            return dict(id=self.id, title=self.title, insights=insights)

    async def get_embedded_chunks(self) -> int:
        # This is not efficient, but it's a simple way to get the count
        chunks = await repo_query("source_embedding", select="id", filters={"source_id": self.id})
        return len(chunks)

    async def get_insights(self) -> List[SourceInsight]:
        insights = await repo_query("source_insight", filters={"source_id": self.id})
        return [SourceInsight(**insight) for insight in insights]

    async def add_to_notebook(self, notebook_id: int) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        self.notebook_id = notebook_id
        await self.save()

    async def vectorize(self) -> None:
        """
        Vectorize the source content synchronously.
        """
        logger.info(f"Starting vectorization for source {self.id}")
        self.processing_status = "in_progress"
        await self.save()

        try:
            if not self.full_text:
                raise ValueError(f"Source {self.id} has no text to vectorize")

            EMBEDDING_MODEL = await model_manager.get_embedding_model()
            if not EMBEDDING_MODEL:
                raise ValueError("Embedding model not configured")
            
            chunks = split_text(self.full_text)
            embeddings = await EMBEDDING_MODEL.aembed(chunks)

            embedding_records = [
                SourceEmbedding(
                    source_id=self.id,
                    content=chunk,
                    embedding=embedding,
                ).model_dump(exclude_none=True)
                for chunk, embedding in zip(chunks, embeddings)
            ]

            for record in embedding_records:
                await repo_create("source_embedding", record)

            self.processing_status = "completed"
            await self.save()
            logger.info(f"Vectorization completed for source {self.id}")

        except Exception as e:
            self.processing_status = "failed"
            await self.save()
            logger.error(
                f"Failed to vectorize source {self.id}: {e}"
            )
            raise DatabaseOperationError(e)

    async def add_insight(self, insight_type: str, content: str) -> Any:
        EMBEDDING_MODEL = await model_manager.get_embedding_model()
        if not EMBEDDING_MODEL:
            logger.warning("No embedding model found. Insight will not be searchable.")

        if not insight_type or not content:
            raise InvalidInputError("Insight type and content must be provided")
        
        insight = SourceInsight(
            source_id=self.id,
            insight_type=insight_type,
            content=content,
        )
        await insight.save()
        return insight

    async def delete(self) -> bool:
        """Delete source and clean up associated file if it exists."""
        if self.asset and self.asset.file_path:
            file_path = Path(self.asset.file_path)
            if file_path.exists():
                try:
                    os.unlink(file_path)
                    logger.info(f"Deleted file for source {self.id}: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete file {file_path} for source {self.id}: {e}."
                    )
        return await super().delete()


class Note(ObjectModel):
    table_name: ClassVar[str] = "note"
    notebook_id: int
    title: Optional[str] = None
    note_type: Optional[Literal["human", "ai"]] = None
    content: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_empty(cls, v):
        if v is not None and not v.strip():
            raise InvalidInputError("Note content cannot be empty")
        return v

    async def add_to_notebook(self, notebook_id: int) -> Any:
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        self.notebook_id = notebook_id
        await self.save()

    def get_context(
        self, context_size: Literal["short", "long"] = "short"
    ) -> Dict[str, Any]:
        if context_size == "long":
            return dict(id=self.id, title=self.title, content=self.content)
        else:
            return dict(
                id=self.id,
                title=self.title,
                content=self.content[:100] if self.content else None,
            )

    def needs_embedding(self) -> bool:
        return True

    def get_embedding_content(self) -> Optional[str]:
        return self.content


class ChatSession(ObjectModel):
    table_name: ClassVar[str] = "chat_session"
    notebook_id: Optional[int] = None
    source_id: Optional[int] = None
    title: Optional[str] = None
    model_override: Optional[str] = None

    async def relate_to_notebook(self, notebook_id: int):
        if not notebook_id:
            raise InvalidInputError("Notebook ID must be provided")
        self.notebook_id = notebook_id
        await self.save()

    async def relate_to_source(self, source_id: int):
        if not source_id:
            raise InvalidInputError("Source ID must be provided")
        self.source_id = source_id
        await self.save()



async def text_search(
    keyword: str, results: int, source: bool = True, note: bool = True
):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    
    # This is a simplified implementation. 
    # For better results, use Supabase's full-text search capabilities.
    search_results = []
    if source:
        sources = await repo_query("source", filters={"title": f"ilike.%{keyword}%"})
        search_results.extend(sources)
    if note:
        notes = await repo_query("note", filters={"title": f"ilike.%{keyword}%"})
        search_results.extend(notes)
        
    return search_results[:results]


async def vector_search(
    keyword: str,
    results: int,
    source: bool = True,
    note: bool = True,
    minimum_score=0.2,
):
    if not keyword:
        raise InvalidInputError("Search keyword cannot be empty")
    
    # Get embedding for the search keyword
    EMBEDDING_MODEL = await model_manager.get_embedding_model()
    if not EMBEDDING_MODEL:
        logger.warning("Embedding model not available for vector search")
        return []
    
    try:
        query_embedding = (await EMBEDDING_MODEL.aembed([keyword]))[0]
        
        from open_notebook.database.repository import repo_vector_search
        # Perform vector search on source_embeddings table
        matches = await repo_vector_search(
            table="source_embedding",
            column="embedding",  # The name of the embedding column
            query_embedding=query_embedding,
            similarity_threshold=minimum_score,
            limit=results
        )
        
        # Extract source_ids from matches and fetch the full sources
        source_ids = list(set([match.get('source_id') for match in matches if match.get('source_id')]))
        sources = []
        if source_ids:
            sources = await repo_query("source", filters={"id": {"in": source_ids}})
        
        return sources
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []
