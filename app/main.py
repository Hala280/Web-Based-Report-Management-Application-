"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.core.errors import register_exception_handlers
from app.core.logging_config import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Report Management Platform")

register_exception_handlers(app)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe endpoint."""
    return {"status": "ok"}
