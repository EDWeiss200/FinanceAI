# Руководство по интеграции с Backend API для Frontend разработчика
**Проект:** Finance AI Assistant — Умный финансовый помощник для студентов  
**Базовый URL:** `http://localhost:8000` (или `http://127.0.0.1:8000`)  
**Интерактивная документация (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)  
**Спецификация OpenAPI (JSON):** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 📌 Общие принципы работы

1. **Формат данных:** Все запросы и ответы используют `application/json` (кроме формы логина, которая принимает `application/x-www-form-urlencoded`).
2. **CORS:** Настроен для `http://localhost:5173`, `http://localhost:3000`, `http://127.0.0.1:5173`, `*` с поддержкой передачи заголовков авторизации и cookie (`credentials: true`).
3. **Авторизация:** Поддерживаются **два способа**:
   * **Bearer Token в заголовке (Рекомендуется для React / Vue / мобилок):**  
     `Authorization: Bearer <access_token>`
   * **Куки (Cookie):**  
     Автоматически сохраняется cookie `robert-cookie` при входе через `/auth/jwt/login`.

---

## 🔐 1. Авторизация и регистрация

### 1.1 Регистрация нового студента
При успешной регистрации бэкенд **автоматически создает реалистичную финансовую песочницу**:
* Баланс на карте: от 4 500 до 14 500 руб.
* Доходы: государственная стипендия, смены на подработке, помощь от родителей, кэшбэк.
* Расходы за 30 дней: столовая вуза, супермаркеты, студенческий транспорт, шаурма/фастфуд, печать лаб, общежитие, подписки.

* **Метод:** `POST`
* **URL:** `/auth/register`
* **Тело запроса (JSON):**
```json
{
  "email": "student@university.ru",
  "password": "StrongPassword123!",
  "username": "Иван Смирнов"
}
```
* **Ответ (201 Created):**
```json
{
  "id": 1,
  "email": "student@university.ru",
  "username": "Иван Смирнов",
  "balance": 9850.50,
  "is_active": true,
  "is_superuser": false,
  "is_verified": false
}
```

---

### 1.2 Вход (Получение Bearer токена) — Рекомендуемый способ
* **Метод:** `POST`
* **URL:** `/auth/bearer/login`
* **Content-Type:** `application/x-www-form-urlencoded`
* **Параметры формы (form-data):**
  * `username` (строка): email пользователя (например, `student@university.ru`)
  * `password` (строка): пароль
