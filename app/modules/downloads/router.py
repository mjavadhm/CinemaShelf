"""FastAPI HTTP endpoints for the downloads module."""
from fastapi import APIRouter

router = APIRouter(prefix="/downloads", tags=["downloads"])
