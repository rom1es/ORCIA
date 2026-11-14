"""Schemas for Password Lifecycle & IAM Temporary Credentials (`Story 17.6`, `AD-6`).

Carries models for password change, password reset, and temporary credential provisioning.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChangePasswordRequest(BaseModel):
    """Request payload for `POST /api/v1/auth/change-password`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=1, max_length=256)


class ChangePasswordResponse(BaseModel):
    """Response payload for `POST /api/v1/auth/change-password`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    success: bool = True
    email: str = Field(..., min_length=3, max_length=255)
    must_change_password: bool = False
    trace_id: str = Field(..., min_length=32, max_length=32)


class TemporaryPasswordProvisionResponse(BaseModel):
    """Response payload for temporary password generation/reset on IAM accounts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str = Field(..., min_length=1, max_length=64)
    principal_id: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=160)
    temporary_password: str = Field(..., min_length=12, max_length=128)  # pragma: allowlist secret
    must_change_password: bool = True
    trace_id: str = Field(..., min_length=32, max_length=32)
