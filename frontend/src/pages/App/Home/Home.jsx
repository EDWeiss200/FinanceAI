import React, { useState, useEffect } from 'react';
import ChatAssistant from '../ChatAssistant';
import './Home.css';

const MONTHS = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

export default function Home() {
  const [currentMonthIndex, setCurrentMonthIndex] = useState(8); // Сентябрь по умолчанию
  
  // Данные категорий с бэкенда
  const [incomeCategories, setIncomeCategories] = useState([]);
  const [expenseCategories, setExpenseCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Состояние модального окна добавления (только для расходов)
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');

  // Состояние активного выпадающего меню карточки
  const [activeMenuId, setActiveMenuId] = useState(null);

  const currentMonth = MONTHS[currentMonthIndex];

  // Загрузка категорий из API
  useEffect(() => {
    async function loadCategories() {
      setLoading(true);
      try {
        const token = localStorage.getItem('access_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const res = await fetch('http://localhost:8000/users/categories?sort_by=amount_desc', {
          headers
        });

        if (res.ok) {
          const data = await res.json();
          // Доходы и расходы автоматически сгруппированы бэкендом по категориям
          setIncomeCategories(data.income_categories || []);
          setExpenseCategories(data.expense_categories || []);
        }
      } catch (err) {
        console.error('Ошибка при загрузке категорий:', err);
      } finally {
        setLoading(false);
      }
    }

    loadCategories();
  }, [currentMonthIndex]);

  // Переключение месяца
  const handlePrevMonth = () => {
    setCurrentMonthIndex((prev) => (prev === 0 ? 11 : prev - 1));
    setActiveMenuId(null);
  };

  const handleNextMonth = () => {
    setCurrentMonthIndex((prev) => (prev === 11 ? 0 : prev + 1));
    setActiveMenuId(null);
  };

  // Открытие модального окна добавления Расхода
  const openAddModal = () => {
    setTitle('');
    setAmount('');
    setDescription('');
    setIsModalOpen(true);
    setActiveMenuId(null);
  };

  // Ручное добавление карточки расхода
  const handleAddExpense = (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    const newCard = {
      id: Date.now(),
      category: title,
      total_amount: parseFloat(amount) || 0,
      description: description,
      isLocal: true // маркер локально созданной карточки
    };

    setExpenseCategories((prev) => [newCard, ...prev]);
    setIsModalOpen(false);
  };

  // Удаление локальной карточки
  const handleDeleteCard = (cardId) => {
    setExpenseCategories((prev) => prev.filter((card) => card.id !== cardId));
    setActiveMenuId(null);
  };

  // Переключение меню 3 точек
  const toggleMenu = (e, cardId) => {
    e.stopPropagation();
    setActiveMenuId((prev) => (prev === cardId ? null : cardId));
  };

  // Закрытие контекстного меню при клике снаружи
  useEffect(() => {
    const handleOutsideClick = () => setActiveMenuId(null);
    window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, []);

  return (
    <div className="dashboard-container">
      {/* Боковая панель */}
      <aside className="sidebar">
        <div className="sidebar-group">
          <div className="circle-btn"></div>
          <div className="circle-btn"></div>
          <div className="circle-btn"></div>
        </div>
        <div className="sidebar-group bottom">
          <div className="circle-btn"></div>
          <div className="circle-btn"></div>
        </div>
      </aside>

      {/* Основной контент */}
      <main className="main-content">
        {/* Выбор месяца */}
        <header className="month-selector">
          <div className="month-badge">{currentMonth}</div>
          <div className="month-controls">
            <button className="nav-arrow" onClick={handlePrevMonth}>&lt;</button>
            <button className="nav-arrow" onClick={handleNextMonth}>&gt;</button>
          </div>
        </header>

        {/* Секция Доходы (карточки автоматически сгруппированы, плюсик убран) */}
        <section className="cards-section">
          <h2 className="section-title">Доходы</h2>
          <div className="cards-row">
            {incomeCategories.map((item, idx) => (
              <div key={item.id || idx} className="card income-card">
                <div className="card-header">{item.category}</div>
                <div className="card-body">
                  <div className="card-amount">
                    {Number(item.total_amount).toLocaleString('ru-RU')} ₽
                  </div>
                  
                  {item.description && (
                    <div className="card-desc">{item.description}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Секция Расходы */}
        <section className="cards-section">
          <h2 className="section-title">Расходы</h2>
          <div className="cards-row">
            {expenseCategories.map((item, idx) => {
              const cardId = item.id || `exp-${idx}`;
              return (
                <div key={cardId} className="card expense-card">
                  <div className="card-header">{item.category}</div>
                  <div className="card-body">
                    <div className="card-amount">
                      {Number(item.total_amount).toLocaleString('ru-RU')} ₽
                    </div>
                    
                    {item.description && (
                      <div className="card-desc">{item.description}</div>
                    )}
                    
                    {/* Меню с возможностью удаления только для локальных карточек */}
                    {item.isLocal && (
                      <>
                        <div className="card-more" onClick={(e) => toggleMenu(e, cardId)}>
                          ...
                        </div>

                        {activeMenuId === cardId && (
                          <div className="card-dropdown-menu" onClick={(e) => e.stopPropagation()}>
                            <button className="delete-btn" onClick={() => handleDeleteCard(cardId)}>
                              Удалить
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
            
            <button className="add-card-btn" onClick={openAddModal}>
              +
            </button>
          </div>
        </section>
      </main>

      {/* Чат с финансовым ИИ-помощником */}
      <ChatAssistant />

      {/* Модальное окно создания расхода */}
      {isModalOpen && (
        <div className="modal-overlay">
          <form className="modal-content" onSubmit={handleAddExpense}>
            <h3>Добавить расход ({currentMonth})</h3>
            <input
              type="text"
              placeholder="Категория / Название"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
            <input
              type="number"
              placeholder="Сумма (₽)"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <textarea
              placeholder="Описание карточки"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows="3"
            />
            <div className="modal-actions">
              <button type="button" className="btn-cancel" onClick={() => setIsModalOpen(false)}>
                Отмена
              </button>
              <button type="submit" className="btn-submit">
                Создать
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}