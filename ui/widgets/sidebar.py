"""
Боковая панель навигации AnyDuplicate Advanced
Разделы: Поиск, Результаты, История, Настройки
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal, QSize, QByteArray
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer
from pathlib import Path
from core.i18n import tr

ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"

# Кэш для SVG
_svg_cache: dict[str, str] = {}


def _load_svg_icon(name: str, color: str = "#C8C8D0", size: int = 20) -> QIcon:
    """
    Загружает SVG-иконку и перекрашивает её в указанный цвет.
    Использует QSvgRenderer для рендеринга без временных файлов.
    """
    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QPen(QColor(color), 2))
        painter.drawRect(2, 2, size - 4, size - 4)
        painter.drawLine(4, size // 2, size - 4, size // 2)
        painter.drawLine(size // 2, 4, size // 2, size - 4)
        painter.end()
        return QIcon(pixmap)
    
    try:
        cache_key = f"{name}:{color}"
        if cache_key not in _svg_cache:
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            svg_content = svg_content.replace('currentColor', color)
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
            _svg_cache[cache_key] = svg_content
        else:
            svg_content = _svg_cache[cache_key]
        
        renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except Exception:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)


class NavButton(QPushButton):
    """Кнопка навигации в боковой панели."""
    
    def __init__(self, text: str, icon_name: str = "", section_id: str = "", parent=None):
        super().__init__(text, parent)
        self.section_id = section_id
        self._active = False
        
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setProperty("navBtn", True)
        
        # Загружаем иконку если есть (с перекрашиванием в светлый)
        if icon_name:
            icon = _load_svg_icon(icon_name, "#C8C8D0", 20)
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20))
        
        self._update_style()
    
    def setActive(self, active: bool):
        self._active = active
        self.setChecked(active)
        self._update_style()
    
    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                QPushButton[navBtn="true"] {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(91, 143, 239, 0.2), stop:1 transparent);
                    color: #5B8FEF;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton[navBtn="true"]:hover {
                    background-color: rgba(91, 143, 239, 0.15);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton[navBtn="true"] {
                    background-color: transparent;
                    color: #8B8B95;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton[navBtn="true"]:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #E8E8ED;
                }
            """)
    
    def enterEvent(self, event):
        if not self._active:
            self.setStyleSheet("""
                QPushButton[navBtn="true"] {
                    background-color: rgba(255, 255, 255, 0.05);
                    color: #E8E8ED;
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 500;
                }
            """)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self._active:
            self._update_style()
        super().leaveEvent(event)


