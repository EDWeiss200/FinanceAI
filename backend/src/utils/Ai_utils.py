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
    "Ограничения расчетов: Математический прогноз построен на основе фактических среднемесячных доходов и расходов "
    "и предполагает сохранение текущего темпа заработка. Не учитывает внезапные форс-мажоры и крупные непредсказуемые траты. "
    "При наличии рисков падения доходов рекомендуется формировать резервную подушку безопасности."
)


# =====================================================================
# 0. Классификация запроса пользователя
# =====================================================================

# Паттерны запросов, которые НЕ являются финансовыми
OFF_TOPIC_PATTERNS = [
    # Программирование и код
    r"\b(class|def|function|import|return|console\.log|System\.out|public\s+static|int\s+main|void|println)\b",
    r"\b(java|python|javascript|c\+\+|html|css|react|django|flask|spring|kotlin|swift)\b",
    r"\b(напиши|создай|сгенерируй|покажи)\s+(код|класс|функцию|программу|скрипт|метод|алгоритм)\b",
    # Домашние задания не по финансам
    r"\b(реферат|сочинение|эссе|курсовая|диплом)\s+(на\s+тему|по\s+(физике|химии|истории|биологии|литературе|математике))\b",
    # Общие вопросы, приветствия и болтовня (включая сленг: бро, чувак, друг и т.д.)
    r"^\s*(привет|здравствуй|хай|хей|здарова|салам|добрый\s+(день|вечер|утро)|доброе\s+утро|как дела|как ты|что делаешь|кто ты|расскажи о себе|расскажи анекдот|спасибо|пока|до свидания)\b",
    r"^\s*(hi|hello|hey|how are you|what'?s up|good morning|good night)\b",
    # Рецепты, погода, развлечения
    r"\b(рецепт|погода|фильм|сериал|музыка|песня|игра|играть)\b",
]

# Паттерны рискованных финансовых запросов
RISKY_PATTERNS = {
    # Иностранные валюты — работаем только с рублями
    "foreign_currency": r"\b(\d+)\s*(тенге|теньге|долларо?в?|евро|\$|€|£|¥|₸|usd|eur|gbp|kzt|грн|гривен|юаней?|йен[ыа]?|фунто?в?|крон[ыа]?)\b",
    # Инвестиционные вопросы (ИИР запрещены)
    "investment": r"\b(вложить|вкладывать|куда\s+вложить|инвестиц|инвестировать|акции|облигации|криптовалют[аыуе]|крипт[ауеы]?|биткоин|btc|eth|ethereum|трейдинг|форекс|forex|брокер|ценные\s+бумаги|фондов(?:ый|ого)?\s+рын(?:ок|ке))\b",
    # Кредиты и долги (не в компетенции)
    "credit": r"\b(кредит|ипотек[аеу]|займ|микрозайм|рассрочк[аеу]|долг[иу]|коллектор)\b",
    # Нереальные суммы для студента
    "unrealistic_amount": None,  # Проверяется отдельной логикой
    # Азартные игры и мошенничество
    "gambling": r"\b(казино|ставк[аиу]|букмекер|тотализатор|лотере[яюи]|пирамид[аеу]|быстрый заработок|заработать без вложений|финансовая пирамида|схема|обман)\b",
}

# Слова-маркеры финансовой тематики
FINANCIAL_KEYWORDS = [
    r"\b(накопить|копить|сберечь|отложить|сэкономить|экономить|бюджет|финанс)\b",
    r"\b(доход[ыа]?|расход[ыа]?|зарплат[аеу]|стипенди[яюи]|подработк[аеу])\b",
    r"\b(денег|деньги|денежн|рубл[ейяь]|тыс\.?|₽|руб\.?)\b",
    r"\b(трат[аыу]|покупк[аиу]|купить|цена|стоимость|цель)\b",
    r"\b(баланс|счет|карт[аеу]|вклад|сбережени[яе])\b",
    r"\b(подписк[аиу]|платеж[ие]|коммуналк[аеу]|аренд[аеу])\b",
]


