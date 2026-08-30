#!/bin/bash

# Переходим в рабочую папку
cd /home/aktivator/ai_friend

# 1. Создаем командный канал связи между Docker и Zorin OS
mkfifo ~/ai_friend/cmd.fifo 2>/dev/null

# 2. Запускаем фоновый слушатель команд на хосте Zorin OS
(while true; do
    if read -r line < ~/ai_friend/cmd.fifo; then
        if [[ "$line" == http* ]] || [[ -e "$line" ]]; then
            xdg-open "$line" 2>/dev/null &
        else
            eval "$line" 2>/dev/null &
        fi
    fi
done) &
PIPE_PID=$!

# 3. Функция очистки процессов при закрытии
cleanup() {
    echo ""
    echo "Мяу! Выключаю Активу..."
    kill $PIPE_PID 2>/dev/null
    docker compose down 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 4. Разрешаем отображение аватарки на экране Zorin OS
xhost +local:root > /dev/null 2>&1
xhost +local:1000 > /dev/null 2>&1

# 5. Запускаем наш защищенный Docker-контейнер!
docker compose up

cleanup
