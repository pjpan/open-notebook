from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar, cast

from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_validator,
    model_validator,
)

from open_notebook.database.repository import (
    repo_create,
    repo_delete,
    repo_delete_int_id,
    repo_query,
    repo_relate,
    repo_relate_int_ids,
    repo_update,
    repo_update_int_id,
    repo_upsert,
)
from open_notebook.exceptions import (
    DatabaseOperationError,
    InvalidInputError,
    NotFoundError,
)

T = TypeVar("T", bound="ObjectModel")


class ObjectModel(BaseModel):
    id: Optional[int] = None
    table_name: ClassVar[str] = ""
    nullable_fields: ClassVar['set[str]'] = set()  # Fields that can be saved as None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    @classmethod
    async def get_all(cls: Type[T], order_by=None) -> List[T]:
        try:
            if not cls.table_name:
                raise InvalidInputError(
                    "get_all() must be called from a specific model class"
                )
            
            # Note: order_by is not directly supported in the new repo_query,
            # would need to be added if required.
            result = await repo_query(cls.table_name)
            objects = [cls(**obj) for obj in result]
            return objects
        except Exception as e:
            logger.error(f"Error fetching all {cls.table_name}: {str(e)}")
            raise DatabaseOperationError(e)

    @classmethod
    async def get(cls: Type[T], id: int) -> T:
        if not id:
            raise InvalidInputError("ID cannot be empty")
        try:
            if not cls.table_name:
                raise InvalidInputError(
                    "get() must be called from a specific model class"
                )

            result = await repo_query(cls.table_name, filters={"id": id})
            if result:
                return cls(**result[0])
            else:
                raise NotFoundError(f"{cls.table_name} with id {id} not found")
        except Exception as e:
            logger.error(f"Error fetching object with id {id}: {str(e)}")
            raise NotFoundError(f"Object with id {id} not found - {str(e)}")

    def needs_embedding(self) -> bool:
        return False

    def get_embedding_content(self) -> Optional[str]:
        return None

    async def save(self) -> None:
        from open_notebook.ai.models import model_manager

        try:
            self.model_validate(self.model_dump(), strict=True)
            data = self._prepare_save_data()
            
            if self.needs_embedding():
                embedding_content = self.get_embedding_content()
                if embedding_content:
                    EMBEDDING_MODEL = await model_manager.get_embedding_model()
                    if not EMBEDDING_MODEL:
                        logger.warning(
                            "No embedding model found. Content will not be searchable."
                        )
                    else:
                        # Generate embedding for the content
                        embedding = (await EMBEDDING_MODEL.aembed([embedding_content]))[0]
                        # Store the embedding in the data to be saved
                        data["embedding"] = embedding

            if self.id is None:
                repo_result = await repo_create(self.__class__.table_name, data)
            else:
                # Using the integer ID version of the update function
                repo_result_list = await repo_update_int_id(
                    self.__class__.table_name, self.id, data
                )
                repo_result = repo_result_list[0] if repo_result_list else None

            if repo_result:
                for key, value in repo_result.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

        except ValidationError as e:
            logger.error(f"Validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving record: {e}")
            raise DatabaseOperationError(e)

    def _prepare_save_data(self) -> Dict[str, Any]:
        data = self.model_dump(exclude={"id", "created", "updated"})
        return {
            key: value
            for key, value in data.items()
            if value is not None or key in self.__class__.nullable_fields
        }

    async def delete(self) -> bool:
        if self.id is None:
            raise InvalidInputError("Cannot delete object without an ID")
        try:
            logger.debug(f"Deleting record with id {self.id}")
            await repo_delete_int_id(self.table_name, self.id)
            return True
        except Exception as e:
            logger.error(
                f"Error deleting {self.__class__.table_name} with id {self.id}: {str(e)}"
            )
            raise DatabaseOperationError(
                f"Failed to delete {self.__class__.table_name}"
            )

    async def relate(
        self, relationship: str, target_table: str, target_id: int, data: Optional['Dict'] = {}
    ) -> Any:
        if not relationship or not target_id or not self.id:
            raise InvalidInputError("Relationship and target ID must be provided")
        try:
            return await repo_relate_int_ids(
                from_table=self.table_name,
                from_id=self.id,
                relationship=relationship,
                to_table=target_table,
                to_id=target_id,
                data=data,
            )
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            raise DatabaseOperationError(e)

    @field_validator("created", "updated", mode="before")
    @classmethod
    def parse_datetime(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value


class RecordModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
        extra="allow",
        from_attributes=True,
    )

    record_id: ClassVar[str]
    _instances: ClassVar[Dict[str, "RecordModel"]] = {}

    def __new__(cls, **kwargs):
        if cls.record_id in cls._instances:
            instance = cls._instances[cls.record_id]
            if kwargs:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
            return instance
        instance = super().__new__(cls)
        cls._instances[cls.record_id] = instance
        return instance

    async def _load_from_db(self):
        result = await repo_query(self.table_name, filters={"id": self.record_id})
        if result:
            for key, value in result[0].items():
                if hasattr(self, key):
                    setattr(self, key, value)

    @classmethod
    async def get_instance(cls) -> "RecordModel":
        instance = cls()
        await instance._load_from_db()
        return instance

    async def update(self):
        data = self.model_dump()
        await repo_upsert(
            self.table_name,
            "id",
            data,
        )
        await self._load_from_db()
        return self

    @classmethod
    def clear_instance(cls):
        if cls.record_id in cls._instances:
            del cls._instances[cls.record_id]

    async def patch(self, model_dict: dict):
        for key, value in model_dict.items():
            setattr(self, key, value)
        await self.update()
