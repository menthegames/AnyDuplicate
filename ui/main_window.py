"""
Главное окно AnyDuplicate Advanced
Объединяет все страницы, кастомный title bar, боковую панель, меню, статус-бар.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QStatusBar, QMessageBox, QApplication, QLabel, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, Slot, QTimer, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QAction, QIcon, QFont, QKeySequence, QPixmap
from pathlib import Path

from core.config_manager import ConfigManager
from core.i18n import tr, init_i18n
from core.license_manager import LicenseManager
from core.update_checker import UpdateChecker, UpdateInfo
from ui.theme import apply_theme
from ui.widgets.animations import animate_page_switch
from ui.widgets.title_bar import TitleBar
from ui.widgets.sidebar import Sidebar
from ui.pages.main_page import MainPage
from ui.pages.results_page import ResultsPage
from ui.pages.history_page import HistoryPage
from ui.pages.dashboard_page import DashboardPage
from ui.dialogs.license_dialog import LicenseDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.about_dialog import AboutDialog
from ui.dialogs.help_dialog import HelpDialog


class MainWindow(QMainWindow):

    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.license_manager = LicenseManager()

        # Убираем стандартный заголовок Windows
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setWindowTitle("AnyDuplicate Advanced — Pro" if self.license_manager.is_pro else "AnyDuplicate Advanced — Free")
        self.setMinimumSize(1000, 680)
        self.resize(1200, 800)

        # Иконка
        icon_path = Path(__file__).parent.parent / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._setup_ui()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._setup_tray()
        self._apply_theme()

        # Анимация появления
        QTimer.singleShot(50, self._fade_in)

        # Проверка обновлений при запуске (только для Pro)
        if self.license_manager.is_pro:
            QTimer.singleShot(3000, self._check_updates_silent)

    def _setup_ui(self):
        """Создаёт UI: title bar, боковая панель, стек страниц."""
        central = QWidget()
        central.setProperty("mainWindow", True)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Кастомный title bar
        self.title_bar = TitleBar()
        self.title_bar.minimize_signal.connect(self.showMinimized)
        self.title_bar.maximize_signal.connect(self._toggle_maximize)
        self.title_bar.close_signal.connect(self.close)
        self.title_bar.set_version_label(self.license_manager.is_pro)
        main_layout.addWidget(self.title_bar)

        # Основной контент: боковая панель + страницы
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Боковая панель
        self.sidebar = Sidebar()
        self.sidebar.section_changed.connect(self._switch_section)
        self.sidebar.pro_section_clicked.connect(self._show_license)
        self.sidebar.set_pro(self.license_manager.is_pro)
        content_layout.addWidget(self.sidebar)

        # Стек страниц
        self.stack = QStackedWidget()
        self.stack.setProperty("contentStack", True)

        self.main_page = MainPage(self.config, self.license_manager)
        self.results_page = ResultsPage(self.config)
        self.history_page = HistoryPage(self.config)
        self.dashboard_page = DashboardPage()

        self.stack.addWidget(self.main_page)      # index 0
        self.stack.addWidget(self.results_page)    # index 1
        self.stack.addWidget(self.history_page)    # index 2
        self.stack.addWidget(self.dashboard_page)  # index 3

        # Связь: после сканирования переключаемся на результаты
        self.main_page.scan_complete.connect(self._show_results)

        content_layout.addWidget(self.stack, 1)
        main_layout.addLayout(content_layout, 1)

        # Стиль главного контейнера
        central.setStyleSheet("""
            QWidget[mainWindow="true"] {
                background-color: #0A0A0C;
            }
            QWidget[contentStack="true"] {
                background-color: #0F0F12;
            }
        """)

    def _setup_shortcuts(self):
        """Настраивает клавиатурные сокращения."""
        # Ctrl+O — открыть папку
        open_shortcut = QAction(tr("shortcut.open_folder", "Открыть папку"), self)
        open_shortcut.setShortcut(QKeySequence("Ctrl+O"))
        open_shortcut.triggered.connect(self._shortcut_open)
        self.addAction(open_shortcut)

        # Ctrl+F — поиск/фокус на фильтры
        find_shortcut = QAction(tr("shortcut.find", "Поиск"), self)
        find_shortcut.setShortcut(QKeySequence("Ctrl+F"))
        find_shortcut.triggered.connect(self._shortcut_find)
        self.addAction(find_shortcut)

        # Ctrl+Q — выход
        quit_shortcut = QAction(tr("shortcut.quit", "Выход"), self)
        quit_shortcut.setShortcut(QKeySequence("Ctrl+Q"))
        quit_shortcut.triggered.connect(self.close)
        self.addAction(quit_shortcut)

        # Ctrl+S — настройки
        settings_shortcut = QAction(tr("shortcut.settings", "Настройки"), self)
        settings_shortcut.setShortcut(QKeySequence("Ctrl+,"))
        settings_shortcut.triggered.connect(self._show_settings)
        self.addAction(settings_shortcut)

        # F5 — начать сканирование
        scan_shortcut = QAction(tr("shortcut.scan", "Сканировать"), self)
        scan_shortcut.setShortcut(QKeySequence("F5"))
        scan_shortcut.triggered.connect(self._shortcut_scan)
        self.addAction(scan_shortcut)

        # Delete — удалить выбранное
        delete_shortcut = QAction(tr("shortcut.delete", "Удалить"), self)
        delete_shortcut.setShortcut(QKeySequence("Delete"))
        delete_shortcut.triggered.connect(self._shortcut_delete)
        self.addAction(delete_shortcut)

        # Escape — назад на главную
        back_shortcut = QAction(tr("shortcut.back", "Назад"), self)
        back_shortcut.setShortcut(QKeySequence("Escape"))
        back_shortcut.triggered.connect(self._shortcut_back)
        self.addAction(back_shortcut)

    def _setup_statusbar(self):
        """Создаёт строку состояния."""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #0A0A0C;
                color: #8B8B95;
                border-top: 1px solid #2A2A30;
                padding: 2px 12px;
                font-size: 12px;
            }
        """)
        self.setStatusBar(self.status_bar)
        self._update_status_ready()

    def _update_status_ready(self):
        """Обновляет статус-бар с учётом языка."""
        if self.license_manager.is_pro:
            self.status_bar.showMessage(tr("status.pro_ready", "AnyDuplicate Advanced Pro | Готов к работе"))
        else:
            self.status_bar.showMessage(tr("status.ready", "Готов к работе"))

    def _setup_tray(self):
        """Создаёт иконку в системном трее."""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = Path(__file__).parent.parent / "app_icon.ico"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Запасная иконка
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.darkGray)
            self.tray_icon.setIcon(QIcon(pixmap))

        self.tray_icon.setToolTip("AnyDuplicate Advanced")

        # Контекстное меню трея
        tray_menu = QMenu()

        show_action = tray_menu.addAction(tr("tray.show", "Показать окно"))
        show_action.triggered.connect(self._show_from_tray)

        tray_menu.addSeparator()

        # Проверить обновления (только для Pro)
        if self.license_manager.is_pro:
            update_action = tray_menu.addAction(tr("tray.check_updates", "Проверить обновления"))
            update_action.triggered.connect(self._check_updates_manual)
            tray_menu.addSeparator()

        quit_action = tray_menu.addAction(tr("tray.quit", "Выход"))
        quit_action.triggered.connect(self._quit_app)

        self.tray_icon.setContextMenu(tray_menu)

        # Двойной клик — показать окно
        self.tray_icon.activated.connect(self._on_tray_activated)

        self.tray_icon.show()

    def _show_from_tray(self):
        """Восстанавливает окно из трея."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        """Обработчик активации иконки трея."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _quit_app(self):
        """Полный выход из приложения."""
        self.tray_icon.hide()
        QApplication.instance().quit()

    def _apply_theme(self):
        """Применяет тёмную тему."""
        apply_theme(QApplication.instance())

    def _fade_in(self):
        """Анимация появления окна."""
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def _toggle_maximize(self):
        """Переключает между развёрнутым и нормальным состоянием."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.title_bar.updateMaximizeIcon(self.isMaximized())

    @Slot(str)
    def _switch_section(self, section_id: str):
        """Переключает раздел в стеке страниц с анимацией."""
        mapping = {
            "search": 0,
            "results": 1,
            "history": 2,
            "dashboard": 3,
            "settings": None,  # открывается как диалог
        }
        idx = mapping.get(section_id)
        if idx is not None:
            old_idx = self.stack.currentIndex()
            if old_idx != idx:
                animate_page_switch(self.stack, old_idx, idx)
            else:
                self.stack.setCurrentIndex(idx)
            self.title_bar.setTitle(f"AnyDuplicate Advanced — {section_id.capitalize()}")
        elif section_id == "settings":
            self._show_settings()
        elif section_id == "help":
            self._show_help()


    @Slot(object)
    def _show_results(self, scanner):
        """Обновляет данные результатов после сканирования, оставаясь на текущей странице."""
        self.results_page.set_scanner(scanner)
        # Не переключаем на вкладку результатов — пользователь остаётся на главной
        # self.sidebar.set_active("results")
        # self.title_bar.setTitle("AnyDuplicate Advanced — Результаты")

        # Добавляем в историю
        total_files, total_size = scanner.calculate_stats()
        from core.utils import format_size
        self.history_page.add_entry(
            scanner.config.get("source_path", "—"),
            len(scanner.preview_data),
            total_files,
            format_size(total_size)
        )

        # Обновляем дашборд
        self.dashboard_page.set_scanner(scanner)

        # Бейдж на результаты
        self.sidebar.add_badge("results", len(scanner.preview_data))

        self.status_bar.showMessage(
            tr("status.found_duplicates", "Найдено дубликатов: {count} групп").format(
                count=len(scanner.duplicates)
            )
        )

        # Уведомление в трей о завершении сканирования
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "AnyDuplicate Advanced",
                tr("tray.scan_complete", "Сканирование завершено. Найдено дубликатов: {count} групп").format(
                    count=len(scanner.duplicates)
                ),
                QSystemTrayIcon.Information,
                3000
            )

    def _show_settings(self):
        """Открывает диалог настроек."""
        dialog = SettingsDialog(self.config, self)
        dialog.language_changed.connect(self._on_language_changed)
        if dialog.exec():
            self.status_bar.showMessage(tr("status.settings_saved", "Настройки сохранены"))

    def _on_language_changed(self):
        """Обрабатывает смену языка в настройках."""
        # Переинициализируем i18n (синглтон ConfigManager() вернёт тот же объект с обновлённым языком)
        init_i18n()
        # Обновляем статус-бар
        self._update_status_ready()
        # Обновляем заголовок окна
        self.setWindowTitle("AnyDuplicate Advanced")
        # Обновляем меню трея (пересоздаём)
        self._setup_tray()
        # Обновляем текст всех страниц и виджетов
        self.main_page.retranslate_ui()
        self.results_page.retranslate_ui()
        self.history_page.retranslate_ui()
        self.dashboard_page.retranslate_ui()
        self.sidebar.retranslate_ui()

    def _show_license(self):
        """Открывает диалог активации лицензии."""
        dialog = LicenseDialog(self.license_manager, self)
        if dialog.exec():
            self.status_bar.showMessage(
                tr("status.license_activated", "AnyDuplicate Advanced Pro | Лицензия активирована")
            )

    def _check_updates_silent(self):
        """Тихая проверка обновлений при запуске (только для Pro)."""
        self.status_bar.showMessage(tr("status.checking_updates", "Проверка обновлений..."))
        checker = UpdateChecker()
        info = checker.check()
        if info and info.is_available:
            # Показываем уведомление в трее
            if self.tray_icon.isVisible():
                self.tray_icon.showMessage(
                    "AnyDuplicate Advanced",
                    tr("tray.update_available", "Доступно обновление v{version}! Нажмите 'Проверить обновления' в меню трея для подробностей.").format(
                        version=info.latest_version
                    ),
                    QSystemTrayIcon.Information,
                    5000
                )
            self.status_bar.showMessage(
                tr("status.update_available", "Доступно обновление v{version}. Нажмите 'Проверить обновления' в меню трея.").format(
                    version=info.latest_version
                )
            )
        else:
            self._update_status_ready()

    def _check_updates_manual(self):
        """Ручная проверка обновлений с диалогом результата."""
        self.status_bar.showMessage(tr("status.checking_updates", "Проверка обновлений..."))
        QApplication.processEvents()

        checker = UpdateChecker()
        info = checker.check()

        if info is None:
            QMessageBox.warning(
                self,
                tr("update.error_title", "Ошибка проверки"),
                tr("update.error_text", "Не удалось проверить обновления.\nПроверьте подключение к интернету.")
            )
            self.status_bar.showMessage(tr("status.update_error", "Ошибка проверки обновлений"))
            return

        if info.is_available:
            msg = QMessageBox(self)
            msg.setWindowTitle(tr("update.title", "Доступно обновление"))
            msg.setText(
                tr("update.text", "Доступна новая версия v{latest}\n\nТекущая версия: v{current}\n\nЧто нового:\n{notes}...").format(
                    latest=info.latest_version,
                    current=info.current_version,
                    notes=info.release_notes[:300]
                )
            )
            msg.setInformativeText(
                tr("update.download", "Скачать: {url}").format(url=info.download_url)
            )
            msg.setStandardButtons(QMessageBox.Open | QMessageBox.Cancel)
            msg.setDefaultButton(QMessageBox.Open)
            if msg.exec() == QMessageBox.Open:
                import webbrowser
                webbrowser.open(info.download_url)
            self.status_bar.showMessage(
                tr("status.update_found", "Доступно обновление v{version}").format(version=info.latest_version)
            )
        else:
            QMessageBox.information(
                self,
                tr("update.no_updates_title", "Обновлений нет"),
                tr("update.no_updates_text", "У вас актуальная версия v{current}.").format(current=info.current_version)
            )
            self._update_status_ready()

    def _show_help(self):
        """Открывает диалог справки."""
        HelpDialog(self).exec()

    def _show_about(self):
        """Открывает диалог 'О программе'."""
        AboutDialog(self).exec()


    # --- Обработчики клавиатурных сокращений ---
    def _shortcut_open(self):
        """Ctrl+O: открыть папку."""
        self.stack.setCurrentIndex(0)
        self.sidebar.set_active("search")
        self.main_page._browse_folder()

    def _shortcut_find(self):
        """Ctrl+F: фокус на фильтры."""
        self.stack.setCurrentIndex(0)
        self.sidebar.set_active("search")
        self.main_page.filter_combo.setFocus()

    def _shortcut_scan(self):
        """F5: начать сканирование."""
        self.stack.setCurrentIndex(0)
        self.sidebar.set_active("search")
        self.main_page._start_scan()

    def _shortcut_delete(self):
        """Delete: удалить выбранное (на странице результатов)."""
        if self.stack.currentIndex() == 1:
            self.results_page._execute_action("delete")


    def _shortcut_back(self):
        """Escape: назад на главную."""
        if self.stack.currentIndex() == 1:
            self.results_page._go_back()
        else:
            self.stack.setCurrentIndex(0)
            self.sidebar.set_active("search")

    def changeEvent(self, event):
        """Отслеживает изменение состояния окна (максимизация/восстановление)."""
        if event.type() == QEvent.WindowStateChange:
            self.title_bar.updateMaximizeIcon(self.isMaximized())
        super().changeEvent(event)

    def closeEvent(self, event):
        """Сворачивает окно в системный трей вместо закрытия."""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "AnyDuplicate Advanced",
                tr("tray.minimized", "Приложение свёрнуто в трей. Дважды кликните для восстановления."),
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()
