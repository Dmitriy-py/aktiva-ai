#!/bin/bash

export QT_QPA_PLATFORM=xcb

cleanup() {
    echo "Завершение работы Активы..."
    kill $GUI_PID 2>/dev/null
    kill $CHAT_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

python3 avatar_gui.py &
GUI_PID=$!

sleep 1

python3 ai_voice_chat.py &
CHAT_PID=$!

wait $CHAT_PID
cleanup
