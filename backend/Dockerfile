# используем официальный легкий образ Python
FROM python:3.11-slim

# запрещаем питону писать файлы .pyc и буферизовать логи
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# устанавливаем системные зависимости (ffmpeg необходим для pydub)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копируем весь остальной код проекта
COPY . .
