import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const API_BASE_URL = 'http://localhost:8000';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState(true);

  // Проверка сохраненного токена при загрузке приложения
  useEffect(() => {
    async function verifyUserToken() {
      const savedToken = localStorage.getItem('access_token');
      if (!savedToken) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/users/me`, {
          headers: {
            'Authorization': `Bearer ${savedToken}`,
          },
        });

        if (res.ok) {
          const userData = await res.json();
          setUser(userData);
          setToken(savedToken);
        } else {
          // Если токен истек или недействителен — сбрасываем авторизацию
          localStorage.removeItem('access_token');
          setUser(null);
          setToken(null);
        }
      } catch (err) {
        console.error('Ошибка проверки токена авторизации:', err);
        // При ошибке сети не сбрасываем авторизацию сразу, но сбрасываем если сервер вернул ошибку
      } finally {
        setIsLoading(false);
      }
    }

    verifyUserToken();
  }, []);

  // Вход пользователя в систему (Bearer Token)
  const login = async (email, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim()); // fastapi-users ожидает поле username (в него передаем email)
      formData.append('password', password);

      const res = await fetch(`${API_BASE_URL}/auth/bearer/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData.toString(),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        if (errorData.detail === 'LOGIN_BAD_CREDENTIALS') {
          return { success: false, error: 'Неверный email или пароль.' };
        }
        return { success: false, error: errorData.detail || 'Не удалось войти. Проверьте введенные данные.' };
      }

      const data = await res.json();
      const accessToken = data.access_token;
      localStorage.setItem('access_token', accessToken);
      setToken(accessToken);

      // Получаем профиль авторизованного пользователя
      const profileRes = await fetch(`${API_BASE_URL}/users/me`, {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      if (profileRes.ok) {
        const profileData = await profileRes.json();
        setUser(profileData);
      }

      return { success: true };
    } catch (err) {
      console.error('Ошибка при входе:', err);
      return { success: false, error: 'Ошибка подключения к серверу. Убедитесь, что бэкенд запущен.' };
    }
  };

  // Регистрация нового пользователя
  const register = async (username, email, password) => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: json_payload({
          username: username.trim(),
          email: email.trim(),
          password: password,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        if (errorData.detail === 'REGISTER_USER_ALREADY_EXISTS') {
          return { success: false, error: 'Пользователь с таким email уже зарегистрирован.' };
        }
        if (Array.isArray(errorData.detail)) {
          const firstErr = errorData.detail[0]?.msg || 'Ошибка валидации полей';
          return { success: false, error: firstErr };
        }
        return { success: false, error: errorData.detail || 'Не удалось зарегистрироваться. Попробуйте еще раз.' };
      }

      // После успешной регистрации сразу выполняем вход
      const loginResult = await login(email, password);
      return loginResult;
    } catch (err) {
      console.error('Ошибка при регистрации:', err);
      return { success: false, error: 'Ошибка соединения с сервером при регистрации.' };
    }
  };

  // Выход из системы
  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Вспомогательная функция безопасной сериализации JSON
function json_payload(obj) {
  return JSON.stringify(obj);
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth должен использоваться внутри AuthProvider');
  }
  return context;
}
