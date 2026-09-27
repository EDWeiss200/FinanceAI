import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import './AuthPage.css';

export default function AuthPage() {
  const { login, register } = useAuth();

  // Режим: 'login' или 'register'
  const [mode, setMode] = useState('login');

  // Поля формы
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [username, setUsername] = useState('');

  // Состояния UI
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Сброс ошибок при смене режима
  const switchMode = (newMode) => {
    setMode(newMode);
    setErrorMsg('');
  };

  // Обработка отправки формы
  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!email.trim() || !password) {
      setErrorMsg('Пожалуйста, заполните все обязательные поля.');
      return;
    }

    if (mode === 'register') {
      if (!username.trim()) {
        setErrorMsg('Укажите ваше имя или псевдоним.');
        return;
      }
      if (password.length < 6) {
        setErrorMsg('Пароль должен содержать не менее 6 символов.');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg('Введенные пароли не совпадают.');
        return;
      }
    }

    setIsSubmitting(true);

    try {
      if (mode === 'login') {
        const result = await login(email, password);
        if (!result.success) {
          setErrorMsg(result.error);
        }
      } else {
        const result = await register(username, email, password);
        if (!result.success) {
          setErrorMsg(result.error);
        }
      }
    } catch {
      setErrorMsg('Произошла непредвиденная ошибка. Попробуйте снова.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Быстрый демо-вход для демонстрации
  const handleDemoLogin = async () => {
    setErrorMsg('');
    setIsSubmitting(true);
    // Используем демо-аккаунт или создаем тестовый вход
    const demoEmail = 'hackathon_demo@financeai.ru';
    const demoPass = 'Student2026!';

    const result = await login(demoEmail, demoPass);
    if (!result.success) {
      // Если демо-пользователь еще не существует с таким паролем, пробуем зарегистрировать
      const regResult = await register('Алексей Смирнов', demoEmail, demoPass);
      if (!regResult.success) {
        setErrorMsg(regResult.error || 'Не удалось выполнить демо-вход.');
      }
    }
    setIsSubmitting(false);
  };

  return (
    <div className="auth-container">
      {/* Фоновые декоративные элементы */}
      <div className="auth-glow glow-1"></div>
      <div className="auth-glow glow-2"></div>

      <div className="auth-card">
        {/* Шапка формы */}
        <div className="auth-header">
          <div className="auth-brand-badge">
            <span className="brand-dot"></span>
            FinanceAI
          </div>
          <h1 className="auth-title">
            {mode === 'login' ? 'С возвращением!' : 'Создайте аккаунт'}
          </h1>
          <p className="auth-subtitle">
            {mode === 'login'
              ? 'Войдите в личный кабинет умного финансового помощника'
              : 'Управляйте бюджетом и достигайте финансовых целей с ИИ'}
          </p>
        </div>

        {/* Переключатель вкладок */}
        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => switchMode('login')}
          >
            Вход
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => switchMode('register')}
          >
            Регистрация
          </button>
        </div>

        {/* Сообщение об ошибке */}
        {errorMsg && (
          <div className="auth-error-banner">
            <span className="error-icon">⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Форма */}
        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="username">Имя или никнейм</label>
              <div className="input-wrapper">
                <span className="input-icon">👤</span>
                <input
                  id="username"
                  type="text"
                  className="form-input"
                  placeholder="Например, Иван Смирнов"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="email">Электронная почта</label>
            <div className="input-wrapper">
              <span className="input-icon">✉️</span>
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="student@example.ru"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
                required
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Пароль</label>
            <div className="input-wrapper">
              <span className="input-icon">🔒</span>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                placeholder={mode === 'register' ? 'Минимум 6 символов' : 'Ваш пароль'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
                required
              />
              <button
                type="button"
                className="password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="confirmPassword">Подтверждение пароля</label>
              <div className="input-wrapper">
                <span className="input-icon">🔒</span>
                <input
                  id="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  placeholder="Повторите пароль"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>
          )}

          {mode === 'register' && (
            <div className="auth-feature-hint">
              <span className="hint-icon">✨</span>
              <span>
                При регистрации для вас автоматически сформируется финансовая песочница с историей за 3 месяца и реалистичным балансом!
              </span>
            </div>
          )}

          <button
            type="submit"
            className="auth-submit-btn"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="btn-spinner-content">
                <span className="spinner-dot"></span>
                Подождите...
              </span>
            ) : mode === 'login' ? (
              'Войти в систему →'
            ) : (
              'Создать аккаунт →'
            )}
          </button>
        </form>

        {/* Разделитель и кнопка Демо */}
        {mode === 'login' && (
          <div className="auth-footer-section">
            <div className="auth-divider">
              <span>или быстрый доступ</span>
            </div>
            <button
              type="button"
              className="demo-login-btn"
              onClick={handleDemoLogin}
              disabled={isSubmitting}
            >
              🚀 Демо-вход (аккаунт студента)
            </button>
          </div>
        )}

        {/* Переключатель внизу */}
        <div className="auth-bottom-switch">
          {mode === 'login' ? (
            <span>
              Впервые у нас?{' '}
              <button
                type="button"
                className="link-button"
                onClick={() => switchMode('register')}
              >
                Зарегистрироваться
              </button>
            </span>
          ) : (
            <span>
              Уже есть аккаунт?{' '}
              <button
                type="button"
                className="link-button"
                onClick={() => switchMode('login')}
              >
                Войти
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
