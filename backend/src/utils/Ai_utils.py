import json
import math
import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from models.models import Transaction, TransactionType


# Проверенные финансовые источники (требование кейса Т-Банка)
TRUSTED_FINANCIAL_SOURCES = [
    "https://journal.tinkoff.ru/guide/smart-budget/ — Т-Ж: Как грамотно распределять бюджет студенту",
    "https://fincult.info/article/finansovyy-plan-dlya-nachinayushchikh/ — Финансовая культура (Банк России): Личный финансовый план",
    "https://journal.tinkoff.ru/guide/emergency-fund/ — Т-Ж: Зачем нужна подушка безопасности и как её собрать",
]

SERVICE_DISCLAIMER = (
    "⚠️ Важное уведомление: Сервис носит исключительно информационно-просветительский характер, "
    "не является индивидуальной инвестиционной рекомендацией (ИИР) и не принимает финансовые решения "
    "вместо пользователя."
)

SERVICE_LIMITATIONS = (
    "Ограничения расчетов: Математический прогноз построен на основе данных о доходах и расходах за последние 30 дней "
    "и предполагает сохранение текущего темпа заработка. Не учитывает внезапные форс-мажоры и крупные непредсказуемые траты. "
    "Для студентов с нестабильной подработкой рекомендуется ориентироваться на консервативный сценарий (с учетом спада в сессию)."
)


# =====================================================================
# 1. Python-функция точного математического расчета бюджета и накоплений
# =====================================================================

