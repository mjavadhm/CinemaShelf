"""FastAPI HTTP endpoints for the library module."""
from fastapi import APIRouter

router = APIRouter(prefix="/library", tags=["library"])
