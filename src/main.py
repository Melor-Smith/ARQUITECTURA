"""Punto de entrada ASGI: ``uvicorn src.main:app``."""

from src.adapters.inbound.http.app import crear_app

app = crear_app()