def classify_query(user_query: str) -> Dict[str, Any]:
    """
    Классифицирует запрос пользователя по типам:
    - 'financial' — корректный финансовый запрос → полный пайплайн с Tool Calling
    - 'off_topic' — нерелевантный запрос (болтовня, программирование) → лёгкий текстовый ответ
    - 'risky' — рискованный запрос (иностранная валюта, инвестиции, азарт) → обозначение ограничений
    """
    query_lower = user_query.strip().lower()

    # 1. Проверка на полностью нерелевантный запрос
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, query_lower, re.IGNORECASE):
            # Но если есть ещё и финансовые ключевые слова — это финансовый запрос с лишним контекстом
            has_financial = any(re.search(fp, query_lower, re.IGNORECASE) for fp in FINANCIAL_KEYWORDS)
            if not has_financial:
                return {
                    "type": "off_topic",
                    "reason": "Запрос не относится к финансовой тематике.",
                    "details": None,
                }

    # 2. Проверка на рискованные паттерны
    for risk_type, pattern in RISKY_PATTERNS.items():
        if pattern is None:
            continue
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            return {
                "type": "risky",
                "reason": risk_type,
                "details": match.group(0),
            }

    # 3. Проверка на нереально маленькие/большие суммы для студента
    amount_match = re.search(r"(\d+[\s_]*\d*)\s*(руб|₽|р\b|тыс)", query_lower)
    if amount_match:
        raw = re.sub(r"[\s_]+", "", amount_match.group(1))
        try:
            val = float(raw)
            unit = (amount_match.group(2) or "").lower()
            if "тыс" in unit and val < 100000:
                val *= 1000.0
            # Слишком маленькие суммы (меньше 100 рублей)
            if 0 < val < 100:
                return {
                    "type": "risky",
                    "reason": "too_small_amount",
                    "details": f"{val} руб.",
                }
            # Нереально большие суммы для студента (свыше 10 млн)
            if val > 10_000_000:
                return {
                    "type": "risky",
                    "reason": "unrealistic_amount",
                    "details": f"{val:,.0f} руб.",
                }
        except ValueError:
            pass

    # 4. По умолчанию считаем финансовым запросом
    return {"type": "financial", "reason": None, "details": None}


def build_off_topic_response(user_query: str) -> str:
    """Формирует корректный ответ на нерелевантный запрос."""
    query_lower = user_query.strip().lower()

    # Приветствия
    greetings = ["привет", "здравствуй", "как дела", "hi", "hello", "hey"]
    if any(g in query_lower for g in greetings):
        return (
            "👋 Привет! Я — твой персональный финансовый ИИ-ассистент.\n\n"
            "Я помогу тебе:\n"
            "• Рассчитать план накоплений на конкретную цель\n"
            "• Проанализировать расходы и найти, где можно сэкономить\n"
            "• Оценить баланс и финансовую подушку безопасности\n\n"
            "Напиши, на что хочешь накопить или задай вопрос по расходам! 🎯"
        )

    # Благодарности и прощания
    farewells = ["спасибо", "пока", "до свидания"]
    if any(f in query_lower for f in farewells):
        return (
            "Рад был помочь! 😊 Если появятся финансовые вопросы — обращайся. "
            "Удачи с бюджетом и накоплениями!"
        )

    # Программирование
    code_keywords = ["class", "def", "function", "код", "программ", "скрипт", "java", "python", "html"]
    if any(k in query_lower for k in code_keywords):
        return (
            "🚫 К сожалению, я не могу помочь с программированием — "
            "это за пределами моей компетенции.\n\n"
            "Я — **финансовый ИИ-помощник** и умею:\n"
            "• Рассчитать план накоплений на любую цель\n"
            "• Проанализировать структуру доходов и расходов\n"
            "• Подсказать, где студенту можно сэкономить\n\n"
            "Попробуй спросить, например: «Хочу накопить на ноутбук 60 000 ₽ за полгода»"
        )

    # Универсальный ответ для прочих нерелевантных тем
    return (
        "🤔 Этот вопрос выходит за рамки моей специализации.\n\n"
        "Я — **финансовый ИИ-помощник** для студентов и могу помочь с:\n"
        "• Планированием бюджета и накоплений\n"
        "• Анализом расходов по категориям\n"
        "• Оценкой финансовой подушки безопасности\n\n"
        "Напиши финансовый вопрос, и я с радостью помогу! 💰"
    )


