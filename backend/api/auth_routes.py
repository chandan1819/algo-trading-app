"""Authentication API routes."""

from __future__ import annotations
from typing import Optional

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.smartapi_auth import SmartAPIAuth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

auth_service = SmartAPIAuth()


class LoginRequest(BaseModel):
    client_id: str
    password: str
    totp: str


class LoginResponse(BaseModel):
    status: str
    message: str
    client_id: str


class StatusResponse(BaseModel):
    logged_in: bool
    client_id: Optional[str] = None
    session_age_seconds: Optional[float] = None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login with SmartAPI credentials."""
    try:
        auth_service.login()
        return LoginResponse(
            status="success",
            message="Login successful",
            client_id=request.client_id,
        )
    except Exception as e:
        logger.error("Login failed: %s", e)
        raise HTTPException(status_code=401, detail=f"Login failed: {e}")


@router.post("/logout")
async def logout():
    """Logout and terminate the current session."""
    try:
        auth_service.logout()
        return {"status": "success", "message": "Logged out successfully"}
    except Exception as e:
        logger.error("Logout error: %s", e)
        raise HTTPException(status_code=500, detail=f"Logout failed: {e}")


@router.get("/status", response_model=StatusResponse)
async def session_status():
    """Check the current session status."""
    import time

    from backend.core.config import settings

    is_valid = auth_service._is_session_valid()
    age = (time.time() - auth_service._login_time) if is_valid else None
    return StatusResponse(
        logged_in=is_valid,
        client_id=settings.ANGEL_CLIENT_ID if is_valid else None,
        session_age_seconds=age,
    )
