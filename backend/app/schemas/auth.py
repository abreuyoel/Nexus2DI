from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginMercaderistaRequest(BaseModel):
    cedula: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    username: str
    user_id: int


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ConfirmResetPasswordRequest(BaseModel):
    code: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
