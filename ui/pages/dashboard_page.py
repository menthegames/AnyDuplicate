"""
Страница дашборда AnyDuplicate Advanced
Круговые диаграммы, гистограммы, метрики, timeline.
"""
import math
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QGridLayout, QFrame, QSizePolicy, QToolTip
)
from PySide6.QtCore import Qt, QSize, QPoint, QTimer

from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QFontMetrics,
    QMouseEvent, QCursor
)

from core.i18n import tr
from core.utils import format_size, get_file_type_category


# Цветовая палитра для диаграмм
CHART_COLORS = [
    QColor("#5B8FEF"),  # синий
    QColor("#EF5B5B"),  # красный
    QColor("#5BEF8F"),  # зелёный
    QColor("#EFBF5B"),  # жёлтый
    QColor("#BF5BEF"),  # фиолетовый
    QColor("#5BEFEF"),  # голубой
    QColor("#EF8F5B"),  # оранжевый
    QColor("#8F5BEF"),  # индиго
    QColor("#5BEFBF"),  # бирюзовый
    QColor("#EF5BBF"),  # розовый
]

def _get_category_labels():
    """Возвращает актуальные названия категорий с учётом текущего языка."""
    return {
        "image": tr("dashboard.category_image", "Изображения"),
        "document": tr("dashboard.category_document", "Документы"),
        "video": tr("dashboard.category_video", "Видео"),
        "audio": tr("dashboard.category_audio", "Аудио"),
        "archive": tr("dashboard.category_archive", "Архивы"),
        "other": tr("dashboard.category_other", "Прочее"),
    }

CATEGORY_COLORS = {
    "image": QColor("#5B8FEF"),
    "document": QColor("#EFBF5B"),
    "video": QColor("#EF5B5B"),
    "audio": QColor("#5BEF8F"),
    "archive": QColor("#BF5BEF"),
    "other": QColor("#8B8B95"),
}

# Маппинг названий категорий (из легенды) обратно в ключи для Timeline
CATEGORY_LABEL_TO_KEY = {
    "Изображения": "image", "Images": "image",
    "Документы": "document", "Documents": "document",
    "Видео": "video", "Videos": "video",
    "Аудио": "audio", "Audio": "audio",
    "Архивы": "archive", "Archives": "archive",
    "Прочее": "other", "Other": "other",
}