def calculate_savings_plan(
    target_amount: float,
    monthly_income: float,
    monthly_expenses: float,
    guaranteed_income: float = 0.0,
    variable_income: float = 0.0,
    regular_expenses: float = 0.0,
    discretionary_expenses: float = 0.0,
    current_savings: float = 0.0,
    target_months: Optional[int] = None,
    risk_buffer_percent: float = 10.0,
) -> Dict[str, Any]:
    """
    Выполняет строгий математический расчет бюджета и темпа накоплений для студента с подработкой.
    Нейросеть не считает в уме — расчеты полностью детерминированы кодом (требование Т-Банка).

    :param target_amount: Целевая сумма накопления (в рублях).
    :param monthly_income: Общий ежемесячный подтвержденный доход (в рублях).
    :param monthly_expenses: Общие ежемесячные расходы (в рублях).
    :param guaranteed_income: Гарантированный доход (стипендия).
    :param variable_income: Переменный доход (подработка, смены, фриланс).
    :param regular_expenses: Обязательные регулярные платежи (подписки, связь, транспорт).
    :param discretionary_expenses: Гибкие расходы (кафе, развлечения, покупки).
    :param current_savings: Стартовые сбережения / свободный баланс (в рублях).
    :param target_months: Желаемый срок достижения цели в месяцах (если указан).
    :param risk_buffer_percent: Процент подушки безопасности/непредвиденных трат (по умолчанию 10%).
    :return: Словарь с точными метриками базового и стресс-сценария (период сессии).
    """
    target_amount = float(target_amount)
    monthly_income = float(monthly_income)
    monthly_expenses = float(monthly_expenses)
    guaranteed_income = float(guaranteed_income)
    variable_income = float(variable_income)
    regular_expenses = float(regular_expenses)
    discretionary_expenses = float(discretionary_expenses)
    current_savings = max(0.0, float(current_savings))
    risk_buffer_percent = float(risk_buffer_percent)

    # 1. Свободный денежный поток в месяц (профицит или дефицит)
    free_cash_flow = round(monthly_income - monthly_expenses, 2)
    # Остаток суммы до цели с учетом уже имеющихся средств
    remaining_target = max(0.0, round(target_amount - current_savings, 2))

    # Случай А: Накоплений уже достаточно для покрытия цели
    if remaining_target <= 0.0:
        return {
            "target_amount": target_amount,
            "current_savings": current_savings,
            "remaining_target": 0.0,
            "monthly_income": monthly_income,
            "guaranteed_income": guaranteed_income,
            "variable_income": variable_income,
            "monthly_expenses": monthly_expenses,
            "regular_expenses": regular_expenses,
            "discretionary_expenses": discretionary_expenses,
            "free_cash_flow": free_cash_flow,
            "safe_monthly_savings": 0.0,
            "required_monthly_savings": 0.0,
            "estimated_months": 0,
            "stress_scenario_months": 0,
            "is_achievable": True,
            "daily_savings_recommendation": 0.0,
            "weekly_savings_recommendation": 0.0,
            "recommended_cut_percentage": 0.0,
            "status": "already_achieved",
            "details": "У вас уже достаточно средств на счете для достижения этой цели прямо сейчас.",
        }

    # Случай Б: Дефицит бюджета (расходы превышают или равны доходам)
    if free_cash_flow <= 0.0:
        deficit = abs(free_cash_flow)
        months_fallback = target_months if (target_months and target_months > 0) else 12
        required_savings = round(remaining_target / months_fallback, 2)
        needed_discretionary_cut = round(
            ((deficit + required_savings) / discretionary_expenses * 100.0) if discretionary_expenses > 0 else 0.0, 1
        )

        return {
            "target_amount": target_amount,
            "current_savings": current_savings,
            "remaining_target": remaining_target,
            "monthly_income": monthly_income,
            "guaranteed_income": guaranteed_income,
            "variable_income": variable_income,
            "monthly_expenses": monthly_expenses,
            "regular_expenses": regular_expenses,
            "discretionary_expenses": discretionary_expenses,
            "free_cash_flow": free_cash_flow,
            "safe_monthly_savings": 0.0,
            "required_monthly_savings": required_savings,
            "estimated_months": None,
            "stress_scenario_months": None,
            "is_achievable": False,
            "daily_savings_recommendation": 0.0,
            "weekly_savings_recommendation": 0.0,
            "recommended_cut_percentage": min(100.0, needed_discretionary_cut),
            "status": "deficit",
            "details": (
                f"Внимание: ежемесячные траты ({monthly_expenses:.2f} руб.) превышают доходы ({monthly_income:.2f} руб.) "
                f"на {deficit:.2f} руб./мес. Рекомендуется оптимизировать гибкие расходы (кафе, фастфуд, развлечения)."
            ),
        }

    # Случай В: Профицит бюджета. Расчет безопасных ежемесячных отчислений с учетом подушки
    buffer_factor = max(0.0, 1.0 - (risk_buffer_percent / 100.0))
    safe_monthly_savings = round(free_cash_flow * buffer_factor, 2)

    # Расчетный срок при безопасном темпе накоплений
    estimated_months = math.ceil(remaining_target / safe_monthly_savings) if safe_monthly_savings > 0 else None

    # Стресс-сценарий для студента с подработкой (во время сессии/экзаменов подработка падает на 40%)
    stress_variable_income = variable_income * 0.60
    stress_monthly_income = guaranteed_income + stress_variable_income
    stress_free_cash_flow = stress_monthly_income - monthly_expenses
    if stress_free_cash_flow > 0:
        stress_safe_savings = stress_free_cash_flow * buffer_factor
        stress_scenario_months = math.ceil(remaining_target / stress_safe_savings) if stress_safe_savings > 0 else None
    else:
        stress_scenario_months = None

    # Если пользователь задал фиксированный желаемый срок
    if target_months and target_months > 0:
        required_monthly_savings = round(remaining_target / target_months, 2)
        is_achievable = safe_monthly_savings >= required_monthly_savings

        if is_achievable:
            recommended_cut = 0.0
            details = (
                f"Цель полностью реалистична! Для накопления {target_amount:,.2f} руб. за {target_months} мес. "
                f"достаточно откладывать по {required_monthly_savings:,.2f} руб./мес. "
                f"При этом сохраняется подушка безопасности {risk_buffer_percent}% на непредвиденные траты."
            )
        else:
            shortage_per_month = round(required_monthly_savings - safe_monthly_savings, 2)
            recommended_cut = round(
                (shortage_per_month / discretionary_expenses * 100.0) if discretionary_expenses > 0 else 0.0, 1
            )
            details = (
                f"При текущем уровне расходов за {target_months} мес. цель труднодостижима: "
                f"нужно откладывать {required_monthly_savings:,.2f} руб./мес., а безопасный остаток — {safe_monthly_savings:,.2f} руб./мес. "
                f"Необходимо сократить гибкие траты (кафе, развлечения) на {shortage_per_month:,.2f} руб./мес. ({recommended_cut}%) "
                f"либо увеличить комфортный срок накопления до {estimated_months} мес."
            )
    else:
        # Срок не задан — рассчитываем оптимальный срок на основе безопасного потока
        required_monthly_savings = safe_monthly_savings
        is_achievable = True
        recommended_cut = 0.0
        details = (
            f"Оптимальный план: откладывать по {safe_monthly_savings:,.2f} руб./мес. "
            f"Цель будет гарантированно достигнута за {estimated_months} мес."
        )

    daily_recommendation = round(required_monthly_savings / 30.0, 2)
    weekly_recommendation = round(required_monthly_savings / 4.33, 2)

    return {
        "target_amount": target_amount,
        "current_savings": current_savings,
        "remaining_target": remaining_target,
        "monthly_income": monthly_income,
        "guaranteed_income": guaranteed_income,
        "variable_income": variable_income,
        "monthly_expenses": monthly_expenses,
        "regular_expenses": regular_expenses,
        "discretionary_expenses": discretionary_expenses,
        "free_cash_flow": free_cash_flow,
        "safe_monthly_savings": safe_monthly_savings,
        "required_monthly_savings": required_monthly_savings,
        "estimated_months": estimated_months,
        "stress_scenario_months": stress_scenario_months,
        "is_achievable": is_achievable,
        "daily_savings_recommendation": daily_recommendation,
        "weekly_savings_recommendation": weekly_recommendation,
        "recommended_cut_percentage": recommended_cut,
        "status": "success",
        "details": details,
    }


