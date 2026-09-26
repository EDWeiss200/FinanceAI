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


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """
    Менеджер пользователей fastapi-users.
    Управляет созданием, аутентификацией и генерацией реалистичной
    финансовой песочницы для студента с подработкой.
    """
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """
        Метод вызывается автоматически сразу после успешной регистрации пользователя.
        Генерирует реалистичный студенческий профиль:
        - Баланс: 4 500 – 14 000 руб. (типичный остаток на карте студента);
        - Доходы: академическая стипендия, смены на подработке, помощь от родителей, кэшбэк;
        - Расходы: столовая вуза, недорогие супермаркеты, студенческий проезд, шаурма/фастфуд,
          печать отчетов по лабам, общежитие, студенческие подписки.
        """
        print(f"Пользователь {user.id} ({user.email}) успешно зарегистрирован. Создаем студенческий профиль...")

        now = datetime.now(timezone.utc)

        # 1. Реалистичный студенческий баланс на дебетовой карте (от 4 500 до 14 500 руб.)
        initial_balance = round(random.uniform(4500.0, 14500.0), 2)

        transactions_to_create: List[Transaction] = []

        # 2. Доходы студента за последний месяц (~25 000 - 36 000 руб. всего)
        # А) Государственная академическая стипендия (10-14 дней назад)
        stipend_date = now - timedelta(days=random.randint(10, 14), hours=random.randint(2, 8))
        stipend_amount = round(random.uniform(2800.0, 4500.0), 2)
        transactions_to_create.append(
            Transaction(
                user_id=user.id,
                amount=stipend_amount,
                type=TransactionType.INCOME.value,
                category="Стипендия",
                description="Академическая стипендия вуза",
                transaction_date=stipend_date,
            )
        )

        # Б) Заработок за подработку (смены бариста, курьер, репетиторство, промоутер)
        job_variants = [
            "Смены бариста в кофейне",
            "Выплаты за курьерские доставки",
            "Подработка: промоутер на выставке",
            "Оплата за репетиторство по математике",
            "Помощник администратора (смены)",
        ]
        salary_date = now - timedelta(days=random.randint(2, 6), hours=random.randint(1, 9))
        salary_amount = round(random.uniform(17000.0, 24000.0), 2)
        transactions_to_create.append(
            Transaction(
                user_id=user.id,
                amount=salary_amount,
                type=TransactionType.INCOME.value,
                category="Подработка и смены",
                description=random.choice(job_variants),
                transaction_date=salary_date,
            )
        )

        # В) Поддержка от родителей / перевод на питание
        parents_date = now - timedelta(days=random.randint(18, 24), hours=random.randint(3, 11))
        parents_amount = round(random.uniform(4000.0, 7000.0), 2)
        transactions_to_create.append(
            Transaction(
                user_id=user.id,
                amount=parents_amount,
                type=TransactionType.INCOME.value,
                category="Помощь от родителей",
                description="Перевод от родителей на питание",
                transaction_date=parents_date,
            )
        )

        # Г) Кэшбэк по молодежной карте банка
        cashback_date = now - timedelta(days=random.randint(1, 4), hours=random.randint(1, 6))
        cashback_amount = round(random.uniform(180.0, 480.0), 2)
        transactions_to_create.append(
            Transaction(
                user_id=user.id,
                amount=cashback_amount,
                type=TransactionType.INCOME.value,
                category="Кэшбэк",
                description="Кэшбэк за покупки в категориях месяца",
                transaction_date=cashback_date,
            )
        )

        # 3. Реалистичные студенческие расходы по категориям
        student_expense_templates = [
            # Столовая вуза и быстрые перекусы на парах
            (
                "Столовая и перекусы",
                [
                    "Обед в столовой: суп и второе",
                    "Сосиска в тесте и чай в буфете",
                    "Кофе из вендингового автомата перед парой",
                    "Сырники со сметаной в буфете",
                    "Сэндвич и морс на перемене",
                ],
                (120.0, 310.0),
                12,
            ),
            # Недорогие супермаркеты у дома (базовые продукты)
            (
                "Супермаркеты (продукты)",
                [
                    "Пятёрочка: макароны, яйца, чай",
                    "Магнит у дома: хлеб и молоко",
                    "Магазин 'Чижик': базовые продукты",
                    "Супермаркет 'Ярче!': творог и овсянка",
                ],
                (220.0, 780.0),
                8,
            ),
            # Студенческий транспорт (льготные поездки и редкое такси)
            (
                "Транспорт",
                [
                    "Студенческий проездной на месяц",
                    "Поездка на автобусе до корпуса",
                    "Метро по карте студента",
                    "Трамвай до общежития",
                    "Поездка на автобусе",
                    "Срочное такси (проспал утреннюю пару)",
                ],
                (38.0, 160.0),
                10,
            ),
            # Студенческий фастфуд и шаурма
            (
                "Фастфуд и шаурма",
                [
                    "Шаурма классическая у универа",
                    "Додо Пицца: кусочек пепперони",
                    "Вкусно и точка: бургер и кола",
                    "Ростикс: перекус с одногруппником",
                ],
                (190.0, 420.0),
                5,
            ),
            # Связь и студенческие подписки
            (
                "Связь и подписки",
                [
                    "Яндекс Плюс (студенческая скидка)",
                    "Мобильный тариф со студенческой скидкой",
                    "Telegram Premium",
                ],
                (99.0, 390.0),
                3,
            ),
            # Учебные расходы (печать, канцтовары)
            (
                "Учеба и печать",
                [
                    "Печать отчета по лабораторной",
                    "Распечатка методички и конспектов",
                    "Тетради и ручки в канцтоварах",
                ],
                (45.0, 230.0),
                3,
            ),
            # Общежитие и бытовые мелочи
            (
                "Общежитие и быт",
                [
                    "Оплата проживания в общежитии за месяц",
                    "Стиральный порошок и хозтовары",
                ],
                (350.0, 1100.0),
                2,
            ),
            # Недорогой досуг с друзьями
            (
                "Досуг с друзьями",
                [
                    "Студенческий билет в кино",
                    "Настольные игры в антикафе",
                    "Кофе навынос на прогулке",
                ],
                (260.0, 680.0),
                3,
            ),
        ]

        # Генерация транзакций со случайными датами за последние 30 дней
        for category, items, (min_p, max_p), count in student_expense_templates:
            for _ in range(count):
                days_ago = random.randint(1, 29)
                hours_ago = random.randint(1, 23)
                minutes_ago = random.randint(1, 59)
                tx_date = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
                desc = random.choice(items)
                cost = round(random.uniform(min_p, max_p), 2)

                transactions_to_create.append(
                    Transaction(
                        user_id=user.id,
                        amount=cost,
                        type=TransactionType.EXPENSE.value,
                        category=category,
                        description=desc,
                        transaction_date=tx_date,
                    )
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
            f"создано {len(transactions_to_create)} реалистичных студенческих транзакций."
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