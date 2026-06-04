"""
Страница истории сканирований AnyDuplicate Advanced
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Slot, QSize, QByteArray
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from pathlib import Path
import json
import datetime

from core.i18n import tr


# Кэш для SVG-иконок статуса
_status_icons: dict[str, QIcon] = {}
ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"


def _get_status_icon(status: str) -> QIcon:
    """Возвращает QIcon для статуса на основе SVG-иконки."""
    cache_key = f"status:{status}"
    if cache_key in _status_icons:
        return _status_icons[cache_key]
    
    # Маппинг статусов на иконки
    icon_map = {
        "✓": "check",
        "✔": "check",
        "success": "check",
        "warning": "warning",
        "error": "close",
        "✕": "close",
        "failed": "close",
    }
    
    icon_name = icon_map.get(status, "question")
    svg_path = ICONS_DIR / f"{icon_name}.svg"
    
    if svg_path.exists():
        try:
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            svg_content = svg_content.replace('currentColor', '#5B8FEF')
            svg_content = svg_content.replace('stroke="currentColor"', 'stroke="#5B8FEF"')
            svg_content = svg_content.replace('fill="currentColor"', 'fill="#5B8FEF"')
            
            renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon = QIcon(pixmap)
        except Exception:
            icon = QIcon()
    else:
        icon = QIcon()
    
    _status_icons[cache_key] = icon
    return icon


class HistoryPage(QWidget):
    """Страница истории сканирований."""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Заголовок
        self.title = QLabel(tr("history.title", "История сканирований"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title.setFont(title_font)
        self.title.setStyleSheet("color: #E8E8ED;")
        layout.addWidget(self.title)
        
        self.desc = QLabel(tr("history.description", "Здесь отображаются предыдущие сессии сканирования."))
        self.desc.setStyleSheet("color: #8B8B95; font-size: 12px;")
        layout.addWidget(self.desc)
        
        # Таблица истории
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels([
            tr("history.col_date", "Дата"),
            tr("history.col_folder", "Папка"),
            tr("history.col_groups", "Групп"),
            tr("history.col_copies", "Копий"),
            tr("history.col_size", "Объём"),
            tr("history.col_status", "Статус")
        ])
        self.history_tree.setAlternatingRowColors(True)
        self.history_tree.setRootIsDecorated(False)
        self.history_tree.setAnimated(True)
        self.history_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #2A2A30;
                border-radius: 8px;
                background-color: #141416;
                alternate-background-color: #1A1A1E;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                color: #C8C8D0;
            }
            QTreeWidget::item:selected {
                background-color: rgba(91, 143, 239, 0.2);
                color: #5B8FEF;
            }
            QHeaderView::section {
                background-color: #0A0A0C;
                color: #8B8B95;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2A2A30;
                font-weight: 600;
            }
        """)
        
        header = self.history_tree.header()
        header.setStretchLastSection(True)
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.history_tree, 1)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        self.load_btn = QPushButton(tr("history.load_session", "Загрузить сессию"))
        self.load_btn.clicked.connect(self._load_session)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E24;
                color: #E8E8ED;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2A2A32;
                border-color: #5B8FEF;
            }
        """)
        
        self.clear_btn = QPushButton(tr("history.clear", "Очистить историю"))
        self.clear_btn.clicked.connect(self._clear_history)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.1);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
            }
        """)
        
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        # Загружаем историю
        self._load_history()
    
    def retranslate_ui(self):
        """Обновляет текст всех элементов при смене языка."""
        # Заголовок и описание
        self.title.setText(tr("history.title", "История сканирований"))
        self.desc.setText(tr("history.description", "Здесь отображаются предыдущие сессии сканирования."))

        # Заголовки таблицы
        self.history_tree.setHeaderLabels([
            tr("history.col_date", "Дата"),
            tr("history.col_folder", "Папка"),
            tr("history.col_groups", "Групп"),
            tr("history.col_copies", "Копий"),
            tr("history.col_size", "Объём"),
            tr("history.col_status", "Статус")
        ])

        # Кнопки
        self.load_btn.setText(tr("history.load_session", "Загрузить сессию"))
        self.clear_btn.setText(tr("history.clear", "Очистить историю"))

        # Перезагружаем историю для обновления данных
        self._load_history()

    def _load_history(self):
        """Загружает историю из конфига."""
        history = self.config.get("scan_history", [])
        self.history_tree.clear()
        
        for entry in history:
            item = QTreeWidgetItem()
            item.setText(0, entry.get("date", "—"))
            item.setText(1, entry.get("path", "—"))
            item.setText(2, str(entry.get("groups", 0)))
            item.setText(3, str(entry.get("copies", 0)))
            item.setText(4, entry.get("size", "—"))
            
            # Статус с SVG-иконкой вместо эмодзи
            status = entry.get("status", "✓")
            icon = _get_status_icon(status)
            if not icon.isNull():
                item.setIcon(5, icon)
            item.setText(5, "")
            
            self.history_tree.addTopLevelItem(item)
        
        for i in range(6):
            self.history_tree.resizeColumnToContents(i)
    
    def add_entry(self, path: str, groups: int, copies: int, size: str):
        """Добавляет запись в историю."""
        history = self.config.get("scan_history", [])
        history.insert(0, {
            "date": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
            "path": path,
            "groups": groups,
            "copies": copies,
            "size": size,
            "status": "✓"
        })
        # Ограничиваем историю 50 записями
        if len(history) > 50:
            history = history[:50]
        self.config.set("scan_history", history)
        self._load_history()
    
    def _load_session(self):
        """Загружает сессию из JSON-файла."""
        path, _ = QFileDialog.getOpenFileName(
            self, tr("history.load_dialog_title", "Загрузить сессию"), "",
            tr("history.load_dialog_filter", "JSON файлы (*.json)")
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                QMessageBox.information(
                    self, tr("history.loaded_title", "Сессия загружена"),
                    tr("history.loaded_msg", "Загружена сессия: {date}\nГрупп: {groups}\nКопий: {copies}").format(
                        date=data.get('date', '—'),
                        groups=data.get('groups', 0),
                        copies=data.get('copies', 0)
                    )
                )
            except Exception as e:
                QMessageBox.warning(self, tr("history.error_title", "Ошибка"),
                    tr("history.load_error", "Не удалось загрузить сессию: {error}").format(error=e))
    
    def _clear_history(self):
        """Очищает историю."""
        reply = QMessageBox.question(
            self, tr("history.clear_title", "Очистить историю"),
            tr("history.clear_confirm", "Вы уверены, что хотите очистить всю историю сканирований?"),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config.set("scan_history", [])
            self._load_history()