# =====================================================================
# 2. JSON-схема инструмента (Tool Definition) в формате OpenAI
# =====================================================================

SAVINGS_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "calculate_savings_plan",
        "description": (
            "Выполняет точный математический расчет финансового плана, бюджета и темпа накоплений на цель. "
            "ОБЯЗАТЕЛЬНО используй этот инструмент для любых числовых вычислений. Запрещено считать сроки и отчисления самостоятельно!"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_amount": {
                    "type": "number",
                    "description": "Целевая сумма накопления в рублях (например: 120000)",
                },
                "monthly_income": {
                    "type": "number",
                    "description": "Среднемесячный доход пользователя в рублях из переданного системного контекста",
                },
                "monthly_expenses": {
                    "type": "number",
                    "description": "Среднемесячные расходы пользователя в рублях из переданного системного контекста",
                },
                "guaranteed_income": {
                    "type": "number",
                    "description": "Гарантированный доход (стипендия) в рублях",
                },
                "variable_income": {
                    "type": "number",
                    "description": "Переменный доход (подработка, фриланс, смены) в рублях",
                },
                "regular_expenses": {
                    "type": "number",
                    "description": "Обязательные регулярные платежи (подписки, связь, транспорт) в рублях",
                },
                "discretionary_expenses": {
                    "type": "number",
                    "description": "Гибкие расходы (кафе, фастфуд, развлечения, покупки) в рублях",
                },
                "current_savings": {
                    "type": "number",
                    "description": "Текущий баланс или стартовые сбережения пользователя (по умолчанию 0)",
                },
                "target_months": {
                    "type": "integer",
                    "description": "Желаемый срок накопления в месяцах, если пользователь явно указал его в запросе",
                },
                "risk_buffer_percent": {
                    "type": "number",
                    "description": "Процент подушки безопасности/непредвиденных расходов (по умолчанию 10)",
                },
            },
            "required": ["target_amount", "monthly_income", "monthly_expenses"],
        },
    },
}


# =====================================================================
# 3. Агрегация транзакций пользователя (Сегмент: Студент с подработкой)
# =====================================================================

