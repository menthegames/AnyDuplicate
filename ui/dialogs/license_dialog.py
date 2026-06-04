"""
Диалог активации Pro-лицензии AnyDuplicate Advanced
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.license_manager import LicenseManager


class LicenseDialog(QDialog):
    """Диалог активации Pro-версии."""

    def __init__(self, license_manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.setWindowTitle("AnyDuplicate Advanced — Активация Pro")
        self.setMinimumWidth(450)
        self.setModal(True)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Заголовок
        title = QLabel("AnyDuplicate Advanced Pro")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Описание
        desc = QLabel(
            "Активируйте Pro-версию для доступа ко всем функциям:\n"
            "• Встроенный просмотр изображений, документов, видео\n"
            "• Умный выбор оригинала\n"
            "• Hardlink-режим\n"
            "• Приоритетная поддержка"
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Поле ввода ключа
        input_layout = QVBoxLayout()
        input_layout.addWidget(QLabel("Введите лицензионный ключ:"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("ANY-PRO-...")
        self.key_input.setMinimumHeight(36)
        input_layout.addWidget(self.key_input)
        layout.addLayout(input_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        activate_btn = QPushButton("Активировать")
        activate_btn.clicked.connect(self._activate)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(activate_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _activate(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Ошибка", "Введите лицензионный ключ.")
            return

        if self.license_manager.activate(key):
            QMessageBox.information(
                self, "Успех",
                "Лицензия активирована!\n\n"
                "Перезапустите приложение для применения всех Pro-функций."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self, "Ошибка",
                "Неверный лицензионный ключ.\n\n"
                "Проверьте правильность ввода или приобретите лицензию."
            )
