#!/bin/bash

echo "🛑 Остановка бота..."

if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "✅ Бот (PID $PID) остановлен."
    else
        echo "⚠️ Процесс с PID $PID не найден. Возможно, бот уже остановлен."
    fi
    rm bot.pid
else
    echo "❌ Файл bot.pid не найден. Бот, возможно, не был запущен через deploy.sh."
fi