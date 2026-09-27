import React, { useState, useEffect } from 'react';
import { useAuth } from '../../../context/AuthContext';
import ChatAssistant from '../ChatAssistant';
import './Home.css';

const MONTHS = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

export default function Home() {
  const { user, token, logout } = useAuth();
  const [currentMonthIndex, setCurrentMonthIndex] = useState(8); // Сентябрь по умолчанию
  
  // Данные категорий с бэкенда
  const [incomeCategories, setIncomeCategories] = useState([]);
  const [expenseCategories, setExpenseCategories] = useState([]);
  const [currentBalance, setCurrentBalance] = useState(user?.balance || 0);
  const [netCashFlow, setNetCashFlow] = useState(0);
  const [loading, setLoading] = useState(true);

  // Финансовые цели пользователя
  const [goals, setGoals] = useState([]);
  const [loadingGoals, setLoadingGoals] = useState(false);

  // Состояние выбранной категории для детального просмотра операций
  const [selectedCategory, setSelectedCategory] = useState(null);

  const currentMonth = MONTHS[currentMonthIndex];

  // Форматирование даты транзакции
  const formatTransactionDate = (dateStr) => {
    if (!dateStr) return 'Не указана';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  // Загрузка категорий из API
  useEffect(() => {
    async function loadCategories() {
      setLoading(true);
      try {
        if (!token) {
          logout();
          return;
        }
        const headers = { 'Authorization': `Bearer ${token}` };

        const monthNumber = currentMonthIndex + 1;
        const year = 2026;

        const res = await fetch(`http://localhost:8000/users/categories?month=${monthNumber}&year=${year}&sort_by=amount_desc`, {
          headers
        });

        if (res.status === 401) {
          logout();
          return;
        }

        if (res.ok) {
          const data = await res.json();
          // Доходы и расходы автоматически сгруппированы бэкендом за выбранный месяц
          setIncomeCategories(data.income_categories || []);
          setExpenseCategories(data.expense_categories || []);
          if (data.current_balance !== undefined) {
            setCurrentBalance(data.current_balance);
          }
          if (data.net_cash_flow !== undefined) {
            setNetCashFlow(data.net_cash_flow);
          }
        } else {
          setIncomeCategories([]);
          setExpenseCategories([]);
        }
      } catch (err) {
        console.error('Ошибка при загрузке категорий:', err);
        setIncomeCategories([]);
        setExpenseCategories([]);
      } finally {
        setLoading(false);
      }
    }

    loadCategories();
  }, [currentMonthIndex, token]);

  // Загрузка финансовых целей пользователя
  const loadGoals = async () => {
    if (!token) return;
    try {
      setLoadingGoals(true);
      const res = await fetch('http://localhost:8000/users/goals', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.status === 401) {
        logout();
        return;
      }
      if (res.ok) {
        const data = await res.json();
        setGoals(data || []);
      }
    } catch (err) {
      console.error('Ошибка при загрузке целей:', err);
    } finally {
      setLoadingGoals(false);
    }
  };

  // Загружаем цели при монтировании и изменении токена
  useEffect(() => {
    loadGoals();
  }, [token]);

  // Слушатель события создания цели из ИИ-чата
  useEffect(() => {
    const handleGoalEvent = () => {
      loadGoals();
    };
    window.addEventListener('finance_goal_created', handleGoalEvent);
    return () => window.removeEventListener('finance_goal_created', handleGoalEvent);
  }, [token]);

  // Удаление финансовой цели
  const handleDeleteGoal = async (goalId, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`http://localhost:8000/users/goals/${goalId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok || res.status === 204) {
        setGoals((prev) => prev.filter((g) => g.id !== goalId));
      }
    } catch (err) {
      console.error('Ошибка при удалении цели:', err);
    }
  };

  // Закрытие модального окна по Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSelectedCategory(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Переключение месяца
  const handlePrevMonth = () => {
    setCurrentMonthIndex((prev) => (prev === 0 ? 11 : prev - 1));
  };

  const handleNextMonth = () => {
    setCurrentMonthIndex((prev) => (prev === 11 ? 0 : prev + 1));
  };

  return (
    <div className="dashboard-container">
      {/* Боковая панель */}
      <aside className="sidebar">
        <div className="sidebar-group">
          <div className="circle-btn active-app-icon" title="FinanceAI">AI</div>
        </div>
        <div className="sidebar-group bottom">
          <div className="circle-btn logout-circle-btn" onClick={logout} title="Выйти из аккаунта">
            🚪
          </div>
        </div>
      </aside>

      {/* Основной контент */}
      <main className="main-content">
        {/* Верхняя панель: выбор месяца, баланс и профиль */}
        <header className="dashboard-header">
          <div className="month-selector">
            <div className="month-badge">{currentMonth}</div>
            <div className="month-controls">
              <button className="nav-arrow" onClick={handlePrevMonth} title="Предыдущий месяц">&lt;</button>
              <button className="nav-arrow" onClick={handleNextMonth} title="Следующий месяц">&gt;</button>
            </div>
          </div>

          <div className="header-right-actions">
            <div className="current-balance-card">
              <div className="balance-icon-pill">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="5" width="20" height="14" rx="2" />
                  <line x1="2" y1="10" x2="22" y2="10" />
                </svg>
              </div>
              <div className="balance-text-block">
                <span className="balance-label">Текущий баланс</span>
                <span className="balance-value">
                  {Number(currentBalance).toLocaleString('ru-RU')} ₽
                </span>
              </div>
              {netCashFlow !== 0 && (
                <div
                  className={`balance-trend-badge ${netCashFlow > 0 ? 'positive' : 'negative'}`}
                  title={`Чистый итог за ${currentMonth.toLowerCase()}`}
                >
                  {netCashFlow > 0 ? '↑ +' : '↓ '}{Number(netCashFlow).toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽
                </div>
              )}
            </div>

            <div className="user-profile-widget">
              <div className="user-avatar-badge" title={user?.email || 'Профиль'}>
                {user?.username ? user.username.charAt(0).toUpperCase() : '👤'}
              </div>
              <div className="user-text-info">
                <span className="user-name-span">{user?.username || 'Студент'}</span>
                <span className="user-email-span">{user?.email || ''}</span>
              </div>
              <button className="user-logout-button" onClick={logout} title="Выйти из системы">
                Выйти
              </button>
            </div>
          </div>
        </header>

        {/* Секция Финансовые цели */}
        <section className="cards-section goals-section">
          <div className="section-title-wrap">
            <h2 className="section-title">
              🎯 Финансовые цели
              {goals.length > 0 && (
                <span className="section-count-tag">{goals.length}</span>
              )}
            </h2>
          </div>

          {loadingGoals ? (
            <div className="cards-status-box">
              <span className="status-spinner">⏳</span> Загрузка целей...
            </div>
          ) : goals.length > 0 ? (
            <div className="cards-row goals-cards-row">
              {goals.map((goal) => {
                const target = Number(goal.target_amount) || 0;
                const current = Number(goal.current_amount) || 0;
                const percent = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;

                let deadlineFormatted = 'Срок не указан';
                if (goal.deadline) {
                  try {
                    const d = new Date(goal.deadline);
                    deadlineFormatted = d.toLocaleDateString('ru-RU', {
                      month: 'long',
                      year: 'numeric',
                    });
                  } catch {
                    deadlineFormatted = goal.deadline;
                  }
                }

                return (
                  <div key={goal.id} className="card goal-card" title={goal.title}>
                    <div className="card-header goal-card-header">
                      <div className="goal-title-wrap">
                        <span className="goal-flag-icon">🎯</span>
                        <span className="goal-title-text">{goal.title}</span>
                      </div>
                      <button
                        className="goal-card-close-btn"
                        onClick={(e) => handleDeleteGoal(goal.id, e)}
                        title="Удалить цель"
                      >
                        ✕
                      </button>
                    </div>

                    <div className="card-body goal-card-body">
                      <div className="goal-amount-row">
                        <span className="card-amount goal-amount">
                          {target.toLocaleString('ru-RU')} ₽
                        </span>
                        <span className="goal-status-badge">
                          {percent >= 100 ? 'Выполнена' : 'В процессе'}
                        </span>
                      </div>

                      {/* Прогресс накоплений */}
                      <div className="goal-progress-box">
                        <div className="goal-progress-track">
                          <div
                            className="goal-progress-bar"
                            style={{ width: `${Math.max(5, percent)}%` }}
                          ></div>
                        </div>
                        <div className="goal-progress-info">
                          <span>{current.toLocaleString('ru-RU')} ₽</span>
                          <span className="goal-progress-percent">{percent}%</span>
                        </div>
                      </div>

                      <div className="goal-card-footer">
                        <span className="goal-deadline-pill">
                          📅 {deadlineFormatted}
                        </span>
                        <span className="goal-ai-pill">✨ ИИ-план</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-goals-banner">
              <div className="empty-goals-left">
                <span className="empty-goals-icon">🎯</span>
                <div className="empty-goals-texts">
                  <span className="empty-goals-heading">У вас пока нет активных целей накопления</span>
                  <span className="empty-goals-subtext">
                    Напишите в чат ассистенту: <em>«Хочу накопить 60 000 ₽ на ноутбук»</em>, и цель с планом автоматически появится здесь!
                  </span>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Секция Доходы */}
        <section className="cards-section">
          <h2 className="section-title">Доходы</h2>
          {loading ? (
            <div className="cards-status-box">
              <span className="status-spinner">⏳</span> Загрузка доходов...
            </div>
          ) : incomeCategories.length > 0 ? (
            <div className="cards-row">
              {incomeCategories.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="card income-card clickable-card"
                  onClick={() => setSelectedCategory(item)}
                  title="Нажмите, чтобы посмотреть историю операций"
                >
                  <div className="card-header">{item.category}</div>
                  <div className="card-body">
                    <div className="card-amount">
                      {Number(item.total_amount).toLocaleString('ru-RU')} ₽
                    </div>
                    
                    {item.description && (
                      <div className="card-desc">{item.description}</div>
                    )}

                    <div className="card-footer-hint">
                      <span>{item.count || item.transactions?.length || 0} операций</span>
                      <span className="card-hint-arrow">→</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-month-container">
              <span className="empty-month-icon">📭</span>
              <div className="empty-month-title">Нет данных о доходах</div>
              <div className="empty-month-subtitle">За {currentMonth.toLowerCase()} 2026 г. поступлений не зафиксировано</div>
            </div>
          )}
        </section>

        {/* Секция Расходы */}
        <section className="cards-section">
          <h2 className="section-title">Расходы</h2>
          {loading ? (
            <div className="cards-status-box">
              <span className="status-spinner">⏳</span> Загрузка расходов...
            </div>
          ) : expenseCategories.length > 0 ? (
            <div className="cards-row">
              {expenseCategories.map((item, idx) => {
                const cardId = item.id || `exp-${idx}`;
                return (
                  <div
                    key={cardId}
                    className="card expense-card clickable-card"
                    onClick={() => setSelectedCategory(item)}
                    title="Нажмите, чтобы посмотреть подробный список трат"
                  >
                    <div className="card-header">{item.category}</div>
                    <div className="card-body">
                      <div className="card-amount">
                        {Number(item.total_amount).toLocaleString('ru-RU')} ₽
                      </div>
                      
                      {item.description && (
                        <div className="card-desc">{item.description}</div>
                      )}

                      <div className="card-footer-hint">
                        <span>{item.count || item.transactions?.length || 0} операций</span>
                        <span className="card-hint-arrow">→</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-month-container">
              <span className="empty-month-icon">📭</span>
              <div className="empty-month-title">Нет данных о расходах</div>
              <div className="empty-month-subtitle">За {currentMonth.toLowerCase()} 2026 г. расходов не найдено</div>
            </div>
          )}
        </section>
      </main>

      {/* Чат с финансовым ИИ-помощником */}
      <ChatAssistant onGoalCreated={loadGoals} />

      {/* Модальное окно детализации операций по выбранной категории */}
      {selectedCategory && (
        <div className="modal-overlay" onClick={() => setSelectedCategory(null)}>
          <div className="modal-category-details" onClick={(e) => e.stopPropagation()}>
            {/* Шапка модального окна */}
            <div className="modal-detail-header">
              <div className="detail-header-left">
                <span className={`detail-type-badge ${selectedCategory.type === 'income' ? 'income' : 'expense'}`}>
                  {selectedCategory.type === 'income' ? '📈 Доход' : '📉 Расход'}
                </span>
                <h3 className="detail-category-title">{selectedCategory.category}</h3>
              </div>
              <button
                className="modal-close-icon"
                onClick={() => setSelectedCategory(null)}
                title="Закрыть"
              >
                ✕
              </button>
            </div>

            {/* Ключевые показатели категории */}
            <div className="detail-stats-grid">
              <div className="detail-stat-card">
                <span className="stat-label">Всего за месяц</span>
                <span className={`stat-value ${selectedCategory.type === 'income' ? 'income-color' : 'expense-color'}`}>
                  {Number(selectedCategory.total_amount).toLocaleString('ru-RU')} ₽
                </span>
              </div>
              <div className="detail-stat-card">
                <span className="stat-label">Операций</span>
                <span className="stat-value">
                  {selectedCategory.count || selectedCategory.transactions?.length || 0}
                </span>
              </div>
              <div className="detail-stat-card">
                <span className="stat-label">Средний чек</span>
                <span className="stat-value">
                  {Number(
                    selectedCategory.average_amount ||
                    (selectedCategory.total_amount / (selectedCategory.transactions?.length || 1))
                  ).toLocaleString('ru-RU', { maximumFractionDigits: 0 })} ₽
                </span>
              </div>
              {selectedCategory.percentage != null && selectedCategory.percentage > 0 && (
                <div className="detail-stat-card">
                  <span className="stat-label">Доля в бюджете</span>
                  <span className="stat-value">{selectedCategory.percentage}%</span>
                </div>
              )}
            </div>

            {/* Список конкретных операций/трат в категории */}
            <div className="detail-transactions-section">
              <div className="detail-section-title">
                <span>Детализация операций</span>
                <span className="tx-count-pill">
                  {selectedCategory.transactions?.length || 0} записей
                </span>
              </div>

              <div className="detail-transactions-list">
                {selectedCategory.transactions && selectedCategory.transactions.length > 0 ? (
                  selectedCategory.transactions.map((tx, idx) => (
                    <div key={tx.id || idx} className="tx-item-row">
                      <div className="tx-item-left">
                        <div className={`tx-icon-circle ${tx.type === 'income' ? 'income' : 'expense'}`}>
                          {tx.type === 'income' ? '↓' : '↑'}
                        </div>
                        <div className="tx-info-block">
                          <div className="tx-description">
                            {tx.description || selectedCategory.category}
                          </div>
                          <div className="tx-date">
                            {formatTransactionDate(tx.transaction_date)}
                          </div>
                        </div>
                      </div>

                      <div className={`tx-amount ${tx.type === 'income' ? 'income-color' : 'expense-color'}`}>
                        {tx.type === 'income' ? '+' : '-'} {Number(tx.amount).toLocaleString('ru-RU')} ₽
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="empty-transactions-placeholder">
                    <span className="empty-icon">📭</span>
                    <p>В этой категории пока нет записей о транзакциях</p>
                  </div>
                )}
              </div>
            </div>

            {/* Подвал модалки */}
            <div className="modal-detail-footer">
              <button
                className="btn-close-detail"
                onClick={() => setSelectedCategory(null)}
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}