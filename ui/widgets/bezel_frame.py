"""
Double-Bezel архитектура
Вложенные QFrame с разными стилями для создания эффекта "двойной рамки"
"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush


class BezelFrame(QFrame):
    """
    Фрейм с двойной рамкой (Double-Bezel).
    
    Внешняя рамка — тёмная (bg_card), внутренняя — чуть светлее (bg_elevated).
    Создаёт эффект глубины и премиальности.
    
    Использование:
        frame = BezelFrame()
        frame.setContentWidget(my_widget)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("bezel", True)
        
        # Внешний контейнер (основной фон)
        self.setObjectName("outerBezel")
        
        # Внутренний контейнер
        self._inner_frame = QFrame(self)
        self._inner_frame.setObjectName("innerBezel")
        self._inner_frame.setProperty("card", True)
        
        # Layout для внутреннего контента
        self._inner_layout = QVBoxLayout(self._inner_frame)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)
        
        # Основной layout
        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(2, 2, 2, 2)
        self._outer_layout.addWidget(self._inner_frame)
        
        # Стили
        self._apply_styles()
    
    def _apply_styles(self):
        """Применяет QSS стили для Double-Bezel эффекта."""
        self.setStyleSheet("""
            #outerBezel {
                background-color: #0A0A0C;
                border: 1px solid #2A2A30;
                border-radius: 14px;
            }
            #innerBezel {
                background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 12px;
            }
        """)
    
    def setContentWidget(self, widget):
        """Устанавливает виджет-наполнение во внутреннюю рамку."""
        self._inner_layout.addWidget(widget)
    
    def setContentLayout(self, layout):
        """Устанавливает layout во внутреннюю рамку."""
        self._inner_layout.addLayout(layout)
    
    def innerFrame(self) -> QFrame:
        """Возвращает внутренний фрейм для дополнительной настройки."""
        return self._inner_frame


class BezelCard(QFrame):
    """
    Карточка с Double-Bezel эффектом для отображения контента.
    Используется для метрик, превью, секций дашборда.
    """
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("bezelCard", True)
        
        # Основной layout
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # Bezel-рамка
        self._bezel = BezelFrame(self)
        
        # Внутренний контент
        self._content_widget = QFrame()
        self._content_widget.setObjectName("cardContent")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(8)
        
        self._bezel.setContentWidget(self._content_widget)
        self._layout.addWidget(self._bezel)
        
        # Стили
        self._content_widget.setStyleSheet("""
            #cardContent {
                background-color: transparent;
                border: none;
            }
        """)
    
    def contentLayout(self) -> QVBoxLayout:
        """Возвращает layout контента для добавления виджетов."""
        return self._content_layout
    
    def contentWidget(self) -> QFrame:
        """Возвращает виджет контента."""
        return self._content_widget