* **Ответ (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```
> **Важно:** Сохраните `access_token` в `localStorage` или в state менеджере (Pinia, Redux, Zustand) и передавайте во все последующие запросы:
> `headers: { "Authorization": `Bearer ${token}` }`

---

### 1.3 Вход через Cookie (Альтернативный способ)
* **Метод:** `POST`
* **URL:** `/auth/jwt/login`
* **Content-Type:** `application/x-www-form-urlencoded`
* **Параметры формы:** `username`, `password`
* **Ответ:** 204 No Content (ставится кука `robert-cookie`).

---

## 👤 2. Профиль и баланс пользователя

### 2.1 Получение текущего профиля и баланса
* **Метод:** `GET`
* **URL:** `/users/me`
* **Заголовки:** `Authorization: Bearer <access_token>`
* **Ответ (200 OK):**
```json
{
  "id": 1,
  "username": "Иван Смирнов",
  "email": "student@university.ru",
  "balance": 9850.50
}
```

---

## 📊 3. Аналитика расходов и доходов по категориям

### 3.1 Сводка категорий (Идеально для графиков, круговых диаграмм и дашбордов)
* **Метод:** `GET`
* **URL:** `/users/categories`
* **Заголовки:** `Authorization: Bearer <access_token>`
* **Query-параметры (необязательные):**
  * `sort_by` (строка, по умолчанию `"amount_desc"`):
    * `amount_desc` — по убыванию суммы трат/доходов (от самых крупных к мелким);
    * `amount_asc` — по возрастанию суммы;
    * `count_desc` — по частоте покупок (показывает частые микро-траты студента: столовая, проезд);
    * `name` — по алфавиту названий категорий.
  * `tx_type` (строка, опционально):
    * `expense` — вернуть только категории расходов;
    * `income` — вернуть только категории доходов;
    * `null` (не передавать) — вернуть и доходы, и расходы.

* **Пример запроса:** `/users/categories?sort_by=amount_desc`
* **Ответ (200 OK):**
```json
{
  "current_balance": 9850.50,
  "total_income": 26989.42,
  "total_expense": 12431.00,
  "net_cash_flow": 14558.42,
  "expense_categories": [
    {
      "category": "Супермаркеты (продукты)",
      "type": "expense",
      "total_amount": 3980.00,
      "count": 8,
      "percentage": 32.0,
      "average_amount": 497.50,
      "transactions": [
        {
          "id": 14,
          "user_id": 1,
          "amount": 540.00,
          "type": "expense",
          "category": "Супермаркеты (продукты)",
          "description": "Пятёрочка: макароны, яйца, чай",
          "transaction_date": "2026-09-24T15:30:00Z"
        }
      ]
    },
    {
      "category": "Столовая и перекусы",
      "type": "expense",
      "total_amount": 2177.73,
      "count": 12,
      "percentage": 17.5,
      "average_amount": 181.48,
      "transactions": []
    },
    {
      "category": "Досуг с друзьями",
      "type": "expense",
      "total_amount": 1478.88,
      "count": 3,
      "percentage": 11.9,
      "average_amount": 492.96,
      "transactions": []
    },
    {
      "category": "Фастфуд и шаурма",
      "type": "expense",
      "total_amount": 1444.43,
      "count": 5,
      "percentage": 11.6,
      "average_amount": 288.89,
      "transactions": []
    },
    {
      "category": "Общежитие и быт",
      "type": "expense",
      "total_amount": 1119.37,
      "count": 2,
      "percentage": 9.0,
      "average_amount": 559.68,
      "transactions": []
    },
    {
      "category": "Транспорт",
      "type": "expense",
      "total_amount": 947.36,
      "count": 10,
      "percentage": 7.6,
      "average_amount": 94.74,
      "transactions": []
    },
    {
      "category": "Связь и подписки",
      "type": "expense",
      "total_amount": 864.95,
      "count": 3,
      "percentage": 7.0,
      "average_amount": 288.32,
      "transactions": []
    },
    {
      "category": "Учеба и печать",
      "type": "expense",
      "total_amount": 418.28,
      "count": 3,
      "percentage": 3.4,
      "average_amount": 139.43,
      "transactions": []
    }
  ],
  "income_categories": [
    {
      "category": "Подработка и смены",
      "type": "income",
      "total_amount": 17817.00,
      "count": 1,
      "percentage": 66.0,
      "average_amount": 17817.00,
      "transactions": []
    },
    {
      "category": "Помощь от родителей",
      "type": "income",
      "total_amount": 5779.33,
      "count": 1,
      "percentage": 21.4,
      "average_amount": 5779.33,
      "transactions": []
    },
    {
      "category": "Стипендия",
      "type": "income",
      "total_amount": 3018.94,
      "count": 1,
      "percentage": 11.2,
      "average_amount": 3018.94,
      "transactions": []
    },
    {
      "category": "Кэшбэк",
      "type": "income",
      "total_amount": 374.15,
      "count": 1,
      "percentage": 1.4,
      "average_amount": 374.15,
      "transactions": []
    }
  ]
}
```

---

## 💳 4. Транзакции (История операций)

### 4.1 Получить список всех транзакций пользователя
* **Метод:** `GET`
* **URL:** `/users/transactions`
* **Заголовки:** `Authorization: Bearer <access_token>`
* **Query-параметры:**
  * `tx_type` (опционально): `"income"` или `"expense"`
* **Ответ (200 OK):** Массив объектов `TransactionReadSchema`, отсортированных по дате (свежие сверху):
```json
[
  {
    "id": 1,
    "user_id": 1,
    "amount": 3018.94,
    "type": "income",
    "category": "Стипендия",
    "description": "Академическая стипендия вуза",
    "transaction_date": "2026-09-14T12:00:00Z"
  },
  {
    "id": 2,
    "user_id": 1,
    "amount": 250.00,
    "type": "expense",
    "category": "Столовая и перекусы",
    "description": "Обед в столовой: суп и второе",
    "transaction_date": "2026-09-25T11:45:00Z"
  }
]
```

---

## 🤖 5. Финансовый ИИ-помощник (Кейс Т-Банка)

### 5.1 Запрос к ИИ-консультанту
Принимает естественный запрос студента, загружает историю его доходов и расходов, передает в нейросеть с **механизмом Tool Calling** (точный расчет математики кодом).

* **Метод:** `POST`
* **URL:** `/users/advisor`
* **Заголовки:** `Authorization: Bearer <access_token>`
* **Тело запроса (JSON):**
```json
{
  "query": "Хочу накопить на новый учебный ноутбук 60000 рублей за 6 месяцев. Реально ли это?",
  "save_as_goal": true
}
```
> Если `save_as_goal = true`, бэкенд **автоматически создаст запись в таблице финансовых целей пользователя** (`/users/goals`).

* **Ответ (200 OK):**
```json
{
  "advice": "🎯 **Финансовый план накопления для студента**\n\nЦель: **Учебный ноутбук** на сумму **60,000.00 руб.**...",
  "calculation": {
    "target_amount": 60000.0,
    "current_savings": 0.0,
    "remaining_target": 60000.0,
    "monthly_income": 26989.42,
    "guaranteed_income": 3018.94,
    "variable_income": 23970.48,
    "monthly_expenses": 12431.00,
    "regular_expenses": 2931.68,
    "discretionary_expenses": 9499.32,
    "free_cash_flow": 14558.42,
    "safe_monthly_savings": 13102.58,
    "required_monthly_savings": 10000.0,
    "estimated_months": 5,
    "stress_scenario_months": 9,
    "is_achievable": true,
    "daily_savings_recommendation": 333.33,
    "weekly_savings_recommendation": 2309.47,
    "recommended_cut_percentage": 0.0,
    "status": "success",
    "details": "Цель полностью реалистична! Для накопления 60,000.00 руб. за 6 мес. достаточно откладывать по 10,000.00 руб./мес. При этом сохраняется подушка безопасности 10.0% на непредвиденные траты."
  },
  "user_balance": 9850.50,
  "monthly_income": 26989.42,
  "monthly_expenses": 12431.00,
  "top_expense_categories": {
    "Супермаркеты (продукты)": 3980.00,
    "Столовая и перекусы": 2177.73,
    "Досуг с друзьями": 1478.88
  },
  "regular_payments": {
    "Связь и подписки": 864.95,
    "Транспорт": 947.36,
    "Общежитие и быт": 1119.37
  },
  "large_transactions": [
    {
      "category": "Общежитие и быт",
      "description": "Оплата проживания в общежитии за месяц",
      "amount": 1050.00,
      "date": "10.09.2026"
    }
  ],
  "action_items": [
    "Настроить автоперевод в копилку: сразу переводить по 5,000 руб. в день стипендии и в день зарплаты за смену.",
    "Установить недельный лимит на кафе и фастфуд в мобильном приложении банка.",
    "Проверить список платных подписок и отключить те сервисы, которыми редко пользуетесь во время учебы.",
    "Не трогать резервную подушку безопасности (10% от свободных денег), чтобы не залезать в долги в сессию."
  ],
  "limitations": "Ограничения расчетов: Математический прогноз построен на основе данных за последние 30 дней и предполагает сохранение текущего темпа заработка. Не учитывает внезапные форс-мажоры. Для студентов с нестабильной подработкой рекомендуется ориентироваться на консервативный сценарий.",
  "disclaimer": "⚠️ Важное уведомление: Сервис носит исключительно информационно-просветительский характер, не является индивидуальной инвестиционной рекомендацией (ИИР) и не принимает финансовые решения вместо пользователя.",
  "sources": [
    "https://journal.tinkoff.ru/guide/smart-budget/ — Т-Ж: Как грамотно распределять бюджет студенту",
    "https://fincult.info/article/finansovyy-plan-dlya-nachinayushchikh/ — Финансовая культура (Банк России): Личный финансовый план"
  ],
  "goal_created": {
    "id": 1,
    "user_id": 1,
    "title": "Учебный ноутбук",
    "target_amount": 60000.0,
    "current_amount": 0.0,
    "deadline": "2027-03-26",
    "created_at": "2026-09-26T18:45:00Z"
  }
}
```

---

## 🎯 6. Финансовые цели (Goals)

### 6.1 Список всех целей студента
* **Метод:** `GET`
* **URL:** `/users/goals`
* **Заголовки:** `Authorization: Bearer <access_token>`
* **Ответ (200 OK):**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Учебный ноутбук",
    "target_amount": 60000.0,
    "current_amount": 10000.0,
    "deadline": "2027-03-26",
    "created_at": "2026-09-26T18:45:00Z"
  }
]
```

### 6.2 Создание цели вручную
* **Метод:** `POST`
* **URL:** `/users/goals`
* **Заголовки:** `Authorization: Bearer <access_token>`
* **Тело запроса (JSON):**
```json
{
  "title": "Новые беспроводные наушники",
  "target_amount": 15000.0,
  "current_amount": 2000.0,
  "deadline": "2026-12-31"
}
```
* **Ответ (201 Created):** Объект созданной цели.

---

## 💻 7. Готовые интерфейсы TypeScript для фронтенда

Скопируйте этот блок в ваш файл `src/types/api.ts`:

```typescript
// 1. Профиль пользователя
export interface UserProfile {
  id: number;
  username: string;
  email: string;
  balance: number;
}

// 2. Транзакция
export interface Transaction {
  id: number;
  user_id: number;
  amount: number;
  type: 'income' | 'expense';
  category: string;
  description: string | null;
  transaction_date: string;
}

// 3. Категория в аналитике
export interface CategorySummaryItem {
  category: string;
  type: 'income' | 'expense';
  total_amount: number;
  count: number;
  percentage: number;
  average_amount: number;
  transactions: Transaction[];
}

export interface CategoriesSummaryResponse {
  current_balance: number;
  total_income: number;
  total_expense: number;
  net_cash_flow: number;
  income_categories: CategorySummaryItem[];
  expense_categories: CategorySummaryItem[];
}

// 4. Финансовая цель
export interface Goal {
  id: number;
  user_id: number;
  title: string;
  target_amount: number;
  current_amount: number;
  deadline: string | null;
  created_at: string;
}

// 5. Результат точного математического расчета Tool Calling
export interface SavingsPlanCalculation {
  target_amount: number;
  current_savings: number;
  remaining_target: number;
  monthly_income: number;
  guaranteed_income: number;
  variable_income: number;
  monthly_expenses: number;
  regular_expenses: number;
  discretionary_expenses: number;
  free_cash_flow: number;
  safe_monthly_savings: number;
  required_monthly_savings: number;
  estimated_months: number | null;
  stress_scenario_months: number | null; // Срок накопления в сессию при падении подработки на 40%
  is_achievable: boolean;
  daily_savings_recommendation: number;
  weekly_savings_recommendation: number;
  recommended_cut_percentage: number;
  status: 'success' | 'deficit' | 'already_achieved';
  details: string;
}

// 6. Ответ ИИ-помощника
export interface AIAdvisorResponse {
  advice: string;
  calculation: SavingsPlanCalculation | null;
  user_balance: number;
  monthly_income: number;
  monthly_expenses: number;
  top_expense_categories: Record<string, number>;
  regular_payments: Record<string, number>;
  large_transactions: Array<{
    category: string;
    description: string;
    amount: number;
    date: string;
  }>;
  action_items: string[];
  limitations: string;
  disclaimer: string;
  sources: string[];
  goal_created: Goal | null;
}
```

---

## 🚀 8. Пример вызова на Axios / Fetch

### Настройка экземпляра Axios (`src/api/client.ts`):
```typescript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true, // для работы с cookie
});

// Автоматическая подстановка токена из памяти
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Запрос к ИИ-консультанту:
```typescript
import { apiClient } from './client';
import { AIAdvisorResponse } from '../types/api';

export async function askFinancialAdvisor(query: string, saveAsGoal = true): Promise<AIAdvisorResponse> {
  const response = await apiClient.post<AIAdvisorResponse>('/users/advisor', {
    query,
    save_as_goal: saveAsGoal,
  });
  return response.data;
}
```

### Получение категорий для круговой диаграммы:
```typescript
import { apiClient } from './client';
import { CategoriesSummaryResponse } from '../types/api';

export async function fetchCategories(): Promise<CategoriesSummaryResponse> {
  const response = await apiClient.get<CategoriesSummaryResponse>('/users/categories?sort_by=amount_desc');
  return response.data;
}
```
