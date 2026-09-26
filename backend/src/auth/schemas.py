from pydantic import EmailStr
from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """Схема чтения данных пользователя для fastapi-users."""
    id: int 
    username: str
    email: EmailStr
    balance: float = 0.0
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False


class UserCreate(schemas.BaseUserCreate):
    """Схема регистрации нового пользователя."""
    email: EmailStr
    password: str
    username: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False


class UserUpdate(schemas.BaseUserUpdate):
    """Схема обновления данных пользователя."""
    username: Optional[str] = None
    balance: Optional[float] = None