"""
Тема AnyDuplicate Advanced
Полная QSS тема с градиентами, тенями, скруглениями, hover-эффектами.
Цветовая палитра: глубокий чёрный #0A0A0C, карточки #141416, акцент #5B8FEF
"""
from PySide6.QtWidgets import QApplication, QWidget, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


def apply_shadow(widget: QWidget, blur_radius: int = 20, offset: int = 4, opacity: int = 80):
    """
    Применяет эффект тени к виджету (замена box-shadow из CSS).
    
    Args:
        widget: целевой виджет
        blur_radius: радиус размытия тени
        offset: смещение тени по Y
        opacity: прозрачность тени (0-255)
    """
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, offset)
    shadow.setColor(QColor(0, 0, 0, opacity))
    widget.setGraphicsEffect(shadow)


def apply_theme(app: QApplication):
    """Применяет тёмную тему к приложению."""
    _apply_dark_theme(app)


def _apply_dark_theme(app: QApplication):
    """Тёмная тема — основная."""
    
    DARK_QSS = """
    /* ===== ГЛОБАЛЬНЫЕ НАСТРОЙКИ ===== */
    QWidget {
        background-color: #0A0A0C;
        color: #C8C8D0;
        font-family: "Geist", "Segoe UI", "Arial", sans-serif;
        font-size: 13px;
    }
    
    QTextEdit, QPlainTextEdit {
        font-family: "Geist Mono", "Consolas", "Courier New", monospace;
    }
    
    QMainWindow {
        background-color: #0A0A0C;
    }
    
    /* ===== СКРОЛЛБАРЫ ===== */
    QScrollBar:vertical {
        background-color: #141416;
        width: 8px;
        border-radius: 4px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background-color: #2A2A30;
        border-radius: 4px;
        min-height: 30px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #5B8FEF;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }
    QScrollBar:horizontal {
        background-color: #141416;
        height: 8px;
        border-radius: 4px;
    }
    QScrollBar::handle:horizontal {
        background-color: #2A2A30;
        border-radius: 4px;
        min-width: 30px;
    }
    QScrollBar::handle:horizontal:hover {
        background-color: #5B8FEF;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        width: 0;
    }
    
    /* ===== КНОПКИ ===== */
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1E1E24, stop:1 #16161C);
        color: #E8E8ED;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 500;
    }
    QPushButton:hover {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #2A2A32, stop:1 #1E1E26);
        border-color: #5B8FEF;
    }
    QPushButton:pressed {
        background-color: #1A1A22;
        border-color: #4A7FDF;
        padding-top: 9px;
        padding-bottom: 7px;
    }
    QPushButton:disabled {
        background-color: #121216;
        color: #4A4A50;
        border-color: #1E1E24;
    }
    QPushButton:focus {
        border-color: #5B8FEF;
    }
    
    /* ===== ПОЛЯ ВВОДА ===== */
    QLineEdit {
        background-color: #141416;
        color: #E8E8ED;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        selection-background-color: rgba(91, 143, 239, 0.3);
    }
    QLineEdit:focus {
        border-color: #5B8FEF;
        background-color: #18181C;
    }
    QLineEdit:disabled {
        background-color: #0E0E12;
        color: #4A4A50;
    }
    QLineEdit::placeholder {
        color: #5A5A60;
    }
    
    /* ===== ВЫПАДАЮЩИЕ СПИСКИ ===== */
    QComboBox {
        background-color: #141416;
        color: #E8E8ED;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 20px;
    }
    QComboBox:hover {
        border-color: #5B8FEF;
    }
    QComboBox::drop-down {
        border: none;
        width: 30px;
        border-left: 1px solid #2A2A30;
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
    }
    QComboBox::down-arrow {
        width: 10px;
        height: 10px;
    }
    QComboBox QAbstractItemView {
        background-color: #141416;
        color: #E8E8ED;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        selection-background-color: rgba(91, 143, 239, 0.2);
        selection-color: #5B8FEF;
        padding: 4px;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 12px;
        border-radius: 4px;
        min-height: 28px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    /* ===== ЧЕКБОКСЫ ===== */
    QCheckBox {
        color: #C8C8D0;
        spacing: 8px;
        font-size: 13px;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #2A2A30;
        border-radius: 4px;
        background-color: #141416;
    }
    QCheckBox::indicator:hover {
        border-color: #5B8FEF;
    }
    QCheckBox::indicator:checked {
        background-color: #5B8FEF;
        border-color: #5B8FEF;
    }
    
    /* ===== РАДИОКНОПКИ ===== */
    QRadioButton {
        color: #C8C8D0;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #2A2A30;
        border-radius: 10px;
        background-color: #141416;
    }
    QRadioButton::indicator:hover {
        border-color: #5B8FEF;
    }
    QRadioButton::indicator:checked {
        background-color: #5B8FEF;
        border-color: #5B8FEF;
    }
    
    /* ===== ГРУППЫ ===== */
    QGroupBox {
        background-color: #141416;
        border: 1px solid #2A2A30;
        border-radius: 12px;
        margin-top: 16px;
        padding: 16px 12px 12px 12px;
        font-weight: 600;
        font-size: 13px;
        color: #E8E8ED;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        background-color: #0A0A0C;
        border: 1px solid #2A2A30;
        border-radius: 6px;
        margin-left: 8px;
        color: #5B8FEF;
    }
    
    /* ===== ПРОГРЕСС-БАР ===== */
    QProgressBar {
        background-color: #141416;
        border: 1px solid #2A2A30;
        border-radius: 6px;
        text-align: center;
        color: #E8E8ED;
        font-size: 11px;
        font-weight: 600;
        height: 20px;
    }
    QProgressBar::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #5B8FEF, stop:1 #7C3AED);
        border-radius: 5px;
    }
    
    /* ===== ТАБЛИЦЫ ===== */
    QTreeWidget, QTableWidget, QTableView {
        background-color: #141416;
        alternate-background-color: #18181C;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        outline: none;
    }
    QTreeWidget::item, QTableWidget::item, QTableView::item {
        padding: 6px 8px;
        border-bottom: 1px solid #1E1E24;
        color: #C8C8D0;
    }
    QTreeWidget::item:selected, QTableWidget::item:selected, QTableView::item:selected {
        background-color: rgba(91, 143, 239, 0.2);
        color: #5B8FEF;
    }
    QTreeWidget::item:hover, QTableWidget::item:hover, QTableView::item:hover {
        background-color: rgba(255, 255, 255, 0.03);
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
    
    /* ===== СПИСКИ ===== */
    QListWidget {
        background-color: #141416;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        outline: none;
    }
    QListWidget::item {
        padding: 8px 12px;
        border-radius: 4px;
    }
    QListWidget::item:selected {
        background-color: rgba(91, 143, 239, 0.2);
        color: #5B8FEF;
    }
    QListWidget::item:hover {
        background-color: rgba(255, 255, 255, 0.03);
    }
    
    /* ===== ТЕКСТОВЫЕ ПОЛЯ ===== */
    QTextEdit, QPlainTextEdit {
        font-family: "Geist Mono", "Consolas", "Courier New", monospace;
        background-color: #141416;
        color: #C8C8D0;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        padding: 8px;
        selection-background-color: rgba(91, 143, 239, 0.3);
    }
    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #5B8FEF;
    }
    
    /* ===== ЛЕЙБЛЫ ===== */
    QLabel {
        color: #C8C8D0;
        background-color: transparent;
    }
    
    /* ===== СПЛИТТЕРЫ ===== */
    QSplitter::handle {
        background-color: #2A2A30;
    }
    QSplitter::handle:horizontal {
        width: 2px;
    }
    QSplitter::handle:vertical {
        height: 2px;
    }
    
    /* ===== СТАТУС-БАР ===== */
    QStatusBar {
        background-color: #0A0A0C;
        color: #8B8B95;
        border-top: 1px solid #2A2A30;
        font-size: 12px;
    }
    QStatusBar::item {
        border: none;
    }
    
    /* ===== ТУЛТИПЫ ===== */
    QToolTip {
        background-color: #1E1E24;
        color: #E8E8ED;
        border: 1px solid #2A2A30;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }
    
    /* ===== МЕНЮ ===== */
    QMenuBar {
        background-color: #0A0A0C;
        border-bottom: 1px solid #2A2A30;
        padding: 2px;
    }
    QMenuBar::item {
        padding: 6px 12px;
        border-radius: 6px;
        color: #8B8B95;
    }
    QMenuBar::item:selected {
        background-color: rgba(91, 143, 239, 0.15);
        color: #5B8FEF;
    }
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
    
    /* ===== ДИАЛОГИ ===== */
    QDialog {
        background-color: #0F0F12;
    }
    
    /* ===== СПИН-БОКС ===== */
    QSpinBox {
        background-color: #141416;
        color: #E8E8ED;
        border: 1px solid #2A2A30;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 13px;
    }
    QSpinBox:focus {
        border-color: #5B8FEF;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        border: none;
        background-color: transparent;
        width: 20px;
    }
    """
    
    app.setStyleSheet(DARK_QSS)
