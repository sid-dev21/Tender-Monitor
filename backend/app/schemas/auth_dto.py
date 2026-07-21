"""Request/response schemas for authentication."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import User


def _validate_password_strength(value: str) -> str:
    """Shared rule: at least one letter and one digit (min/max length via Field)."""
    if not any(c.isdigit() for c in value) or not any(c.isalpha() for c in value):
        raise ValueError("password must contain both letters and digits")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("password")
    @classmethod
    def _strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strength(cls, value: str) -> str:
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    company_profile: str | None
    keywords: list[str]
    notification_emails: list[EmailStr]
    is_active: bool

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(
            id=str(user.id),
            email=user.email,
            company_profile=user.company_profile,
            keywords=user.keywords,
            notification_emails=user.notification_emails,
            is_active=user.is_active,
        )


class CompanyProfileUpdate(BaseModel):
    company_profile: str = Field(default="", max_length=2000)
