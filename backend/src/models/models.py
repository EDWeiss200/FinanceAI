from datetime import datetime, date
from typing import Annotated, Optional, List
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Float, DateTime, Date, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from fastapi_users.db import SQLAlchemyBaseUserTable

# Общие метаданные для таблиц и миграций Alembic
metadata = MetaData()


class Base(DeclarativeBase):
    """Базовый декларативный класс для моделей SQLAlchemy."""
    metadata = metadata


# Аннотация для первичного целочисленного ключа с автоинкрементом
intpk = Annotated[int, mapped_column(Integer, primary_key=True, index=True)]


class TransactionType(str, Enum):
    """Перечисление типов транзакций: доход или расход."""
    INCOME = "income"
    EXPENSE = "expense"


class User(SQLAlchemyBaseUserTable[int], Base):
    """
    Модель пользователя в системе.
    Расширяет стандартную таблицу fastapi-users полем баланса и связями.
    """
    __tablename__ = "users"

    id: Mapped[intpk] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(length=100), nullable=False)
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Текущий баланс пользователя (в рублях)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Связи один-ко-многим с каскадным удалением
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    goals: Mapped[List["Goal"]] = relationship(
        "Goal",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def to_read_model(self):
        """Преобразование модели пользователя в Pydantic схему."""
        from schemas.schemas import UserReadSchema
        return UserReadSchema(
            id=self.id,
            username=self.username,
            email=self.email,
            balance=self.balance
        )


class Transaction(Base):
    """
    Модель финансовых транзакций пользователя.
    Хранит как доходы (стипендия, зарплата), так и расходы по категориям.
    """
    __tablename__ = "transactions"

    id: Mapped[intpk] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Сумма транзакции (всегда положительное число)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    # Тип операции: income (доход) или expense (расход)
    type: Mapped[str] = mapped_column(
        String(length=20),
        nullable=False,
        default=TransactionType.EXPENSE.value
    )
    # Категория (например: Продукты, Кафе, Стипендия, Подписки, Транспорт)
    category: Mapped[str] = mapped_column(String(length=100), nullable=False, index=True)
    # Описание транзакции (комментарий, торговая точка)
    description: Mapped[Optional[str]] = mapped_column(String(length=255), nullable=True)
    # Дата и время проведения операции
    transaction_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )

    # Обратная связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="transactions")

    def to_read_model(self):
        """Преобразование транзакции в Pydantic схему."""
        from schemas.schemas import TransactionReadSchema
        return TransactionReadSchema(
            id=self.id,
            user_id=self.user_id,
            amount=self.amount,
            type=self.type,
            category=self.category,
            description=self.description,
            transaction_date=self.transaction_date
        )


class Goal(Base):
    """
    Модель финансовых целей пользователя.
    Используется для постановки и отслеживания прогресса накоплений.
    """
    __tablename__ = "goals"

    id: Mapped[intpk] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Название цели (например: "Новый ноутбук для учебы", "Подушка безопасности")
    title: Mapped[str] = mapped_column(String(length=255), nullable=False)
    # Необходимая сумма для накопления (в рублях)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    # Уже накопленная сумма
    current_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # Желаемая дата достижения цели
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Дата создания цели
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        nullable=False
    )

    # Обратная связь с пользователем
    user: Mapped["User"] = relationship("User", back_populates="goals")

    def to_read_model(self):
        """Преобразование цели в Pydantic схему."""
        from schemas.schemas import GoalReadSchema
        return GoalReadSchema(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            target_amount=self.target_amount,
            current_amount=self.current_amount,
            deadline=self.deadline,
            created_at=self.created_at
        )
