"""Compatibility layer providing zero-dependency BaseModel and Field for Python 3.12+.

Seamlessly uses pydantic if installed, or falls back to a clean Python object model.
Ensures Phase 0 & Phase 1 execute hermetically on clean Python 3.12 systems.
"""

from collections.abc import Callable
import copy
from dataclasses import field
import json
from typing import Any

try:
    from pydantic import BaseModel as _PydanticBaseModel
    from pydantic import Field as _PydanticField
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


if HAS_PYDANTIC:
    BaseModel = _PydanticBaseModel
    Field = _PydanticField
else:
    class _FieldInfo:
        def __init__(
            self,
            default: Any = ...,
            default_factory: Callable[[], Any] | None = None,
            description: str | None = None,
        ) -> None:
            self.default = default
            self.default_factory = default_factory
            self.description = description

    def Field(
        default: Any = ...,
        *,
        default_factory: Callable[[], Any] | None = None,
        ge: float | None = None,
        le: float | None = None,
        description: str | None = None,
    ) -> Any:
        """Lightweight field metadata definition."""
        return _FieldInfo(default=default, default_factory=default_factory, description=description)

    class BaseModel:
        """Zero-dependency Pydantic-compatible base model."""

        def __init__(self, **kwargs: Any) -> None:
            # 1. Collect all class annotations and default values across MRO
            cls_fields: dict[str, Any] = {}
            for base in reversed(self.__class__.__mro__):
                if hasattr(base, "__annotations__"):
                    for field_name in base.__annotations__:
                        if hasattr(base, field_name):
                            cls_fields[field_name] = getattr(base, field_name)
                        else:
                            cls_fields[field_name] = ...

            # 2. Populate instance attributes
            for name, val in cls_fields.items():
                if name in kwargs:
                    setattr(self, name, kwargs[name])
                elif isinstance(val, _FieldInfo):
                    if val.default_factory is not None:
                        setattr(self, name, val.default_factory())
                    elif val.default is not ...:
                        setattr(self, name, copy.deepcopy(val.default))
                    else:
                        setattr(self, name, None)
                elif val is not ...:
                    setattr(self, name, copy.deepcopy(val))
                else:
                    setattr(self, name, None)

            # 3. Set any extra kwargs provided
            for k, v in kwargs.items():
                if k not in cls_fields:
                    setattr(self, k, v)

        def model_dump(self) -> dict[str, Any]:
            """Serialize model attributes to dictionary."""
            result: dict[str, Any] = {}
            for k, v in self.__dict__.items():
                if k.startswith("_"):
                    continue
                if isinstance(v, BaseModel):
                    result[k] = v.model_dump()
                elif isinstance(v, list):
                    result[k] = [item.model_dump() if isinstance(item, BaseModel) else item for item in v]
                elif isinstance(v, dict):
                    result[k] = {dk: dv.model_dump() if isinstance(dv, BaseModel) else dv for dk, dv in v.items()}
                else:
                    result[k] = v
            return result

        def model_dump_json(self) -> str:
            """Serialize model to JSON string."""
            return json.dumps(self.model_dump(), default=str)

        def model_copy(self, update: dict[str, Any] | None = None) -> Any:
            """Return a shallow copy of the model with optional updates."""
            obj_copy = copy.copy(self)
            if update:
                for k, v in update.items():
                    setattr(obj_copy, k, v)
            return obj_copy

        def __repr__(self) -> str:
            fields_str = ", ".join(f"{k}={v!r}" for k, v in self.model_dump().items())
            return f"{self.__class__.__name__}({fields_str})"


__all__ = ["BaseModel", "Field", "HAS_PYDANTIC"]
