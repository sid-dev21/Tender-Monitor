"""Shared annotated field types used across models."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, HttpUrl, TypeAdapter

_http_url_adapter = TypeAdapter(HttpUrl)


def _validate_http_url(value: str) -> str:
    """Validate the string is a real http(s) URL, but return it as a plain str.

    We keep base_url as `str` (not pydantic's HttpUrl) because pymongo stores str
    natively, whereas an HttpUrl object cannot be BSON-encoded.
    """
    _http_url_adapter.validate_python(value)  # raises ValidationError if invalid
    return value.rstrip("/")


# A string guaranteed to be a valid http(s) URL.
HttpUrlStr = Annotated[str, AfterValidator(_validate_http_url)]
