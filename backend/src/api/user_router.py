from datetime import date, timedelta
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from auth.auth import current_user
from database.database import get_async_session
from models.models import User, Transaction, Goal
from schemas.schemas import (
    UserReadSchema,
    TransactionReadSchema,
    CategorySummaryItem,
    CategoriesSummaryResponse,
    GoalReadSchema,
    GoalCreateSchema,
    AIAdvisorRequest,
    AIAdvisorResponse,
)
from utils.Ai_utils import process_ai_financial_advice


router = APIRouter(
    tags=["Пользователь и Финансовый ИИ"],
    prefix="/users",
)


@router.get("/me", response_model=UserReadSchema, summary="Получить профиль текущего пользователя с балансом")
async def get_current_user_profile(
    user: User = Depends(current_user),
):
    """Возвращает информацию о текущем авторизованном пользователе и его балансе."""
    return UserReadSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        balance=user.balance,
    )


@router.get(
    "/transactions",
    response_model=List[TransactionReadSchema],
    summary="Получить список транзакций (песочница доходов и расходов)",
)
async def get_user_transactions(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    tx_type: Optional[str] = Query(None, description="Фильтр по типу: 'income' или 'expense'"),
):
    """
    Возвращает список всех транзакций пользователя за последний месяц.
    Можно фильтровать по типу: tx_type='income' или tx_type='expense'.
    """
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.transaction_date))
    )
    if tx_type:
        stmt = stmt.where(Transaction.type == tx_type)

    result = await session.execute(stmt)
    transactions = result.scalars().all()
    return transactions


@router.get(
    "/categories",
    response_model=CategoriesSummaryResponse,
    summary="Сводка доходов и расходов по категориям с гибкой сортировкой",
)
@router.get(
    "/analytics/categories",
    response_model=CategoriesSummaryResponse,
    include_in_schema=False,
)
async def get_categories_summary(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
    sort_by: str = Query(
        "amount_desc",
        description=(
            "Сортировка категорий: "
            "'amount_desc' (по убыванию суммы), "
            "'amount_asc' (по возрастанию суммы), "
            "'count_desc' (по числу операций), "
            "'name' (по алфавиту)"
        ),
    ),
    tx_type: Optional[str] = Query(
        None,
        description="Фильтр по типу операций: 'income' (только доходы), 'expense' (только расходы) или None (все)",
    ),
):
    """
    Группирует и сортирует доходы и расходы студента по категориям:
    - Считает общую сумму, количество операций, процент от бюджета и средний чек;
    - Позволяет сортировать категории по объему средств (по убыванию/возрастанию), частоте покупок или алфавиту;
    - Прикрепляет список входящих в каждую категорию операций.
    """
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(desc(Transaction.transaction_date))
    )
    if tx_type:
        stmt = stmt.where(Transaction.type == tx_type)

    result = await session.execute(stmt)
    transactions = list(result.scalars().all())

    # Подсчет общих сумм
    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    net_cash_flow = round(total_income - total_expense, 2)

    # Группировка транзакций по типу и категории
    income_dict: Dict[str, List[Transaction]] = {}
    expense_dict: Dict[str, List[Transaction]] = {}

    for tx in transactions:
        cat = tx.category or "Прочее"
        if tx.type == "income":
            income_dict.setdefault(cat, []).append(tx)
        else:
            expense_dict.setdefault(cat, []).append(tx)

    def build_category_items(cat_dict: Dict[str, List[Transaction]], total_type: float, item_type: str) -> List[CategorySummaryItem]:
        items: List[CategorySummaryItem] = []
        for cat_name, tx_list in cat_dict.items():
            cat_sum = round(sum(t.amount for t in tx_list), 2)
            count = len(tx_list)
            pct = round((cat_sum / total_type * 100.0) if total_type > 0 else 0.0, 1)
            avg = round((cat_sum / count) if count > 0 else 0.0, 2)

            items.append(
                CategorySummaryItem(
                    category=cat_name,
                    type=item_type,
                    total_amount=cat_sum,
                    count=count,
                    percentage=pct,
                    average_amount=avg,
                    transactions=[t.to_read_model() for t in tx_list],
                )
            )

        # Применение сортировки к категориям
        if sort_by == "amount_asc":
            items.sort(key=lambda x: x.total_amount)
        elif sort_by == "count_desc":
            items.sort(key=lambda x: x.count, reverse=True)
        elif sort_by == "name":
            items.sort(key=lambda x: x.category.lower())
        else:  # 'amount_desc' по умолчанию
            items.sort(key=lambda x: x.total_amount, reverse=True)

        return items

    income_items = build_category_items(income_dict, total_income, "income") if tx_type != "expense" else []
    expense_items = build_category_items(expense_dict, total_expense, "expense") if tx_type != "income" else []

    return CategoriesSummaryResponse(
        current_balance=round(user.balance, 2),
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        net_cash_flow=net_cash_flow,
        income_categories=income_items,
        expense_categories=expense_items,
    )


