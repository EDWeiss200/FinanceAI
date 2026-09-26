import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import ChatAssistant from "./ChatAssistant";

const MONTHS = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];

export default function App() {
  const [currentMonthIndex, setCurrentMonthIndex] = useState(8); // Сентябрь по умолчанию
  const [cardsByMonth, setCardsByMonth] = useState({});

  // Состояние модального окна добавления
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalType, setModalType] = useState("income");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  // Состояние активного контекстного меню (какой карточки открыто меню)
  const [activeMenuId, setActiveMenuId] = useState(null);

  const currentMonth = MONTHS[currentMonthIndex];

  // Переключение месяца
  const handlePrevMonth = () => {
    setCurrentMonthIndex((prev) => (prev === 0 ? 11 : prev - 1));
    setActiveMenuId(null);
  };

  const handleNextMonth = () => {
    setCurrentMonthIndex((prev) => (prev === 11 ? 0 : prev + 1));
    setActiveMenuId(null);
  };

  // Открытие модального окна
  const openAddModal = (type) => {
    setModalType(type);
    setTitle("");
    setAmount("");
    setDescription("");
    setIsModalOpen(true);
    setActiveMenuId(null);
  };

  // Добавление карточки
  const handleAddCard = (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    const newCard = {
      id: Date.now(),
      title,
      amount: amount || "0",
      description,
    };

    setCardsByMonth((prev) => {
      const monthData = prev[currentMonth] || { income: [], expense: [] };
      return {
        ...prev,
        [currentMonth]: {
          ...monthData,
          [modalType]: [...monthData[modalType], newCard],
        },
      };
    });

    setIsModalOpen(false);
  };

  // Удаление карточки
  const handleDeleteCard = (cardId, type) => {
    setCardsByMonth((prev) => {
      const monthData = prev[currentMonth] || { income: [], expense: [] };
      return {
        ...prev,
        [currentMonth]: {
          ...monthData,
          [type]: monthData[type].filter((card) => card.id !== cardId),
        },
      };
    });
    setActiveMenuId(null);
  };

  // Переключение видимости меню у конкретной карточки
  const toggleMenu = (e, cardId) => {
    e.stopPropagation();
    setActiveMenuId((prev) => (prev === cardId ? null : cardId));
  };

  // Закрывать меню при клике в любое другое место
  useEffect(() => {
    const handleOutsideClick = () => setActiveMenuId(null);
    window.addEventListener("click", handleOutsideClick);
    return () => window.removeEventListener("click", handleOutsideClick);
  }, []);

  const currentMonthData = cardsByMonth[currentMonth] || {
    income: [],
    expense: [],
  };

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
            <button className="nav-arrow" onClick={handlePrevMonth}>
              &lt;
            </button>
            <button className="nav-arrow" onClick={handleNextMonth}>
              &gt;
            </button>
          </div>
        </header>

        {/* Доходы */}
        <section className="cards-section">
          <h2 className="section-title">Доходы</h2>
          <div className="cards-row">
            {currentMonthData.income.map((card) => (
              <div key={card.id} className="card income-card">
                <div className="card-header">{card.title}</div>
                <div className="card-body">
                  <div className="card-amount">{card.amount}</div>
                  <div className="card-desc">
                    {card.description || "тут будет текст"}
                  </div>

                  {/* Кнопка 3 точки */}
                  <div
                    className="card-more"
                    onClick={(e) => toggleMenu(e, card.id)}
                  >
                    ...
                  </div>

                  {/* Выпадающее меню */}
                  {activeMenuId === card.id && (
                    <div
                      className="card-dropdown-menu"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        className="delete-btn"
                        onClick={() => handleDeleteCard(card.id, "income")}
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <button
              className="add-card-btn"
              onClick={() => openAddModal("income")}
            >
              +
            </button>
          </div>
        </section>

        {/* Расходы */}
        <section className="cards-section">
          <h2 className="section-title">Расходы</h2>
          <div className="cards-row">
            {currentMonthData.expense.map((card) => (
              <div key={card.id} className="card expense-card">
                <div className="card-header">{card.title}</div>
                <div className="card-body">
                  <div className="card-amount">{card.amount}</div>
                  <div className="card-desc">
                    {card.description || "тут будет текст"}
                  </div>

                  {/* Кнопка 3 точки */}
                  <div
                    className="card-more"
                    onClick={(e) => toggleMenu(e, card.id)}
                  >
                    ...
                  </div>

                  {/* Выпадающее меню */}
                  {activeMenuId === card.id && (
                    <div
                      className="card-dropdown-menu"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        className="delete-btn"
                        onClick={() => handleDeleteCard(card.id, "expense")}
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <button
              className="add-card-btn"
              onClick={() => openAddModal("expense")}
            >
              +
            </button>
          </div>
        </section>
      </main>

      {/* Чат с финансовым ИИ-помощником */}
      <ChatAssistant />

      {/* Модальное окно создания */}
      {isModalOpen && (
        <div className="modal-overlay">
          <form className="modal-content" onSubmit={handleAddCard}>
            <h3>
              Добавить {modalType === "income" ? "доход" : "расход"} (
              {currentMonth})
            </h3>
            <input
              type="text"
              placeholder="Название карточки"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
            <input
              type="text"
              placeholder="Сумма"
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
              <button
                type="button"
                className="btn-cancel"
                onClick={() => setIsModalOpen(false)}
              >
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
