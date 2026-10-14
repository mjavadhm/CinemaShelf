"""FastAPI HTTP endpoints for the metadata module."""
from fastapi import APIRouter

router = APIRouter(prefix="/metadata", tags=["metadata"])