@router.get(
    "/goals",
    response_model=List[GoalReadSchema],
    summary="Получить финансовые цели пользователя",
)
async def get_user_goals(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Возвращает список всех финансовых целей текущего пользователя."""
    stmt = select(Goal).where(Goal.user_id == user.id).order_by(desc(Goal.created_at))
    result = await session.execute(stmt)
    goals = result.scalars().all()
    return goals


@router.post(
    "/goals",
    response_model=GoalReadSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую финансовую цель вручную",
)
async def create_goal(
    goal_data: GoalCreateSchema,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создает новую финансовую цель для пользователя."""
    new_goal = Goal(
        user_id=user.id,
        title=goal_data.title,
        target_amount=goal_data.target_amount,
        current_amount=goal_data.current_amount,
        deadline=goal_data.deadline,
    )
    session.add(new_goal)
    await session.commit()
    await session.refresh(new_goal)
    return new_goal


@router.post(
    "/advisor",
    response_model=AIAdvisorResponse,
    summary="Запрос к финансовому ИИ-помощнику (LLM + Tool Calling)",
)
async def ask_financial_advisor(
    request: AIAdvisorRequest,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Основной эндпоинт финансового ИИ-консультанта:
    1. Загружает из PostgreSQL сгенерированные транзакции пользователя (песочницу Plaid).
    2. Передает их в системный контекст LLM (ProxyAPI / OpenAI).
    3. Применяет механизм Tool Calling: модель передает параметры в python-функцию
       точного математического расчета бюджета и темпа накоплений.
    4. Если запрошено `save_as_goal=True`, сохраняет распознанную цель в БД.
    5. Возвращает обоснованные рекомендации, расчеты, топ расходов и ссылки на источники.
    """
    # 1. Извлекаем транзакции пользователя из базы данных
    stmt = select(Transaction).where(Transaction.user_id == user.id)
    result = await session.execute(stmt)
    transactions = list(result.scalars().all())

    # 2. Вызываем ИИ-модуль с Tool Calling
    ai_result = await process_ai_financial_advice(
        user_query=request.query,
        transactions=transactions,
        user_balance=user.balance,
    )

    created_goal: Optional[Goal] = None

    # 3. Сохранение цели в БД, если пользователь установил флаг
    if request.save_as_goal and ai_result.get("extracted_goal"):
        goal_info = ai_result["extracted_goal"]
        target_amount = float(goal_info.get("target_amount", 0.0))

        if target_amount > 0:
            target_months = goal_info.get("target_months") or 6
            deadline = date.today() + timedelta(days=int(target_months * 30.5))

            new_goal = Goal(
                user_id=user.id,
                title=goal_info.get("title", "Финансовая цель"),
                target_amount=target_amount,
                current_amount=0.0,
                deadline=deadline,
            )
            session.add(new_goal)
            await session.commit()
            await session.refresh(new_goal)
            created_goal = new_goal

    return AIAdvisorResponse(
        advice=ai_result["advice"],
        calculation=ai_result.get("calculation"),
        user_balance=ai_result["user_balance"],
        monthly_income=ai_result["monthly_income"],
        monthly_expenses=ai_result["monthly_expenses"],
        top_expense_categories=ai_result["top_expense_categories"],
        regular_payments=ai_result.get("regular_payments", {}),
        large_transactions=ai_result.get("large_transactions", []),
        action_items=ai_result.get("action_items", []),
        limitations=ai_result.get("limitations", ""),
        disclaimer=ai_result.get("disclaimer", ""),
        sources=ai_result.get("sources", []),
        goal_created=created_goal.to_read_model() if created_goal else None,
    )


# Эндпоинт для совместимости с предыдущим маршрутом
@router.get("", response_model=UserReadSchema, include_in_schema=False)
async def get_info_user_alias(
    user: User = Depends(current_user),
):
    """Псевдоним для получения профиля текущего пользователя."""
    return UserReadSchema(
        id=user.id,
        username=user.username,
        email=user.email,
        balance=user.balance,
    )