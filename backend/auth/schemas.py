from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, ser_json_timedelta='float')

    id: str
    username: str
    email: str
    role: str
    created_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]


class TokenRefresh(BaseModel):
    refresh_token: str
