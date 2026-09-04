from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.auth_router import login_router
from database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando Server")
    yield
    await engine.dispose()
    print("Apagando Server")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["127.0.0.1"],
)

app.include_router(login_router, prefix="/login", tags=["login"])