from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes.relay import router
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(router)
