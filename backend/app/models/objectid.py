"""A reusable Pydantic v2 type that understands MongoDB's ObjectId.

MongoDB stores every document's primary key as a BSON ObjectId. Pydantic v2 does
not know that type out of the box, so we teach it here — once — and reuse the
`PyObjectId` alias everywhere a model needs an ObjectId field.

Behaviour:
- Accepts an existing ObjectId, or a 24-char hex string, and normalizes to ObjectId.
- Serializes to a plain string in JSON mode (API responses).
- Stays a real ObjectId in Python mode (so pymongo stores it natively).
- Advertises itself as a string in the OpenAPI schema (so /docs is correct).
"""

from __future__ import annotations

from typing import Annotated, Any

from bson import ObjectId
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class _ObjectIdAnnotation:
    """Pydantic hooks that turn a bare `ObjectId` into a validated, serializable type."""

    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source: type[Any], _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> ObjectId:
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str) and ObjectId.is_valid(value):
                return ObjectId(value)
            raise ValueError(f"Not a valid ObjectId: {value!r}")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                str, when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # Represent ObjectId as a string in OpenAPI / JSON schema.
        return handler(core_schema.str_schema())


# The alias used across all models, e.g. `id: PyObjectId | None`.
PyObjectId = Annotated[ObjectId, _ObjectIdAnnotation]
