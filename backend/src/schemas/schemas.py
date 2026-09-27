from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field


class UserReadSchema(BaseModel):
    """Схема для отображения данных пользователя."""
    id: int
    username: str
    email: EmailStr
    balance: float = 0.0

    class Config:
        from_attributes = True


class TransactionReadSchema(BaseModel):
    """Схема для отображения транзакции (дохода или расхода)."""
    id: int
    user_id: int
    amount: float = Field(..., description="Сумма транзакции в рублях")
    type: str = Field(..., description="Тип операции: income или expense")
    category: str = Field(..., description="Категория транзакции")
    description: Optional[str] = Field(None, description="Описание или комментарий")
    transaction_date: datetime = Field(..., description="Дата и время транзакции")

    class Config:
        from_attributes = True


class CategorySummaryItem(BaseModel):
    """Схема сводки по отдельной категории доходов или расходов."""
    category: str = Field(..., description="Название категории")
    type: str = Field(..., description="Тип операции: income (доход) или expense (расход)")
    total_amount: float = Field(..., description="Суммарный объем средств по категории (руб.)")
    count: int = Field(..., description="Количество транзакций в категории")
    percentage: float = Field(..., description="Доля в процентах от общего объема доходов/расходов")
    average_amount: float = Field(..., description="Средний чек транзакции в категории (руб.)")
    transactions: List[TransactionReadSchema] = Field(default_factory=list, description="Список транзакций в данной категории")


class CategoriesSummaryResponse(BaseModel):
    """Схема ответа для группировки и сортировки доходов и расходов по категориям."""
    current_balance: float = Field(..., description="Текущий баланс пользователя")
    total_income: float = Field(..., description="Общий подтвержденный доход за месяц")
    total_expense: float = Field(..., description="Общие расходы за месяц")
    net_cash_flow: float = Field(..., description="Чистый остаток (доходы минус расходы)")
    income_categories: List[CategorySummaryItem] = Field(default_factory=list, description="Сгруппированные категории доходов")
    expense_categories: List[CategorySummaryItem] = Field(default_factory=list, description="Сгруппированные категории расходов")


class GoalReadSchema(BaseModel):
    """Схема для отображения финансовой цели."""
    id: int
    user_id: int
    title: str = Field(..., description="Название цели")
    target_amount: float = Field(..., description="Целевая сумма")
    current_amount: float = Field(..., description="Текущая накопленная сумма")
    deadline: Optional[date] = Field(None, description="Планируемая дата достижения")
    created_at: datetime = Field(..., description="Дата создания цели")

    class Config:
        from_attributes = True


class GoalCreateSchema(BaseModel):
    """Схема для создания новой цели."""
    title: str = Field(..., min_length=1, max_length=255, description="Название финансовой цели")
    target_amount: float = Field(..., gt=0, description="Необходимая сумма в рублях")
    current_amount: float = Field(default=0.0, ge=0, description="Уже накопленная сумма")
    deadline: Optional[date] = Field(default=None, description="Планируемый дедлайн (дата)")


class AIAdvisorRequest(BaseModel):
    """Схема запроса к финансовому ИИ-помощнику."""
    query: str = Field(
        ...,
        min_length=3,
        description="Запрос пользователя (например: 'Хочу накопить на ноутбук 60000 рублей за 6 месяцев')",
        example="Хочу накопить на учебный ноутбук 60000 рублей за 6 месяцев"
    )
    save_as_goal: bool = Field(
        default=False,
        description="Если True, автоматически сохранит цель в БД при успешном расчете"
    )


class SavingsPlanResult(BaseModel):
    """Результат точного математического расчета финансового плана (Tool Calling)."""
    target_amount: float = Field(..., description="Целевая сумма (руб.)")
    current_savings: float = Field(..., description="Текущие стартовые сбережения (руб.)")
    remaining_target: float = Field(..., description="Остаток до цели (руб.)")
    monthly_income: float = Field(..., description="Общий ежемесячный доход (руб.)")
    guaranteed_income: float = Field(default=0.0, description="Гарантированный доход (стипендия)")
    variable_income: float = Field(default=0.0, description="Переменный доход (подработка, смены)")
    monthly_expenses: float = Field(..., description="Ежемесячные расходы (руб.)")
    regular_expenses: float = Field(default=0.0, description="Обязательные регулярные расходы (подписки, связь, транспорт)")
    discretionary_expenses: float = Field(default=0.0, description="Гибкие расходы (кафе, развлечения, покупки)")
    free_cash_flow: float = Field(..., description="Свободный остаток в месяц (руб.)")
    safe_monthly_savings: float = Field(..., description="Безопасная сумма отчислений с учетом резерва (руб.)")
    required_monthly_savings: float = Field(..., description="Необходимая сумма отчислений в месяц (руб.)")
    estimated_months: Optional[int] = Field(None, description="Расчетный срок накопления в месяцах (базовый сценарий)")
    stress_scenario_months: Optional[int] = Field(None, description="Срок при снижении подработки на 40% (при трудностях или спаде дохода)")
    is_achievable: bool = Field(..., description="Достижима ли цель в текущих условиях")
    daily_savings_recommendation: float = Field(..., description="Рекомендуемая сумма в день (руб.)")
    weekly_savings_recommendation: float = Field(..., description="Рекомендуемая сумма в неделю (руб.)")
    recommended_cut_percentage: float = Field(..., description="Рекомендуемый процент сокращения гибких расходов (%)")
    status: str = Field(..., description="Статус расчета (success, deficit, already_achieved)")
    details: str = Field(..., description="Детальное текстовое резюме расчетов")


class AIAdvisorResponse(BaseModel):
    """Схема ответа финансового ИИ-помощника."""
    advice: str = Field(..., description="Развернутые рекомендации от нейросети с учетом профиля студента")
    calculation: Optional[SavingsPlanResult] = Field(None, description="Результаты точного расчета через Tool Calling")
    user_balance: float = Field(..., description="Текущий баланс пользователя")
    monthly_income: float = Field(..., description="Ежемесячный доход пользователя")
    monthly_expenses: float = Field(..., description="Ежемесячные расходы пользователя")
    top_expense_categories: Dict[str, float] = Field(..., description="Топ категорий расходов за месяц")
    regular_payments: Dict[str, float] = Field(default_factory=dict, description="Регулярные обязательные платежи")
    large_transactions: List[Dict[str, Any]] = Field(default_factory=list, description="Крупные транзакции за месяц")
    action_items: List[str] = Field(default_factory=list, description="Конкретные шаги: что делать студенту дальше")
    limitations: str = Field(..., description="Ограничения продукта и допущения расчетов")
    disclaimer: str = Field(..., description="Отказ от индивидуальных инвестиционных рекомендаций")
    sources: List[str] = Field(default_factory=list, description="Ссылки на проверенные финансовые источники")
    goal_created: Optional[GoalReadSchema] = Field(None, description="Информация о созданной цели (если запрошено сохранение)")
