"""Vercel entrypoint for the ReviewDesk FastAPI application."""

from reviewdesk.app import app

__all__ = ["app"]
