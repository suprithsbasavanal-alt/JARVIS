"""Standardized API Exception Handler & Middleware."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from src.api_layer.rest.base_controller import APIResponse
from src.shared.exceptions.base import JarvisException, SecurityViolationError, ToolExecutionError
from src.shared.logger.logger import get_logger

logger = get_logger("api_layer.middleware")


async def jarvis_exception_handler(request: Request, exc: JarvisException) -> JSONResponse:
    """Transforms internal Jarvis domain exceptions to APIResponse JSON envelopes."""
    logger.error(f"Domain exception caught [{exc.code}]: {exc.message}")

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, SecurityViolationError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ToolExecutionError):
        status_code = status.HTTP_400_BAD_REQUEST

    response_data = APIResponse[None](
        success=False,
        error_code=exc.code,
        message=exc.message,
        data=None
    )
    return JSONResponse(status_code=status_code, content=response_data.model_dump())
