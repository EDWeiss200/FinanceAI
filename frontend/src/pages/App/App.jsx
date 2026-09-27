import React from "react";
import { AuthProvider, useAuth } from "../../context/AuthContext";
import Home from "./Home/Home";
import AuthPage from "../Auth/AuthPage";
import "./App.css";

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  // Пока проверяется наличие сохраненного токена — отображаем экран загрузки
  if (isLoading) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-loading-logo">
          <span className="auth-loading-dot"></span>
          FinanceAI
        </div>
        <div className="auth-loading-spinner"></div>
        <p className="auth-loading-text">Загрузка финансового профиля...</p>
      </div>
    );
  }

  // Если пользователь не авторизован — показываем страницы Входа / Регистрации
  if (!isAuthenticated) {
    return <AuthPage />;
  }

  // Авторизованный пользователь видит основной интерфейс
  return (
    <div className="app-root">
      <Home />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}