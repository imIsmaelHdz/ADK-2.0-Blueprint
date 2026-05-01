import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from travel_helper_api.app.api.v1.chat import router as chat_router
from travel_helper_api.app.core.config import API_TITLE, API_VERSION

logger = logging.getLogger("travel_helper_api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("FastAPI gateway started with in-memory sessions.")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=API_TITLE,
        version=API_VERSION,
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(chat_router)
    return app


app = create_app()
