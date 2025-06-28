import sys
import numpy as np
import sounddevice as sd
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtGui import QPixmap, QTransform, QPainter, QBrush, QColor, QRegion
from PyQt5.QtCore import QTimer, QRect, Qt

class RotatingImage(QWidget):
    def __init__(self, image_path, direction=1):
        super().__init__()
        self.setWindowTitle(f"Image qui tourne: {image_path}")
        self.angle = 0
        self.zoom = 1.0
        self.direction = direction  # +1 = sens horaire, -1 = anti-horaire

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: black;")

        original_pixmap = QPixmap(image_path)
        w, h = original_pixmap.width(), original_pixmap.height()
        side = min(w, h)
        x = (w - side) // 2
        y = (h - side) // 2
        cropped_pixmap = original_pixmap.copy(QRect(x, y, side, side))

        mask = QPixmap(side, side)
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, side, side)
        painter.end()

        rounded_pixmap = QPixmap(side, side)
        rounded_pixmap.fill(Qt.transparent)
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipRegion(QRegion(mask.mask()))
        painter.drawPixmap(0, 0, cropped_pixmap)
        painter.end()

        self.pixmap = rounded_pixmap
        self.label.setPixmap(self.pixmap)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
        self.timer.start(30)

        self.audio_level = 0

    def update_image(self):
        self.angle = (self.angle + self.direction * 2) % 360

        target_zoom = 1.0 + min(self.audio_level * 20, 0.5)
        self.zoom += (target_zoom - self.zoom) * 0.2

        transform = QTransform().rotate(self.angle).scale(self.zoom, self.zoom)
        rotated = self.pixmap.transformed(transform, mode=1)
        self.label.setPixmap(rotated)

    def set_audio_level(self, level):
        self.audio_level = level

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Audio partagé entre les deux fenêtres
    audio_level = {"value": 0}

    def shared_audio_callback(indata, frames, time, status):
        rms = np.sqrt(np.mean(indata**2))
        audio_level["value"] = rms

    stream = sd.InputStream(callback=shared_audio_callback, channels=1, samplerate=44100, blocksize=1024)
    stream.start()

    # Crée les fenêtres avec directions opposées
    window1 = RotatingImage("./foto.jpg", direction=1)   # Sens horaire
    window2 = RotatingImage("./foto2.jpg", direction=-1) # Sens antihoraire

    # Timer partagé pour synchroniser les updates audio/zoom
    def update_all():
        level = audio_level["value"]
        window1.set_audio_level(level)
        window2.set_audio_level(level)
        window1.update_image()
        window2.update_image()

    global_timer = QTimer()
    global_timer.timeout.connect(update_all)
    global_timer.start(30)

    window1.show()
    window2.show()

    try:
        sys.exit(app.exec_())
    finally:
        stream.stop()
        stream.close()
