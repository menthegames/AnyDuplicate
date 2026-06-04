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
    QGridLayout, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics

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


class PieChart(QWidget):
    """Круговая диаграмма, рисованная через QPainter."""

    def __init__(self, data: dict, title: str = "", parent=None):
        """
        Args:
            data: словарь {label: value}
            title: заголовок диаграммы
        """
        super().__init__(parent)
        self.data = data
        self.chart_title = title
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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

        # Считаем сумму
        total = sum(self.data.values())
        if total == 0:
            painter.setPen(QColor("#6B6B75"))
            font = QFont("Geist", 11)
            painter.setFont(font)
            painter.drawText(0, 0, w, h, Qt.AlignCenter, tr("dashboard.no_data", "Нет данных"))
            painter.end()
            return

        # Рисуем сектора
        cx, cy = w // 2, h // 2 + 10
        radius = min(w, h) // 2 - 50

        start_angle = 90 * 16  # начинаем сверху
        colors = list(CHART_COLORS)
        labels = list(self.data.items())

        for i, (label, value) in enumerate(labels):
            span_angle = int((value / total) * 360 * 16)
            color = colors[i % len(colors)]
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

        # Легенда справа
        legend_x = w - 120
        legend_y = 50
        painter.setFont(QFont("Geist", 9))

        for i, (label, value) in enumerate(labels):
            color = colors[i % len(colors)]
            pct = (value / total) * 100
            y = legend_y + i * 22

            # Цветной квадратик
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(legend_x, y, 10, 10)

            # Текст
            painter.setPen(QColor("#C8C8D0"))
            painter.drawText(legend_x + 16, y, 100, 12, Qt.AlignLeft,
                            f"{label} ({pct:.1f}%)")

        painter.end()


class BarChart(QWidget):
    """Гистограмма, рисованная через QPainter."""

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
        self.setMinimumSize(400, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        margin_bottom = 50
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
        for i, (label, value) in enumerate(self.data):
            x = margin_left + (chart_w / bar_count) * i + 4
            bar_h = int((value / max_val) * chart_h) if max_val > 0 else 0
            y = margin_top + chart_h - bar_h

            color = CHART_COLORS[i % len(CHART_COLORS)]
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), y, int(bar_w), bar_h, 3, 3)

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


class TimelineChart(QWidget):
    """Гистограмма по месяцам (timeline создания/изменения файлов)."""

    def __init__(self, dates: list, title: str = "", parent=None):
        """
        Args:
            dates: список datetime объектов
            title: заголовок
        """
        super().__init__(parent)
        self.chart_title = title

        # Группируем по месяцам
        month_counts = Counter()
        for dt in dates:
            key = dt.strftime("%Y-%m")
            month_counts[key] += 1

        # Сортируем по дате
        self.data = sorted(month_counts.items())
        self.setMinimumSize(400, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        margin_bottom = 40
        chart_w = w - margin_left - margin_right
        chart_h = h - margin_top - margin_bottom

        max_val = max(v for _, v in self.data)
        bar_count = len(self.data)
        bar_w = max(8, chart_w / bar_count - 4)

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

        # Столбцы
        for i, (label, value) in enumerate(self.data):
            x = margin_left + (chart_w / bar_count) * i + 2
            bar_h = int((value / max_val) * chart_h) if max_val > 0 else 0
            y = margin_top + chart_h - bar_h

            color = QColor("#5B8FEF")
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(x), y, int(bar_w), bar_h, 2, 2)

            # Подпись месяца
            painter.setPen(QColor("#8B8B95"))
            painter.setFont(QFont("Geist", 7))
            month_label = label[5:]  # только месяц
            painter.drawText(int(x) - 4, margin_top + chart_h + 5,
                           int(bar_w + 8), 30, Qt.AlignCenter, month_label)

        painter.end()


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

        # --- Ряд: круговая диаграмма + гистограмма ---
        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)

        # Круговая диаграмма по типам
        self.pie_chart = PieChart({}, tr("dashboard.pie_title", "Распределение по типам файлов"))
        charts_row.addWidget(self.pie_chart, 1)

        # Гистограмма топ-10 групп
        self.bar_chart = BarChart([], tr("dashboard.bar_title", "Топ-10 групп по размеру"))
        charts_row.addWidget(self.bar_chart, 2)

        self._scroll_layout.addLayout(charts_row)

        # --- Timeline ---
        self.timeline = TimelineChart([], tr("dashboard.timeline_title", "Файлы по месяцам (дата изменения)"))
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

        self.metric_groups.value_label.setText(str(total_groups))
        self.metric_files.value_label.setText(str(total_files))
        self.metric_size.value_label.setText(format_size(total_size))
        self.metric_saved.value_label.setText(format_size(saved_size))

        # --- Круговая диаграмма ---
        pie_data = {}
        labels = _get_category_labels()
        for cat, count in category_counts.most_common():
            label = labels.get(cat, cat)
            pie_data[label] = count
        self.pie_chart.data = pie_data
        self.pie_chart.update()

        # --- Гистограмма топ-10 ---
        self.bar_chart.data = group_sizes[:10]
        self.bar_chart.update()

        # --- Timeline ---
        self.timeline.data = sorted(
            Counter(dt.strftime("%Y-%m") for dt in all_dates).items()
        )
        self.timeline.update()
