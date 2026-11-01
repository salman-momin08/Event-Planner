"""Vercel ASGI entrypoint for the FastAPI backend service."""
from __future__ import annotations

from app.main import create_app

app = create_app()
