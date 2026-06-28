"""Optional FastAPI router for the workspace code-request queue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .workspace_code_request_queue import (
    create_code_request,
    list_code_requests,
    read_code_request,
    update_code_request_status,
)

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore[assignment]
    HTTPException = None  # type: ignore[assignment]
    BaseModel = object  # type: ignore[assignment]

    def Field(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return kwargs.get("default")


if APIRouter is not None:
    class CodeRequestCreate(BaseModel):
        title: str = Field(default="code_request", min_length=1, max_length=120)
        prompt: str = Field(min_length=1)
        metadata: dict[str, Any] = Field(default_factory=dict)


def build_workspace_code_request_router(queue_dir: Path | str):
    """Build a FastAPI router for local code-work requests."""
    if APIRouter is None or HTTPException is None:
        raise RuntimeError("FastAPI is not installed; use the core queue helpers directly.")

    router = APIRouter(prefix="/api/workspace/code-requests", tags=["workspace-code-requests"])

    @router.post("")
    def create_request(payload: CodeRequestCreate):
        return create_code_request(
            prompt=payload.prompt,
            title=payload.title,
            queue_dir=queue_dir,
            metadata=payload.metadata,
        )

    @router.get("")
    def list_requests(status: str | None = None, limit: int = 50):
        return {"requests": list_code_requests(queue_dir=queue_dir, status=status, limit=limit)}

    @router.get("/{request_id}")
    def get_request(request_id: str):
        try:
            return read_code_request(request_id, queue_dir=queue_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/{request_id}/status/{status}")
    def set_status(request_id: str, status: str):
        try:
            return update_code_request_status(request_id, status, queue_dir=queue_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
