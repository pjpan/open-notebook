from fastapi import APIRouter, HTTPException
from loguru import logger

from api.models import (
    RebuildRequest,
    RebuildResponse,
)
from open_notebook.database.repository import repo_count
from commands.embedding_commands import rebuild_embeddings

router = APIRouter()


@router.post("/rebuild", response_model=RebuildResponse)
async def start_rebuild(request: RebuildRequest):
    """
    Start a synchronous operation to rebuild embeddings.

    - **mode**: "existing" (re-embed items with embeddings) or "all" (embed everything)
    - **include_sources**: Include sources in rebuild (default: true)
    - **include_notes**: Include notes in rebuild (default: true)
    - **include_insights**: Include insights in rebuild (default: true)

    Returns the result of the rebuild operation.
    """
    try:
        logger.info(f"Starting rebuild request: mode={request.mode}")

        total_estimate = 0
        if request.include_sources:
            total_estimate += await repo_count("source")
        if request.include_notes:
            total_estimate += await repo_count("note")
        if request.include_insights:
            total_estimate += await repo_count("source_insight")

        logger.info(f"Estimated {total_estimate} items to process")

        result = await rebuild_embeddings(
            mode=request.mode,
            include_sources=request.include_sources,
            include_notes=request.include_notes,
            include_insights=request.include_insights,
        )

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error_message"))

        return RebuildResponse(
            total_items=result.get("total_items", 0),
            processed_items=result.get("processed_items", 0),
            failed_items=result.get("failed_items", 0),
            message=f"Rebuild operation completed.",
        )

    except Exception as e:
        logger.error(f"Failed to start rebuild: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start rebuild operation: {str(e)}"
        )
