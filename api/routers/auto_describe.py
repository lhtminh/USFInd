"""Vision auto-description endpoint — calls the LLM with the uploaded image."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.deps import require_user
from app.core import auto_description
from app.core.db import User

router = APIRouter(prefix="/api", tags=["auto_describe"])


@router.post("/auto-describe")
async def describe_upload(
    photo: UploadFile = File(...),
    user: User = Depends(require_user),
) -> dict:
    """Generate a short factual description of the uploaded image."""
    data = await photo.read()
    try:
        description = auto_description.auto_describe(data)
    except auto_description.AutoDescriptionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}") from exc
    return {"description": description, "user_id": str(user.id)}
