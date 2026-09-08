from fastapi import FastAPI
from contextlib import asynccontextmanager
from exception_handler import register_exception_handlers, register_middlewares
from fastapi.middleware.cors import CORSMiddleware
from routers import login_router, status_router, trades_router
from database import engine
from config import setup_logging

setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando Server")
    yield
    await engine.dispose()
    print("Apagando Server")

app = FastAPI(
    lifespan=lifespan,
    docs_url="",
    openapi_url=""
    )

register_exception_handlers(app)
register_middlewares(app)    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bncapibot.duckdns.org"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(login_router, prefix="/login", tags=["login"])
app.include_router(status_router, prefix="/status", tags=["status"])
app.include_router(trades_router, prefix="/trades", tags=["trades"])