class Sidebar(QWidget):
    """Боковая панель навигации."""
    
    section_changed = Signal(str)  # section_id
    pro_section_clicked = Signal()  # клик по Pro/Активировать Pro
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setProperty("sidebar", True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)
        
        # Логотип / название
        logo_label = QLabel("AnyDuplicate")
        logo_font = QFont()
        logo_font.setPointSize(14)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setStyleSheet("color: #E8E8ED; padding: 8px 12px 16px 12px;")
        layout.addWidget(logo_label)
        
        # Разделитель
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #2A2A30;")
        layout.addWidget(separator)
        
        layout.addSpacing(8)
        
        # Кнопки навигации
        self._buttons = {}
        nav_items = [
            (tr("nav.search", "  Поиск"), "search", "search"),
            (tr("nav.results", "  Результаты"), "file", "results"),
            (tr("nav.dashboard", "  Дашборд"), "dashboard", "dashboard"),
            (tr("nav.history", "  История"), "history", "history"),
            (tr("nav.settings", "  Настройки"), "settings", "settings"),
            (tr("nav.help", "  Справка"), "help", "help"),
        ]
        
        # Tooltip'ы для кнопок навигации
        nav_tooltips = {
            "search": tr("nav.tooltip.search", "Поиск дубликатов — выберите папку и настройте фильтры"),
            "results": tr("nav.tooltip.results", "Результаты последнего сканирования"),
            "dashboard": tr("nav.tooltip.dashboard", "Дашборд — статистика и аналитика по результатам"),
            "history": tr("nav.tooltip.history", "История предыдущих сессий сканирования"),
            "settings": tr("nav.tooltip.settings", "Настройки приложения, тема, лицензия"),
            "help": tr("nav.tooltip.help", "Справка по использованию приложения"),
        }

        
        for text, icon, section_id in nav_items:
            btn = NavButton(text, icon, section_id)
            btn.setToolTip(nav_tooltips.get(section_id, ""))
            btn.clicked.connect(lambda checked, sid=section_id: self._on_section_clicked(sid))
            layout.addWidget(btn)
            self._buttons[section_id] = btn
        
        layout.addStretch()
        
        # --- Pro / Активировать Pro секция ---
        self._pro_layout = QHBoxLayout()
        self._pro_layout.setContentsMargins(0, 0, 0, 0)
        self._pro_layout.setSpacing(0)
        
        self._pro_btn = QPushButton()
        self._pro_btn.setCursor(Qt.PointingHandCursor)
        self._pro_btn.setMinimumHeight(44)
        self._pro_btn.clicked.connect(self.pro_section_clicked.emit)
        layout.addWidget(self._pro_btn)
        
        # Версия внизу
        version_label = QLabel("v3.0.0")
        version_label.setStyleSheet("color: #5A5A60; font-size: 11px; padding: 8px 12px;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        # Стиль панели
        self.setStyleSheet("""
            QWidget[sidebar="true"] {
                background-color: #0A0A0C;
                border-right: 1px solid #2A2A30;
            }
        """)
    
    def set_pro(self, is_pro: bool):
        """Обновляет кнопку Pro/Активировать Pro в зависимости от статуса лицензии."""
        if is_pro:
            self._pro_btn.setText(tr("nav.pro", "  Pro"))
            self._pro_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(91, 143, 239, 0.1);
                    color: #5B8FEF;
                    border: 1px solid rgba(91, 143, 239, 0.3);
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: rgba(91, 143, 239, 0.2);
                    border: 1px solid rgba(91, 143, 239, 0.5);
                }
            """)
        else:
            self._pro_btn.setText(tr("nav.activate_pro", "  Активировать Pro"))
            self._pro_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #8B8B95;
                    border: 1px solid #2A2A30;
                    border-radius: 8px;
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid #5B8FEF;
                    color: #5B8FEF;
                }
            """)
    
    def retranslate_ui(self):
        """Обновляет текст кнопок навигации при смене языка."""
        nav_items = [
            ("search", tr("nav.search", "  Поиск"), tr("nav.tooltip.search", "Поиск дубликатов — выберите папку и настройте фильтры")),
            ("results", tr("nav.results", "  Результаты"), tr("nav.tooltip.results", "Результаты последнего сканирования")),
            ("dashboard", tr("nav.dashboard", "  Дашборд"), tr("nav.tooltip.dashboard", "Дашборд — статистика и аналитика по результатам")),
            ("history", tr("nav.history", "  История"), tr("nav.tooltip.history", "История предыдущих сессий сканирования")),
            ("settings", tr("nav.settings", "  Настройки"), tr("nav.tooltip.settings", "Настройки приложения, тема, лицензия")),
            ("help", tr("nav.help", "  Справка"), tr("nav.tooltip.help", "Справка по использованию приложения")),
        ]

        for section_id, text, tooltip in nav_items:
            if section_id in self._buttons:
                btn = self._buttons[section_id]
                btn.setText(text)
                btn.setToolTip(tooltip)
    
    def _on_section_clicked(self, section_id: str):
        """Обрабатывает клик по разделу."""
        for sid, btn in self._buttons.items():
            btn.setActive(sid == section_id)
        self.section_changed.emit(section_id)
    
    def set_active(self, section_id: str):
        """Устанавливает активный раздел и деактивирует остальные."""
        for sid, btn in self._buttons.items():
            btn.setActive(sid == section_id)
    
    def add_badge(self, section_id: str, count: int):
        """Добавляет бейдж с количеством к кнопке."""
        if section_id in self._buttons and count > 0:
            btn = self._buttons[section_id]
            current_text = btn.text()
            # Убираем старый бейдж если был
            if "(" in current_text:
                current_text = current_text.split(" (")[0]
            btn.setText(f"{current_text} ({count})")
