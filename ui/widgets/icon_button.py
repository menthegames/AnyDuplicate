"""
Кастомная кнопка с SVG-иконкой (Phosphor Light стиль)
Поддерживает flat, danger, icon-only варианты
"""
from PySide6.QtWidgets import QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QSize, QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer
from pathlib import Path


# Путь к папке с иконками
ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "icons"

# Кэш для уже обработанных SVG (чтобы не читать файл каждый раз)
_svg_cache: dict[str, str] = {}


def _load_svg(name: str, color: str = "#C8C8D0", size: int = 20) -> QIcon:
    """
    Загружает SVG-иконку и перекрашивает её в указанный цвет.
    Использует QSvgRenderer для рендеринга без временных файлов.
    """
    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        # Создаём простую заглушку-иконку
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
        # Читаем SVG из кэша или с диска
        cache_key = f"{name}:{color}"
        if cache_key not in _svg_cache:
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            # Заменяем цвет на нужный
            svg_content = svg_content.replace('currentColor', color)
            svg_content = svg_content.replace('stroke="currentColor"', f'stroke="{color}"')
            svg_content = svg_content.replace('fill="currentColor"', f'fill="{color}"')
            _svg_cache[cache_key] = svg_content
        else:
            svg_content = _svg_cache[cache_key]
        
        # Рендерим SVG в QPixmap через QSvgRenderer
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


class IconButton(QPushButton):
    """
    Кнопка с SVG-иконкой.
    
    Особенности:
    - Поддержка flat-стиля (прозрачный фон)
    - Поддержка danger-стиля (красный)
    - Автоматическая смена цвета иконки при hover
    - Icon-only режим (квадратная кнопка без текста)
    """
    
    def __init__(self, icon_name: str = "", text: str = "", parent=None,
                 flat: bool = False, danger: bool = False, icon_size: int = 20):
        super().__init__(text, parent)
        
        self._icon_name = icon_name
        self._icon_size = icon_size
        self._flat = flat
        self._danger = danger
        
        # Устанавливаем свойства для QSS стилизации
        if flat:
            self.setProperty("flat", True)
        if danger:
            self.setProperty("danger", True)
        
        # Загружаем иконку
        if icon_name:
            self._update_icon("#C8C8D0")
        
        # Размер
        self.setMinimumHeight(36)
        if not text and icon_name:
            # Icon-only режим
            self.setFixedSize(36, 36)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    
    def _update_icon(self, color: str):
        """Обновляет иконку с указанным цветом."""
        if self._icon_name:
            icon = _load_svg(self._icon_name, color, self._icon_size)
            self.setIcon(icon)
            self.setIconSize(QSize(self._icon_size, self._icon_size))
    
    def enterEvent(self, event):
        """При наведении меняем цвет иконки на акцентный."""
        if self._icon_name:
            self._update_icon("#8BB5FF")
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """При уходе курсора возвращаем цвет."""
        if self._icon_name:
            self._update_icon("#C8C8D0")
        super().leaveEvent(event)
    
    def setIconByName(self, name: str):
        """Меняет иконку по имени файла (без .svg)."""
        self._icon_name = name
        self._update_icon("#C8C8D0")
