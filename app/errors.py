from __future__ import annotations

from fastapi import HTTPException


def raise_http_exception(exc: Exception, *, status_code: int = 500, code: str = "internal_error") -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": str(exc)}) from exc


def packet_error_payload(exc: Exception) -> dict:
    return {"error": exc.__class__.__name__.lower(), "message": "internal service error"}
