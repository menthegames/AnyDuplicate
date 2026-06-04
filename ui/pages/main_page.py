"""
Главная страница AnyDuplicate Advanced
Выбор папки, фильтров, запуск сканирования.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QProgressBar, QGroupBox,
    QFileDialog, QTextEdit, QMessageBox, QSpinBox, QRadioButton
)
from PySide6.QtCore import Signal, Slot, Qt
from pathlib import Path
from core.i18n import tr
from core.utils import FILTERS_RU, FILTERS_EN, get_extensions
from core.scanner import Scanner
from ui.preview_window import PreviewWindow


class MainPage(QWidget):
    """Главная страница: выбор папки, настройки, запуск сканирования."""

    scan_complete = Signal(object)  # scanner
    scan_finished = Signal()  # для безопасного вызова из потока
    log_signal = Signal(str)
    progress_signal = Signal(int)  # сигнал для обновления прогресса из потока

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.scanner = None
        self._setup_ui()
        self._load_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Выбор папки ---
        self.folder_group = QGroupBox(tr("main.folder_group", "Папка для сканирования"))
        folder_layout = QHBoxLayout(self.folder_group)
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(tr("main.folder_placeholder", "Выберите папку..."))
        self.folder_input.setReadOnly(True)
        self.folder_input.setToolTip(tr("main.folder_tooltip", "Путь к папке для сканирования.\nМожно перетащить папку из проводника"))
        self.browse_btn = QPushButton(tr("main.browse_btn", "Обзор"))
        self.browse_btn.setToolTip(tr("main.browse_tooltip", "Открыть диалог выбора папки для сканирования"))
        self.browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(self.folder_input, 1)
        folder_layout.addWidget(self.browse_btn)
        layout.addWidget(self.folder_group)

        # --- Фильтры ---
        self.filter_group = QGroupBox(tr("main.filter_group", "Фильтр файлов"))
        filter_layout = QVBoxLayout(self.filter_group)

        filter_row = QHBoxLayout()
        self.filter_combo = QComboBox()
        from core.i18n import get_current_language
        lang = get_current_language()
        filters = FILTERS_EN if lang == "en" else FILTERS_RU
        for name in filters:
            self.filter_combo.addItem(name)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.filter_combo.setToolTip(tr("main.filter_tooltip", "Выберите тип файлов для сканирования.\n«Свои» — введите расширения вручную"))
        self.filter_type_label = QLabel(tr("main.filter_type_label", "Тип:"))
        filter_row.addWidget(self.filter_type_label)
        filter_row.addWidget(self.filter_combo, 1)
        filter_layout.addLayout(filter_row)

        self.custom_ext_input = QLineEdit()
        self.custom_ext_input.setPlaceholderText(".jpg, .png, .heic")
        self.custom_ext_input.setVisible(False)
        self.custom_ext_input.setToolTip(tr("main.custom_ext_tooltip", "Введите расширения через запятую, например: .jpg, .png, .heic"))
        filter_layout.addWidget(self.custom_ext_input)

        self.exclude_check = QCheckBox(tr("main.exclude_check", "Исключить системные папки ($Recycle.Bin, System Volume Info)"))
        self.exclude_check.setChecked(True)
        self.exclude_check.setToolTip(tr("main.exclude_tooltip", "Исключить системные папки Windows из сканирования для ускорения"))
        filter_layout.addWidget(self.exclude_check)

        layout.addWidget(self.filter_group)

        # --- Алгоритм хэширования ---
        self.hash_group = QGroupBox(tr("main.hash_group", "Алгоритм хэширования"))
        hash_layout = QHBoxLayout(self.hash_group)
        self.hash_combo = QComboBox()
        self.hash_combo.addItems([
            tr("main.hash_md5", "MD5 (быстрый)"),
            "SHA-256",
            "SHA-512",
            tr("main.hash_blake3", "BLAKE3 (рекомендуется)")
        ])
        hash_layout.addWidget(self.hash_combo, 1)
        layout.addWidget(self.hash_group)

        # --- Критерий оригинала ---
        self.criteria_group = QGroupBox(tr("main.criteria_group", "Критерий выбора оригинала"))
        criteria_layout = QHBoxLayout(self.criteria_group)
        self.criteria_combo = QComboBox()
        self.criteria_combo.addItems([
            tr("main.criteria_date", "По дате (новее — оригинал)"),
            tr("main.criteria_size", "По размеру (больше — оригинал)"),
            tr("main.criteria_path", "По пути (короче — оригинал)")
        ])
        criteria_layout.addWidget(self.criteria_combo, 1)
        layout.addWidget(self.criteria_group)

        # --- Прогресс ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # --- Лог ---
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setPlaceholderText(tr("main.log_placeholder", "Лог сканирования..."))
        layout.addWidget(self.log_output)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        self.scan_btn = QPushButton(tr("main.scan_btn", "Начать сканирование"))
        self.scan_btn.setToolTip(tr("main.scan_tooltip", "Запустить сканирование выбранной папки на дубликаты"))
        self.scan_btn.clicked.connect(self._start_scan)
        self.stop_btn = QPushButton(tr("main.stop_btn", "Остановить"))
        self.stop_btn.setToolTip(tr("main.stop_tooltip", "Остановить текущее сканирование"))
        self.stop_btn.clicked.connect(self._stop_scan)
        self.stop_btn.setEnabled(False)
        self.preview_btn = QPushButton(tr("main.preview_btn", "Просмотр дубликатов"))
        self.preview_btn.setToolTip(tr("main.preview_tooltip", "Открыть окно предпросмотра найденных дубликатов"))
        self.preview_btn.clicked.connect(self._open_preview)
        self.preview_btn.setEnabled(False)
        self.preview_btn.setVisible(False)
        btn_layout.addWidget(self.scan_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.preview_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

        # Связь сигналов
        self.log_signal.connect(self._append_log)
        self.scan_finished.connect(self._on_scan_complete)
        self.progress_signal.connect(self._update_progress)

    def retranslate_ui(self):
        """Обновляет текст всех элементов при смене языка."""
        # Группа выбора папки
        self.folder_group.setTitle(tr("main.folder_group", "Папка для сканирования"))
        self.folder_input.setPlaceholderText(tr("main.folder_placeholder", "Выберите папку..."))
        self.folder_input.setToolTip(tr("main.folder_tooltip", "Путь к папке для сканирования.\nМожно перетащить папку из проводника"))
        self.browse_btn.setText(tr("main.browse_btn", "Обзор"))
        self.browse_btn.setToolTip(tr("main.browse_tooltip", "Открыть диалог выбора папки для сканирования"))

        # Группа фильтров
        self.filter_group.setTitle(tr("main.filter_group", "Фильтр файлов"))
        self.filter_type_label.setText(tr("main.filter_type_label", "Тип:"))
        self.filter_combo.setToolTip(tr("main.filter_tooltip", "Выберите тип файлов для сканирования.\n«Свои» — введите расширения вручную"))
        self.custom_ext_input.setPlaceholderText(".jpg, .png, .heic")
        self.custom_ext_input.setToolTip(tr("main.custom_ext_tooltip", "Введите расширения через запятую, например: .jpg, .png, .heic"))
        self.exclude_check.setText(tr("main.exclude_check", "Исключить системные папки ($Recycle.Bin, System Volume Info)"))
        self.exclude_check.setToolTip(tr("main.exclude_tooltip", "Исключить системные папки Windows из сканирования для ускорения"))

        # Группа хэширования
        self.hash_group.setTitle(tr("main.hash_group", "Алгоритм хэширования"))
        current_hash = self.hash_combo.currentText()
        self.hash_combo.clear()
        self.hash_combo.addItems([
            tr("main.hash_md5", "MD5 (быстрый)"),
            "SHA-256",
            "SHA-512",
            tr("main.hash_blake3", "BLAKE3 (рекомендуется)")
        ])

        # Группа критерия
        self.criteria_group.setTitle(tr("main.criteria_group", "Критерий выбора оригинала"))
        current_criteria = self.criteria_combo.currentText()
        self.criteria_combo.clear()
        self.criteria_combo.addItems([
            tr("main.criteria_date", "По дате (новее — оригинал)"),
            tr("main.criteria_size", "По размеру (больше — оригинал)"),
            tr("main.criteria_path", "По пути (короче — оригинал)")
        ])

        # Лог и кнопки
        self.log_output.setPlaceholderText(tr("main.log_placeholder", "Лог сканирования..."))
        self.scan_btn.setText(tr("main.scan_btn", "Начать сканирование"))
        self.scan_btn.setToolTip(tr("main.scan_tooltip", "Запустить сканирование выбранной папки на дубликаты"))
        self.stop_btn.setText(tr("main.stop_btn", "Остановить"))
        self.stop_btn.setToolTip(tr("main.stop_tooltip", "Остановить текущее сканирование"))
        self.preview_btn.setText(tr("main.preview_btn", "Просмотр дубликатов"))
        self.preview_btn.setToolTip(tr("main.preview_tooltip", "Открыть окно предпросмотра найденных дубликатов"))

        # Обновляем фильтр комбобокс (сохраняем выбранный элемент)
        current_filter = self.filter_combo.currentText()
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        from core.i18n import get_current_language
        from core.utils import FILTERS_RU, FILTERS_EN
        lang = get_current_language()
        filters = FILTERS_EN if lang == "en" else FILTERS_RU
        for name in filters:
            self.filter_combo.addItem(name)
        self.filter_combo.blockSignals(False)

    def _load_config(self):
        path = self.config.get("source_path", "")
        if path:
            self.folder_input.setText(path)
        self.exclude_check.setChecked(self.config.get("exclude_system", True))

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, tr("main.browse_dialog_title", "Выберите папку для сканирования"))
        if path:
            self.folder_input.setText(path)
            self.config.set("source_path", path)

    def _on_filter_changed(self, text):
        is_custom = "Свои" in text or "Custom" in text or "свои" in text.lower()
        self.custom_ext_input.setVisible(is_custom)

    def _get_hash_algorithm(self) -> str:
        # Используем индекс, а не текст, чтобы не зависеть от языка
        index = self.hash_combo.currentIndex()
        mapping = ["md5", "sha256", "sha512", "blake3"]
        return mapping[index] if 0 <= index < len(mapping) else "md5"

    def _get_criteria(self) -> str:
        return self.criteria_combo.currentText()

    def _start_scan(self):
        path = self.folder_input.text().strip()
        if not path or not Path(path).is_dir():
            QMessageBox.warning(self, tr("main.error_title", "Ошибка"), tr("main.error_folder", "Выберите существующую папку для сканирования."))
            return

        self.log_output.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        filter_text = self.filter_combo.currentText()
        custom_ext = self.custom_ext_input.text() if ("Свои" in filter_text or "Custom" in filter_text) else ""
        extensions = get_extensions(filter_text, custom_ext) or None

        hash_algo = self._get_hash_algorithm()
        criteria = self._get_criteria()
        exclude_system = self.exclude_check.isChecked()

        self.scanner = Scanner(
            self.config,
            log_callback=lambda msg: self.log_signal.emit(msg),
            progress_callback=lambda pct: self.progress_signal.emit(pct)
        )
        self.scanner.scan(
            source_path=path,
            extensions=extensions or [],
            hash_algorithm=hash_algo,
            criteria=criteria,
            exclude_system=exclude_system,
            on_complete=self.scan_finished.emit
        )

    def _stop_scan(self):
        if self.scanner:
            self.scanner.stop()
            self.log_signal.emit(tr("main.scan_stopped", "Сканирование остановлено пользователем."))
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_scan_complete(self):
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.scanner and self.scanner.duplicates:
            self.scan_complete.emit(self.scanner)
            self.preview_btn.setEnabled(True)
            self.preview_btn.setVisible(True)
        else:
            self.log_signal.emit(tr("main.no_duplicates", "Дубликаты не найдены."))
            self.preview_btn.setEnabled(False)
            self.preview_btn.setVisible(False)

    def _open_preview(self):
        """Открывает окно предпросмотра дубликатов."""
        if self.scanner and self.scanner.preview_data:
            preview = PreviewWindow(self.scanner.preview_data, self)
            preview.exec()

    @Slot(int)
    def _update_progress(self, pct):
        """Безопасное обновление прогресс-бара из любого потока через сигнал."""
        self.progress_bar.setValue(pct)

    @Slot(str)
    def _append_log(self, msg):
        self.log_output.append(msg)
        # Автоскролл
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