def summarize_user_finances(transactions: List[Transaction], current_balance: float) -> Dict[str, Any]:
    """
    Анализирует транзакции студента с подработкой за месяц:
    - Разделяет доходы на гарантированную стипендию и плавающую подработку;
    - Выделяет обязательные регулярные платежи (подписки, транспорт, связь);
    - Группирует гибкие расходы (кафе, фастфуд, покупки, развлечения);
    - Находит крупные разовые транзакции (> 2000 руб.).
    """
    total_income = 0.0
    guaranteed_income = 0.0
    variable_income = 0.0

    total_expenses = 0.0
    regular_expenses = 0.0
    discretionary_expenses = 0.0

    income_by_category: Dict[str, float] = {}
    expenses_by_category: Dict[str, float] = {}
    regular_payments: Dict[str, float] = {}
    large_transactions: List[Dict[str, Any]] = []

    # Категории обязательных регулярных платежей студента
    regular_categories = {"Связь и подписки", "Транспорт", "Общежитие и быт"}

    for tx in transactions:
        amount = float(tx.amount)
        category = tx.category or "Прочее"

        if tx.type == TransactionType.INCOME.value or tx.type == "income":
            total_income += amount
            income_by_category[category] = round(income_by_category.get(category, 0.0) + amount, 2)

            if "стипенди" in category.lower() or "стипенди" in (tx.description or "").lower():
                guaranteed_income += amount
            else:
                variable_income += amount
        else:
            total_expenses += amount
            expenses_by_category[category] = round(expenses_by_category.get(category, 0.0) + amount, 2)

            # Выделение регулярных обязательных платежей
            if category in regular_categories:
                regular_expenses += amount
                regular_payments[category] = round(regular_payments.get(category, 0.0) + amount, 2)
            else:
                discretionary_expenses += amount

            # Выделение крупных покупок (для студента от 1000 руб.)
            if amount >= 1000.0:
                large_transactions.append({
                    "category": category,
                    "description": tx.description or "Крупная покупка",
                    "amount": round(amount, 2),
                    "date": tx.transaction_date.strftime("%d.%m.%Y") if hasattr(tx.transaction_date, "strftime") else str(tx.transaction_date),
                })

    total_income = round(total_income, 2)
    total_expenses = round(total_expenses, 2)
    guaranteed_income = round(guaranteed_income, 2)
    variable_income = round(variable_income, 2)
    regular_expenses = round(regular_expenses, 2)
    discretionary_expenses = round(discretionary_expenses, 2)

    # Сортировка категорий расходов по убыванию суммы
    sorted_expenses = dict(sorted(expenses_by_category.items(), key=lambda item: item[1], reverse=True))

    return {
        "current_balance": round(current_balance, 2),
        "total_income": total_income,
        "guaranteed_income": guaranteed_income,
        "variable_income": variable_income,
        "total_expenses": total_expenses,
        "regular_expenses": regular_expenses,
        "discretionary_expenses": discretionary_expenses,
        "income_by_category": income_by_category,
        "expenses_by_category": sorted_expenses,
        "regular_payments": regular_payments,
        "large_transactions": large_transactions[:5],
        "free_cash_flow": round(total_income - total_expenses, 2),
    }


