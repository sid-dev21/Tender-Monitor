"""Generic repository base: typed CRUD over a MongoDB collection.

Each concrete repository subclasses this, sets `collection_name` and `model`, and
gets insert/find/update/delete for free — all returning validated Pydantic models
instead of raw dicts. Business code never touches pymongo directly.
"""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.models.base import MongoModel, utcnow

T = TypeVar("T", bound=MongoModel)


class BaseRepository(Generic[T]):
    """CRUD operations shared by every collection-backed repository."""

    collection_name: ClassVar[str]
    model: type[T]

    def __init__(self, db: AsyncDatabase) -> None:
        self._db = db
        self.collection: AsyncCollection = db[self.collection_name]

    # --- (de)serialization helpers ---
    def _to_doc(self, model: T) -> dict[str, Any]:
        """Model -> Mongo document. Drops a None _id so Mongo assigns a real one."""
        doc = model.model_dump(by_alias=True)
        if doc.get("_id") is None:
            doc.pop("_id", None)
        return doc

    def _to_model(self, doc: dict[str, Any] | None) -> T | None:
        return self.model.model_validate(doc) if doc is not None else None

    @staticmethod
    def _oid(value: str | ObjectId) -> ObjectId:
        return value if isinstance(value, ObjectId) else ObjectId(value)

    # --- CRUD ---
    async def insert(self, model: T) -> T:
        """Insert a new document; sets and returns the model with its new id."""
        result = await self.collection.insert_one(self._to_doc(model))
        model.id = result.inserted_id
        return model

    async def find_by_id(self, id_: str | ObjectId) -> T | None:
        return self._to_model(await self.collection.find_one({"_id": self._oid(id_)}))

    async def find(
        self,
        filter: dict[str, Any] | None = None,
        *,
        limit: int = 0,
        skip: int = 0,
        sort: list[tuple[str, int]] | None = None,
    ) -> list[T]:
        cursor = self.collection.find(filter or {})
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return [self.model.model_validate(doc) async for doc in cursor]

    async def find_one(self, filter: dict[str, Any]) -> T | None:
        return self._to_model(await self.collection.find_one(filter))

    async def update_by_id(self, id_: str | ObjectId, changes: dict[str, Any]) -> T | None:
        """Apply a $set patch (auto-refreshing updated_at) and return the new doc."""
        patch = {**changes, "updated_at": utcnow()}
        doc = await self.collection.find_one_and_update(
            {"_id": self._oid(id_)},
            {"$set": patch},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_model(doc)

    async def delete_by_id(self, id_: str | ObjectId) -> bool:
        result = await self.collection.delete_one({"_id": self._oid(id_)})
        return result.deleted_count == 1

    async def count(self, filter: dict[str, Any] | None = None) -> int:
        return await self.collection.count_documents(filter or {})
