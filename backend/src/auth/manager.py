import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin, schemas, models, exceptions
from config import SECRET_USER_MANAGER
from .database import User_Now as User, get_user_db
from database.database import async_session_maker
from models.models import Transaction, TransactionType, User as DBUser


SECRET = SECRET_USER_MANAGER


def generate_student_transactions_for_month(
    user_id: int,
    year: int,
    month: int,
    max_day: Optional[int] = None,
) -> List[Transaction]:
    """
    Генерирует реалистичный набор студенческих доходов и расходов за указанный месяц и год:
    - Сентябрь: учеба, столовая вуза, подработка, стипендия, общежитие, транспорт.
    - Август: летние смены, подготовка к учебе, досуг с друзьями, покупки.
    - Июль: летняя сессия и подработка, отдых, кафе, фастфуд.
    """
    limit_day = max_day if max_day is not None else 28
    created_txs: List[Transaction] = []

    def make_dt(day: int, hour: int = 12, minute: int = 0) -> datetime:
        d = min(max(1, day), limit_day)
        return datetime(year, month, d, hour, minute, tzinfo=timezone.utc)

    # 1. ДОХОДЫ МЕСЯЦА
    # А) Государственная академическая стипендия
    stipend_day = random.randint(10, min(15, limit_day))
    stipend_amount = round(random.uniform(3100.0, 4600.0), 2)
    created_txs.append(
        Transaction(
            user_id=user_id,
            amount=stipend_amount,
            type=TransactionType.INCOME.value,
            category="Стипендия",
            description="Государственная академическая стипендия",
            transaction_date=make_dt(stipend_day, random.randint(9, 14), random.randint(10, 50)),
        )
    )

    # Б) Подработка и смены (летом смен больше и заработок выше)
    job_templates = [
        ("Смены бариста в кофейне", (8500.0, 13000.0)),
        ("Выплаты за курьерские смены", (9000.0, 14000.0)),
        ("Подработка: промоутер на мероприятиях", (6500.0, 11000.0)),
        ("Оплата за репетиторство школьникам", (7000.0, 12000.0)),
    ]
    # Первая выплата в первой половине месяца
    desc1, (min_s1, max_s1) = random.choice(job_templates)
    day_salary1 = random.randint(3, min(8, limit_day))
    created_txs.append(
        Transaction(
            user_id=user_id,
            amount=round(random.uniform(min_s1, max_s1), 2),
            type=TransactionType.INCOME.value,
            category="Подработка и смены",
            description=desc1,
            transaction_date=make_dt(day_salary1, random.randint(14, 19), random.randint(5, 55)),
        )
    )

    # Вторая выплата во второй половине месяца (если месяц позволяет)
    if limit_day >= 18:
        desc2, (min_s2, max_s2) = random.choice(job_templates)
        day_salary2 = random.randint(18, min(25, limit_day))
        created_txs.append(
            Transaction(
                user_id=user_id,
                amount=round(random.uniform(min_s2, max_s2), 2),
                type=TransactionType.INCOME.value,
                category="Подработка и смены",
                description=desc2,
                transaction_date=make_dt(day_salary2, random.randint(15, 20), random.randint(5, 55)),
            )
        )

    # В) Помощь от родителей
    parents_day = random.randint(1, min(6, limit_day))
    parents_amount = round(random.uniform(4000.0, 7500.0), 2)
    created_txs.append(
        Transaction(
            user_id=user_id,
            amount=parents_amount,
            type=TransactionType.INCOME.value,
            category="Помощь от родителей",
            description="Перевод от родителей на питание",
            transaction_date=make_dt(parents_day, random.randint(10, 18), random.randint(10, 45)),
        )
    )

    # Г) Кэшбэк
    if limit_day >= 20:
        cashback_day = random.randint(20, min(27, limit_day))
        cashback_amount = round(random.uniform(210.0, 520.0), 2)
        created_txs.append(
            Transaction(
                user_id=user_id,
                amount=cashback_amount,
                type=TransactionType.INCOME.value,
                category="Кэшбэк",
                description="Кэшбэк за покупки по карте",
                transaction_date=make_dt(cashback_day, 12, 30),
            )
        )

    # 2. РАСХОДЫ МЕСЯЦА
    expense_categories_config = [
        (
            "Столовая и перекусы",
            [
                "Обед в столовой: суп и второе",
                "Сосиска в тесте и чай в буфете",
                "Кофе из вендингового автомата",
                "Сырники со сметаной в буфете",
                "Сэндвич и морс на перемене",
            ],
            (130.0, 330.0),
            random.randint(7, 11),
        ),
        (
            "Супермаркеты (продукты)",
            [
                "Пятёрочка: макароны, яйца, чай",
                "Магнит у дома: хлеб, молоко, сыр",
                "Магазин 'Чижик': базовые продукты",
                "Супермаркет 'Ярче!': творог и овсянка",
                "ВкусВилл: полезный перекус",
            ],
            (230.0, 850.0),
            random.randint(6, 9),
        ),
        (
            "Транспорт",
            [
                "Студенческий проездной на месяц",
                "Поездка на автобусе до учебы",
                "Метро по карте студента",
                "Трамвай до общежития",
                "Поездка на автобусе",
            ],
            (40.0, 180.0),
            random.randint(6, 9),
        ),
        (
            "Фастфуд и шаурма",
            [
                "Шаурма классическая у универа",
                "Додо Пицца: кусочек пепперони",
                "Вкусно и точка: бургер и кола",
                "Ростикс: комбо-обед",
            ],
            (210.0, 460.0),
            random.randint(4, 6),
        ),
        (
            "Связь и подписки",
            [
                "Яндекс Плюс (студенческая скидка)",
                "Мобильный тариф со студенческой скидкой",
                "Telegram Premium",
            ],
            (99.0, 399.0),
            3,
        ),
        (
            "Учеба и печать",
            [
                "Печать отчетов и материалов",
                "Распечатка методички и конспектов",
                "Тетради и ручки в канцтоварах",
            ],
            (50.0, 260.0),
            random.randint(2, 4),
        ),
        (
            "Общежитие и быт",
            [
                "Оплата проживания в общежитии",
                "Стиральный порошок и бытовая химия",
            ],
            (380.0, 1150.0),
            2,
        ),
        (
            "Досуг с друзьями",
            [
                "Билет в кино со студенческой скидкой",
                "Настольные игры в антикафе",
                "Кофе навынос на прогулке",
                "Боулинг с одногруппниками",
            ],
            (280.0, 720.0),
            random.randint(3, 5),
        ),
    ]

    for category, items, (min_p, max_p), count in expense_categories_config:
        for _ in range(count):
            day = random.randint(1, limit_day)
            hour = random.randint(8, 22)
            minute = random.randint(0, 59)
            desc = random.choice(items)
            cost = round(random.uniform(min_p, max_p), 2)

            created_txs.append(
                Transaction(
                    user_id=user_id,
                    amount=cost,
                    type=TransactionType.EXPENSE.value,
                    category=category,
                    description=desc,
                    transaction_date=make_dt(day, hour, minute),
                )
            )

    return created_txs


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """
        Метод вызывается автоматически сразу после успешной регистрации пользователя.
        Генерирует реалистичную историю транзакций за 3 месяца:
        - Июль 2026 (летняя подработка, отдых, базовые расходы);
        - Август 2026 (пик подработок, подготовка к учебному году);
        - Сентябрь 2026 (текущий учебный месяц: стипендия, общежитие, столовая вуза).
        """
        print(f"Пользователь {user.id} ({user.email}) успешно зарегистрирован. Создаем студенческий профиль за 3 месяца...")

        # Реалистичный студенческий баланс на дебетовой карте (от 8 000 до 16 000 руб.)
        initial_balance = round(random.uniform(8000.0, 16000.0), 2)

        transactions_to_create: List[Transaction] = []

        # 1. Июль 2026 (полный месяц, 31 день)
        transactions_to_create.extend(
            generate_student_transactions_for_month(user.id, 2026, 7, max_day=31)
        )

        # 2. Август 2026 (полный месяц, 31 день)
        transactions_to_create.extend(
            generate_student_transactions_for_month(user.id, 2026, 8, max_day=31)
        )

        # 3. Сентябрь 2026 (текущий месяц до 27 числа включительно)
        transactions_to_create.extend(
            generate_student_transactions_for_month(user.id, 2026, 9, max_day=27)
        )

        # 4. Сохранение данных в базу данных PostgreSQL (financeai)
        async with async_session_maker() as session:
            db_user = await session.get(DBUser, user.id)
            if db_user:
                db_user.balance = initial_balance

            session.add_all(transactions_to_create)
            await session.commit()

        print(
            f"Студенческая песочница создана для пользователя ID {user.id}: "
            f"баланс {initial_balance:,.2f} руб., "
            f"создано {len(transactions_to_create)} транзакций за июль, август и сентябрь 2026 г."
        )

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Запрос на сброс пароля для пользователя {user.id}. Токен сброса: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Запрос верификации для пользователя {user.id}. Токен верификации: {token}")

    async def create(
        self,
        user_create: schemas.UC,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> models.UP:
        """
        Создание нового пользователя в базе данных с вызовом обработчика on_after_register.
        """
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)

        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, request)

        return created_user


async def get_user_manager(user_db=Depends(get_user_db)):
    """Фабрика зависимости внедрения UserManager."""
    yield UserManager(user_db)