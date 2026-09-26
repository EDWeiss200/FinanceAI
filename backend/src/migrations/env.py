from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER
from models.models import Base

# Объект конфигурации Alembic
config = context.config
section = config.config_ini_section

# Передаем параметры подключения из config.py в конфигурацию Alembic
config.set_section_option(section, "DB_HOST", str(DB_HOST))
config.set_section_option(section, "DB_USER", str(DB_USER))
config.set_section_option(section, "DB_PASS", str(DB_PASS))
config.set_section_option(section, "DB_NAME", str(DB_NAME))
config.set_section_option(section, "DB_PORT", str(DB_PORT))

# Формируем синхронный URL для psycopg2 драйвера
sync_db_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
config.set_main_option("sqlalchemy.url", sync_db_url)

# Настройка логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метаданные моделей для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн-режиме (генерация SQL-скрипта)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в онлайн-режиме с реальным подключением к БД."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