def build_system_prompt(finance_summary: Dict[str, Any]) -> str:
    """Формирует системный промпт для LLM с учетом профиля студента с подработкой."""
    balance = finance_summary["current_balance"]
    income = finance_summary["total_income"]
    guaranteed = finance_summary["guaranteed_income"]
    variable = finance_summary["variable_income"]
    expenses = finance_summary["total_expenses"]
    regular = finance_summary["regular_expenses"]
    discretionary = finance_summary["discretionary_expenses"]
    cash_flow = finance_summary["free_cash_flow"]

    expenses_lines = []
    for cat, amount in finance_summary["expenses_by_category"].items():
        percentage = round((amount / expenses * 100), 1) if expenses > 0 else 0
        expenses_lines.append(f"  - {cat}: {amount:,.2f} руб. ({percentage}%)")
    expenses_text = "\n".join(expenses_lines) if expenses_lines else "  Нет данных о расходах."

    regular_lines = [f"  - {cat}: {amount:,.2f} руб." for cat, amount in finance_summary["regular_payments"].items()]
    regular_text = "\n".join(regular_lines) if regular_lines else "  Нет регулярных платежей."

    return f"""Ты — персональный финансовый ИИ-помощник Т-Банка для молодежи.
Твой пользователь: студент 18-25 лет, совмещающий учебу в вузе и подработку (фриланс / смены).
Его доходы состоят из гарантированной части (стипендия) и переменной (подработка). Во время сессии подработка может сокращаться.

ФИНАНСОВЫЙ ПРОФИЛЬ СТУДЕНТА ЗА ПОСЛЕДНИЙ МЕСЯЦ:
- Баланс карты: {balance:,.2f} руб.
- Общий месячный доход: {income:,.2f} руб.
  * Гарантированная стипендия: {guaranteed:,.2f} руб.
  * Доход от подработки / фриланса: {variable:,.2f} руб.
- Общие месячные расходы: {expenses:,.2f} руб.
  * Обязательные регулярные платежи (подписки, связь, транспорт): {regular:,.2f} руб.
  * Гибкие расходы (кафе, фастфуд, развлечения, покупки): {discretionary:,.2f} руб.
- Структура расходов по категориям:
{expenses_text}
- Обязательные регулярные списания:
{regular_text}
- Свободный денежный поток: {cash_flow:,.2f} руб./мес.

СТРОГИЕ ПРАВИЛА (ТРЕБОВАНИЯ КЕЙСА Т-БАНКА):
1. ЗАПРЕЩЕНО выполнять расчеты сроков, сумм и процентов самостоятельно в тексте!
2. Для любых математических расчетов ты ОБЯЗАН вызвать инструмент `calculate_savings_plan`, передав точные числа из профиля выше.
3. Не давай индивидуальных инвестиционных рекомендаций (ИИР) и не принимай решения за пользователя.
4. Отвечай дружелюбно, структурированно, без менторского тона, понятным для студента языком.
5. Обязательно дай конкретный пошаговый план (3-4 действия), как студенту легче откладывать деньги (автонакопления в день выплаты стипендии/смены, контроль импульсивных трат на кофе/фастфуд).
"""


# =====================================================================
# 4. Резервный парсер запроса пользователя
# =====================================================================

def fallback_extract_target(user_query: str) -> Tuple[str, float, Optional[int]]:
    """
    Резервный анализатор запроса с помощью регулярных выражений.
    Гарантирует стабильную работу MVP бэкенда на демо хакатона.
    """
    # Поиск суммы (например: 150000, 150 000, 120k, 50 тыс. руб.)
    amount = 50000.0
    amount_match = re.search(r"(\d+(?:[\s_]\d+)*)\s*(тыс(?:\.|яч[ей|и]?)?|k|к|руб(?:лей|\.)?|р\b)?", user_query, re.IGNORECASE)
    if amount_match:
        raw_num = re.sub(r"[\s_]+", "", amount_match.group(1))
        unit = (amount_match.group(2) or "").lower()
        try:
            val = float(raw_num)
            if any(k in unit for k in ["тыс", "k", "к"]) and val < 100000:
                val *= 1000.0
            if val > 0:
                amount = val
        except ValueError:
            pass

    # Поиск срока в месяцах
    months = None
    month_match = re.search(r"(\d+)\s*(?:мес|месяц|месяца|месяцев)", user_query, re.IGNORECASE)
    if month_match:
        try:
            months = int(month_match.group(1))
        except ValueError:
            pass
    elif "год" in user_query.lower():
        months = 12
    elif "полгода" in user_query.lower():
        months = 6

    # Название цели (отсекаем стоп-слова)
    title = user_query.strip()
    clean_title = re.sub(r"(хочу накопить на|накопить на|купить|собрать на)\s*", "", title, flags=re.IGNORECASE).strip()
    if clean_title:
        title = clean_title.capitalize()
    if len(title) > 60:
        title = title[:57] + "..."

    return title, amount, months


# =====================================================================
# 5. Главный метод взаимодействия с LLM через Tool Calling
# =====================================================================

