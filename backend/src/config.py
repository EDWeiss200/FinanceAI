from dotenv import load_dotenv
import os

load_dotenv()

# Настройки подключения к базе данных PostgreSQL (база financeai)
DB_HOST = os.environ.get("DB_HOST") or "localhost"
DB_USER = os.environ.get("DB_USER") or "postgres"
DB_PASS = os.environ.get("DB_PASS") or "12345"
DB_NAME = os.environ.get("DB_NAME") or "financeai"
DB_PORT = os.environ.get("DB_PORT") or "5432"

# Секретные ключи для аутентификации fastapi-users
SECRET_AUTH = os.environ.get("SECRET_AUTH") or "SUPER_SECRET_AUTH_KEY_FOR_HACKATHON_123"
SECRET_USER_MANAGER = os.environ.get("SECRET_USER_MANAGER") or "SUPER_SECRET_USER_MANAGER_KEY_FOR_HACKATHON_123"

# Строка подключения для асинхронного драйвера asyncpg
DATABASE_URL_CONFIG = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Настройки для подключения к LLM (OpenAI / ProxyAPI)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("PROXY_API_KEY") or ""
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL") or "https://api.proxyapi.ru/openai/v1"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

# CORS настройки для фронтенда
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS") or "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_RAW.split(",") if origin.strip()]