"""
Диалог "О программе" AnyDuplicate Advanced
"""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class AboutDialog(QDialog):
    """Информация о приложении."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setMinimumWidth(350)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("AnyDuplicate Advanced")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        version = QLabel("Версия 3.0.0")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        desc = QLabel(
            "Профессиональный инструмент для поиска и удаления\n"
            "дубликатов файлов на вашем компьютере.\n\n"
            "• Быстрое сканирование по размеру и хэшу\n"
            "• Поддержка MD5, SHA-256, SHA-512, BLAKE3\n"
            "• Умный выбор оригинала\n"
            "• Hardlink-режим для экономии места\n"
            "• Современный интерфейс на PySide6"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        copyright_label = QLabel("© 2024 AnyDuplicate Team")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
