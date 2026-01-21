import os
from typing import List, Optional

from esperanto import AIFactory
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from api.models import (
    DefaultModelsResponse,
    ModelCreate,
    ModelResponse,
    ProviderAvailabilityResponse,
)
from open_notebook.ai.models import DefaultModels, Model
from open_notebook.database.repository import repo_query
from open_notebook.exceptions import InvalidInputError

router = APIRouter()


# ... (helper functions _check_openai_compatible_support and _check_azure_support remain the same)


@router.get("/models", response_model=List[ModelResponse])
async def get_models(
    type: Optional[str] = Query(None, description="Filter by model type"),
):
    """Get all configured models with optional type filtering."""
    try:
        if type:
            models = await Model.get_models_by_type(type)
        else:
            models = await Model.get_all()

        return [ModelResponse(**model.model_dump()) for model in models]
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail="Error fetching models")


@router.post("/models", response_model=ModelResponse)
async def create_model(model_data: ModelCreate):
    """Create a new model configuration."""
    try:
        valid_types = ["language", "embedding", "text_to_speech", "speech_to_text"]
        if model_data.type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type. Must be one of: {valid_types}",
            )

        existing = await repo_query(
            "model",
            filters={
                "provider": model_data.provider,
                "name": model_data.name,
                "type": model_data.type,
            },
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_data.name}' already exists for provider '{model_data.provider}'",
            )

        new_model = Model(**model_data.model_dump())
        await new_model.save()

        return ModelResponse(**new_model.model_dump())
    except HTTPException:
        raise
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise HTTPException(status_code=500, detail="Error creating model")


@router.delete("/models/{model_id}")
async def delete_model(model_id: int):
    """Delete a model configuration."""
    try:
        model = await Model.get(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        await model.delete()
        return {"message": "Model deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model {model_id}: {e}")
        raise HTTPException(status_code=500, detail="Error deleting model")


@router.get("/models/defaults", response_model=DefaultModelsResponse)
async def get_default_models():
    """Get default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()
        return DefaultModelsResponse(**defaults.model_dump())
    except Exception as e:
        logger.error(f"Error fetching default models: {e}")
        raise HTTPException(status_code=500, detail="Error fetching default models")


@router.put("/models/defaults", response_model=DefaultModelsResponse)
async def update_default_models(defaults_data: DefaultModelsResponse):
    """Update default model assignments."""
    try:
        defaults = await DefaultModels.get_instance()
        update_data = defaults_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(defaults, key, value)
        await defaults.update()
        return DefaultModelsResponse(**defaults.model_dump())
    except Exception as e:
        logger.error(f"Error updating default models: {e}")
        raise HTTPException(status_code=500, detail="Error updating default models")


@router.get("/models/providers", response_model=ProviderAvailabilityResponse)
async def get_provider_availability():
    """Get provider availability based on environment variables."""
    # ... (this function does not have database interactions and remains the same)
    return ProviderAvailabilityResponse(available=[], unavailable=[], supported_types={})
