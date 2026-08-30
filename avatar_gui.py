import sys
import json
import os
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt6.QtGui import QMovie
from PyQt6.QtCore import Qt, QTimer, QPoint

class AktivAAvatar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;")
        
        self.avatar_size = 220
        self.setFixedSize(self.avatar_size, self.avatar_size)
        
        self.label = QLabel(self)
        self.label.setFixedSize(self.avatar_size, self.avatar_size)
        self.label.setScaledContents(True)
        
        # Список доступных анимированных состояний и эмоций
        self.emotion_names = ["idle", "listening", "speaking", "happy", "thinking", "shame", "angry", "neutral"]
        self.movies = {}
        
        # Загружаем гифки (если какой-то гифки нет, ставим фолбэк)
        self.load_movies()
        
        self.current_state = ""
        self.update_animation("idle")

        # Позиционирование в правый нижний угол
        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.avatar_size - 30
        y = screen.height() - self.avatar_size - 80
        self.move(x, y)

        self.old_pos = None
        self.show()

        # Таймер проверки состояния (каждые 200 мс)
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_state)
        self.timer.start(200)

    def load_movies(self):
        for name in self.emotion_names:
            path = f"avatar/{name}.gif"
            if os.path.exists(path) and os.path.getsize(path) > 0:
                self.movies[name] = QMovie(path)
            else:
                # Если отдельной гифки с эмоцией нет, используем speaking.gif или idle.gif
                fallback = "avatar/speaking.gif" if name not in ["idle", "listening"] else "avatar/idle.gif"
                self.movies[name] = QMovie(fallback)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def update_animation(self, target_state):
        if target_state != self.current_state and target_state in self.movies:
            self.label.setMovie(self.movies[target_state])
            self.movies[target_state].start()
            self.current_state = target_state
            self.repaint()

    def check_state(self):
        if os.path.exists("state.json"):
            try:
                with open("state.json", "r") as f:
                    data = json.load(f)
                    state = data.get("state", "idle")
                    emotion = data.get("emotion", "neutral")
                    
                    # Если она говорит, выбираем конкретную эмоцию (happy, thinking и т.д.)
                    target = emotion if (state == "speaking" and emotion in self.movies) else state
                    self.update_animation(target)
            except Exception:
                pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AktivAAvatar()
    sys.exit(app.exec())
