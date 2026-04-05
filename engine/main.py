"""Compatibility shim exposing the FastAPI app at engine.main:app."""

from app.main import app

__all__ = ["app"]
