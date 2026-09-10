import uuid
import logging
import traceback
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import LOG_ERROR

logger = logging.getLogger(__name__)


def formato_error(request: Request, codigo: int, mensaje: str):
    return {
        "detail": {"msg": mensaje},
        "code": codigo,
        "correlation_id": getattr(request.state, "correlation_id", None),
    }


def register_middlewares(app: FastAPI):
    @app.middleware("http")
    async def agregar_correlation_id(request: Request, call_next):
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["x-correlation-id"] = correlation_id
        return response


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        cid = getattr(request.state, "correlation_id", None)
        if exc.status_code >= 500:
            logger.error(f"[{cid}] {request.method} {request.url} → HTTP {exc.status_code}: {exc.detail}")
        content = exc.detail if isinstance(exc.detail, dict) else {"msg": exc.detail}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": content, "correlation_id": cid},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        cid = getattr(request.state, "correlation_id", None)
        logger.error(f"[{cid}] Validation fallida: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content=formato_error(request, 422, "Datos invalidos"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        cid = getattr(request.state, "correlation_id", None)
        logger.critical(f"[{cid}] {request.method} {request.url}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content=formato_error(request, 500, "Error interno del servidor"),
        )