def build_risky_response(risk_reason: str, risk_details: Optional[str] = None) -> str:
    """Формирует корректный ответ на рискованный запрос с обозначением ограничений."""

    if risk_reason == "foreign_currency":
        return (
            f"⚠️ **Ограничение сервиса: валюта**\n\n"
            f"Обнаружена иностранная валюта в запросе: **{risk_details}**.\n\n"
            f"Наш сервис работает **исключительно с рублями (₽)**, так как:\n"
            f"• Данные о доходах и расходах в банковской системе ведутся в рублях\n"
            f"• Конвертация курсов валют в реальном времени не входит в функциональность MVP\n"
            f"• Мы не можем гарантировать точность расчётов в иностранной валюте\n\n"
            f"💡 Переформулируй запрос в рублях, и я сделаю точный расчёт!\n"
            f"Пример: «Хочу накопить 30 000 ₽ на велосипед за 4 месяца»"
        )

    if risk_reason == "investment":
        return (
            "⚠️ **Ограничение сервиса: инвестиции**\n\n"
            "Я **не даю индивидуальных инвестиционных рекомендаций (ИИР)** — "
            "это запрещено для информационно-просветительских сервисов.\n\n"
            "Мои компетенции:\n"
            "• Расчёт плана накоплений на конкретную цель\n"
            "• Анализ бюджета студента с подработкой\n"
            "• Рекомендации по оптимизации расходов\n\n"
            "Для инвестиционных вопросов обратись к лицензированному финансовому консультанту "
            "или изучи материалы на fincult.info (Банк России)."
        )

    if risk_reason == "credit":
        return (
            "⚠️ **Ограничение сервиса: кредиты и займы**\n\n"
            "Я **не консультирую по кредитам, ипотеке и займам** — "
            "это требует анализа кредитной истории и индивидуальной оценки рисков.\n\n"
            "Мои компетенции:\n"
            "• Помочь спланировать накопления, чтобы обойтись без кредитов\n"
            "• Рассчитать, сколько нужно откладывать для достижения цели\n"
            "• Оптимизировать расходы для ускорения накоплений\n\n"
            "Попробуй спросить: «Хочу накопить 60 000 ₽ — за сколько реально?»"
        )

    if risk_reason == "gambling":
        return (
            "🚫 **Ограничение сервиса**\n\n"
            "Я не поддерживаю запросы, связанные с азартными играми, "
            "ставками, финансовыми пирамидами и схемами «быстрого заработка».\n\n"
            "Единственный надежный способ накопить — это **системное управление бюджетом**: "
            "контроль расходов, регулярные отчисления и финансовая дисциплина.\n\n"
            "Готов помочь с реалистичным планом накоплений! 💪"
        )

    if risk_reason == "too_small_amount":
        return (
            f"🤔 Указанная сумма ({risk_details}) слишком мала для составления плана накоплений.\n\n"
            f"Для полноценного финансового расчёта укажи цель от **100 ₽** и выше.\n\n"
            f"Примеры:\n"
            f"• «Хочу накопить 5 000 ₽ на учебники»\n"
            f"• «Накопить 30 000 ₽ на смартфон за 3 месяца»\n"
            f"• «Сколько откладывать на ноутбук 60 000 ₽?»"
        )

    if risk_reason == "unrealistic_amount":
        return (
            f"⚠️ **Ограничение: нереалистичная сумма**\n\n"
            f"Указанная сумма ({risk_details}) значительно превышает "
            f"типичный бюджет студента с подработкой.\n\n"
            f"Мой расчётный модуль оптимизирован для целей студентов в диапазоне "
            f"**1 000 — 1 000 000 ₽**.\n\n"
            f"Для крупных сумм рекомендую обратиться к персональному финансовому консультанту."
        )

    # Неизвестный тип риска — generic ответ
    return (
        "⚠️ Этот запрос выходит за рамки моих возможностей.\n\n"
        "Я — финансовый помощник для студентов и специализируюсь на:\n"
        "• Планировании накоплений на конкретные цели\n"
        "• Анализе доходов и расходов\n"
        "• Оптимизации бюджета\n\n"
        "Переформулируй запрос, и я постараюсь помочь!"
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
    include_stress_scenario: bool = False,
) -> Dict[str, Any]:
    """
    Выполняет строгий математический расчет бюджета и темпа накоплений для студента с подработкой.
    Нейросеть не считает в уме — расчеты полностью детерминированы кодом (требование Т-Банка).
    Стресс-сценарий (спад подработки на 40%) рассчитывается ТОЛЬКО если пользователь сам указал трудности.
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

    # 1. Свободный денежный поток в месяц
    free_cash_flow = round(monthly_income - monthly_expenses, 2)
    remaining_target = max(0.0, round(target_amount - current_savings, 2))

    # Случай А: Накоплений уже достаточно
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
            "stress_scenario_months": None,
            "is_achievable": True,
            "daily_savings_recommendation": 0.0,
            "weekly_savings_recommendation": 0.0,
            "recommended_cut_percentage": 0.0,
            "status": "already_achieved",
            "details": "У вас уже достаточно средств на счете для достижения этой цели прямо сейчас.",
        }

    # Случай Б: Дефицит бюджета
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

    # Случай В: Профицит бюджета
    buffer_factor = max(0.0, 1.0 - (risk_buffer_percent / 100.0))
    safe_monthly_savings = round(free_cash_flow * buffer_factor, 2)
    estimated_months = math.ceil(remaining_target / safe_monthly_savings) if safe_monthly_savings > 0 else None

    # Стресс-сценарий (рассчитывается ТОЛЬКО если пользователь сам прямо спросил о трудностях/сессии/спаде дохода)
    stress_scenario_months = None
    if include_stress_scenario and variable_income > 0:
        stress_variable_income = variable_income * 0.60
        stress_monthly_income = guaranteed_income + stress_variable_income
        stress_free_cash_flow = stress_monthly_income - monthly_expenses
        if stress_free_cash_flow > 0:
            stress_safe_savings = stress_free_cash_flow * buffer_factor
            stress_scenario_months = math.ceil(remaining_target / stress_safe_savings) if stress_safe_savings > 0 else None
    else:
        stress_scenario_months = None

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
                f"Необходимо сократить гибкие траты на {shortage_per_month:,.2f} руб./мес. ({recommended_cut}%) "
                f"либо увеличить срок до {estimated_months} мес."
            )
    else:
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
            "Выполняет точный математический расчет финансового плана накопления на конкретную цель. "
            "Вызывай этот инструмент ТОЛЬКО если пользователь хочет накопить деньги на определенную цель, "
            "купить конкретную вещь или отложить определенную сумму (например: 'хочу накопить на ноутбук 60000 руб'). "
            "НЕ вызывай этот инструмент для общих вопросов, аналитики трат, вопросов 'на чем сэкономить', "
            "'какая самая большая трата', баланса или обычного общения — на них отвечай обычным текстом."
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
                    "description": "Стартовые накопления, выделенные на цель, ТОЛЬКО если пользователь прямо указал их в тексте запроса (например: 'у меня уже есть 10 000 ₽'). Если пользователь не назвал сумму стартовых накоплений, передавай 0.0, так как текущий баланс карты нужен студенту для повседневной жизни (питание, общежитие, транспорт)!",
                },
                "target_months": {
                    "type": "integer",
                    "description": "Желаемый срок накопления в месяцах, если пользователь явно указал его в запросе",
                },
                "risk_buffer_percent": {
                    "type": "number",
                    "description": "Процент подушки безопасности/непредвиденных расходов (по умолчанию 10)",
                },
                "include_stress_scenario": {
                    "type": "boolean",
                    "description": "Устанавливай True ТОЛЬКО если пользователь прямо спросил про сессию, экзамены, возможные трудности или спад заработка. Если об этом не спрашивалось, передавай False.",
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
    Анализирует историю транзакций студента и вычисляет корректные СРЕДНЕМЕСЯЧНЫЕ показатели:
    - Определяет количество уникальных месяцев в выборке (например: июль, август, сентябрь = 3 месяца);
    - Делит накопленные суммы доходов и расходов на количество месяцев;
    - Это предотвращает искажение ежемесячного бюджета при наличии истории за несколько месяцев.
    """
    if not transactions:
        return {
            "current_balance": round(current_balance, 2),
            "total_income": 0.0,
            "guaranteed_income": 0.0,
            "variable_income": 0.0,
            "total_expenses": 0.0,
            "regular_expenses": 0.0,
            "discretionary_expenses": 0.0,
            "income_by_category": {},
            "expenses_by_category": {},
            "regular_payments": {},
            "large_transactions": [],
            "free_cash_flow": 0.0,
            "months_analyzed": 1,
        }

    # 1. Определяем уникальные календарные месяцы в выборке транзакций
    months_set = set()
    for tx in transactions:
        if tx.transaction_date:
            months_set.add((tx.transaction_date.year, tx.transaction_date.month))
    months_count = max(1, len(months_set))

    total_income_sum = 0.0
    guaranteed_income_sum = 0.0
    variable_income_sum = 0.0
    total_expenses_sum = 0.0
    regular_expenses_sum = 0.0
    discretionary_expenses_sum = 0.0

    income_by_category: Dict[str, float] = {}
    expenses_by_category: Dict[str, float] = {}
    regular_payments: Dict[str, float] = {}
    large_transactions: List[Dict[str, Any]] = []

    regular_categories = {"Связь и подписки", "Транспорт", "Общежитие и быт"}

    # Сортируем транзакции по дате (от самых свежих)
    sorted_txs = sorted(
        transactions,
        key=lambda x: x.transaction_date if x.transaction_date else datetime.min,
        reverse=True,
    )

    for tx in sorted_txs:
        amount = float(tx.amount)
        category = tx.category or "Прочее"

        if tx.type == TransactionType.INCOME.value or tx.type == "income":
            total_income_sum += amount
            income_by_category[category] = round(income_by_category.get(category, 0.0) + amount, 2)
            if "стипенди" in category.lower() or "стипенди" in (tx.description or "").lower():
                guaranteed_income_sum += amount
            else:
                variable_income_sum += amount
        else:
            total_expenses_sum += amount
            expenses_by_category[category] = round(expenses_by_category.get(category, 0.0) + amount, 2)
            if category in regular_categories:
                regular_expenses_sum += amount
                regular_payments[category] = round(regular_payments.get(category, 0.0) + amount, 2)
            else:
                discretionary_expenses_sum += amount

            if amount >= 1000.0 and len(large_transactions) < 5:
                dt_str = (
                    tx.transaction_date.strftime("%d.%m.%Y")
                    if hasattr(tx.transaction_date, "strftime")
                    else str(tx.transaction_date)
                )
                large_transactions.append({
                    "category": category,
                    "description": tx.description or "Крупная покупка",
                    "amount": round(amount, 2),
                    "date": dt_str,
                })

    # Приводим к среднемесячным значениям (в месяц)
    monthly_income = round(total_income_sum / months_count, 2)
    monthly_expenses = round(total_expenses_sum / months_count, 2)
    guaranteed_income = round(guaranteed_income_sum / months_count, 2)
    variable_income = round(variable_income_sum / months_count, 2)
    regular_expenses = round(regular_expenses_sum / months_count, 2)
    discretionary_expenses = round(discretionary_expenses_sum / months_count, 2)
    free_cash_flow = round(monthly_income - monthly_expenses, 2)

    avg_expenses_by_category = {
        cat: round(amt / months_count, 2)
        for cat, amt in sorted(expenses_by_category.items(), key=lambda item: item[1], reverse=True)
    }
    avg_income_by_category = {
        cat: round(amt / months_count, 2)
        for cat, amt in income_by_category.items()
    }
    avg_regular_payments = {
        cat: round(amt / months_count, 2)
        for cat, amt in regular_payments.items()
    }

    return {
        "current_balance": round(current_balance, 2),
        "total_income": monthly_income,
        "guaranteed_income": guaranteed_income,
        "variable_income": variable_income,
        "total_expenses": monthly_expenses,
        "regular_expenses": regular_expenses,
        "discretionary_expenses": discretionary_expenses,
        "income_by_category": avg_income_by_category,
        "expenses_by_category": avg_expenses_by_category,
        "regular_payments": avg_regular_payments,
        "large_transactions": large_transactions,
        "free_cash_flow": free_cash_flow,
        "months_analyzed": months_count,
        "raw_total_income": round(total_income_sum, 2),
        "raw_total_expenses": round(total_expenses_sum, 2),
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
    months_analyzed = finance_summary.get("months_analyzed", 1)

    expenses_lines = []
    for cat, amount in finance_summary["expenses_by_category"].items():
        percentage = round((amount / expenses * 100), 1) if expenses > 0 else 0
        expenses_lines.append(f"  - {cat}: {amount:,.2f} руб./мес. ({percentage}%)")
    expenses_text = "\n".join(expenses_lines) if expenses_lines else "  Нет данных о расходах."

    regular_lines = [
        f"  - {cat}: {amount:,.2f} руб./мес."
        for cat, amount in finance_summary["regular_payments"].items()
    ]
    regular_text = "\n".join(regular_lines) if regular_lines else "  Нет регулярных платежей."

    safe_savings_est = round(cash_flow * 0.9, 2) if cash_flow > 0 else 0.0

    return f"""Ты — персональный финансовый ИИ-ассистент.
Твой пользователь: студент 18-25 лет, совмещающий учебу в вузе и подработку (фриланс / смены).

ФИНАНСОВЫЙ ПРОФИЛЬ СТУДЕНТА (СРЕДНЕМЕСЯЧНЫЕ ПОКАЗАТЕЛИ ЗА {months_analyzed} МЕС.):
- Баланс дебетовой карты: {balance:,.2f} руб. (средства на текущую жизнь и питание)
- Среднемесячный подтвержденный доход: {income:,.2f} руб./мес.
  * Стипендия: {guaranteed:,.2f} руб./мес.
  * Доход от подработки и смен: {variable:,.2f} руб./мес.
- Среднемесячные расходы: {expenses:,.2f} руб./мес.
  * Обязательные регулярные платежи (связь, транспорт, общежитие): {regular:,.2f} руб./мес.
  * Гибкие расходы (столовая, супермаркеты, кафе, досуг): {discretionary:,.2f} руб./мес.
- Реальный свободный остаток: {cash_flow:,.2f} руб./мес.
- Безопасная сумма для накоплений с учетом 10% подушки безопасности: ~{safe_savings_est:,.2f} руб./мес.
- Структура расходов по категориям в месяц:
{expenses_text}
- Обязательные регулярные списания в месяц:
{regular_text}

СТРОГИЕ ПРАВИЛА:
1. Инструмент `calculate_savings_plan` предназначен ИСКЛЮЧИТЕЛЬНО для точного расчета плана накоплений на конкретную финансовую цель (когда пользователь хочет накопить, купить вещь или отложить конкретную сумму, например: «хочу накопить на ноутбук 60 000 ₽»).
2. ВАЖНО: Среднемесячный свободный остаток студента составляет около {cash_flow:,.2f} руб./мес. Студент МОЖЕТ откладывать ТОЛЬКО безопасную часть от этого остатка (около {safe_savings_est:,.2f} руб./мес.).
   Никогда не предлагай откладывать нереалистичные суммы вроде 50 000 руб./мес., если свободный остаток студента в месяц составляет около {cash_flow:,.2f} руб.!
3. Текущий баланс карты ({balance:,.2f} руб.) — это операционные средства студента на еду и текущую жизнь. Не вычитай его из цели (передавай в tool current_savings=0.0), если только пользователь прямо не попросил использовать свои накопления.
4. Если пользователь задает аналитический вопрос по своим расходам («Какая самая большая трата?», «На чем сэкономить?», «Какой у меня баланс?», «Сколько уходит на кафе?»), отвечай структурированным текстом на основе данных из финансового профиля выше. В таких случаях ЗАПРЕЩЕНО вызывать инструмент `calculate_savings_plan`!
5. Для расчетов по цели накоплений ЗАПРЕЩЕНО считать в уме — ОБЯЗАТЕЛЬНО вызывай инструмент `calculate_savings_plan`.
6. Не давай индивидуальных инвестиционных рекомендаций (ИИР) и не принимай решения за пользователя.
7. Отвечай дружелюбно, структурированно, понятным для студента языком.
8. Если запрос НЕ связан с финансами (болтовня, код, учеба) — вежливо скажи, что ты финансовый помощник, и перечисли свои возможности. НЕ вызывай инструмент.
9. Если указана иностранная валюта — объясни, что сервис работает только с рублями.
10. Если запрос об инвестициях, кредитах, ипотеке — объясни ограничения и перенаправь.
11. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО упоминать сессию, экзамены или стресс-сценарии в стандартных ответах, если пользователь САМ прямо не спросил о возможных трудностях или снижении дохода. Никаких упоминаний сессии «из воздуха»!
12. Если пользователь САМ прямо спросил про сессию, экзамены, временные трудности или спад заработка — передавай в инструмент `calculate_savings_plan` аргумент include_stress_scenario=True и подробно проанализируй возможные риски и срок в ответе.
"""


# =====================================================================
# 4. Резервный парсер запроса пользователя
# =====================================================================

def fallback_extract_target(user_query: str) -> Tuple[Optional[str], Optional[float], Optional[int]]:
    """
    Резервный анализатор запроса с помощью регулярных выражений.
    Извлекает сумму и срок ТОЛЬКО если они явно присутствуют в запросе.
    Никаких сумм по умолчанию (50 000 и т.д.) здесь нет!
    """
    amount = None
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

    # Название цели извлекаем только если пользователь действительно формулирует цель накопления
    title = None
    goal_match = re.search(r"(хочу накопить на|накопить на|собрать на|купить|отложить на)\s*([^\d,\.]+)", user_query, re.IGNORECASE)
    if goal_match:
        extracted_t = goal_match.group(2).strip()
        if extracted_t:
            title = extracted_t.capitalize()
            if len(title) > 60:
                title = title[:57] + "..."

    # Стартовые сбережения (только если пользователь прямо указал их в запросе)
    stated_savings = 0.0
    savings_match = re.search(
        r"(?:уже\s+(?:есть|отложено|накоплено)|сбережени(?:я|й))\s*[:\-—]?\s*(\d+(?:[\s_]\d+)*)\s*(тыс(?:\.|яч[ей|и]?)?|k|к|руб(?:лей|\.)?|р\b)?",
        user_query,
        re.IGNORECASE,
    )
    if savings_match:
        raw_s = re.sub(r"[\s_]+", "", savings_match.group(1))
        u = (savings_match.group(2) or "").lower()
        try:
            s_val = float(raw_s)
            if any(k in u for k in ["тыс", "k", "к"]) and s_val < 100000:
                s_val *= 1000.0
            stated_savings = s_val
        except ValueError:
            pass

    return title, amount, months, stated_savings


# =====================================================================
# 5. Главный метод взаимодействия с LLM через Tool Calling
# =====================================================================

async def process_ai_financial_advice(
    user_query: str,
    transactions: List[Transaction],
    user_balance: float,
) -> Dict[str, Any]:
    """
    Основная логика ИИ-модуля финансового ассистента:
    0. Классифицирует запрос (финансовый / нерелевантный / рискованный).
    1. Для нерелевантных — возвращает лёгкий ответ без расчётов.
    2. Для рискованных — обозначает ограничения без вызова Tool Calling.
    3. Для финансовых — полный пайплайн: профиль → LLM → Tool Calling → план.
    """
    # Шаг 0: Классификация запроса
    classification = classify_query(user_query)
    query_type = classification["type"]

    # Базовая финансовая сводка (нужна для полей user_balance и т.п.)
    finance_summary = summarize_user_finances(transactions, user_balance)

    # --- НЕРЕЛЕВАНТНЫЙ ЗАПРОС (болтовня, программирование, прочее) ---
    if query_type == "off_topic":
        print(f"Классификация запроса: OFF_TOPIC — «{user_query[:50]}...»")
        advice_text = build_off_topic_response(user_query)
        return {
            "advice": advice_text,
            "calculation": None,
            "user_balance": finance_summary["current_balance"],
            "monthly_income": finance_summary["total_income"],
            "monthly_expenses": finance_summary["total_expenses"],
            "top_expense_categories": finance_summary["expenses_by_category"],
            "regular_payments": finance_summary.get("regular_payments", {}),
            "large_transactions": [],
            "action_items": [],
            "limitations": (
                "⚠️ Ограничения сервиса: Я — финансовый ИИ-помощник и могу отвечать "
                "только на вопросы, связанные с бюджетом, накоплениями и расходами студента. "
                "Вопросы по программированию, учёбе и другим темам — вне моей компетенции."
            ),
            "disclaimer": SERVICE_DISCLAIMER,
            "sources": [],
            "extracted_goal": None,
        }

    # --- РИСКОВАННЫЙ ЗАПРОС (иностранная валюта, инвестиции, кредиты, азарт) ---
    if query_type == "risky":
        print(f"Классификация запроса: RISKY ({classification['reason']}) — «{user_query[:50]}...»")
        advice_text = build_risky_response(classification["reason"], classification.get("details"))
        return {
            "advice": advice_text,
            "calculation": None,
            "user_balance": finance_summary["current_balance"],
            "monthly_income": finance_summary["total_income"],
            "monthly_expenses": finance_summary["total_expenses"],
            "top_expense_categories": finance_summary["expenses_by_category"],
            "regular_payments": finance_summary.get("regular_payments", {}),
            "large_transactions": [],
            "action_items": [],
            "limitations": (
                f"⚠️ Ограничения сервиса: Запрос классифицирован как «{classification['reason']}». "
                f"Сервис работает только с рублёвыми целями накоплений для студентов. "
                f"Не даём инвестиционных рекомендаций, не консультируем по кредитам и займам."
            ),
            "disclaimer": SERVICE_DISCLAIMER,
            "sources": [],
            "extracted_goal": None,
        }

    # --- ФИНАНСОВЫЙ ЗАПРОС: полный пайплайн с Tool Calling ---
    print(f"Классификация запроса: FINANCIAL — «{user_query[:50]}...»")
    system_prompt = build_system_prompt(finance_summary)

    client = AsyncOpenAI(
        api_key=OPENAI_API_KEY or "dummy-key-for-local-fallback",
        base_url=OPENAI_BASE_URL,
    )

    calculation_result: Optional[Dict[str, Any]] = None
    ai_advice_text: str = ""
    goal_title, extracted_amount, extracted_months, stated_savings = fallback_extract_target(user_query)

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
                    raw_target = tool_args.get("target_amount") or extracted_amount

                    if raw_target and float(raw_target) > 0:
                        # Проверяем, заявлял ли пользователь о наличии стартовых сбережений на цель
                        user_stated_savings = bool(
                            re.search(
                                r"(у меня (?:уже )?(?:есть|отложено)|накоплено|сбережения?|стартов(?:ый|ые))",
                                user_query,
                                re.IGNORECASE,
                            )
                        )
                        passed_savings = float(tool_args.get("current_savings", 0.0))
                        # Если пользователь явно не называл сбережения, не тратим операционный баланс карты
                        actual_savings = passed_savings if user_stated_savings else 0.0

                        # Проверяем, спрашивал ли пользователь о трудностях, экзаменах или снижении дохода
                        has_hardship_query = bool(
                            re.search(
                                r"(сесси[яиею]|экзамен[ыа]|спад|трудн|проблем|сложност|увольн|болезн|форс-мажор|если.*(?:упадет|снизится|меньше|сократ)|хватит ли)",
                                user_query,
                                re.IGNORECASE,
                            )
                        )
                        include_stress = bool(tool_args.get("include_stress_scenario", False)) or has_hardship_query

                        calculation_result = calculate_savings_plan(
                            target_amount=float(raw_target),
                            monthly_income=float(finance_summary["total_income"]),
                            monthly_expenses=float(finance_summary["total_expenses"]),
                            guaranteed_income=float(finance_summary["guaranteed_income"]),
                            variable_income=float(finance_summary["variable_income"]),
                            regular_expenses=float(finance_summary["regular_expenses"]),
                            discretionary_expenses=float(finance_summary["discretionary_expenses"]),
                            current_savings=actual_savings,
                            target_months=tool_args.get("target_months") or extracted_months,
                            risk_buffer_percent=float(tool_args.get("risk_buffer_percent", 10.0)),
                            include_stress_scenario=include_stress,
                        )

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(calculation_result, ensure_ascii=False),
                        })

            # Шаг 3: Финальный ответ модели
            second_response = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
            )
            ai_advice_text = second_response.choices[0].message.content or ""
        else:
            # LLM не вызвал Tool Calling — запрос не требует расчёта
            # (аналитический вопрос, общий финансовый вопрос, вопрос о тратах и т.п.)
            ai_advice_text = response_message.content or ""
            calculation_result = None
            print("LLM ответил без Tool Calling — расчёт накоплений не требуется.")

    except Exception as exc:
        print(f"Обработка запроса через резервный локальный движок (причина: {exc})")

        # Пытаемся определить: запрос требует расчёт накопления или это аналитический вопрос?
        savings_markers = re.search(
            r"(накопить|копить|отложить|собрать|откладывать|сколько.*откладывать|хочу\s+купить)",
            user_query, re.IGNORECASE
        )

        has_hardship_query = bool(
            re.search(
                r"(сесси[яиею]|экзамен[ыа]|спад|трудн|проблем|сложност|увольн|болезн|форс-мажор|если.*(?:упадет|снизится|меньше|сократ)|хватит ли)",
                user_query,
                re.IGNORECASE,
            )
        )

        if savings_markers and extracted_amount and extracted_amount > 0:
            # Запрос про конкретное накопление — делаем резервный расчёт
            calculation_result = calculate_savings_plan(
                target_amount=extracted_amount,
                monthly_income=finance_summary["total_income"],
                monthly_expenses=finance_summary["total_expenses"],
                guaranteed_income=finance_summary["guaranteed_income"],
                variable_income=finance_summary["variable_income"],
                regular_expenses=finance_summary["regular_expenses"],
                discretionary_expenses=finance_summary["discretionary_expenses"],
                current_savings=stated_savings,
                target_months=extracted_months,
                include_stress_scenario=has_hardship_query,
            )

            top_cats = list(finance_summary["expenses_by_category"].items())[:3]
            top_cats_text = ", ".join([f"{c} ({a:,.0f} руб.)" for c, a in top_cats]) if top_cats else "отсутствуют"

            if calculation_result["is_achievable"]:
                months_text = f"{calculation_result['estimated_months']} мес." if calculation_result['estimated_months'] else "12 мес."
                stress_info = ""
                if calculation_result.get("stress_scenario_months"):
                    stress_info = f"\n- В период возможных трудностей (при спаде подработки на 40%): **{calculation_result['stress_scenario_months']} мес.**"

                ai_advice_text = (
                    f"🎯 **Финансовый план накопления для студента**\n\n"
                    f"Цель: **{goal_title or 'Накопление'}** на сумму **{calculation_result['target_amount']:,.2f} руб.**\n\n"
                    f"📊 **Точный расчет бюджета:**\n"
                    f"- Свободный остаток: {calculation_result['free_cash_flow']:,.2f} руб./мес.\n"
                    f"- Рекомендуемый темп: **{calculation_result['required_monthly_savings']:,.2f} руб./мес.** (~{calculation_result['daily_savings_recommendation']:,.2f} руб./день)\n"
                    f"- Срок достижения цели: **{months_text}**{stress_info}\n\n"
                    f"💡 **Рекомендации:**\n"
                    f"Основные гибкие траты: {top_cats_text}. "
                    f"Сократив их на 10-15%, вы создадите подушку безопасности и быстрее достигнете цели!"
                )
            else:
                ai_advice_text = (
                    f"⚠️ **Анализ бюджета выявил дефицит свободных средств**\n\n"
                    f"Цель: **{goal_title or 'Накопление'}** на сумму **{calculation_result['target_amount']:,.2f} руб.**\n\n"
                    f"Текущие расходы ({calculation_result['monthly_expenses']:,.2f} руб.) превышают доход ({calculation_result['monthly_income']:,.2f} руб.).\n"
                    f"Необходимо сократить гибкие расходы на {calculation_result['recommended_cut_percentage']}%."
                )
        else:
            # Аналитический или общий финансовый вопрос — отвечаем без расчёта
            calculation_result = None
            top_cats = list(finance_summary["expenses_by_category"].items())[:3]
            top_cats_text = ", ".join([f"{c} ({a:,.0f} руб.)" for c, a in top_cats]) if top_cats else "нет данных"

            large = finance_summary.get("large_transactions", [])
            largest_text = ""
            if large:
                lg = large[0]
                largest_text = f"Самая крупная трата: {lg['description']} — {lg['amount']:,.2f} руб. ({lg['category']}, {lg['date']}).\n"

            ai_advice_text = (
                f"📊 **Финансовая сводка за месяц**\n\n"
                f"- Баланс: {finance_summary['current_balance']:,.2f} руб.\n"
                f"- Доходы: {finance_summary['total_income']:,.2f} руб.\n"
                f"- Расходы: {finance_summary['total_expenses']:,.2f} руб.\n"
                f"- Свободный остаток: {finance_summary['free_cash_flow']:,.2f} руб./мес.\n\n"
                f"Топ категорий расходов: {top_cats_text}.\n"
                f"{largest_text}\n"
                f"Если хочешь рассчитать план накопления на покупку, укажи сумму и желаемый срок!"
            )

    # Формируем конкретные шаги только если был расчет финансовой цели
    action_items = []
    if calculation_result and calculation_result.get("required_monthly_savings", 0) > 0:
        monthly_save = calculation_result["required_monthly_savings"]
        action_items = [
            f"Настроить автоперевод в копилку: переводить {monthly_save / 2:,.0f} руб. в день стипендии и в день зарплаты.",
            "Установить недельный лимит на кафе и доставку еды в приложении банка.",
            "Проверить платные подписки и отключить неиспользуемые.",
            "Не трогать подушку безопасности (10% от свободных средств) на случай непредвиденных расходов.",
        ]

    # Данные для сохранения цели в БД формируются только если цель реально рассчитывалась
    extracted_goal_info = None
    if calculation_result and calculation_result.get("target_amount", 0) > 0:
        extracted_goal_info = {
            "title": goal_title or "Финансовая цель",
            "target_amount": calculation_result["target_amount"],
            "target_months": calculation_result.get("estimated_months") or extracted_months,
        }

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
        "limitations": SERVICE_LIMITATIONS if calculation_result else "",
        "disclaimer": SERVICE_DISCLAIMER,
        "sources": TRUSTED_FINANCIAL_SOURCES if calculation_result else [],
        "extracted_goal": extracted_goal_info,
    }
