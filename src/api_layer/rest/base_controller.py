"""Standardized API Response Schemas and Base Controller Contract."""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard envelope format for all HTTP REST responses."""
    success: bool
    data: Optional[T] = None
    error_code: Optional[str] = None
    message: Optional[str] = None
