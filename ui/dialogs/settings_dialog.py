"""
Диалог настроек AnyDuplicate Advanced
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QGroupBox, QSlider
)
from PySide6.QtCore import Qt, Signal
from core.i18n import tr


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""

    language_changed = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(tr("settings.title", "Настройки"))
        self.setMinimumWidth(400)
        self.setModal(True)
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Язык
        lang_group = QGroupBox(tr("settings.language_group", "Язык"))
        lang_layout = QHBoxLayout(lang_group)
        lang_layout.addWidget(QLabel(tr("settings.language_label", "Язык интерфейса:")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([tr("settings.lang_ru", "Русский"), tr("settings.lang_en", "English")])
        lang_layout.addWidget(self.lang_combo, 1)
        layout.addWidget(lang_group)

        # Потоки
        thread_group = QGroupBox(tr("settings.performance_group", "Производительность"))
        thread_layout = QHBoxLayout(thread_group)
        thread_layout.addWidget(QLabel(tr("settings.threads_label", "Потоков:")))
        self.thread_slider = QSlider(Qt.Horizontal)
        self.thread_slider.setMinimum(1)
        self.thread_slider.setMaximum(16)
        self.thread_slider.setTickPosition(QSlider.TicksBelow)
        self.thread_slider.setTickInterval(1)
        self.thread_slider.valueChanged.connect(self._on_threads_changed)
        thread_layout.addWidget(self.thread_slider, 1)
        self.thread_value_label = QLabel("4")
        self.thread_value_label.setMinimumWidth(24)
        self.thread_value_label.setAlignment(Qt.AlignCenter)
        thread_layout.addWidget(self.thread_value_label)
        layout.addWidget(thread_group)

        layout.addStretch()

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(tr("settings.save_btn", "Сохранить"))
        save_btn.clicked.connect(self._save_settings)
        cancel_btn = QPushButton(tr("settings.cancel_btn", "Отмена"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _on_threads_changed(self, value: int):
        """Обновляет метку при изменении слайдера."""
        self.thread_value_label.setText(str(value))

    def _load_settings(self):
        lang = self.config.get("language", "ru")
        self.lang_combo.setCurrentIndex(0 if lang == "ru" else 1)

        self.thread_slider.setValue(self.config.get("threads", 4))

    def _save_settings(self):
        old_lang = self.config.get("language", "ru")
        new_lang = "ru" if self.lang_combo.currentIndex() == 0 else "en"
        self.config.set("language", new_lang)
        self.config.set("threads", self.thread_slider.value())
        if old_lang != new_lang:
            self.language_changed.emit()
        self.accept()
