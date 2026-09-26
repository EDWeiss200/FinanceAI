from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from auth.auth import auth_backend, bearer_backend, fastapi_users
from auth.schemas import UserCreate, UserRead
from api.user_router import router as user_router
from database.database import engine
from models.models import Base



app = FastAPI(
    title="Finance AI Assistant — Умный финансовый помощник",
    description=(
        "MVP бэкенда для финансового ассистента. Включает авторизацию с автогенерацией "
        "финансовой песочницы (транзакции доходов и расходов), работу с целями и "
        "ИИ-консультанта с механизмом Tool Calling для точных математических расчетов бюджета."
    ),
    version="1.0.0",
)

# Разрешенные источники для CORS (поддержка локальной разработки и фронтенда)
origins = [
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1",
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:3000",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Сервисные"])
async def root():
    """Корневой эндпоинт для проверки статуса сервиса."""
    return {
        "status": "online",
        "service": "Finance AI Assistant MVP",
        "docs_url": "/docs",
        "message": "Сервер работает корректно",
    }


# Роутер авторизации через Cookie (удобно для браузера)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["Авторизация"],
)

# Роутер авторизации через Bearer Token (удобно для фронтенда и мобильных клиентов)
app.include_router(
    fastapi_users.get_auth_router(bearer_backend),
    prefix="/auth/bearer",
    tags=["Авторизация"],
)

# Роутер регистрации новых пользователей
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Авторизация"],
)

# Роутер пользователей, транзакций и финансового ИИ-советника
app.include_router(user_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)