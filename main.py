#!/usr/bin/env python3
"""
AnyDuplicate Advanced v3.0
Современный инструмент для поиска и удаления дубликатов файлов.
Запуск: python main.py
"""
import sys
import os
from pathlib import Path

# Добавляем корень проекта в sys.path для корректных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QSplashScreen, QProgressBar, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QFontDatabase
from ui.main_window import MainWindow


class SplashScreen(QSplashScreen):
    """Кастомный splash screen с логотипом и прогресс-баром."""

    def __init__(self):
        super().__init__()

        # Создаём pixmap для splash screen
        splash_size = (520, 340)
        pixmap = QPixmap(*splash_size)
        pixmap.fill(QColor("#0A0A0C"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Фон с градиентом
        painter.fillRect(0, 0, splash_size[0], splash_size[1], QColor("#0A0A0C"))

        # Акцентная линия сверху
        painter.fillRect(0, 0, splash_size[0], 3, QColor("#5B8FEF"))

        # Логотип (текстовый)
        font_title = QFont("Geist", 28, QFont.Weight.DemiBold)
        painter.setFont(font_title)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(0, 60, splash_size[0], 50, Qt.AlignCenter, "AnyDuplicate")

        font_subtitle = QFont("Geist", 14)
        painter.setFont(font_subtitle)
        painter.setPen(QColor("#8B8B95"))
        painter.drawText(0, 100, splash_size[0], 40, Qt.AlignCenter, "Advanced v3.0")

        # Иконка-заглушка (кружок с буквой A)
        painter.setBrush(QColor("#5B8FEF"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            splash_size[0] // 2 - 30, 150, 60, 60, 12, 12
        )
        font_icon = QFont("Geist", 28, QFont.Weight.Bold)
        painter.setFont(font_icon)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            splash_size[0] // 2 - 30, 150, 60, 60,
            Qt.AlignCenter, "A"
        )

        # Подпись
        font_tagline = QFont("Geist", 10)
        painter.setFont(font_tagline)
        painter.setPen(QColor("#5B8FEF"))
        from core.i18n import tr
        painter.drawText(0, 230, splash_size[0], 30, Qt.AlignCenter, tr("splash.tagline", "Поиск и удаление дубликатов"))

        painter.end()

        self.setPixmap(pixmap)

        # Прогресс-бар поверх splash
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(60, 280, 400, 6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1E1E24;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #5B8FEF;
                border-radius: 3px;
            }
        """)

        # Текст статуса загрузки
        self.status_label = self._create_status_label()
        self.status_label.setGeometry(60, 295, 400, 20)

    def _create_status_label(self):
        """Создаёт QLabel для отображения статуса загрузки."""
        from PySide6.QtWidgets import QLabel
        from core.i18n import tr
        label = QLabel(tr("splash.loading", "Загрузка..."), self)
        label.setStyleSheet("color: #6B6B75; font-size: 11px;")
        label.setAlignment(Qt.AlignCenter)
        return label

    def set_progress(self, value: int, status: str = ""):
        """Обновляет прогресс и статус."""
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)
        QApplication.processEvents()


def _load_fonts():
    """Загружает шрифты Geist из папки assets/fonts."""
    fonts_dir = Path(__file__).resolve().parent / "assets" / "fonts"
    if not fonts_dir.exists():
        print(f"[WARNING] Папка шрифтов не найдена: {fonts_dir}")
        return
    
    loaded = 0
    for ttf_file in sorted(fonts_dir.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(ttf_file))
        if font_id == -1:
            print(f"[WARNING] Не удалось загрузить шрифт: {ttf_file.name}")
        else:
            loaded += 1
    
    print(f"[INFO] Загружено шрифтов: {loaded}")


def global_exception_hook(exc_type, exc_value, exc_traceback):
    """Глобальный обработчик необработанных исключений.
    Логирует ошибку и показывает сообщение пользователю вместо молчаливого падения."""
    import traceback
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"[FATAL] Необработанное исключение:\n{error_msg}", file=sys.stderr)
    # Пытаемся показать сообщение пользователю через QMessageBox
    try:
        from PySide6.QtWidgets import QMessageBox
        app = QApplication.instance()
        if app:
            QMessageBox.critical(
                None,
                "AnyDuplicate Advanced — Критическая ошибка",
                f"Произошла неожиданная ошибка:\n\n{exc_value}\n\n"
                f"Подробности записаны в консоль (stderr).\n"
                f"Пожалуйста, сообщите об этой ошибке разработчику."
            )
    except Exception:
        pass  # Если не удалось показать диалог — игнорируем


def main():
    # Устанавливаем глобальный обработчик исключений
    sys.excepthook = global_exception_hook

    # Настройки высокого DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AnyDuplicate Advanced")
    app.setOrganizationName("AnyDuplicate")
    app.setApplicationVersion("3.0.0")

    # Глобальный стиль
    app.setStyle("Fusion")

    # Splash screen
    splash = SplashScreen()
    splash.show()
    QApplication.processEvents()

    # Этапы загрузки с прогрессом
    splash.set_progress(10, "Инициализация...")
    QApplication.processEvents()

    splash.set_progress(20, "Загрузка шрифтов...")
    _load_fonts()
    QApplication.processEvents()

    splash.set_progress(30, "Загрузка конфигурации...")
    from core.i18n import init_i18n
    init_i18n()
    QApplication.processEvents()

    splash.set_progress(50, "Проверка лицензии...")
    from core.license_manager import LicenseManager
    license_manager = LicenseManager()
    QApplication.processEvents()

    splash.set_progress(70, "Загрузка темы...")
    from ui.theme import apply_theme
    apply_theme(app)
    QApplication.processEvents()

    splash.set_progress(90, "Создание главного окна...")
    window = MainWindow()
    QApplication.processEvents()

    splash.set_progress(100, "Готово!")
    QApplication.processEvents()

    # Закрываем splash и показываем главное окно
    splash.finish(window)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
