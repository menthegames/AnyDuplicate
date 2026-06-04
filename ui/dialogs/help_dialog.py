"""
Диалог справки AnyDuplicate Advanced
Содержит описание функций, настроек, клавиатурных сокращений и практических советов.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextBrowser, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon
from pathlib import Path
from core.i18n import tr
from ui.helpers.icons import icon_img


class HelpDialog(QDialog):
    """Диалог справки приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("help.title", "Справка"))
        self.setMinimumSize(680, 520)
        self.resize(720, 560)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel(tr("help.title", "Справка"))
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setStyleSheet("color: #E8E8ED;")
        layout.addWidget(title)

        # Текст справки
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: #141416;
                color: #C8C8D0;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 16px;
                font-size: 13px;
                line-height: 1.6;
            }
            QTextBrowser h1, QTextBrowser h2, QTextBrowser h3 {
                color: #E8E8ED;
            }
            QTextBrowser h2 {
                font-size: 15px;
                margin-top: 16px;
                margin-bottom: 8px;
            }
            QTextBrowser h3 {
                font-size: 13px;
                margin-top: 12px;
                margin-bottom: 6px;
            }
            QTextBrowser ul {
                margin-left: 20px;
            }
            QTextBrowser li {
                margin-bottom: 4px;
            }
            QTextBrowser code {
                color: #5B8FEF;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }
            QTextBrowser b {
                color: #E8E8ED;
            }
        """)
        self._update_content()
        layout.addWidget(self.browser, 1)

        # Кнопка закрытия
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton(tr("help.close_btn", "Закрыть"))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B8FEF;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 28px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4A7DE0;
            }
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Стиль диалога
        self.setStyleSheet("""
            QDialog {
                background-color: #0F0F12;
            }
        """)

    def _update_content(self):
        """Обновляет содержимое справки в зависимости от текущего языка."""
        lang = self._get_lang()
        if lang == "en":
            content = self._get_english_content()
        else:
            content = self._get_russian_content()
        self.browser.setHtml(content)

    def _get_lang(self) -> str:
        """Возвращает текущий язык из конфига."""
        from core.config_manager import ConfigManager
        lang = ConfigManager().get("language", "ru")
        return lang if lang else "ru"

    def retranslate_ui(self):
        """Обновляет заголовок и содержимое при смене языка."""
        self.setWindowTitle(tr("help.title", "Справка"))
        self._update_content()

    def _get_russian_content(self) -> str:
        i = icon_img
        return f"""\
<h1>AnyDuplicate Advanced — Справка</h1>

<p><b>AnyDuplicate Advanced</b> — профессиональный инструмент для поиска и удаления дубликатов файлов. Поддерживает любые типы файлов: изображения, документы, видео, аудио, архивы и другие.</p>

<hr>

<h2>{i("clipboard")} Основные функции</h2>

<h3>{i("magnifying_glass", 20, 4)} Поиск дубликатов</h3>
<ul>
<li>Выберите папку для сканирования (кнопка <b>«Обзор»</b> или перетащите папку из проводника)</li>
<li>Настройте фильтр по типу файлов: изображения, документы, видео, аудио, архивы или свои расширения</li>
<li>Выберите алгоритм хэширования: <b>MD5</b> (быстрый) или <b>BLAKE3</b> (рекомендуется, надёжнее)</li>
<li>Укажите критерий выбора оригинала: по дате, размеру или пути</li>
<li>Нажмите <b>«Начать сканирование»</b> (F5)</li>
</ul>

<h3>{i("chart_bar", 20, 4)} Результаты</h3>
<ul>
<li>Просмотр найденных групп дубликатов с сортировкой и фильтрацией</li>
<li>Поиск по имени файла</li>
<li>Фильтр по типу и размеру файлов</li>
<li>Фильтр «Только hardlink'и» — показывает файлы, являющиеся жёсткими ссылками</li>
<li>Выбор файлов чекбоксами для массовых операций</li>
</ul>

<h3>{i("image", 20, 4)} Предпросмотр</h3>
<ul>
<li>Встроенный просмотр изображений, документов (PDF, DOCX, XLSX), видео и аудио</li>
<li>Навигация по группам дубликатов</li>
<li>Визуальное сравнение оригиналов и копий</li>
</ul>

<h3>{i("package", 20, 4)} Пакетная обработка</h3>
<ul>
<li>Выберите действие для каждой группы: <b>Оставить</b>, <b>Удалить</b>, <b>Переместить</b> или <b>Заменить hardlink'ом</b></li>
<li>Применение массовых операций ко всем файлам группы</li>
<li>Прогресс-бар и отчёт о результатах</li>
</ul>

<h3>{i("floppy_disk", 20, 4)} Сохранение и загрузка сессий</h3>
<ul>
<li>Сохраняйте результаты сканирования в JSON-файл для последующего анализа</li>
<li>Загружайте ранее сохранённые сессии</li>
<li>Экспорт в CSV для обработки в электронных таблицах</li>
</ul>

<h3>{i("chart_line", 20, 4)} Дашборд</h3>
<ul>
<li>Статистика по группам дубликатов, файлам и объёму</li>
<li>Круговая диаграмма распределения по типам файлов</li>
<li>Гистограмма топ-10 групп по размеру</li>
<li>Таймлайн файлов по месяцам</li>
</ul>

<h3>{i("scroll", 20, 4)} История</h3>
<ul>
<li>Автоматическое сохранение истории сканирований</li>
<li>Загрузка сессий из истории</li>
<li>Очистка истории</li>
</ul>

<hr>

<h2>{i("gear")} Настройки</h2>
<ul>
<li><b>Язык интерфейса:</b> Русский / English — переключение без перезапуска</li>
<li><b>Производительность:</b> количество потоков для сканирования (по умолчанию — оптимальное)</li>
</ul>

<hr>

<h2>{i("keyboard")} Клавиатурные сокращения</h2>
<ul>
<li><b>Ctrl+O</b> — Открыть папку для сканирования</li>
<li><b>Ctrl+F</b> — Фокус на фильтры</li>
<li><b>F5</b> — Начать сканирование</li>
<li><b>Delete</b> — Удалить выбранные файлы (на странице результатов)</li>
<li><b>Escape</b> — Назад на главную</li>
<li><b>Ctrl+Q</b> — Выход из приложения</li>
<li><b>Ctrl+,</b> — Открыть настройки</li>
</ul>

<hr>

<h2>{i("lightbulb")} Практические советы</h2>

<h3>{i("image", 20, 4)} Работа с изображениями</h3>
<ul>
<li>Используйте <b>BLAKE3</b> для точного сравнения — он устойчивее к коллизиям, чем MD5</li>
<li>Фильтр «Изображения» автоматически отбирает .jpg, .png, .gif, .bmp, .tiff, .webp, .heic, .svg</li>
<li>Предпросмотр позволяет визуально сравнить дубликаты перед удалением</li>
<li>Критерий «По дате (новее — оригинал)» удобен для фотографий: оставляет самую свежую версию</li>
</ul>

<h3>{i("file_text", 20, 4)} Работа с документами</h3>
<ul>
<li>Фильтр «Документы» охватывает .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt, .rtf, .odt, .ods, .odp, .csv</li>
<li>Для текстовых документов используйте критерий «По размеру (больше — оригинал)» — более полная версия обычно крупнее</li>
<li>Пакетная обработка с перемещением удобна для сортировки найденных копий в отдельную папку</li>
</ul>

<h3>{i("video_camera", 20, 4)} Работа с видео и аудио</h3>
<ul>
<li>Фильтр «Видео»: .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm, .m4v</li>
<li>Фильтр «Аудио»: .mp3, .wav, .flac, .aac, .ogg, .wma, .m4a, .opus</li>
<li>Для больших медиафайлов используйте <b>MD5</b> — он быстрее, а коллизии для уникальных файлов маловероятны</li>
<li>Hardlink-режим позволяет сэкономить место, не удаляя файлы — все копии указывают на одни и те же данные на диске</li>
</ul>

<h3>{i("package", 20, 4)} Работа с архивами и другими файлами</h3>
<ul>
<li>Фильтр «Архивы»: .zip, .rar, .7z, .tar, .gz, .bz2, .xz, .iso</li>
<li>Для произвольных типов используйте опцию «Свои» и введите расширения вручную через запятую (например: <code>.exe, .dll, .dat</code>)</li>
<li>Исключение системных папок ускоряет сканирование и предотвращает случайное удаление системных файлов</li>
</ul>

<h3>{i("wrench", 20, 4)} Общие рекомендации</h3>
<ul>
<li>Перед массовым удалением <b>сохраните сессию</b> — это позволит восстановить результаты без повторного сканирования</li>
<li>Используйте <b>пакетную обработку</b> для групп с одинаковым действием (например, удалить все копии в группе)</li>
<li>Режим <b>«Заменить hardlink'ом»</b> безопаснее удаления: файлы остаются на месте, но занимают место только одного оригинала</li>
<li>Для очень больших папок (сотни тысяч файлов) увеличьте количество потоков в настройках</li>
<li>Регулярно проверяйте <b>Дашборд</b> для анализа эффективности очистки диска</li>
</ul>

<hr>

<p style="color: #8B8B95; font-size: 11px;">AnyDuplicate Advanced v3.0.0</p>
"""

    def _get_english_content(self) -> str:
        i = icon_img
        return f"""\
<h1>AnyDuplicate Advanced — Help</h1>

<p><b>AnyDuplicate Advanced</b> is a professional tool for finding and removing duplicate files. It supports all file types: images, documents, video, audio, archives, and more.</p>

<hr>

<h2>{i("clipboard")} Main Features</h2>

<h3>{i("magnifying_glass", 20, 4)} Finding Duplicates</h3>
<ul>
<li>Select a folder to scan (click <b>«Browse»</b> or drag & drop a folder from Explorer)</li>
<li>Configure file type filter: images, documents, video, audio, archives, or custom extensions</li>
<li>Choose hashing algorithm: <b>MD5</b> (fast) or <b>BLAKE3</b> (recommended, more reliable)</li>
<li>Set original selection criteria: by date, size, or path</li>
<li>Click <b>«Start Scan»</b> (F5)</li>
</ul>

<h3>{i("chart_bar", 20, 4)} Results</h3>
<ul>
<li>View found duplicate groups with sorting and filtering</li>
<li>Search by file name</li>
<li>Filter by file type and size</li>
<li>«Hardlinks only» filter — shows files that are hard links</li>
<li>Select files with checkboxes for batch operations</li>
</ul>

<h3>{i("image", 20, 4)} Preview</h3>
<ul>
<li>Built-in preview for images, documents (PDF, DOCX, XLSX), video, and audio</li>
<li>Navigate through duplicate groups</li>
<li>Visual comparison of originals and copies</li>
</ul>

<h3>{i("package", 20, 4)} Batch Processing</h3>
<ul>
<li>Choose an action for each group: <b>Keep</b>, <b>Delete</b>, <b>Move</b>, or <b>Replace with hardlink</b></li>
<li>Apply bulk operations to all files in a group</li>
<li>Progress bar and result report</li>
</ul>

<h3>{i("floppy_disk", 20, 4)} Save & Load Sessions</h3>
<ul>
<li>Save scan results to a JSON file for later analysis</li>
<li>Load previously saved sessions</li>
<li>Export to CSV for spreadsheet processing</li>
</ul>

<h3>{i("chart_line", 20, 4)} Dashboard</h3>
<ul>
<li>Statistics on duplicate groups, files, and volume</li>
<li>Pie chart of distribution by file type</li>
<li>Bar chart of top 10 groups by size</li>
<li>File timeline by month</li>
</ul>

<h3>{i("scroll", 20, 4)} History</h3>
<ul>
<li>Automatic scan history saving</li>
<li>Load sessions from history</li>
<li>Clear history</li>
</ul>

<hr>

<h2>{i("gear")} Settings</h2>
<ul>
<li><b>Interface language:</b> Русский / English — switch without restart</li>
<li><b>Performance:</b> number of scan threads (default is optimal)</li>
</ul>

<hr>

<h2>{i("keyboard")} Keyboard Shortcuts</h2>
<ul>
<li><b>Ctrl+O</b> — Open folder to scan</li>
<li><b>Ctrl+F</b> — Focus on filters</li>
<li><b>F5</b> — Start scanning</li>
<li><b>Delete</b> — Delete selected files (on results page)</li>
<li><b>Escape</b> — Back to main page</li>
<li><b>Ctrl+Q</b> — Quit application</li>
<li><b>Ctrl+,</b> — Open settings</li>
</ul>

<hr>

<h2>{i("lightbulb")} Practical Tips</h2>

<h3>{i("image", 20, 4)} Working with Images</h3>
<ul>
<li>Use <b>BLAKE3</b> for accurate comparison — it's more collision-resistant than MD5</li>
<li>The «Images» filter automatically selects .jpg, .png, .gif, .bmp, .tiff, .webp, .heic, .svg</li>
<li>Preview lets you visually compare duplicates before deletion</li>
<li>The «By date (newer = original)» criterion is convenient for photos: it keeps the newest version</li>
</ul>

<h3>{i("file_text", 20, 4)} Working with Documents</h3>
<ul>
<li>The «Documents» filter covers .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt, .rtf, .odt, .ods, .odp, .csv</li>
<li>For text documents, use the «By size (larger = original)» criterion — the more complete version is usually larger</li>
<li>Batch processing with Move is convenient for sorting found copies into a separate folder</li>
</ul>

<h3>{i("video_camera", 20, 4)} Working with Video & Audio</h3>
<ul>
<li>«Video» filter: .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm, .m4v</li>
<li>«Audio» filter: .mp3, .wav, .flac, .aac, .ogg, .wma, .m4a, .opus</li>
<li>For large media files, use <b>MD5</b> — it's faster, and collisions for unique files are unlikely</li>
<li>Hardlink mode saves space without deleting files — all copies point to the same data on disk</li>
</ul>

<h3>{i("package", 20, 4)} Working with Archives & Other Files</h3>
<ul>
<li>«Archives» filter: .zip, .rar, .7z, .tar, .gz, .bz2, .xz, .iso</li>
<li>For custom types, use the «Custom» option and enter extensions manually separated by commas (e.g.: <code>.exe, .dll, .dat</code>)</li>
<li>Excluding system folders speeds up scanning and prevents accidental deletion of system files</li>
</ul>

<h3>{i("wrench", 20, 4)} General Recommendations</h3>
<ul>
<li>Before bulk deletion, <b>save your session</b> — this lets you restore results without re-scanning</li>
<li>Use <b>batch processing</b> for groups with the same action (e.g., delete all copies in a group)</li>
<li><b>«Replace with hardlink»</b> mode is safer than deletion: files remain in place but only take up space of one original</li>
<li>For very large folders (hundreds of thousands of files), increase the thread count in settings</li>
<li>Regularly check the <b>Dashboard</b> to analyze disk cleanup effectiveness</li>
</ul>

<hr>

<p style="color: #8B8B95; font-size: 11px;">AnyDuplicate Advanced v3.0.0</p>
"""