async def process_ai_financial_advice(
    user_query: str,
    transactions: List[Transaction],
    user_balance: float,
) -> Dict[str, Any]:
    """
    Основная логика ИИ-модуля для кейса Т-Банка:
    1. Формирует профиль студента с подработкой из транзакций.
    2. Передает контекст и запрос в LLM (ProxyAPI / OpenAI).
    3. Принимает вызов Tool Calling, исполняет python-функцию calculate_savings_plan.
    4. Генерирует план действий (Action Items), ограничения и ссылки на проверенные источники.
    """
    finance_summary = summarize_user_finances(transactions, user_balance)
    system_prompt = build_system_prompt(finance_summary)

    client = AsyncOpenAI(
        api_key=OPENAI_API_KEY or "dummy-key-for-local-fallback",
        base_url=OPENAI_BASE_URL,
    )

    calculation_result: Optional[Dict[str, Any]] = None
    ai_advice_text: str = ""
    goal_title, extracted_amount, extracted_months = fallback_extract_target(user_query)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
    ]

    try:
        if not OPENAI_API_KEY or OPENAI_API_KEY.strip() == "":
            raise ValueError("Ключ OPENAI_API_KEY не установлен в переменных окружения.")

        # Шаг 1: Запрос к LLM с объявлением инструментов
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=[SAVINGS_TOOL_DEFINITION],
            tool_choice="auto",
            temperature=0.3,
        )

        response_message = response.choices[0].message

        # Шаг 2: Проверка Tool Calling
        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "calculate_savings_plan":
                    tool_args = json.loads(tool_call.function.arguments)

                    # ВЫЗОВ ТОЧНОЙ PYTHON-ФУНКЦИИ
                    calculation_result = calculate_savings_plan(
                        target_amount=float(tool_args.get("target_amount", extracted_amount)),
                        monthly_income=float(tool_args.get("monthly_income", finance_summary["total_income"])),
                        monthly_expenses=float(tool_args.get("monthly_expenses", finance_summary["total_expenses"])),
                        guaranteed_income=float(tool_args.get("guaranteed_income", finance_summary["guaranteed_income"])),
                        variable_income=float(tool_args.get("variable_income", finance_summary["variable_income"])),
                        regular_expenses=float(tool_args.get("regular_expenses", finance_summary["regular_expenses"])),
                        discretionary_expenses=float(tool_args.get("discretionary_expenses", finance_summary["discretionary_expenses"])),
                        current_savings=float(tool_args.get("current_savings", 0.0)),
                        target_months=tool_args.get("target_months") or extracted_months,
                        risk_buffer_percent=float(tool_args.get("risk_buffer_percent", 10.0)),
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(calculation_result, ensure_ascii=False),
                    })

            # Шаг 3: Получение финального ответа от модели
            second_response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
            )
            ai_advice_text = second_response.choices[0].message.content or ""
        else:
            ai_advice_text = response_message.content or ""
            calculation_result = calculate_savings_plan(
                target_amount=extracted_amount,
                monthly_income=finance_summary["total_income"],
                monthly_expenses=finance_summary["total_expenses"],
                guaranteed_income=finance_summary["guaranteed_income"],
                variable_income=finance_summary["variable_income"],
                regular_expenses=finance_summary["regular_expenses"],
                discretionary_expenses=finance_summary["discretionary_expenses"],
                current_savings=0.0,
                target_months=extracted_months,
            )

    except Exception as exc:
        print(f"Обработка запроса через резервный локальный движок (причина: {exc})")
        calculation_result = calculate_savings_plan(
            target_amount=extracted_amount,
            monthly_income=finance_summary["total_income"],
            monthly_expenses=finance_summary["total_expenses"],
            guaranteed_income=finance_summary["guaranteed_income"],
            variable_income=finance_summary["variable_income"],
            regular_expenses=finance_summary["regular_expenses"],
            discretionary_expenses=finance_summary["discretionary_expenses"],
            current_savings=0.0,
            target_months=extracted_months,
        )

        top_cats = list(finance_summary["expenses_by_category"].items())[:3]
        top_cats_text = ", ".join([f"{c} ({a:,.0f} руб.)" for c, a in top_cats]) if top_cats else "отсутствуют"

        if calculation_result["is_achievable"]:
            months_text = f"{calculation_result['estimated_months']} мес." if calculation_result['estimated_months'] else "12 мес."
            stress_info = ""
            if calculation_result.get("stress_scenario_months"):
                stress_info = f"\n- В период сессии (при спаде подработки на 40%): **{calculation_result['stress_scenario_months']} мес.**"

            ai_advice_text = (
                f"🎯 **Финансовый план накопления для студента**\n\n"
                f"Цель: **{goal_title}** на сумму **{calculation_result['target_amount']:,.2f} руб.**\n\n"
                f"📊 **Точный расчет бюджета:**\n"
                f"- Общий доход: {calculation_result['monthly_income']:,.2f} руб. (стипендия: {calculation_result['guaranteed_income']:,.2f} руб., подработка: {calculation_result['variable_income']:,.2f} руб.)\n"
                f"- Обязательные регулярные платежи: {calculation_result['regular_expenses']:,.2f} руб.\n"
                f"- Гибкие расходы (кафе, фастфуд, покупки): {calculation_result['discretionary_expenses']:,.2f} руб.\n"
                f"- Свободный остаток: {calculation_result['free_cash_flow']:,.2f} руб./мес.\n"
                f"- Рекомендуемый темп: **{calculation_result['required_monthly_savings']:,.2f} руб./мес.** (~{calculation_result['daily_savings_recommendation']:,.2f} руб./день)\n"
                f"- Срок достижения цели (базовый темп): **{months_text}**{stress_info}\n\n"
                f"💡 **Рекомендации по оптимизации для студента:**\n"
                f"Ваши основные категории гибких трат: {top_cats_text}. "
                f"Если сократить походы в кофейни и доставку еды хотя бы на 10-15%, вы сможете создать неприкосновенную подушку безопасности "
                f"и достичь цели даже в период сессии!"
            )
        else:
            ai_advice_text = (
                f"⚠️ **Анализ бюджета выявил дефицит свободных средств**\n\n"
                f"Цель: **{goal_title}** на сумму **{calculation_result['target_amount']:,.2f} руб.**\n\n"
                f"Текущие расходы ({calculation_result['monthly_expenses']:,.2f} руб.) почти полностью съедают доход ({calculation_result['monthly_income']:,.2f} руб.).\n"
                f"Чтобы откладывать {calculation_result['required_monthly_savings']:,.2f} руб./мес., "
                f"необходимо сократить категорию гибких расходов ({calculation_result['discretionary_expenses']:,.2f} руб.) "
                f"на {calculation_result['recommended_cut_percentage']}%."
            )

    # Формируем конкретные шаги для студента (Action items)
    action_items = [
        f"Настроить автоперевод в копилку: сразу переводить {calculation_result['required_monthly_savings']/2:,.0f} руб. в день стипендии и в день зарплаты за подработку.",
        "Установить недельный лимит на кафе и доставку готовой еды в мобильном приложении банка.",
        "Проверить список платных подписок и отключить те сервисы, которыми редко пользуетесь во время учебы.",
        "Не трогать резервную подушку безопасности (10% от свободных денег), чтобы не залезать в долги в сессию.",
    ]

    return {
        "advice": ai_advice_text,
        "calculation": calculation_result,
        "user_balance": finance_summary["current_balance"],
        "monthly_income": finance_summary["total_income"],
        "monthly_expenses": finance_summary["total_expenses"],
        "top_expense_categories": finance_summary["expenses_by_category"],
        "regular_payments": finance_summary["regular_payments"],
        "large_transactions": finance_summary["large_transactions"],
        "action_items": action_items,
        "limitations": SERVICE_LIMITATIONS,
        "disclaimer": SERVICE_DISCLAIMER,
        "sources": TRUSTED_FINANCIAL_SOURCES,
        "extracted_goal": {
            "title": goal_title,
            "target_amount": calculation_result["target_amount"] if calculation_result else extracted_amount,
            "target_months": calculation_result.get("estimated_months") if calculation_result else extracted_months,
        },
    }
