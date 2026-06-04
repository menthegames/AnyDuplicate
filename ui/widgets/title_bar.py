"""
Кастомный title bar для AnyDuplicate Advanced
Без стандартного заголовка Windows, свой с иконкой, названием, кнопками
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QPoint, Signal, QSize, QByteArray
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer
from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"

# Кэш для SVG-иконок title bar
_title_icon_cache: dict[str, QIcon] = {}


def _load_title_icon(name: str, color: str = "#C8C8D0", size: int = 14) -> QIcon:
    """Загружает SVG-иконку для кнопок title bar."""
    cache_key = f"title:{name}:{color}"
    if cache_key in _title_icon_cache:
        return _title_icon_cache[cache_key]
    
    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        icon = QIcon()
        _title_icon_cache[cache_key] = icon
        return icon
    
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        svg_content = svg_content.replace('currentColor', color)
        svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
        
        renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon = QIcon(pixmap)
    except Exception:
        icon = QIcon()
    
    _title_icon_cache[cache_key] = icon
    return icon


class TitleBarButton(QPushButton):
    """Кнопка управления окном (свернуть/развернуть/закрыть) с SVG-иконкой."""
    
    def __init__(self, icon_name: str, color: str = "#C8C8D0", hover_color: str = "#5B8FEF",
                 danger: bool = False, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._color = color
        self._hover_color = "#EF4444" if danger else hover_color
        self._danger = danger
        
        self.setFixedSize(46, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("titleBtn", True)
        
        if danger:
            self.setProperty("danger", True)
        
        # Устанавливаем SVG-иконку
        self._update_icon(color)
        self.setIconSize(QSize(14, 14))
    
    def _update_icon(self, color: str):
        """Обновляет иконку с указанным цветом."""
        icon = _load_title_icon(self._icon_name, color, 14)
        if not icon.isNull():
            self.setIcon(icon)
            self.setText("")
        else:
            # Fallback: если иконка не загрузилась, показываем символ
            fallback_chars = {
                "minimize": "—",
                "maximize": "□",
                "close": "✕",
            }
            self.setText(fallback_chars.get(self._icon_name, ""))
            self.setIcon(QIcon())
    
    def enterEvent(self, event):
        self._update_icon(self._hover_color)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._update_icon(self._color)
        super().leaveEvent(event)


class TitleBar(QWidget):
    """Кастомная строка заголовка."""
    
    minimize_signal = Signal()
    maximize_signal = Signal()
    close_signal = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setProperty("titleBar", True)
        
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 0, 0, 0)
        self._layout.setSpacing(8)
        
        # Иконка приложения
        self._icon_label = QLabel()
        icon_path = Path(__file__).resolve().parent.parent.parent / "app_icon.ico"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._icon_label.setPixmap(pixmap)
        else:
            self._icon_label.setText("")
        self._icon_label.setFixedSize(20, 20)
        self._layout.addWidget(self._icon_label)
        
        # Название
        self._title_label = QLabel("AnyDuplicate Advanced")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setWeight(QFont.Weight.Medium)
        self._title_label.setFont(title_font)
        self._layout.addWidget(self._title_label)
        
        # Растяжка
        self._layout.addStretch()
        
        # Кнопки управления с SVG-иконками
        self._min_btn = TitleBarButton("minimize", hover_color="#8B8B95")
        self._min_btn.clicked.connect(self.minimize_signal.emit)
        self._layout.addWidget(self._min_btn)
        
        self._max_btn = TitleBarButton("maximize", hover_color="#8B8B95")
        self._max_btn.clicked.connect(self.maximize_signal.emit)
        self._layout.addWidget(self._max_btn)
        
        self._close_btn = TitleBarButton("close", danger=True)
        self._close_btn.clicked.connect(self.close_signal.emit)
        self._layout.addWidget(self._close_btn)
        
        # Стиль
        self.setStyleSheet("""
            QWidget[titleBar="true"] {
                background-color: #0A0A0C;
                border-bottom: 1px solid #2A2A30;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }
        """)
    
    def setTitle(self, title: str):
        self._title_label.setText(title)
    
    def updateMaximizeIcon(self, is_maximized: bool):
        """Обновляет иконку кнопки разворота окна."""
        if is_maximized:
            # Для развёрнутого окна используем minimize как иконку "свернуть в окно"
            self._max_btn._icon_name = "minimize"
        else:
            self._max_btn._icon_name = "maximize"
        self._max_btn._update_icon(self._max_btn._color)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            try:
                window.startSystemMove()
            except AttributeError:
                # Fallback для старых версий PySide6/Qt
                window.windowHandle().startSystemMove()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        self.maximize_signal.emit()
        super().mouseDoubleClickEvent(event)
