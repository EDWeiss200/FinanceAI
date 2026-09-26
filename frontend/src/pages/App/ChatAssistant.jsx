import React, { useState, useEffect, useRef } from "react";

// Быстрые подсказки для студента
const QUICK_PROMPTS = [
  "🎯 Накопить 60 000 ₽ на ноутбук за 6 месяцев",
  "📱 Хочу накопить на новый смартфон за 30 000 ₽",
  "🍕 Как сократить траты на фастфуд и столовую?",
  "⚠️ Хватит ли мне денег в период сессии?",
];

export default function ChatAssistant() {
  const [messages, setMessages] = useState([
    {
      id: "welcome-1",
      sender: "assistant",
      text: "👋 Привет! Я твой персональный финансовый ИИ-помощник Т-Банка.\n\nЯ уже знаю структуру твоих доходов (стипендию и подработку) и реальные расходы. Напиши, на что и какую сумму ты хочешь накопить, и я сделаю точный математический расчет с учетом подушки безопасности и возможного спада подработки в сессию!",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [saveAsGoal, setSaveAsGoal] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Автоскролл к последнему сообщению
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Отправка запроса к бэкенду
  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputValue).trim();
    if (!text || isLoading) return;

    const userMessage = {
      id: "user-" + Date.now(),
      sender: "user",
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      // Получаем токен, если он сохранен в localStorage, иначе запрос уйдет в dev-режиме
      const token = localStorage.getItem("access_token");
      const headers = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch("http://localhost:8000/users/advisor", {
        method: "POST",
        headers,
        body: JSON.stringify({
          query: text,
          save_as_goal: saveAsGoal,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ошибка сервера (${response.status})`);
      }

      const data = await response.json();

      const assistantMessage = {
        id: "ai-" + Date.now(),
        sender: "assistant",
        text: data.advice,
        calculation: data.calculation,
        actionItems: data.action_items,
        sources: data.sources,
        disclaimer: data.disclaimer,
        goalCreated: data.goal_created,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Ошибка при запросе к ИИ:", error);
      const errorMessage = {
        id: "error-" + Date.now(),
        sender: "assistant",
        text: "⚠️ Не удалось связаться с сервером. Убедитесь, что бэкенд запущен на http://localhost:8000.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: "welcome-" + Date.now(),
        sender: "assistant",
        text: "Диалог очищен. О чем ты хочешь спросить или на что планируешь накопить?",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  return (
    <aside className="chat-container">
      {/* Шапка чата */}
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="chat-avatar">🤖</div>
          <div>
            <div className="chat-title">Т-Помощник</div>
            <div className="chat-status">
              <span className="status-dot"></span> Студент с подработкой
            </div>
          </div>
        </div>
        <button
          className="chat-clear-btn"
          onClick={handleClearHistory}
          title="Очистить историю диалога"
        >
          🔄 Очистить
        </button>
      </div>

      {/* Быстрые подсказки-чипсы */}
      <div className="chat-chips-bar">
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            className="chat-chip"
            onClick={() => handleSendMessage(prompt)}
            disabled={isLoading}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Тело сообщений */}
      <div className="chat-messages-scroll">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message-row ${msg.sender}`}>
            {msg.sender === "assistant" && <div className="msg-avatar">🤖</div>}
            <div className={`chat-bubble ${msg.sender}`}>
              {/* Основной текст сообщения */}
              <div className="chat-bubble-text">{msg.text}</div>

              {/* Карточка расчета при наличии Tool Calling */}
              {msg.calculation && (
                <div className="chat-calc-card">
                  <div className="calc-card-header">
                    <span
                      className={`calc-badge ${
                        msg.calculation.is_achievable ? "badge-success" : "badge-warning"
                      }`}
                    >
                      {msg.calculation.is_achievable
                        ? "Цель достижима ✅"
                        : "Требуется оптимизация ⚠️"}
                    </span>
                    {msg.goalCreated && (
                      <span className="calc-badge-goal">🎯 Цель сохранена в БД</span>
                    )}
                  </div>

                  <div className="calc-metrics-grid">
                    <div className="calc-metric-item">
                      <div className="metric-label">Откладывать в месяц</div>
                      <div className="metric-value">
                        {msg.calculation.required_monthly_savings.toLocaleString()} ₽
                      </div>
                      <div className="metric-sub">
                        ~{msg.calculation.daily_savings_recommendation} ₽ в день
                      </div>
                    </div>

                    <div className="calc-metric-item">
                      <div className="metric-label">Срок накопления</div>
                      <div className="metric-value">
                        {msg.calculation.estimated_months
                          ? `${msg.calculation.estimated_months} мес.`
                          : "—"}
                      </div>
                      {msg.calculation.stress_scenario_months && (
                        <div className="metric-sub stress">
                          в сессию: {msg.calculation.stress_scenario_months} мес.
                        </div>
                      )}
                    </div>

                    <div className="calc-metric-item">
                      <div className="metric-label">Свободный остаток</div>
                      <div className="metric-value">
                        {msg.calculation.free_cash_flow.toLocaleString()} ₽/мес.
                      </div>
                      <div className="metric-sub">
                        резерв: 10%
                      </div>
                    </div>
                  </div>

                  {/* Чеклист шагов для студента */}
                  {msg.actionItems && msg.actionItems.length > 0 && (
                    <div className="calc-actions-section">
                      <div className="actions-title">📋 План действий для студента:</div>
                      <ul className="actions-list">
                        {msg.actionItems.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Источники финграмотности */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="calc-sources-section">
                      <div className="sources-title">📚 Проверенные материалы:</div>
                      <div className="sources-links">
                        {msg.sources.map((src, i) => {
                          const [url, desc] = src.split(" — ");
                          return (
                            <a
                              key={i}
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              className="source-link"
                            >
                              🔗 {desc || url}
                            </a>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="chat-bubble-time">{msg.timestamp}</div>
            </div>
          </div>
        ))}

        {/* Анимированный индикатор набора */}
        {isLoading && (
          <div className="chat-message-row assistant">
            <div className="msg-avatar">🤖</div>
            <div className="chat-bubble assistant typing">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Панель ввода */}
      <div className="chat-footer-controls">
        <div className="chat-goal-toggle">
          <label>
            <input
              type="checkbox"
              checked={saveAsGoal}
              onChange={(e) => setSaveAsGoal(e.target.checked)}
            />
            <span>Автоматически добавить цель в профиль</span>
          </label>
        </div>

        <div className="chat-input-bar-enhanced">
          <input
            type="text"
            className="chat-text-input"
            placeholder="Напиши цель (например: Хочу накопить на ноутбук 60 000 ₽)..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            className="chat-send-btn"
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || isLoading}
            title="Отправить запрос"
          >
            ➤
          </button>
        </div>
      </div>
    </aside>
  );
}
