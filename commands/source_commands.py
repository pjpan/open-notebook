import time
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel

from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import Transformation

try:
    from open_notebook.graphs.source import source_graph
except ImportError as e:
    logger.error(f"Failed to import source_graph: {e}")
    raise ValueError("source_graph not available")


async def process_source_command(
    source_id: int,
    content_state: Dict[str, Any],
    notebook_ids: List[int],
    transformations: List[str],
    embed: bool,
) -> Dict[str, Any]:
    """
    Process source content using the source_graph workflow
    """
    start_time = time.time()
    source = None
    try:
        logger.info(f"Starting source processing for source: {source_id}")

        source = await Source.get(source_id)
        if not source:
            raise ValueError(f"Source '{source_id}' not found")

        source.processing_status = "in_progress"
        await source.save()

        transformation_objects = []
        for trans_id in transformations:
            transformation = await Transformation.get(trans_id)
            if not transformation:
                raise ValueError(f"Transformation '{trans_id}' not found")
            transformation_objects.append(transformation)

        result = await source_graph.ainvoke(
            {
                "content_state": content_state,
                "notebook_ids": notebook_ids,
                "apply_transformations": transformation_objects,
                "embed": embed,
                "source_id": source_id,
            }
        )

        processed_source = result["source"]
        processed_source.processing_status = "completed"
        await processed_source.save()

        embedded_chunks = await processed_source.get_embedded_chunks() if embed else 0
        insights_list = await processed_source.get_insights()
        insights_created = len(insights_list)

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully processed source: {processed_source.id} in {processing_time:.2f}s"
        )

        return {
            "success": True,
            "source_id": processed_source.id,
            "embedded_chunks": embedded_chunks,
            "insights_created": insights_created,
            "processing_time": processing_time,
        }

    except Exception as e:
        if source:
            source.processing_status = "failed"
            await source.save()
        
        processing_time = time.time() - start_time
        logger.error(f"Source processing failed: {e}")

        return {
            "success": False,
            "source_id": source_id,
            "processing_time": processing_time,
            "error_message": str(e),
        }
