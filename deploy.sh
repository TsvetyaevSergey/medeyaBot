#!/bin/bash
set -e

echo "🔄 Запуск процесса деплоя..."

# Переход в директорию скрипта
cd "$(dirname "$0")"

#######################################
# 1. Проверка и установка Python 3.10
#######################################
PYTHON_VERSION="3.10.12"

if ! command -v python3.10 > /dev/null 2>&1 || \
   [ "$(python3.10 --version 2>&1 | awk '{print $2}')" != "$PYTHON_VERSION" ]; then
    echo "⏳ Установка Python $PYTHON_VERSION..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.10 python3.10-venv
else
    echo "✅ Python $PYTHON_VERSION уже установлен"
fi

#######################################
# 2. Настройка виртуального окружения
#######################################
VENV_DIR=".venv"

create_venv() {
    echo "⏳ Создание виртуального окружения..."
    python3.10 -m venv "$VENV_DIR"

    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo "❌ Ошибка создания виртуального окружения"
        exit 1
    fi

    echo "✅ Виртуальное окружение создано"
}

if [ -d "$VENV_DIR" ]; then
    if [ -f "$VENV_DIR/bin/activate" ]; then
        echo "♻️ Обновление виртуального окружения..."
        rm -rf "$VENV_DIR"
        create_venv
    else
        echo "⚠️ Обнаружена поврежденная виртуальная среда"
        create_venv
    fi
else
    create_venv
fi

#######################################
# 3. Активация и настройка окружения
#######################################
echo "⏳ Активация окружения..."
source "$VENV_DIR/bin/activate"

echo "🔄 Обновление инструментов..."
python -m pip install --upgrade pip setuptools wheel

echo "📦 Установка зависимостей..."
pip install -r requirements.txt

#######################################
# 4. Запуск бота
#######################################
echo "🚀 Запуск бота..."
nohup python -u bot.py > bot.log 2>&1 &
echo $! > bot.pid

echo "✅ Деплой успешно завершен! PID: $(cat bot.pid)"