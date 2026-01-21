import time
from typing import Dict, List, Literal

from loguru import logger

from open_notebook.ai.models import model_manager
from open_notebook.database.repository import repo_query
from open_notebook.domain.notebook import Note, Source, SourceInsight


async def embed_single_item_command(item_type: str, item_id: int) -> Dict[str, Any]:
    """
    Embed a single item (source, note, or insight)
    """
    start_time = time.time()
    try:
        logger.info(f"Starting embedding for {item_type} with ID: {item_id}")
        
        if item_type == "source":
            item = await Source.get(item_id)
            if not item:
                raise ValueError(f"Source with ID {item_id} not found")
            await item.vectorize()
        elif item_type == "note":
            item = await Note.get(item_id)
            if not item:
                raise ValueError(f"Note with ID {item_id} not found")
            await item.save()  # Auto-embeds if needed
        elif item_type == "insight":
            item = await SourceInsight.get(item_id)
            if not item:
                raise ValueError(f"Insight with ID {item_id} not found")
            await item.save()  # Auto-embeds if needed
        else:
            raise ValueError(f"Unknown item type: {item_type}")
        
        processing_time = time.time() - start_time
        logger.info(f"Successfully embedded {item_type} {item_id} in {processing_time:.2f}s")
        
        return {
            "success": True,
            "item_type": item_type,
            "item_id": item_id,
            "processing_time": processing_time,
        }
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed to embed {item_type} {item_id}: {e}")
        return {
            "success": False,
            "item_type": item_type,
            "item_id": item_id,
            "processing_time": processing_time,
            "error_message": str(e),
        }


async def collect_items_for_rebuild(
    mode: str,
    include_sources: bool,
    include_notes: bool,
    include_insights: bool,
) -> Dict[str, List[int]]:
    """
    Collect items to rebuild based on mode and include flags.
    """
    items: Dict[str, List[int]] = {"sources": [], "notes": [], "insights": []}

    if include_sources:
        # Assuming all sources with text should be processed.
        result = await repo_query("source", select="id", filters={"full_text:not.is": "null"})
        items["sources"] = [item["id"] for item in result] if result else []
        logger.info(f"Collected {len(items['sources'])} sources for rebuild")

    if include_notes:
        # Assuming all notes with content should be processed.
        result = await repo_query("note", select="id", filters={"content:not.is": "null"})
        items["notes"] = [item["id"] for item in result] if result else []
        logger.info(f"Collected {len(items['notes'])} notes for rebuild")

    if include_insights:
        # Assuming all insights should be processed.
        result = await repo_query("source_insight", select="id")
        items["insights"] = [item["id"] for item in result] if result else []
        logger.info(f"Collected {len(items['insights'])} insights for rebuild")

    return items


async def rebuild_embeddings_command(
    mode: Literal["existing", "all"],
    include_sources: bool = True,
    include_notes: bool = True,
    include_insights: bool = True,
) -> Dict:
    """
    Rebuild embeddings for sources, notes, and/or insights
    """
    start_time = time.time()

    try:
        logger.info("=" * 60)
        logger.info(f"Starting embedding rebuild with mode={mode}")
        logger.info(
            f"Include: sources={include_sources}, notes={include_notes}, insights={include_insights}"
        )
        logger.info("=" * 60)

        EMBEDDING_MODEL = await model_manager.get_embedding_model()
        if not EMBEDDING_MODEL:
            raise ValueError("No embedding model configured.")

        logger.info(f"Using embedding model: {EMBEDDING_MODEL}")

        items = await collect_items_for_rebuild(
            mode,
            include_sources,
            include_notes,
            include_insights,
        )

        total_items = (
            len(items["sources"]) + len(items["notes"]) + len(items["insights"])
        )
        logger.info(f"Total items to process: {total_items}")

        if total_items == 0:
            logger.warning("No items found to rebuild")
            return {
                "success": True,
                "total_items": 0,
                "processed_items": 0,
                "failed_items": 0,
                "processing_time": time.time() - start_time,
            }

        sources_processed, notes_processed, insights_processed, failed_items = 0, 0, 0, 0

        logger.info(f"\nProcessing {len(items['sources'])} sources...")
        for idx, source_id in enumerate(items["sources"], 1):
            try:
                source = await Source.get(source_id)
                if not source:
                    logger.warning(f"Source {source_id} not found, skipping")
                    failed_items += 1
                    continue
                await source.vectorize()
                sources_processed += 1
                if idx % 10 == 0 or idx == len(items["sources"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['sources'])} sources processed"
                    )
            except Exception as e:
                logger.error(f"Failed to re-embed source {source_id}: {e}")
                failed_items += 1

        logger.info(f"\nProcessing {len(items['notes'])} notes...")
        for idx, note_id in enumerate(items["notes"], 1):
            try:
                note = await Note.get(note_id)
                if not note:
                    logger.warning(f"Note {note_id} not found, skipping")
                    failed_items += 1
                    continue
                await note.save()  # Auto-embeds
                notes_processed += 1
                if idx % 10 == 0 or idx == len(items["notes"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['notes'])} notes processed"
                    )
            except Exception as e:
                logger.error(f"Failed to re-embed note {note_id}: {e}")
                failed_items += 1

        logger.info(f"\nProcessing {len(items['insights'])} insights...")
        for idx, insight_id in enumerate(items["insights"], 1):
            try:
                insight = await SourceInsight.get(insight_id)
                if not insight:
                    logger.warning(f"Insight {insight_id} not found, skipping")
                    failed_items += 1
                    continue
                await insight.save() # Auto-embeds
                insights_processed += 1
                if idx % 10 == 0 or idx == len(items["insights"]):
                    logger.info(
                        f"  Progress: {idx}/{len(items['insights'])} insights processed"
                    )
            except Exception as e:
                logger.error(f"Failed to re-embed insight {insight_id}: {e}")
                failed_items += 1

        processing_time = time.time() - start_time
        processed_items = sources_processed + notes_processed + insights_processed

        logger.info("=" * 60)
        logger.info("REBUILD COMPLETE")
        # ... logging ...
        logger.info("=" * 60)

        return {
            "success": True,
            "total_items": total_items,
            "processed_items": processed_items,
            "failed_items": failed_items,
            "processing_time": processing_time,
        }

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Rebuild embeddings failed: {e}")
        return {
            "success": False,
            "total_items": 0,
            "processed_items": 0,
            "failed_items": 0,
            "processing_time": processing_time,
            "error_message": str(e),
        }
