"""
Страница результатов сканирования AnyDuplicate Advanced
Таблица дубликатов с группировкой, чекбоксами, фильтрацией, контекстным меню
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QMessageBox,
    QComboBox, QCheckBox, QAbstractItemView, QApplication, QProgressBar,
    QSplitter, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QFont, QAction, QIcon, QCursor, QColor, QBrush
from pathlib import Path
import os
import subprocess
import datetime

from core.i18n import tr
from core.utils import format_size, format_date, get_file_type_category
from core.file_ops import is_hardlink
from ui.dialogs.batch_dialog import BatchDialog


class ResultsPage(QWidget):
    """Страница результатов сканирования."""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.scanner = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Заголовок
        title_layout = QHBoxLayout()
        
        self.title = QLabel(tr("results.title", "Результаты сканирования"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title.setFont(title_font)
        self.title.setStyleSheet("color: #E8E8ED;")
        title_layout.addWidget(self.title)
        
        title_layout.addStretch()
        
        # Статистика
        self.stats_label = QLabel(tr("results.stats_empty", "Групп: 0 | Файлов: 0 | Объём: 0 B"))
        self.stats_label.setStyleSheet("color: #8B8B95; font-size: 12px; padding: 4px 12px;")
        title_layout.addWidget(self.stats_label)
        
        layout.addLayout(title_layout)
        
        # Панель фильтров
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        # Поиск по имени
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("results.search_placeholder", "Поиск по имени файла..."))
        self.search_input.setMinimumWidth(200)
        self.search_input.textChanged.connect(self._apply_filters)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #141416;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #5B8FEF;
            }
        """)
        filter_layout.addWidget(self.search_input)
        
        # Фильтр по типу
        self.type_filter = QComboBox()
        self.type_filter.addItems([
            tr("results.filter_all_types", "Все типы"),
            tr("results.filter_images", "Изображения"),
            tr("results.filter_documents", "Документы"),
            tr("results.filter_video", "Видео"),
            tr("results.filter_audio", "Аудио"),
            tr("results.filter_archives", "Архивы"),
            tr("results.filter_other", "Другое")
        ])
        self.type_filter.currentTextChanged.connect(self._apply_filters)
        self.type_filter.setStyleSheet("""
            QComboBox {
                background-color: #141416;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 8px 12px;
                min-width: 140px;
            }
            QComboBox:hover { border-color: #5B8FEF; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: #141416;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                selection-background-color: rgba(91, 143, 239, 0.2);
            }
        """)
        filter_layout.addWidget(self.type_filter)
        
        # Фильтр по размеру
        self.size_filter = QComboBox()
        self.size_filter.addItems([
            tr("results.size_any", "Любой размер"),
            tr("results.size_lt_1mb", "< 1 MB"),
            tr("results.size_1_10mb", "1-10 MB"),
            tr("results.size_10_100mb", "10-100 MB"),
            tr("results.size_100mb_1gb", "100 MB - 1 GB"),
            tr("results.size_gt_1gb", "> 1 GB")
        ])
        self.size_filter.currentTextChanged.connect(self._apply_filters)
        self.size_filter.setStyleSheet(self.type_filter.styleSheet())
        filter_layout.addWidget(self.size_filter)
        
        # Фильтр hardlink
        self.hardlink_filter = QCheckBox(tr("results.hardlink_filter", "Только hardlink'и"))
        self.hardlink_filter.stateChanged.connect(self._apply_filters)
        self.hardlink_filter.setToolTip(tr("results.hardlink_tooltip", "Показать только файлы, являющиеся жёсткими ссылками (st_nlink > 1)"))
        self.hardlink_filter.setStyleSheet("""
            QCheckBox {
                color: #C8C8D0;
                spacing: 6px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2A2A30;
                border-radius: 4px;
                background-color: #141416;
            }
            QCheckBox::indicator:checked {
                background-color: #5B8FEF;
                border-color: #5B8FEF;
            }
        """)
        filter_layout.addWidget(self.hardlink_filter)
        
        filter_layout.addStretch()
        
        # Кнопка "Назад"
        back_btn = QPushButton(tr("results.back_btn", "← Назад к поиску"))
        back_btn.clicked.connect(self._go_back)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #8B8B95;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #E8E8ED;
                border-color: #5B8FEF;
            }
        """)
        filter_layout.addWidget(back_btn)
        
        layout.addLayout(filter_layout)
        
        # Таблица результатов
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "", tr("results.col_group", "Группа"), tr("results.col_file", "Файл"),
            tr("results.col_size", "Размер"), tr("results.col_date", "Дата"),
            tr("results.col_hash", "Хэш"), tr("results.col_path", "Путь")
        ])
        self.tree.setColumnWidth(0, 50)  # чекбокс
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 200)
        self.tree.setColumnWidth(3, 90)
        self.tree.setColumnWidth(4, 140)
        self.tree.setColumnWidth(5, 120)
        self.tree.setColumnWidth(6, 300)
        
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemChanged.connect(self._on_item_changed)
        
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #2A2A30;
                border-radius: 8px;
                background-color: #141416;
                alternate-background-color: #18181C;
                outline: none;
            }
            QTreeWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #1E1E24;
                color: #C8C8D0;
                min-height: 28px;
            }
            QTreeWidget::item:selected {
                background-color: rgba(91, 143, 239, 0.2);
                color: #5B8FEF;
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.03);
            }
            QTreeWidget::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #3A3A44;
                border-radius: 4px;
                background-color: #1A1A20;
                margin: 2px;
            }
            QTreeWidget::indicator:checked {
                background-color: #5B8FEF;
                border-color: #5B8FEF;
            }
            QTreeWidget::indicator:hover {
                border-color: #5B8FEF;
            }
            QHeaderView::section {
                background-color: #0A0A0C;
                color: #8B8B95;
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid #2A2A30;
                border-right: 1px solid #1A1A1E;
                font-weight: 600;
                font-size: 12px;
            }
            QHeaderView::section:hover {
                color: #E8E8ED;
            }
        """)
        
        header = self.tree.header()
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)
        
        layout.addWidget(self.tree, 1)
        
        # Нижняя панель действий
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        # Чекбокс "Выбрать все"
        self.select_all_cb = QCheckBox(tr("results.select_all", "Выбрать все"))
        self.select_all_cb.stateChanged.connect(self._toggle_select_all)
        self.select_all_cb.setStyleSheet("""
            QCheckBox {
                color: #C8C8D0;
                spacing: 6px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #2A2A30;
                border-radius: 4px;
                background-color: #141416;
            }
            QCheckBox::indicator:checked {
                background-color: #5B8FEF;
                border-color: #5B8FEF;
            }
        """)
        action_layout.addWidget(self.select_all_cb)
        
        action_layout.addStretch()
        
        # Кнопки действий
        btn_style = """
            QPushButton {
                background-color: #1E1E24;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2A2A32;
                border-color: #5B8FEF;
            }
            QPushButton:disabled {
                background-color: #121216;
                color: #4A4A50;
                border-color: #1E1E24;
            }
        """
        
        danger_btn_style = """
            QPushButton {
                background-color: rgba(239, 68, 68, 0.1);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
            }
            QPushButton:disabled {
                background-color: rgba(239, 68, 68, 0.05);
                color: rgba(239, 68, 68, 0.3);
                border-color: rgba(239, 68, 68, 0.1);
            }
        """
        
        self.open_btn = QPushButton(tr("results.open_btn", "Открыть"))
        self.open_btn.setToolTip(tr("results.open_tooltip", "Открыть выбранные файлы в системном приложении (до 10 файлов)"))
        self.open_btn.clicked.connect(self._open_selected)
        self.open_btn.setStyleSheet(btn_style)
        action_layout.addWidget(self.open_btn)
        
        self.open_folder_btn = QPushButton(tr("results.open_folder_btn", "В папку"))
        self.open_folder_btn.setToolTip(tr("results.open_folder_tooltip", "Открыть папку с выбранным файлом в проводнике"))
        self.open_folder_btn.clicked.connect(self._open_folder_selected)
        self.open_folder_btn.setStyleSheet(btn_style)
        action_layout.addWidget(self.open_folder_btn)
        
        self.delete_btn = QPushButton(tr("results.delete_btn", "Удалить"))
        self.delete_btn.setToolTip(tr("results.delete_tooltip", "Удалить выбранные файлы (с подтверждением)"))
        self.delete_btn.clicked.connect(self._delete_selected)
        self.delete_btn.setStyleSheet(danger_btn_style)
        action_layout.addWidget(self.delete_btn)
        
        self.export_btn = QPushButton(tr("results.export_btn", "Экспорт CSV"))
        self.export_btn.setToolTip(tr("results.export_tooltip", "Экспортировать результаты сканирования в CSV-файл"))
        self.export_btn.clicked.connect(self._export_csv)
        self.export_btn.setStyleSheet(btn_style)
        action_layout.addWidget(self.export_btn)
        
        # Кнопки сессий
        self.save_session_btn = QPushButton(tr("results.save_session_btn", "Сохранить сессию"))
        self.save_session_btn.setToolTip(tr("results.save_session_tooltip", "Сохранить текущие результаты сканирования в JSON-файл"))
        self.save_session_btn.clicked.connect(self._save_session)
        self.save_session_btn.setStyleSheet(btn_style)
        action_layout.addWidget(self.save_session_btn)
        
        self.load_session_btn = QPushButton(tr("results.load_session_btn", "Загрузить сессию"))
        self.load_session_btn.setToolTip(tr("results.load_session_tooltip", "Загрузить ранее сохранённые результаты из JSON-файла"))
        self.load_session_btn.clicked.connect(self._load_session)
        self.load_session_btn.setStyleSheet(btn_style)
        action_layout.addWidget(self.load_session_btn)
        
        # Кнопка пакетной обработки
        self.batch_btn = QPushButton(tr("results.batch_btn", "Пакетная обработка"))
        self.batch_btn.setToolTip(tr("results.batch_tooltip", "Открыть диалог пакетной обработки дубликатов"))
        self.batch_btn.clicked.connect(self._open_batch_dialog)
        self.batch_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(91, 143, 239, 0.15);
                color: #5B8FEF;
                border: 1px solid rgba(91, 143, 239, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(91, 143, 239, 0.25);
                border-color: #5B8FEF;
            }
            QPushButton:disabled {
                background-color: rgba(91, 143, 239, 0.05);
                color: rgba(91, 143, 239, 0.3);
                border-color: rgba(91, 143, 239, 0.1);
            }
        """)
        action_layout.addWidget(self.batch_btn)
        
        layout.addLayout(action_layout)
    
    def retranslate_ui(self):
        """Обновляет текст всех элементов при смене языка."""
        # Заголовок
        self.title.setText(tr("results.title", "Результаты сканирования"))
        # Статистика
        self._update_stats()

        # Поиск
        self.search_input.setPlaceholderText(tr("results.search_placeholder", "Поиск по имени файла..."))

        # Фильтр по типу
        current_type = self.type_filter.currentText()
        self.type_filter.blockSignals(True)
        self.type_filter.clear()
        self.type_filter.addItems([
            tr("results.filter_all_types", "Все типы"),
            tr("results.filter_images", "Изображения"),
            tr("results.filter_documents", "Документы"),
            tr("results.filter_video", "Видео"),
            tr("results.filter_audio", "Аудио"),
            tr("results.filter_archives", "Архивы"),
            tr("results.filter_other", "Другое")
        ])
        self.type_filter.blockSignals(False)

        # Фильтр по размеру
        current_size = self.size_filter.currentText()
        self.size_filter.blockSignals(True)
        self.size_filter.clear()
        self.size_filter.addItems([
            tr("results.size_any", "Любой размер"),
            tr("results.size_lt_1mb", "< 1 MB"),
            tr("results.size_1_10mb", "1-10 MB"),
            tr("results.size_10_100mb", "10-100 MB"),
            tr("results.size_100mb_1gb", "100 MB - 1 GB"),
            tr("results.size_gt_1gb", "> 1 GB")
        ])
        self.size_filter.blockSignals(False)

        # Hardlink фильтр
        self.hardlink_filter.setText(tr("results.hardlink_filter", "Только hardlink'и"))
        self.hardlink_filter.setToolTip(tr("results.hardlink_tooltip", "Показать только файлы, являющиеся жёсткими ссылками (st_nlink > 1)"))

        # Кнопки
        self.select_all_cb.setText(tr("results.select_all", "Выбрать все"))
        self.open_btn.setText(tr("results.open_btn", "Открыть"))
        self.open_btn.setToolTip(tr("results.open_tooltip", "Открыть выбранные файлы в системном приложении (до 10 файлов)"))
        self.open_folder_btn.setText(tr("results.open_folder_btn", "В папку"))
        self.open_folder_btn.setToolTip(tr("results.open_folder_tooltip", "Открыть папку с выбранным файлом в проводнике"))
        self.delete_btn.setText(tr("results.delete_btn", "Удалить"))
        self.delete_btn.setToolTip(tr("results.delete_tooltip", "Удалить выбранные файлы (с подтверждением)"))
        self.export_btn.setText(tr("results.export_btn", "Экспорт CSV"))
        self.export_btn.setToolTip(tr("results.export_tooltip", "Экспортировать результаты сканирования в CSV-файл"))
        self.save_session_btn.setText(tr("results.save_session_btn", "Сохранить сессию"))
        self.save_session_btn.setToolTip(tr("results.save_session_tooltip", "Сохранить текущие результаты сканирования в JSON-файл"))
        self.load_session_btn.setText(tr("results.load_session_btn", "Загрузить сессию"))
        self.load_session_btn.setToolTip(tr("results.load_session_tooltip", "Загрузить ранее сохранённые результаты из JSON-файла"))
        self.batch_btn.setText(tr("results.batch_btn", "Пакетная обработка"))
        self.batch_btn.setToolTip(tr("results.batch_tooltip", "Открыть диалог пакетной обработки дубликатов"))

        # Обновляем заголовки таблицы
        self.tree.setHeaderLabels([
            "", tr("results.col_group", "Группа"), tr("results.col_file", "Файл"),
            tr("results.col_size", "Размер"), tr("results.col_date", "Дата"),
            tr("results.col_hash", "Хэш"), tr("results.col_path", "Путь")
        ])

        # Перезаполняем дерево для обновления текста групп
        self._populate_tree()

    def set_scanner(self, scanner):
        """Устанавливает сканер и заполняет таблицу."""
        self.scanner = scanner
        self._populate_tree()
    
    def _populate_tree(self):
        """Заполняет дерево результатами."""
        self.tree.clear()
        
        if not self.scanner or not self.scanner.preview_data:
            return
        
        for group_idx, (hash_val, original, dups) in enumerate(self.scanner.preview_data, 1):
            all_files = [original] + dups
            
            # Групповой элемент
            group_item = QTreeWidgetItem()
            group_item.setText(0, "")
            group_item.setText(1, tr("results.group_label", "Группа {idx}").format(idx=group_idx))
            group_item.setText(2, tr("results.group_files", "{count} файлов").format(count=len(all_files)))
            
            # Суммарный размер группы
            total_size = 0
            for f in all_files:
                try:
                    total_size += f.stat().st_size
                except Exception:
                    pass
            group_item.setText(3, format_size(total_size))
            
            group_item.setText(4, "")
            group_item.setText(5, hash_val[:16] + "...")
            group_item.setText(6, "")
            
            # Стиль группы
            group_font = QFont()
            group_font.setBold(True)
            group_item.setFont(1, group_font)
            group_item.setForeground(1, QColor("#5B8FEF"))
            
            group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
            group_item.setCheckState(0, Qt.Unchecked)
            group_item.setData(0, Qt.UserRole, "group")
            
            self.tree.addTopLevelItem(group_item)
            
            # Файлы в группе
            for file_path in all_files:
                file_item = QTreeWidgetItem()
                file_item.setText(0, "")
                file_item.setText(1, "")
                file_item.setText(2, file_path.name)
                try:
                    file_item.setText(3, format_size(file_path.stat().st_size))
                    file_item.setText(4, format_date(
                        datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    ))
                except Exception:
                    file_item.setText(3, "—")
                    file_item.setText(4, "—")
                file_item.setText(5, hash_val[:16] + "...")
                file_item.setText(6, str(file_path))
                
                file_item.setToolTip(2, file_path.name)
                file_item.setToolTip(6, str(file_path))
                
                # Визуальная индикация hardlink
                if is_hardlink(str(file_path)):
                    file_item.setText(2, file_path.name)
                    file_item.setForeground(2, QColor("#F59E0B"))  # янтарный
                    file_item.setToolTip(2, tr("results.hardlink_tooltip_item", "Hardlink (st_nlink > 1)\n{name}").format(name=file_path.name))
                
                file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.Unchecked)
                file_item.setData(0, Qt.UserRole, "file")
                file_item.setData(0, Qt.UserRole + 1, str(file_path))
                
                group_item.addChild(file_item)
        
        # Раскрываем первую группу
        if self.tree.topLevelItemCount() > 0:
            self.tree.topLevelItem(0).setExpanded(True)
        
        self._update_stats()
    
    def _update_stats(self):
        """Обновляет статистику."""
        if not self.scanner:
            self.stats_label.setText(tr("results.stats_empty", "Групп: 0 | Файлов: 0 | Объём: 0 B"))
            return
        
        total_groups = len(self.scanner.preview_data)
        total_files = 0
        total_size = 0
        
        for hash_val, original, dups in self.scanner.preview_data:
            all_files = [original] + dups
            total_files += len(all_files)
            for f in all_files:
                try:
                    total_size += f.stat().st_size
                except Exception:
                    pass
        
        self.stats_label.setText(
            tr("results.stats_format", "Групп: {groups} | Файлов: {files} | Объём: {size}").format(
                groups=total_groups, files=total_files, size=format_size(total_size)
            )
        )
    
    def _apply_filters(self):
        """Применяет фильтры к таблице."""
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        size_filter = self.size_filter.currentText()
        
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            group_visible = False
            
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                file_visible = True
                
                # Фильтр по имени
                if search_text:
                    file_name = file_item.text(2).lower()
                    if search_text not in file_name:
                        file_visible = False
                
                # Фильтр по типу
                if type_filter != tr("results.filter_all_types", "Все типы"):
                    file_path = file_item.text(6)
                    file_type = get_file_type_category(file_path)
                    type_map = {
                        tr("results.filter_images", "Изображения"): "image",
                        tr("results.filter_documents", "Документы"): "document",
                        tr("results.filter_video", "Видео"): "video",
                        tr("results.filter_audio", "Аудио"): "audio",
                        tr("results.filter_archives", "Архивы"): "archive",
                    }
                    expected = type_map.get(type_filter, "")
                    if file_type != expected:
                        file_visible = False
                
                # Фильтр по размеру
                if size_filter != tr("results.size_any", "Любой размер"):
                    size_text = file_item.text(3)
                    size_bytes = self._parse_size(size_text)
                    if not self._check_size_filter(size_bytes, size_filter):
                        file_visible = False
                
                # Фильтр hardlink
                if self.hardlink_filter.isChecked():
                    file_path = file_item.text(6)
                    if not is_hardlink(file_path):
                        file_visible = False
                
                file_item.setHidden(not file_visible)
                if file_visible:
                    group_visible = True
            
            group_item.setHidden(not group_visible)
    
    def _parse_size(self, size_text: str) -> int:
        """Парсит текстовое представление размера в байты."""
        try:
            size_text = size_text.replace(",", ".").strip()
            if "TB" in size_text:
                return int(float(size_text.replace("TB", "").strip()) * 1024**4)
            elif "GB" in size_text:
                return int(float(size_text.replace("GB", "").strip()) * 1024**3)
            elif "MB" in size_text:
                return int(float(size_text.replace("MB", "").strip()) * 1024**2)
            elif "KB" in size_text:
                return int(float(size_text.replace("KB", "").strip()) * 1024)
            elif "B" in size_text:
                return int(float(size_text.replace("B", "").strip()))
        except:
            return 0
        return 0
    
    def _check_size_filter(self, size_bytes: int, filter_text: str) -> bool:
        """Проверяет размер на соответствие фильтру."""
        if filter_text == tr("results.size_lt_1mb", "< 1 MB"):
            return size_bytes < 1024 * 1024
        elif filter_text == tr("results.size_1_10mb", "1-10 MB"):
            return 1024 * 1024 <= size_bytes < 10 * 1024 * 1024
        elif filter_text == tr("results.size_10_100mb", "10-100 MB"):
            return 10 * 1024 * 1024 <= size_bytes < 100 * 1024 * 1024
        elif filter_text == tr("results.size_100mb_1gb", "100 MB - 1 GB"):
            return 100 * 1024 * 1024 <= size_bytes < 1024 * 1024 * 1024
        elif filter_text == tr("results.size_gt_1gb", "> 1 GB"):
            return size_bytes >= 1024 * 1024 * 1024
        return True
    
    def _on_header_clicked(self, index: int):
        """Обрабатывает клик по заголовку для сортировки."""
        self.tree.sortItems(index, Qt.AscendingOrder if index != 3 else Qt.DescendingOrder)
    
    def _toggle_select_all(self, state: int):
        """Выбирает/снимает выбор со всех элементов."""
        checked = state == Qt.Checked
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            if group_item is None:
                continue
            group_item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if file_item is None:
                    continue
                file_item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Обрабатывает изменение состояния элемента."""
        if column == 0:
            # Если это группа, обновляем все дочерние элементы
            if item.data(0, Qt.UserRole) == "group":
                checked = item.checkState(0) == Qt.Checked
                # Блокируем сигналы, чтобы избежать рекурсии
                self.tree.blockSignals(True)
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child is not None:
                        child.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
                self.tree.blockSignals(False)
    
    def _get_selected_files(self) -> list:
        """Возвращает список выбранных файлов."""
        selected = []
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            if group_item is None:
                continue
            for j in range(group_item.childCount()):
                file_item = group_item.child(j)
                if file_item is None:
                    continue
                if file_item.checkState(0) == Qt.Checked:
                    selected.append(file_item.text(6))
        return selected
    
    def _show_context_menu(self, pos):
        """Показывает контекстное меню."""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 10px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 32px 8px 16px;
                border-radius: 6px;
                color: #C8C8D0;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: rgba(91, 143, 239, 0.2);
                color: #5B8FEF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2A2A30;
                margin: 4px 8px;
            }
        """)
        
        open_action = QAction(tr("results.context_open", "Открыть файл"), self)
        open_action.triggered.connect(lambda: self._open_file(item.text(6)))
        menu.addAction(open_action)
        
        open_folder_action = QAction(tr("results.context_open_folder", "Открыть папку"), self)
        open_folder_action.triggered.connect(lambda: self._open_folder(item.text(6)))
        menu.addAction(open_folder_action)
        
        menu.addSeparator()
        
        copy_path_action = QAction(tr("results.context_copy_path", "Копировать путь"), self)
        copy_path_action.triggered.connect(lambda: self._copy_path(item.text(6)))
        menu.addAction(copy_path_action)
        
        menu.addSeparator()
        
        delete_action = QAction(tr("results.context_delete", "Удалить файл"), self)
        delete_action.triggered.connect(lambda: self._delete_file(item.text(6)))
        delete_action.setStyleSheet("color: #EF4444;")
        menu.addAction(delete_action)
        
        menu.exec(self.tree.viewport().mapToGlobal(pos))
    
    def _open_file(self, path: str):
        """Открывает файл в системном приложении."""
        if path and os.path.exists(path):
            os.startfile(path)
    
    def _open_folder(self, path: str):
        """Открывает папку с файлом в проводнике."""
        if path and os.path.exists(path):
            folder = os.path.dirname(path)
            subprocess.Popen(f'explorer /select,"{path}"')
    
    def _copy_path(self, path: str):
        """Копирует путь в буфер обмена."""
        if path:
            QApplication.clipboard().setText(path)
    
    def _delete_file(self, path: str):
        """Удаляет файл с подтверждением."""
        if not path or not os.path.exists(path):
            return
        
        reply = QMessageBox.question(
            self, tr("results.delete_title", "Удаление файла"),
            tr("results.delete_confirm", "Вы уверены, что хотите удалить файл?\n\n{name}").format(name=os.path.basename(path)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(path)
                QMessageBox.information(self, tr("results.deleted_title", "Удалено"), tr("results.deleted_msg", "Файл удалён:\n{name}").format(name=os.path.basename(path)))
            except Exception as e:
                QMessageBox.warning(self, tr("results.error_title", "Ошибка"), tr("results.delete_error", "Не удалось удалить файл:\n{error}").format(error=e))
    
    def _open_selected(self):
        """Открывает выбранные файлы."""
        files = self._get_selected_files()
        if not files:
            QMessageBox.information(self, tr("results.no_selection_title", "Нет выбора"), tr("results.no_selection_open", "Отметьте файлы чекбоксами, чтобы открыть их."))
            return
        for f in files[:10]:  # Ограничение на 10 файлов
            self._open_file(f)
    
    def _open_folder_selected(self):
        """Открывает папки выбранных файлов."""
        files = self._get_selected_files()
        if not files:
            QMessageBox.information(self, tr("results.no_selection_title", "Нет выбора"), tr("results.no_selection_folder", "Отметьте файлы чекбоксами, чтобы открыть папку."))
            return
        self._open_folder(files[0])
    
    def _delete_selected(self):
        """Удаляет выбранные файлы."""
        files = self._get_selected_files()
        if not files:
            QMessageBox.information(self, tr("results.no_selection_title", "Нет выбора"), tr("results.no_selection_delete", "Выберите файлы для удаления."))
            return
        
        reply = QMessageBox.question(
            self, tr("results.delete_multiple_title", "Удаление файлов"),
            tr("results.delete_multiple_confirm", "Вы уверены, что хотите удалить {count} файлов?\n\nЭто действие нельзя отменить.").format(count=len(files)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            deleted = 0
            errors = 0
            for path in files:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        deleted += 1
                except:
                    errors += 1
            
            msg = tr("results.deleted_multiple_msg", "Удалено файлов: {deleted}").format(deleted=deleted)
            if errors:
                msg += tr("results.deleted_errors", "\nОшибок: {errors}").format(errors=errors)
            QMessageBox.information(self, tr("results.result_title", "Результат"), msg)
    
    def _export_csv(self):
        """Экспортирует результаты в CSV."""
        from PySide6.QtWidgets import QFileDialog
        
        path, _ = QFileDialog.getSaveFileName(
            self, tr("results.export_dialog_title", "Экспорт CSV"), "duplicates_report.csv",
            tr("results.export_dialog_filter", "CSV файлы (*.csv)")
        )
        
        if not path:
            return
        
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(tr("results.csv_header", "Группа;Файл;Размер;Дата;Хэш;Путь\n"))
                
                for i in range(self.tree.topLevelItemCount()):
                    group_item = self.tree.topLevelItem(i)
                    group_name = group_item.text(1)
                    
                    for j in range(group_item.childCount()):
                        file_item = group_item.child(j)
                        f.write(
                            f"{group_name};"
                            f"{file_item.text(2)};"
                            f"{file_item.text(3)};"
                            f"{file_item.text(4)};"
                            f"{file_item.text(5)};"
                            f"{file_item.text(6)}\n"
                        )
            
            QMessageBox.information(
                self, tr("results.export_complete_title", "Экспорт завершён"),
                tr("results.export_complete_msg", "Отчёт сохранён:\n{path}").format(path=path)
            )
        except Exception as e:
            QMessageBox.warning(self, tr("results.error_title", "Ошибка"),
                tr("results.export_error", "Не удалось экспортировать:\n{error}").format(error=e))
    
    def _go_back(self):
        """Возвращает на главную страницу."""
        parent = self.parent()
        if parent and hasattr(parent, 'setCurrentIndex'):
            parent.setCurrentIndex(0)
    
    def _save_session(self):
        """Сохраняет сессию в JSON."""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        path, _ = QFileDialog.getSaveFileName(
            self, tr("results.save_dialog_title", "Сохранить сессию"), "session.json",
            tr("results.save_dialog_filter", "JSON файлы (*.json)")
        )
        
        if not path:
            return
        
        try:
            data = []
            for i in range(self.tree.topLevelItemCount()):
                group_item = self.tree.topLevelItem(i)
                group_data = {
                    "group": group_item.text(1),
                    "files": []
                }
                for j in range(group_item.childCount()):
                    file_item = group_item.child(j)
                    group_data["files"].append({
                        "name": file_item.text(2),
                        "size": file_item.text(3),
                        "date": file_item.text(4),
                        "hash": file_item.text(5),
                        "path": file_item.text(6)
                    })
                data.append(group_data)
            
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(
                self, tr("results.save_complete_title", "Сохранение завершено"),
                tr("results.save_complete_msg", "Сессия сохранена:\n{path}").format(path=path)
            )
        except Exception as e:
            QMessageBox.warning(self, tr("results.error_title", "Ошибка"),
                tr("results.save_error", "Не удалось сохранить сессию:\n{error}").format(error=e))
    
    def _load_session(self):
        """Загружает сессию из JSON."""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        path, _ = QFileDialog.getOpenFileName(
            self, tr("results.load_dialog_title", "Загрузить сессию"), "",
            tr("results.load_dialog_filter", "JSON файлы (*.json)")
        )
        
        if not path:
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.tree.clear()
            
            for group_data in data:
                group_item = QTreeWidgetItem()
                group_item.setText(0, "")
                group_item.setText(1, group_data.get("group", ""))
                group_item.setText(2, tr("results.group_files", "{count} файлов").format(count=len(group_data.get("files", []))))
                
                group_font = QFont()
                group_font.setBold(True)
                group_item.setFont(1, group_font)
                group_item.setForeground(1, QColor("#5B8FEF"))
                group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
                group_item.setCheckState(0, Qt.Unchecked)
                group_item.setData(0, Qt.UserRole, "group")
                
                self.tree.addTopLevelItem(group_item)
                
                for file_data in group_data.get("files", []):
                    file_item = QTreeWidgetItem()
                    file_item.setText(0, "")
                    file_item.setText(1, "")
                    file_item.setText(2, file_data.get("name", ""))
                    file_item.setText(3, file_data.get("size", ""))
                    file_item.setText(4, file_data.get("date", ""))
                    file_item.setText(5, file_data.get("hash", ""))
                    file_item.setText(6, file_data.get("path", ""))
                    
                    file_item.setFlags(file_item.flags() | Qt.ItemIsUserCheckable)
                    file_item.setCheckState(0, Qt.Unchecked)
                    file_item.setData(0, Qt.UserRole, "file")
                    file_item.setData(0, Qt.UserRole + 1, file_data.get("path", ""))
                    
                    group_item.addChild(file_item)
            
            self._update_stats()
            
            QMessageBox.information(
                self, tr("results.load_complete_title", "Загрузка завершена"),
                tr("results.load_complete_msg", "Сессия загружена:\n{path}").format(path=path)
            )
        except Exception as e:
            QMessageBox.warning(self, tr("results.error_title", "Ошибка"),
                tr("results.load_error", "Не удалось загрузить сессию:\n{error}").format(error=e))
    
    def _open_batch_dialog(self):
        """Открывает диалог пакетной обработки."""
        if not self.scanner:
            return
        dialog = BatchDialog(self.scanner, self)
        dialog.exec()
        self._populate_tree()
    
    def _execute_action(self, action: str):
        """Выполняет действие над выбранными файлами (для main_window)."""
        if action == "delete":
            self._delete_selected()
        elif action == "open":
            self._open_selected()
        elif action == "export":
            self._export_csv()


