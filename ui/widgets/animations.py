"""
Анимации для AnyDuplicate Advanced
Fade-in, hover-подсветка, press-scale эффекты, переходы между страницами
"""
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QTimer
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect, QStackedWidget


def fade_in(widget: QWidget, duration: int = 300, delay: int = 0):
    """
    Плавное появление виджета (fade-in).
    
    Args:
        widget: целевой виджет
        duration: длительность анимации в мс
        delay: задержка перед началом в мс
    """
    opacity_effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(opacity_effect)
    
    animation = QPropertyAnimation(opacity_effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    if delay > 0:
        animation.setLoopCount(1)
    
    animation.start()
    return animation


def fade_in_sequence(widgets: list, duration: int = 250, stagger: int = 80):
    """
    Последовательное появление группы виджетов.
    
    Args:
        widgets: список виджетов
        duration: длительность каждой анимации
        stagger: задержка между анимациями соседних виджетов
    """
    group = QParallelAnimationGroup()
    
    for i, widget in enumerate(widgets):
        anim = fade_in(widget, duration, delay=i * stagger)
        group.addAnimation(anim)
    
    group.start()
    return group


class HoverHighlight:
    """
    Эффект подсветки при наведении.
    Использование: в enterEvent/leaveEvent виджета вызывать highlight()/unhighlight().
    """
    
    def __init__(self, widget: QWidget, 
                 normal_style: str = "",
                 hover_style: str = "",
                 duration: int = 150):
        self.widget = widget
        self.normal_style = normal_style
        self.hover_style = hover_style
        self.duration = duration
        self._animation = None
    
    def highlight(self):
        """Применяет hover-стиль."""
        if self.hover_style:
            self.widget.setStyleSheet(self.hover_style)
    
    def unhighlight(self):
        """Возвращает обычный стиль."""
        if self.normal_style:
            self.widget.setStyleSheet(self.normal_style)


class PressScale:
    """
    Эффект масштабирования при нажатии (press-scale).
    Создаёт иллюзию "вдавливания" кнопки.
    """
    
    def __init__(self, widget: QWidget, scale_factor: float = 0.95):
        self.widget = widget
        self.scale_factor = scale_factor
        self._original_style = widget.styleSheet()
    
    def press(self):
        """Уменьшает виджет (имитация нажатия)."""
        self.widget.setStyleSheet(
            self._original_style + 
            f"padding-top: {self._get_padding_offset()}px;"
            f"padding-bottom: 0px;"
        )
    
    def release(self):
        """Возвращает исходный размер."""
        self.widget.setStyleSheet(self._original_style)
    
    def _get_padding_offset(self) -> int:
        """Вычисляет смещение для эффекта нажатия."""
        return 2


# Хранилище для анимаций, чтобы они не удалялись сборщиком мусора
_animation_refs = []


def _cleanup_animation(anim):
    """Удаляет ссылку на анимацию после её завершения."""
    if anim in _animation_refs:
        _animation_refs.remove(anim)


def animate_page_switch(stack: QStackedWidget, old_index: int, new_index: int,
                        duration: int = 200):
    """
    Анимация перехода между страницами QStackedWidget.
    Старая страница плавно исчезает (fade-out), затем новая появляется (fade-in).
    
    Args:
        stack: QStackedWidget с переключаемыми страницами
        old_index: индекс текущей (уходящей) страницы
        new_index: индекс новой (приходящей) страницы
        duration: длительность каждой половины анимации в мс
    """
    old_widget = stack.widget(old_index)
    new_widget = stack.widget(new_index)
    
    if not old_widget or not new_widget:
        stack.setCurrentIndex(new_index)
        return
    
    # Fade-out старой страницы
    old_opacity = QGraphicsOpacityEffect(old_widget)
    old_widget.setGraphicsEffect(old_opacity)
    
    fade_out = QPropertyAnimation(old_opacity, b"opacity")
    fade_out.setDuration(duration)
    fade_out.setStartValue(1.0)
    fade_out.setEndValue(0.0)
    fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    # Сохраняем ссылку, чтобы анимация не была удалена сборщиком мусора
    _animation_refs.append(fade_out)
    
    def _on_fade_out_finished():
        # Убираем ссылку на fade_out
        _cleanup_animation(fade_out)
        
        # Переключаем страницу
        stack.setCurrentIndex(new_index)
        
        # Fade-in новой страницы
        new_opacity = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_opacity)
        
        fade_in_anim = QPropertyAnimation(new_opacity, b"opacity")
        fade_in_anim.setDuration(duration)
        fade_in_anim.setStartValue(0.0)
        fade_in_anim.setEndValue(1.0)
        fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Сохраняем ссылку на fade_in_anim
        _animation_refs.append(fade_in_anim)
        fade_in_anim.finished.connect(lambda: _cleanup_animation(fade_in_anim))
        fade_in_anim.start()
    
    fade_out.finished.connect(_on_fade_out_finished)
    fade_out.start()
