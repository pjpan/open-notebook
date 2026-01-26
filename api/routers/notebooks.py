from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models import NotebookCreate, NotebookResponse, NotebookUpdate
from open_notebook.database.repository import repo_count, repo_relate, repo_unrelate
from open_notebook.domain.notebook import Notebook, Source
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


@router.get("/notebooks", response_model=List[NotebookResponse])
async def get_notebooks(
    archived: Optional[bool] = Query(None, description="Filter by archived status"),
):
    """Get all notebooks with optional filtering."""
    try:
        filters = {}
        if archived is not None:
            filters["archived"] = archived

        # Call the new efficient method
        notebooks_with_counts = await Notebook.get_all_with_counts(filters=filters)

        # Map the results to the response model
        response = [
            NotebookResponse(
                id=nb["id"],
                name=nb["name"],
                description=nb["description"],
                archived=nb["archived"],
                created=str(nb["created"]),
                updated=str(nb["updated"]),
                source_count=nb["source_count"],
                note_count=nb["note_count"],
            )
            for nb in notebooks_with_counts
        ]
        return response
    except Exception as e:
        logger.error(f"Error fetching notebooks: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching notebooks")


@router.post("/notebooks", response_model=NotebookResponse)
async def create_notebook(notebook: NotebookCreate):
    """Create a new notebook."""
    try:
        new_notebook = Notebook(name=notebook.name, description=notebook.description)
        await new_notebook.save()
        if new_notebook.id is None:
            raise HTTPException(status_code=500, detail="Failed to create notebook")

        return NotebookResponse(
            id=new_notebook.id,
            name=new_notebook.name,
            description=new_notebook.description,
            archived=new_notebook.archived or False,
            created=str(new_notebook.created),
            updated=str(new_notebook.updated),
            source_count=0,
            note_count=0,
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating notebook: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating notebook")


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(notebook_id: int):
    """Get a specific notebook by ID."""
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        source_count = await repo_count("source", filters={"notebook_id": notebook.id})
        note_count = await repo_count("note", filters={"notebook_id": notebook.id})

        return NotebookResponse(
            id=notebook.id,
            name=notebook.name,
            description=notebook.description,
            archived=notebook.archived,
            created=str(notebook.created),
            updated=str(notebook.updated),
            source_count=source_count,
            note_count=note_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching notebook")


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(notebook_id: int, notebook_update: NotebookUpdate):
    """Update a notebook."""
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")

        update_data = notebook_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(notebook, key, value)
        
        await notebook.save()

        return await get_notebook(notebook_id)
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating notebook")


@router.post("/notebooks/{notebook_id}/sources/{source_id}")
async def add_source_to_notebook(notebook_id: int, source_id: int):
    """Add an existing source to a notebook."""
    try:
        await repo_relate("notebook", notebook_id, "reference", "source", source_id)
        return {"message": "Source linked to notebook successfully"}
    except Exception as e:
        logger.error(f"Error linking source {source_id} to notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error linking source to notebook")


@router.delete("/notebooks/{notebook_id}/sources/{source_id}")
async def remove_source_from_notebook(notebook_id: int, source_id: int):
    """Remove a source from a notebook."""
    try:
        await repo_unrelate("notebook", notebook_id, "reference", "source", source_id)
        return {"message": "Source removed from notebook successfully"}
    except Exception as e:
        logger.error(f"Error removing source {source_id} from notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error removing source from notebook")


@router.delete("/notebooks/{notebook_id}")
async def delete_notebook(notebook_id: int):
    """Delete a notebook."""
    try:
        notebook = await Notebook.get(notebook_id)
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        await notebook.delete()
        return {"message": "Notebook deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notebook {notebook_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting notebook")
