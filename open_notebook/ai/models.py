from typing import ClassVar, Dict, Optional, Union

from esperanto import (
    AIFactory,
    EmbeddingModel,
    LanguageModel,
    SpeechToTextModel,
    TextToSpeechModel,
)
from loguru import logger

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel, RecordModel

ModelType = Union[LanguageModel, EmbeddingModel, SpeechToTextModel, TextToSpeechModel]


class Model(ObjectModel):
    table_name: ClassVar[str] = "model"
    name: str
    provider: str
    type: str

    @classmethod
    async def get_models_by_type(cls, model_type):
        models = await repo_query("model", filters={"type": model_type})
        return [Model(**model) for model in models]


class DefaultModels(RecordModel):
    table_name: ClassVar[str] = "default_models"
    record_id: ClassVar[str] = "default_models" # This should be the primary key of the single row in the table
    default_chat_model: Optional[int] = None
    default_transformation_model: Optional[int] = None
    large_context_model: Optional[int] = None
    default_text_to_speech_model: Optional[int] = None
    default_speech_to_text_model: Optional[int] = None
    default_embedding_model: Optional[int] = None
    default_tools_model: Optional[int] = None

    @classmethod
    async def get_instance(cls) -> "DefaultModels":
        """Always fetch fresh defaults from database"""
        result = await repo_query(cls.table_name, filters={"id": cls.record_id})

        if result:
            data = result[0]
        else:
            data = {}

        # Create new instance with fresh data
        instance = cls(**data)
        return instance


class ModelManager:
    def __init__(self):
        pass

    async def get_model(self, model_id: int, **kwargs) -> Optional[ModelType]:
        """Get a model by ID."""
        if not model_id:
            return None

        try:
            model: Model = await Model.get(model_id)
        except Exception:
            raise ValueError(f"Model with ID {model_id} not found")

        if not model.type or model.type not in [
            "language",
            "embedding",
            "speech_to_text",
            "text_to_speech",
        ]:
            raise ValueError(f"Invalid model type: {model.type}")

        if model.type == "language":
            return AIFactory.create_language(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        elif model.type == "embedding":
            return AIFactory.create_embedding(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        elif model.type == "speech_to_text":
            return AIFactory.create_speech_to_text(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        elif model.type == "text_to_speech":
            return AIFactory.create_text_to_speech(
                model_name=model.name,
                provider=model.provider,
                config=kwargs,
            )
        else:
            raise ValueError(f"Invalid model type: {model.type}")

    async def get_defaults(self) -> DefaultModels:
        """Get the default models configuration from database"""
        defaults = await DefaultModels.get_instance()
        if not defaults:
            raise RuntimeError("Failed to load default models configuration")
        return defaults

    async def get_speech_to_text(self, **kwargs) -> Optional[SpeechToTextModel]:
        """Get the default speech-to-text model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_speech_to_text_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, SpeechToTextModel), (
            f"Expected SpeechToTextModel but got {type(model)}"
        )
        return model

    async def get_text_to_speech(self, **kwargs) -> Optional[TextToSpeechModel]:
        """Get the default text-to-speech model"""
        defaults = await self.get_defaults()
        model_id = defaults.default_text_to_speech_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, TextToSpeechModel), (
            f"Expected TextToSpeechModel but got {type(model)}"
        )
        return model

    async def get_embedding_model(self, **kwargs) -> Optional[EmbeddingModel]:
        """Get the default embedding model"""
.
        defaults = await self.get_defaults()
        model_id = defaults.default_embedding_model
        if not model_id:
            return None
        model = await self.get_model(model_id, **kwargs)
        assert model is None or isinstance(model, EmbeddingModel), (
            f"Expected EmbeddingModel but got {type(model)}"
        )
        return model

    async def get_default_model(self, model_type: str, **kwargs) -> Optional[ModelType]:
        """
        Get the default model for a specific type.
        """
        defaults = await self.get_defaults()
        model_id = None

        if model_type == "chat":
            model_id = defaults.default_chat_model
        elif model_type == "transformation":
            model_id = (
                defaults.default_transformation_model or defaults.default_chat_model
            )
        elif model_type == "tools":
            model_id = defaults.default_tools_model or defaults.default_chat_model
        elif model_type == "embedding":
            model_id = defaults.default_embedding_model
        elif model_type == "text_to_speech":
            model_id = defaults.default_text_to_speech_model
        elif model_type == "speech_to_text":
            model_id = defaults.default_speech_to_text_model
        elif model_type == "large_context":
            model_id = defaults.large_context_model

        if not model_id:
            return None

        return await self.get_model(model_id, **kwargs)


model_manager = ModelManager()