class PieChart(QWidget):
    """Круговая диаграмма, рисованная через QPainter, с hover на секторах."""

    def __init__(self, data: dict, title: str = "", parent=None):
        """
        Args:
            data: словарь {label: value}
            title: заголовок диаграммы
        """
        super().__init__(parent)
        self.data = data
        self.chart_title = title
        self.setMinimumSize(400, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self._hovered_index = -1
        self._sector_rects = []  # для определения hover
        self._tooltip_timer = None
        self._last_tooltip_pos = None


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Заголовок
        title_height = 30
        if self.chart_title:
            painter.setPen(QColor("#E8E8ED"))
            font = QFont("Geist", 12, QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(0, 10, w, title_height, Qt.AlignCenter, self.chart_title)

        # Считаем сумму
        total = sum(self.data.values())
        if total == 0:
            painter.setPen(QColor("#6B6B75"))
            font = QFont("Geist", 11)
            painter.setFont(font)
            painter.drawText(0, 0, w, h, Qt.AlignCenter, tr("dashboard.no_data", "Нет данных"))
            painter.end()
            return

        # Определяем, сколько места нужно под легенду
        labels = list(self.data.items())
        legend_item_height = 20
        legend_padding = 10
        legend_height = len(labels) * legend_item_height + legend_padding + 10

        # Доступная высота для диаграммы
        chart_area_height = h - title_height - legend_height - 10

        # Рисуем сектора
        cx, cy = w // 2, title_height + chart_area_height // 2
        radius = min(w, chart_area_height) // 2 - 20

        start_angle = 90 * 16  # начинаем сверху
        colors = list(CHART_COLORS)
        self._sector_rects = []

        for i, (label, value) in enumerate(labels):
            span_angle = int((value / total) * 360 * 16)
            color = colors[i % len(colors)]

            # Сохраняем bounding box сектора для hover
            # Используем boundingRect пирога
            from PySide6.QtCore import QRectF
            pie_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            self._sector_rects.append((pie_rect, start_angle, span_angle, label, value))

            # Если этот сектор под курсором — рисуем ярче
            if i == self._hovered_index:
                painter.setBrush(color.lighter(130))
                painter.setPen(QPen(QColor("#FFFFFF"), 2))
            else:
                painter.setBrush(color)
                painter.setPen(QPen(QColor("#0A0A0C"), 2))

            painter.drawPie(cx - radius, cy - radius, radius * 2, radius * 2,
                           start_angle, span_angle)
            start_angle += span_angle

        # Центральный круг (donut)
        painter.setBrush(QColor("#0F0F12"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - radius // 2, cy - radius // 2, radius, radius)

        # Текст в центре
        painter.setPen(QColor("#E8E8ED"))
        font = QFont("Geist", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(cx - radius // 2, cy - radius // 2 - 10,
                        radius, radius // 2, Qt.AlignCenter, str(total))

        painter.setPen(QColor("#8B8B95"))
        font = QFont("Geist", 10)
        painter.setFont(font)
        painter.drawText(cx - radius // 2, cy + 5,
                        radius, radius // 2, Qt.AlignCenter, tr("dashboard.files_count", "файлов"))

        # Легенда снизу — в две колонки, если элементов много
        painter.setFont(QFont("Geist", 9))
        cols = 2 if len(labels) > 4 else 1
        col_width = w // cols
        items_per_col = math.ceil(len(labels) / cols)

        for i, (label, value) in enumerate(labels):
            color = colors[i % len(colors)]
            pct = (value / total) * 100

            col = i // items_per_col
            row = i % items_per_col

            legend_x = col * col_width + 20
            legend_y = h - legend_height + 10 + row * legend_item_height

            # Цветной квадратик
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(legend_x, legend_y, 10, 10)

            # Текст
            painter.setPen(QColor("#C8C8D0"))
            painter.drawText(legend_x + 16, legend_y, col_width - 40, 14, Qt.AlignLeft,
                            f"{label} ({pct:.1f}%)")

        painter.end()

    def _find_sector(self, pos):
        """Находит индекс сектора под позицией мыши."""
        for idx, (pie_rect, start_angle, span_angle, label, value) in enumerate(self._sector_rects):
            if not pie_rect.contains(pos):
                continue
            cx = pie_rect.center().x()
            cy = pie_rect.center().y()
            dx = pos.x() - cx
            dy = pos.y() - cy
            angle = math.degrees(math.atan2(-dy, dx))
            if angle < 0:
                angle += 360
            sector_start = (start_angle / 16) % 360
            sector_end = sector_start + (span_angle / 16)
            if sector_start <= sector_end:
                if sector_start <= angle <= sector_end:
                    return idx
            else:
                if angle >= sector_start or angle <= sector_end:
                    return idx
        return -1

    def mouseMoveEvent(self, event: QMouseEvent):
        """Отслеживаем hover над секторами."""
        pos = event.position()
        found = self._find_sector(pos)

        if found != self._hovered_index:
            self._hovered_index = found
            self.update()

        # Показываем тултип — только если позиция изменилась
        current_pos = (int(pos.x()), int(pos.y()))
        if found >= 0:
            if current_pos != self._last_tooltip_pos:
                self._last_tooltip_pos = current_pos
                _, _, _, label, value = self._sector_rects[found]
                total = sum(v for _, v in self.data.items())
                pct = (value / total) * 100
                tooltip_text = f"{label}\n{tr('dashboard.tooltip_files', 'Файлов')}: {value}\n{pct:.1f}%"
                QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        else:
            if self._last_tooltip_pos is not None:
                self._last_tooltip_pos = None
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Сбрасываем hover при уходе мыши."""
        self._hovered_index = -1
        self._last_tooltip_pos = None
        self.update()
        QToolTip.hideText()
        super().leaveEvent(event)



class BarChart(QWidget):
    """Гистограмма, рисованная через QPainter, с hover на столбцах."""

    def __init__(self, data: list, title: str = "", max_bars: int = 10, parent=None):
        """
        Args:
            data: список кортежей (label, value)
            title: заголовок
            max_bars: максимальное количество столбцов
        """
        super().__init__(parent)
        self.data = sorted(data, key=lambda x: x[1], reverse=True)[:max_bars]
        self.chart_title = title
        self.setMinimumSize(400, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self._hovered_index = -1
        self._bar_rects = []
        self._last_tooltip_pos = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Заголовок
        if self.chart_title:
            painter.setPen(QColor("#E8E8ED"))
            font = QFont("Geist", 12, QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(0, 10, w, 30, Qt.AlignCenter, self.chart_title)

        if not self.data:
            painter.setPen(QColor("#6B6B75"))
            font = QFont("Geist", 11)
            painter.setFont(font)
            painter.drawText(0, 0, w, h, Qt.AlignCenter, tr("dashboard.no_data", "Нет данных"))
            painter.end()
            return

        # Параметры
        margin_left = 60
        margin_right = 20
        margin_top = 45
        margin_bottom = 60
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        max_val = max(v for _, v in self.data)
        bar_count = len(self.data)
        bar_w = chart_w / bar_count - 8

        # Ось Y
        painter.setPen(QPen(QColor("#2A2A30"), 1))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + chart_h)
        painter.drawLine(margin_left, margin_top + chart_h,
                        margin_left + chart_w, margin_top + chart_h)

        # Деления оси Y
        painter.setPen(QColor("#6B6B75"))
        painter.setFont(QFont("Geist", 8))
        for i in range(5):
            y = margin_top + chart_h - (chart_h * i / 4)
            val = max_val * i / 4
            painter.drawText(0, int(y) - 6, margin_left - 8, 12,
                            Qt.AlignRight, format_size(int(val)))
            painter.setPen(QPen(QColor("#1E1E24"), 1))
            painter.drawLine(margin_left, int(y), margin_left + chart_w, int(y))
            painter.setPen(QColor("#6B6B75"))

        # Столбцы
        self._bar_rects = []
        for i, (label, value) in enumerate(self.data):
            x = margin_left + (chart_w / bar_count) * i + 4
            bar_h = int((value / max_val) * chart_h) if max_val > 0 else 0
            y = margin_top + chart_h - bar_h

            color = CHART_COLORS[i % len(CHART_COLORS)]
            if i == self._hovered_index:
                color = color.lighter(130)
                painter.setPen(QPen(QColor("#FFFFFF"), 1))
            else:
                painter.setPen(Qt.NoPen)

            painter.setBrush(color)
            painter.drawRoundedRect(int(x), y, int(bar_w), bar_h, 3, 3)

            # Сохраняем rect для hover
            self._bar_rects.append((int(x), y, int(bar_w), bar_h, label, value))

            # Подпись под столбцом
            painter.setPen(QColor("#8B8B95"))
            painter.setFont(QFont("Geist", 7))
            fm = QFontMetrics(painter.font())
            label_text = Path(label).name if len(label) > 20 else label
            elided = fm.elidedText(label_text, Qt.ElideMiddle, int(bar_w + 8))
            painter.drawText(int(x) - 4, margin_top + chart_h + 5,
                           int(bar_w + 8), 40, Qt.AlignCenter | Qt.TextWordWrap,
                           elided)

        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Отслеживаем hover над столбцами."""
        pos = event.position()
        found = -1
        for idx, (rx, ry, rw, rh, label, value) in enumerate(self._bar_rects):
            if rx <= pos.x() <= rx + rw and ry <= pos.y() <= ry + rh:
                found = idx
                break

        if found != self._hovered_index:
            self._hovered_index = found
            self.update()

        # Показываем тултип — только если позиция изменилась
        current_pos = (int(pos.x()), int(pos.y()))
        if found >= 0:
            if current_pos != self._last_tooltip_pos:
                self._last_tooltip_pos = current_pos
                _, _, _, _, label, value = self._bar_rects[found]
                file_name = Path(label).name
                tooltip_text = (
                    f"{tr('dashboard.tooltip_file', 'Файл')}: {file_name}\n"
                    f"{tr('dashboard.tooltip_group_size', 'Размер группы')}: {format_size(value)}"
                )
                QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        else:
            if self._last_tooltip_pos is not None:
                self._last_tooltip_pos = None
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Сбрасываем hover при уходе мыши."""
        self._hovered_index = -1
        self._last_tooltip_pos = None
        self.update()
        QToolTip.hideText()
        super().leaveEvent(event)



class TimelineChart(QWidget):
    """Гистограмма по месяцам (timeline создания/изменения файлов).
    Каждый столбец — stacked bar по типам файлов.
    Подпись: месяц + год на оси X.
    """

    def __init__(self, dates: list, category_data: dict = None, title: str = "", parent=None):
        """
        Args:
            dates: список datetime объектов
            category_data: словарь { "YYYY-MM": {"image": count, "document": count, ...} }
            title: заголовок
        """
        super().__init__(parent)
        self.chart_title = title
        self._category_data = category_data or {}
        self._dates = dates

        # Группируем по месяцам
        month_counts = Counter()
        for dt in dates:
            key = dt.strftime("%Y-%m")
            month_counts[key] += 1

        # Сортируем по дате
        self.data = sorted(month_counts.items())
        self.setMinimumSize(400, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self._hovered_index = -1
        self._bar_rects = []
        self._last_tooltip_pos = None

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Заголовок
        if self.chart_title:
            painter.setPen(QColor("#E8E8ED"))
            font = QFont("Geist", 12, QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(0, 10, w, 30, Qt.AlignCenter, self.chart_title)

        if not self.data:
            painter.setPen(QColor("#6B6B75"))
            font = QFont("Geist", 11)
            painter.setFont(font)
            painter.drawText(0, 0, w, h, Qt.AlignCenter, tr("dashboard.no_data", "Нет данных"))
            painter.end()
            return

        margin_left = 50
        margin_right = 20
        margin_top = 45
        margin_bottom = 50
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        bar_count = len(self.data)
        bar_w = max(12, chart_w / bar_count - 6)

        # Определяем категории, которые есть в данных
        all_cats = set()
        for month_key, cat_counts in self._category_data.items():
            all_cats.update(cat_counts.keys())
        # Сортируем категории в определённом порядке
        cat_order = ["image", "document", "video", "audio", "archive", "other"]
        active_cats = [c for c in cat_order if c in all_cats]

        # Максимальное значение (сумма по всем категориям за месяц)
        max_val = 0
        for month_key, _ in self.data:
            cat_counts = self._category_data.get(month_key, {})
            total = sum(cat_counts.values())
            if total > max_val:
                max_val = total

        if max_val == 0:
            max_val = 1

        # Ось Y
        painter.setPen(QPen(QColor("#2A2A30"), 1))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + chart_h)
        painter.drawLine(margin_left, margin_top + chart_h,
                        margin_left + chart_w, margin_top + chart_h)

        # Деления оси Y
        painter.setPen(QColor("#6B6B75"))
        painter.setFont(QFont("Geist", 8))
        for i in range(4):
            y = margin_top + chart_h - (chart_h * i / 3)
            val = int(max_val * i / 3)
            painter.drawText(0, int(y) - 6, margin_left - 8, 12,
                            Qt.AlignRight, str(val))

        # Столбцы (stacked)
        self._bar_rects = []
        for i, (month_key, total_val) in enumerate(self.data):
            x = margin_left + (chart_w / bar_count) * i + 3
            cat_counts = self._category_data.get(month_key, {})

            current_y = margin_top + chart_h
            for cat in active_cats:
                cat_val = cat_counts.get(cat, 0)
                if cat_val <= 0:
                    continue
                bar_h = int((cat_val / max_val) * chart_h) if max_val > 0 else 0
                if bar_h < 1:
                    continue
                bar_y = current_y - bar_h

                color = CATEGORY_COLORS.get(cat, QColor("#8B8B95"))
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(x), bar_y, int(bar_w), bar_h, 2, 2)

                current_y = bar_y

            # Сохраняем общий rect столбца для hover
            bar_top = margin_top + chart_h
            for cat in active_cats:
                cat_val = cat_counts.get(cat, 0)
                if cat_val > 0:
                    bar_h = int((cat_val / max_val) * chart_h)
                    bar_top -= bar_h
            self._bar_rects.append((int(x), bar_top, int(bar_w), margin_top + chart_h - bar_top, month_key, total_val))

            # Подпись: месяц + год
            painter.setPen(QColor("#8B8B95"))
            painter.setFont(QFont("Geist", 7))
            month_label = month_key[5:]  # MM
            year_label = month_key[:4]   # YYYY
            painter.drawText(int(x) - 4, margin_top + chart_h + 5,
                           int(bar_w + 8), 14, Qt.AlignCenter, month_label)
            painter.drawText(int(x) - 4, margin_top + chart_h + 18,
                           int(bar_w + 8), 14, Qt.AlignCenter, year_label)

        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent):
        """Отслеживаем hover над столбцами."""
        pos = event.position()
        found = -1
        for idx, (rx, ry, rw, rh, month_key, total_val) in enumerate(self._bar_rects):
            if rx <= pos.x() <= rx + rw and ry <= pos.y() <= ry + rh:
                found = idx
                break

        if found != self._hovered_index:
            self._hovered_index = found
            self.update()

        # Показываем тултип — только если позиция изменилась
        current_pos = (int(pos.x()), int(pos.y()))
        if found >= 0:
            if current_pos != self._last_tooltip_pos:
                self._last_tooltip_pos = current_pos
                _, _, _, _, month_key, total_val = self._bar_rects[found]
                cat_counts = self._category_data.get(month_key, {})
                labels = _get_category_labels()
                lines = [
                    f"{tr('dashboard.tooltip_month', 'Месяц')}: {month_key}",
                    f"{tr('dashboard.tooltip_files', 'Файлов')}: {total_val}",
                ]
                for cat in ["image", "document", "video", "audio", "archive", "other"]:
                    if cat in cat_counts and cat_counts[cat] > 0:
                        cat_label = labels.get(cat, cat)
                        lines.append(f"  {cat_label}: {cat_counts[cat]}")
                tooltip_text = "\n".join(lines)
                QToolTip.showText(event.globalPosition().toPoint(), tooltip_text, self)
        else:
            if self._last_tooltip_pos is not None:
                self._last_tooltip_pos = None
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Сбрасываем hover при уходе мыши."""
        self._hovered_index = -1
        self._last_tooltip_pos = None
        self.update()
        QToolTip.hideText()
        super().leaveEvent(event)



class MetricCard(QFrame):
    """Карточка с крупной цифрой и подписью."""

    def __init__(self, value: str, label: str, color: str = "#5B8FEF", parent=None):
        super().__init__(parent)
        self.setProperty("metricCard", True)
        self.setMinimumSize(160, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Значение
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-size: 28px;
            font-weight: bold;
        """)
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)

        # Подпись
        self.label = QLabel(label)
        self.label.setStyleSheet("""
            color: #8B8B95;
            font-size: 12px;
        """)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.setStyleSheet("""
            QFrame[metricCard="true"] {
                background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 12px;
            }
            QFrame[metricCard="true"]:hover {
                border-color: #5B8FEF;
            }
        """)


class DashboardPage(QWidget):
    """Страница дашборда со статистикой и диаграммами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scanner = None
        self._setup_ui()

    def _setup_ui(self):
        """Создаёт UI дашборда."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Заголовок
        self.title = QLabel(tr("dashboard.title", "Дашборд"))
        self.title.setStyleSheet("""
            color: #E8E8ED;
            font-size: 22px;
            font-weight: bold;
        """)
        layout.addWidget(self.title)

        # Подзаголовок
        self.subtitle = QLabel(tr("dashboard.subtitle", "Статистика и аналитика по результатам сканирования"))
        self.subtitle.setStyleSheet("color: #8B8B95; font-size: 13px;")
        layout.addWidget(self.subtitle)

        # Scroll area для контента
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #0F0F12;
                width: 8px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: #2A2A30;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self._scroll_layout = QVBoxLayout(scroll_content)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(16)

        # --- Метрики (сетка 2x2) ---
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        self.metric_groups = MetricCard("0", tr("dashboard.metric_groups", "Групп дубликатов"))
        self.metric_files = MetricCard("0", tr("dashboard.metric_files", "Всего файлов"))
        self.metric_size = MetricCard("0 Б", tr("dashboard.metric_size", "Объём дубликатов"))
        self.metric_saved = MetricCard("0 Б", tr("dashboard.metric_saved", "Можно сэкономить"))

        metrics_grid.addWidget(self.metric_groups, 0, 0)
        metrics_grid.addWidget(self.metric_files, 0, 1)
        metrics_grid.addWidget(self.metric_size, 1, 0)
        metrics_grid.addWidget(self.metric_saved, 1, 1)

        self._scroll_layout.addLayout(metrics_grid)

        # --- Круговая диаграмма (на всю ширину) ---
        self.pie_chart = PieChart({}, tr("dashboard.pie_title", "Распределение по типам файлов"))
        self._scroll_layout.addWidget(self.pie_chart)

        # --- Гистограмма топ-10 групп (на всю ширину) ---
        self.bar_chart = BarChart([], tr("dashboard.bar_title", "Топ-10 групп по размеру"))
        self._scroll_layout.addWidget(self.bar_chart)

        # --- Timeline (на всю ширину) ---
        self.timeline = TimelineChart([], {}, tr("dashboard.timeline_title", "Файлы по месяцам (дата изменения)"))
        self._scroll_layout.addWidget(self.timeline)

        # Сообщение "нет данных"
        self.empty_label = QLabel(
            tr("dashboard.empty_text", "Нет данных для отображения.\n"
               "Выполните сканирование, чтобы увидеть статистику.")
        )
        self.empty_label.setStyleSheet("""
            color: #6B6B75;
            font-size: 14px;
            padding: 40px;
        """)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self._scroll_layout.addWidget(self.empty_label)

        self._scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

    def retranslate_ui(self):
        """Обновляет текст всех элементов при смене языка."""
        # Заголовок и подзаголовок
        self.title.setText(tr("dashboard.title", "Дашборд"))
        self.subtitle.setText(tr("dashboard.subtitle", "Статистика и аналитика по результатам сканирования"))

        # Метрики
        self.metric_groups.label.setText(tr("dashboard.metric_groups", "Групп дубликатов"))
        self.metric_files.label.setText(tr("dashboard.metric_files", "Всего файлов"))
        self.metric_size.label.setText(tr("dashboard.metric_size", "Объём дубликатов"))
        self.metric_saved.label.setText(tr("dashboard.metric_saved", "Можно сэкономить"))

        # Заголовки диаграмм
        self.pie_chart.chart_title = tr("dashboard.pie_title", "Распределение по типам файлов")
        self.pie_chart.update()
        self.bar_chart.chart_title = tr("dashboard.bar_title", "Топ-10 групп по размеру")
        self.bar_chart.update()
        self.timeline.chart_title = tr("dashboard.timeline_title", "Файлы по месяцам (дата изменения)")
        self.timeline.update()

        # Пустое сообщение
        self.empty_label.setText(
            tr("dashboard.empty_text", "Нет данных для отображения.\n"
               "Выполните сканирование, чтобы увидеть статистику.")
        )

        # Обновляем данные для пересчёта категорий
        self._update_data()

    def set_scanner(self, scanner):
        """Обновляет дашборд данными из сканера."""
        self._scanner = scanner
        self._update_data()

    def _update_data(self):
        """Обновляет все виджеты дашборда на основе данных сканера."""
        if not self._scanner or not self._scanner.preview_data:
            # Сбрасываем метрики и диаграммы
            self.metric_groups.value_label.setText("0")
            self.metric_files.value_label.setText("0")
            self.metric_size.value_label.setText("0 Б")
            self.metric_saved.value_label.setText("0 Б")
            self.pie_chart.data = {}
            self.pie_chart.update()
            self.bar_chart.data = []
            self.bar_chart.update()
            self.timeline.data = []
            self.timeline._category_data = {}
            self.timeline.update()
            self.empty_label.show()
            return

        self.empty_label.hide()

        duplicates = self._scanner.duplicates
        preview_data = self._scanner.preview_data

        # --- Метрики ---
        total_groups = len(duplicates)
        total_files = sum(len(v) for v in duplicates.values())
        total_dups = total_files - total_groups  # копии (можно удалить)

        total_size = 0
        saved_size = 0
        all_dates = []
        category_counts = Counter()
        category_sizes = defaultdict(int)
        group_sizes = []

        # Для timeline: категории по месяцам
        timeline_categories = defaultdict(lambda: defaultdict(int))

        for h, original, dups in preview_data:
            group_total = 0
            try:
                orig_size = original.stat().st_size
                group_total += orig_size
            except Exception:
                orig_size = 0

            for d in dups:
                try:
                    s = d.stat().st_size
                    total_size += s
                    saved_size += s
                    group_total += s
                except Exception:
                    pass

                # Дата изменения
                try:
                    mtime = datetime.fromtimestamp(d.stat().st_mtime)
                    all_dates.append(mtime)
                    month_key = mtime.strftime("%Y-%m")
                    cat = get_file_type_category(str(d))
                    timeline_categories[month_key][cat] += 1
                except Exception:
                    pass

                # Категория
                cat = get_file_type_category(str(d))
                category_counts[cat] += 1
                try:
                    category_sizes[cat] += d.stat().st_size
                except Exception:
                    pass

            group_sizes.append((str(original), group_total))

        # --- Метрики ---
        self.metric_groups.value_label.setText(str(total_groups))
        self.metric_files.value_label.setText(str(total_files))
        self.metric_size.value_label.setText(format_size(total_size))
        self.metric_saved.value_label.setText(format_size(saved_size))

        # --- Круговая диаграмма ---
        labels = _get_category_labels()
        pie_data = {}
        for cat in ["image", "document", "video", "audio", "archive", "other"]:
            if category_counts[cat] > 0:
                pie_data[labels.get(cat, cat)] = category_counts[cat]
        self.pie_chart.data = pie_data
        self.pie_chart.update()

        # --- Гистограмма топ-10 ---
        # Фильтруем: показываем только группы, составляющие >1% от общего размера
        if group_sizes and total_size > 0:
            min_significant_size = total_size * 0.01
            significant_groups = [(p, s) for p, s in group_sizes if s >= min_significant_size]
            if significant_groups:
                self.bar_chart.data = significant_groups
            else:
                # Если все группы мелкие — показываем топ-10 самых крупных
                self.bar_chart.data = group_sizes
        else:
            self.bar_chart.data = group_sizes
        self.bar_chart.update()


        # --- Timeline ---
        self.timeline._category_data = dict(timeline_categories)
        self.timeline._dates = all_dates
        # Пересчитываем month_counts
        month_counts = Counter()
        for dt in all_dates:
            key = dt.strftime("%Y-%m")
            month_counts[key] += 1
        self.timeline.data = sorted(month_counts.items())
        self.timeline.update()
