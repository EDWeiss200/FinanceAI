from fastapi_users.authentication import CookieTransport, BearerTransport, AuthenticationBackend, JWTStrategy
from fastapi_users import FastAPIUsers
from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from config import SECRET_AUTH
from .manager import get_user_manager
from .database import User_Now as User


SECRET = SECRET_AUTH


def get_jwt_strategy() -> JWTStrategy:
    """Генерация стратегии JWT с временем жизни токена 24 часа."""
    return JWTStrategy(secret=SECRET, lifetime_seconds=86400)


# Транспорт для cookie (подходит для работы через браузер и локальный Swagger)
cookie_transport = CookieTransport(
    cookie_name="robert-cookie",
    cookie_max_age=86400,
    cookie_secure=False,
    cookie_samesite="lax",
)

# Транспорт для Bearer токена (подходит для мобильных приложений, фронтенда и API-клиентов)
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Бэкенд авторизации по Cookie
auth_backend = AuthenticationBackend(
    name="jwt-cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# Бэкенд авторизации по Bearer Header
bearer_backend = AuthenticationBackend(
    name="jwt-bearer",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# Инициализация FastAPIUsers с поддержкой как Cookie, так и Bearer токенов
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend, bearer_backend],
)

password_hash = PasswordHash((
    Argon2Hasher(),
))
password_helper = PasswordHelper(password_hash)

# Зависимость для получения текущего авторизованного пользователя
current_user = fastapi_users.current_user()
