"""
Окно предпросмотра дубликатов AnyDuplicate Advanced
Слева: оригинал (сверху) и дубликат (снизу).
Справа: список всех групп дубликатов для навигации.
Снизу: информация о текущей группе — список файлов с путями и датами.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QSplitter, QScrollArea,
    QFrame, QWidget, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QStackedWidget, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QApplication, QSlider
)
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QPixmap, QFont, QColor, QImage, QIcon, QPainter, QFontDatabase
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from pathlib import Path
from datetime import datetime
from core.utils import format_size, is_image, is_pdf, is_text, is_docx, is_xlsx, is_pptx, is_audio, is_video
from core.i18n import tr
from ui.preview_handlers import (
    render_pdf_preview, render_text_preview,
    render_docx_preview, render_xlsx_preview, render_pptx_preview,
    get_audio_info, get_video_info
)
import traceback


class PreviewPanel(QFrame):
    """Панель для отображения одного файла (оригинал или дубликат).
    Использует QStackedWidget для переключения между режимами:
    - ImageMode (QLabel с QPixmap) — для изображений и PDF
    - TextMode (QPlainTextEdit readonly) — для TXT, MD, PY, DOCX, PPTX
    - TableMode (QTableWidget) — для XLSX
    """

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            PreviewPanel {
                background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 12px;
            }
        """)
        self._setup_ui(title)

    def _setup_ui(self, title):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Заголовок
        self.title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #E8E8ED;")
        layout.addWidget(self.title_label)

        # QStackedWidget для переключения режимов
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background-color: transparent;")

        # --- Режим 0: Изображение (QLabel с QPixmap) ---
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setFrameShape(QFrame.NoFrame)
        self.image_scroll.setStyleSheet("background-color: transparent;")

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #0F0F12;
                border-radius: 8px;
                padding: 4px;
                color: #C8C8D0;
            }
        """)
        self.image_scroll.setWidget(self.image_label)
        self.stack.addWidget(self.image_scroll)  # index 0

        # --- Режим 1: Текст (QPlainTextEdit readonly) ---
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0F0F12;
                color: #C8C8D0;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        self.stack.addWidget(self.text_edit)  # index 1

        # --- Режим 2: Таблица (QTableWidget) ---
        self.table_widget = QTableWidget()
        self.table_widget.setStyleSheet("""
            QTableWidget {
                background-color: #0F0F12;
                color: #C8C8D0;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                gridline-color: #2A2A30;
                font-size: 9pt;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QHeaderView::section {
                background-color: #1E1E24;
                color: #E8E8ED;
                border: none;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)
        self.stack.addWidget(self.table_widget)  # index 2

        # --- Режим 3: Аудио (QWidget с плеером) ---
        self.audio_widget = QWidget()
        audio_layout = QVBoxLayout(self.audio_widget)
        audio_layout.setSpacing(8)
        audio_layout.setContentsMargins(16, 16, 16, 16)

        # Иконка и название
        self.audio_icon_label = QLabel("🎵")
        self.audio_icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont()
        icon_font.setPointSize(48)
        self.audio_icon_label.setFont(icon_font)
        audio_layout.addWidget(self.audio_icon_label)

        # Информация об аудиофайле
        self.audio_info_label = QLabel("")
        self.audio_info_label.setAlignment(Qt.AlignCenter)
        self.audio_info_label.setWordWrap(True)
        self.audio_info_label.setStyleSheet("color: #8B8B95; font-size: 10pt;")
        audio_layout.addWidget(self.audio_info_label)

        # Кнопки управления
        audio_controls = QHBoxLayout()
        audio_controls.addStretch()

        self.audio_play_btn = QPushButton("▶ Воспроизвести")
        self.audio_play_btn.setCheckable(True)
        self.audio_play_btn.clicked.connect(self._toggle_audio_playback)
        self.audio_play_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B8FEF;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #4A7DE0;
            }
            QPushButton:checked {
                background-color: #EF4444;
            }
        """)
        audio_controls.addWidget(self.audio_play_btn)
        audio_controls.addStretch()
        audio_layout.addLayout(audio_controls)

        # Ползунок прогресса
        self.audio_progress = QSlider(Qt.Horizontal)
        self.audio_progress.setRange(0, 100)
        self.audio_progress.setValue(0)
        self.audio_progress.sliderMoved.connect(self._seek_audio)
        self.audio_progress.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2A2A30;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #5B8FEF;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #5B8FEF;
                border-radius: 3px;
            }
        """)
        audio_layout.addWidget(self.audio_progress)

        # Время и громкость
        audio_bottom = QHBoxLayout()
        self.audio_time_label = QLabel("00:00 / 00:00")
        self.audio_time_label.setStyleSheet("color: #8B8B95; font-size: 9pt;")
        audio_bottom.addWidget(self.audio_time_label)

        audio_bottom.addStretch()

        vol_label = QLabel("🔊")
        vol_label.setStyleSheet("color: #8B8B95;")
        audio_bottom.addWidget(vol_label)

        self.audio_volume = QSlider(Qt.Horizontal)
        self.audio_volume.setRange(0, 100)
        self.audio_volume.setValue(70)
        self.audio_volume.setFixedWidth(100)
        self.audio_volume.valueChanged.connect(self._set_audio_volume)
        self.audio_volume.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2A2A30;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8B8B95;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #5B8FEF;
                border-radius: 2px;
            }
        """)
        audio_bottom.addWidget(self.audio_volume)
        audio_layout.addLayout(audio_bottom)

        self.stack.addWidget(self.audio_widget)  # index 3

        # --- Режим 4: Видео (QWidget с плеером) ---
        self.video_widget = QWidget()
        video_layout = QVBoxLayout(self.video_widget)
        video_layout.setSpacing(8)
        video_layout.setContentsMargins(8, 8, 8, 8)

        # QVideoWidget для отображения видео
        self.video_display = QVideoWidget()
        self.video_display.setStyleSheet("""
            QVideoWidget {
                background-color: #0F0F12;
                border-radius: 8px;
            }
        """)
        video_layout.addWidget(self.video_display, 1)

        # Информация о видеофайле
        self.video_info_label = QLabel("")
        self.video_info_label.setAlignment(Qt.AlignCenter)
        self.video_info_label.setWordWrap(True)
        self.video_info_label.setStyleSheet("color: #8B8B95; font-size: 9pt;")
        video_layout.addWidget(self.video_info_label)

        # Кнопки управления
        video_controls = QHBoxLayout()
        video_controls.addStretch()

        self.video_play_btn = QPushButton("▶ Воспроизвести")
        self.video_play_btn.setCheckable(True)
        self.video_play_btn.clicked.connect(self._toggle_video_playback)
        self.video_play_btn.setStyleSheet("""
            QPushButton {
                background-color: #5B8FEF;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #4A7DE0;
            }
            QPushButton:checked {
                background-color: #EF4444;
            }
        """)
        video_controls.addWidget(self.video_play_btn)
        video_controls.addStretch()
        video_layout.addLayout(video_controls)

        # Ползунок прогресса
        self.video_progress = QSlider(Qt.Horizontal)
        self.video_progress.setRange(0, 100)
        self.video_progress.setValue(0)
        self.video_progress.sliderMoved.connect(self._seek_video)
        self.video_progress.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2A2A30;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #5B8FEF;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #5B8FEF;
                border-radius: 3px;
            }
        """)
        video_layout.addWidget(self.video_progress)

        # Время и громкость
        video_bottom = QHBoxLayout()
        self.video_time_label = QLabel("00:00 / 00:00")
        self.video_time_label.setStyleSheet("color: #8B8B95; font-size: 9pt;")
        video_bottom.addWidget(self.video_time_label)

        video_bottom.addStretch()

        vol_label_v = QLabel("🔊")
        vol_label_v.setStyleSheet("color: #8B8B95;")
        video_bottom.addWidget(vol_label_v)

        self.video_volume = QSlider(Qt.Horizontal)
        self.video_volume.setRange(0, 100)
        self.video_volume.setValue(70)
        self.video_volume.setFixedWidth(100)
        self.video_volume.valueChanged.connect(self._set_video_volume)
        self.video_volume.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #2A2A30;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8B8B95;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #5B8FEF;
                border-radius: 2px;
            }
        """)
        video_bottom.addWidget(self.video_volume)
        video_layout.addLayout(video_bottom)

        self.stack.addWidget(self.video_widget)  # index 4

        layout.addWidget(self.stack, 1)

        # Информация о файле
        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setWordWrap(True)
        info_font = QFont()
        info_font.setPointSize(9)
        self.info_label.setFont(info_font)
        self.info_label.setStyleSheet("color: #8B8B95; padding: 4px;")
        layout.addWidget(self.info_label)

    def _get_safe_max_size(self) -> QSize:
        """Возвращает безопасный максимальный размер для отображения.
        Если viewport ещё не размещён (размер 0), использует запасной размер."""
        viewport_size = self.image_scroll.viewport().size()
        if viewport_size.width() <= 0 or viewport_size.height() <= 0:
            # Запасной размер, если виджет ещё не отрисован
            return QSize(400, 400)
        return viewport_size - QSize(20, 20)

    def display(self, file_path: Path, is_original: bool = False):
        """Отображает файл в панели с автоопределением типа."""
        try:
            self._display_impl(file_path, is_original)
        except Exception as e:
            traceback.print_exc()
            self.stack.setCurrentIndex(0)
            self.image_label.setText(
                tr("preview.display_error", "Ошибка отображения: {error}").format(error=str(e))
            )
            self.info_label.setText("")

    def _display_impl(self, file_path: Path, is_original: bool = False):
        """Внутренняя реализация отображения файла."""
        if not file_path or not file_path.exists():
            self.stack.setCurrentIndex(0)
            self.image_label.setText(tr("preview.file_not_found", "Файл не найден"))
            self.info_label.setText("")
            return

        badge = tr("preview.original_badge", "ОРИГИНАЛ") if is_original else tr("preview.copy_badge", "КОПИЯ")
        self.title_label.setText(f"{badge}")

        try:
            size_str = format_size(file_path.stat().st_size)
            self.info_label.setText(
                f"{file_path.name}\n{file_path.parent}\n{size_str}"
            )
        except Exception:
            self.info_label.setText(f"{file_path.name}\n{file_path.parent}")

        # --- Изображения ---
        if is_image(file_path):
            self.stack.setCurrentIndex(0)
            try:
                # Очищаем предыдущее изображение перед загрузкой нового
                self.image_label.clear()
                self.image_label.setText("")
                QApplication.processEvents()

                # Проверяем размер файла — не загружаем слишком большие изображения
                try:
                    file_size = file_path.stat().st_size
                    # Ограничение: не загружаем изображения > 100 МБ
                    MAX_IMAGE_SIZE = 100 * 1024 * 1024
                    if file_size > MAX_IMAGE_SIZE:
                        self.image_label.setText(
                            tr("preview.image_too_large", "Изображение слишком большое ({size})").format(
                                size=format_size(file_size)
                            )
                        )
                        return
                except Exception:
                    pass

                # Загружаем через QImage — безопаснее, чем QPixmap напрямую
                image = QImage(str(file_path))
                if image.isNull():
                    self.image_label.setText(tr("preview.load_failed", "(не удалось загрузить)"))
                    return
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    max_size = self._get_safe_max_size()
                    scaled = pixmap.scaled(
                        max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    self.image_label.setPixmap(scaled)
                    self.image_label.setFixedSize(scaled.size())
                else:
                    self.image_label.setText(tr("preview.load_failed", "(не удалось загрузить)"))
            except Exception as e:
                traceback.print_exc()
                self.image_label.setText(
                    tr("preview.image_error", "Ошибка загрузки изображения: {error}").format(error=str(e))
                )
            return

        # --- PDF ---
        if is_pdf(file_path):
            self.stack.setCurrentIndex(0)
            pixmap = render_pdf_preview(file_path)
            if pixmap and not pixmap.isNull():
                max_size = self._get_safe_max_size()
                scaled = pixmap.scaled(
                    max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)
                self.image_label.setFixedSize(scaled.size())
            else:
                self.image_label.setText(tr("preview.pdf_failed", "(не удалось отобразить PDF)"))
            return

        # --- XLSX (таблица) ---
        if is_xlsx(file_path):
            self.stack.setCurrentIndex(2)
            rows = render_xlsx_preview(file_path)
            if rows:
                self.table_widget.setRowCount(len(rows))
                self.table_widget.setColumnCount(len(rows[0]) if rows and rows[0] else 0)
                for r, row in enumerate(rows):
                    for c, val in enumerate(row):
                        item = QTableWidgetItem(str(val) if val is not None else "")
                        item.setForeground(QColor("#C8C8D0"))
                        self.table_widget.setItem(r, c, item)
                self.table_widget.resizeColumnsToContents()
            else:
                self.stack.setCurrentIndex(1)
                self.text_edit.setPlainText(tr("preview.xlsx_failed", "(не удалось прочитать XLSX)"))
            return

        # --- DOCX (текст) ---
        if is_docx(file_path):
            self.stack.setCurrentIndex(1)
            text = render_docx_preview(file_path)
            self.text_edit.setPlainText(text or tr("preview.docx_failed", "(не удалось прочитать DOCX)"))
            return

        # --- PPTX (текст) ---
        if is_pptx(file_path):
            self.stack.setCurrentIndex(1)
            text = render_pptx_preview(file_path)
            self.text_edit.setPlainText(text or tr("preview.pptx_failed", "(не удалось прочитать PPTX)"))
            return

        # --- Текстовые файлы ---
        if is_text(file_path):
            self.stack.setCurrentIndex(1)
            text = render_text_preview(file_path)
            self.text_edit.setPlainText(text or tr("preview.text_failed", "(не удалось прочитать файл)"))
            return

        # --- Аудио ---
        if is_audio(file_path):
            self.stack.setCurrentIndex(3)
            # Получаем метаданные
            info = get_audio_info(file_path)
            if info:
                self.audio_info_label.setText(info)
            else:
                self.audio_info_label.setText("")
            # Загружаем в плеер
            self._init_audio_player()
            self._audio_player.setSource(QUrl.fromLocalFile(str(file_path)))
            self.audio_play_btn.setText("▶ Воспроизвести")
            self.audio_play_btn.setChecked(False)
            self.audio_progress.setValue(0)
            self.audio_time_label.setText("00:00 / 00:00")
            return

        # --- Видео ---
        if is_video(file_path):
            self.stack.setCurrentIndex(4)
            # Получаем метаданные
            info = get_video_info(file_path)
            if info:
                self.video_info_label.setText(info)
            else:
                self.video_info_label.setText("")
            # Загружаем в плеер
            self._init_video_player()
            self._video_player.setSource(QUrl.fromLocalFile(str(file_path)))
            self.video_play_btn.setText("▶ Воспроизвести")
            self.video_play_btn.setChecked(False)
            self.video_progress.setValue(0)
            self.video_time_label.setText("00:00 / 00:00")
            return

        # --- Всё остальное ---
        self.stack.setCurrentIndex(0)
        self.image_label.setText(tr("preview.not_supported", "Предпросмотр недоступен для данного типа файлов"))

    # ──────────────────────────────────────────────
    # Аудио плеер
    # ──────────────────────────────────────────────
    def _init_audio_player(self):
        """Инициализирует QMediaPlayer для аудио."""
        if not hasattr(self, '_audio_player') or self._audio_player is None:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._audio_player = QMediaPlayer()
            self._audio_output = QAudioOutput()
            self._audio_player.setAudioOutput(self._audio_output)
            self._audio_player.positionChanged.connect(self._on_audio_position_changed)
            self._audio_player.durationChanged.connect(self._on_audio_duration_changed)
            self._audio_player.mediaStatusChanged.connect(self._on_audio_status_changed)

    def _toggle_audio_playback(self):
        """Включает/выключает воспроизведение аудио."""
        self._init_audio_player()
        if self._audio_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._audio_player.pause()
            self.audio_play_btn.setText("▶ Воспроизвести")
            self.audio_play_btn.setChecked(False)
        else:
            self._audio_player.play()
            self.audio_play_btn.setText("⏸ Пауза")
            self.audio_play_btn.setChecked(True)

    def _on_audio_position_changed(self, position):
        """Обновляет ползунок и метку времени при воспроизведении аудио."""
        duration = self._audio_player.duration()
        if duration > 0:
            progress = int((position / duration) * 100)
            self.audio_progress.blockSignals(True)
            self.audio_progress.setValue(progress)
            self.audio_progress.blockSignals(False)

            # Обновляем метку времени
            pos_secs = position // 1000
            dur_secs = duration // 1000
            pos_m, pos_s = divmod(pos_secs, 60)
            dur_m, dur_s = divmod(dur_secs, 60)
            self.audio_time_label.setText(f"{pos_m:02d}:{pos_s:02d} / {dur_m:02d}:{dur_s:02d}")

    def _on_audio_duration_changed(self, duration):
        """Обновляет метку времени при изменении длительности."""
        if duration > 0:
            dur_secs = duration // 1000
            dur_m, dur_s = divmod(dur_secs, 60)
            self.audio_time_label.setText(f"00:00 / {dur_m:02d}:{dur_s:02d}")

    def _on_audio_status_changed(self, status):
        """Обрабатывает изменение статуса медиа."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.audio_play_btn.setText("▶ Воспроизвести")
            self.audio_play_btn.setChecked(False)
            self.audio_progress.setValue(0)
            self._on_audio_duration_changed(self._audio_player.duration())

    def _seek_audio(self, position):
        """Перемотка аудио."""
        self._init_audio_player()
        duration = self._audio_player.duration()
        if duration > 0:
            seek_pos = int((position / 100) * duration)
            self._audio_player.setPosition(seek_pos)

    def _set_audio_volume(self, value):
        """Устанавливает громкость аудио."""
        self._init_audio_player()
        self._audio_output.setVolume(value / 100.0)

    # ──────────────────────────────────────────────
    # Видео плеер
    # ──────────────────────────────────────────────
    def _init_video_player(self):
        """Инициализирует QMediaPlayer для видео."""
        if not hasattr(self, '_video_player') or self._video_player is None:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            self._video_player = QMediaPlayer()
            self._video_audio_output = QAudioOutput()
            self._video_player.setAudioOutput(self._video_audio_output)
            self._video_player.setVideoOutput(self.video_display)
            self._video_player.positionChanged.connect(self._on_video_position_changed)
            self._video_player.durationChanged.connect(self._on_video_duration_changed)
            self._video_player.mediaStatusChanged.connect(self._on_video_status_changed)

    def _toggle_video_playback(self):
        """Включает/выключает воспроизведение видео."""
        self._init_video_player()
        if self._video_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._video_player.pause()
            self.video_play_btn.setText("▶ Воспроизвести")
            self.video_play_btn.setChecked(False)
        else:
            self._video_player.play()
            self.video_play_btn.setText("⏸ Пауза")
            self.video_play_btn.setChecked(True)

    def _on_video_position_changed(self, position):
        """Обновляет ползунок и метку времени при воспроизведении видео."""
        duration = self._video_player.duration()
        if duration > 0:
            progress = int((position / duration) * 100)
            self.video_progress.blockSignals(True)
            self.video_progress.setValue(progress)
            self.video_progress.blockSignals(False)

            pos_secs = position // 1000
            dur_secs = duration // 1000
            pos_m, pos_s = divmod(pos_secs, 60)
            dur_m, dur_s = divmod(dur_secs, 60)
            self.video_time_label.setText(f"{pos_m:02d}:{pos_s:02d} / {dur_m:02d}:{dur_s:02d}")

    def _on_video_duration_changed(self, duration):
        """Обновляет метку времени при изменении длительности видео."""
        if duration > 0:
            dur_secs = duration // 1000
            dur_m, dur_s = divmod(dur_secs, 60)
            self.video_time_label.setText(f"00:00 / {dur_m:02d}:{dur_s:02d}")

    def _on_video_status_changed(self, status):
        """Обрабатывает изменение статуса видео."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.video_play_btn.setText("▶ Воспроизвести")
            self.video_play_btn.setChecked(False)
            self.video_progress.setValue(0)
            self._on_video_duration_changed(self._video_player.duration())

    def _seek_video(self, position):
        """Перемотка видео."""
        self._init_video_player()
        duration = self._video_player.duration()
        if duration > 0:
            seek_pos = int((position / 100) * duration)
            self._video_player.setPosition(seek_pos)

    def _set_video_volume(self, value):
        """Устанавливает громкость видео."""
        self._init_video_player()
        self._video_audio_output.setVolume(value / 100.0)

    def clear(self):
        """Очищает панель."""
        # Останавливаем плееры
        if hasattr(self, '_audio_player') and self._audio_player is not None:
            self._audio_player.stop()
            self._audio_player.setSource(QUrl())
            self.audio_play_btn.setText("▶ Воспроизвести")
            self.audio_play_btn.setChecked(False)
            self.audio_progress.setValue(0)
            self.audio_time_label.setText("00:00 / 00:00")
            self.audio_info_label.setText("")

        if hasattr(self, '_video_player') and self._video_player is not None:
            self._video_player.stop()
            self._video_player.setSource(QUrl())
            self.video_play_btn.setText("▶ Воспроизвести")
            self.video_play_btn.setChecked(False)
            self.video_progress.setValue(0)
            self.video_time_label.setText("00:00 / 00:00")
            self.video_info_label.setText("")

        self.stack.setCurrentIndex(0)
        self.image_label.clear()
        self.image_label.setText("")
        self.text_edit.clear()
        self.table_widget.clear()
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        self.info_label.setText("")
        self.title_label.setText("")


class PreviewWindow(QDialog):
    """Окно предпросмотра дубликатов."""

    def __init__(self, preview_data: list, parent=None):
        super().__init__(parent)
        self.preview_data = preview_data  # [(hash, original, [dups])]
        self.current_group = 0
        self.current_dup_index = 0
        self._initial_show_done = False

        self.setWindowTitle(tr("preview.window_title", "Предпросмотр дубликатов"))
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)
        self.setModal(True)

        # Стиль окна
        self.setStyleSheet("""
            QDialog {
                background-color: #0A0A0C;
            }
        """)

        self._setup_ui()
        self.retranslate_ui()
        # Заполняем список групп сразу
        self._populate_groups_list()
        # Не вызываем _show_group здесь — отложим до showEvent,
        # чтобы layout был уже рассчитан и viewport имел корректный размер

    def showEvent(self, event):
        """Вызывается при показе окна. Отображаем первую группу после того,
        как layout рассчитан и viewport имеет корректный размер."""
        super().showEvent(event)
        if not self._initial_show_done and self.preview_data:
            self._initial_show_done = True
            # Используем QTimer.singleShot, чтобы дать окну полностью отрисоваться
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self._show_group(0))

    def retranslate_ui(self):
        """Обновляет текст интерфейса при смене языка."""
        self.setWindowTitle(tr("preview.window_title", "Предпросмотр дубликатов"))
        self.prev_group_btn.setText(tr("preview.prev_group", "◀ Предыдущая"))
        self.next_group_btn.setText(tr("preview.next_group", "Следующая ▶"))
        self.groups_header.setText(tr("preview.all_groups", "Все группы дубликатов"))
        self.info_title.setText(tr("preview.files_in_group", "Файлы в текущей группе:"))
        self.close_btn.setText(tr("preview.close", "✕ Закрыть"))
        self.files_tree.setHeaderLabels([
            "",
            tr("preview.file", "Файл"),
            tr("preview.size", "Размер"),
            tr("preview.date_modified", "Дата изменения"),
            tr("preview.path", "Путь")
        ])

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # === Верхняя панель: навигация по группам ===
        nav_layout = QHBoxLayout()

        self.prev_group_btn = QPushButton("◀ Предыдущая")
        self.prev_group_btn.clicked.connect(self._prev_group)
        self.prev_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E24;
                color: #C8C8D0;
                border: 1px solid #2A2A30;
                padding: 6px 16px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2A2A30;
                border-color: #5B8FEF;
            }
            QPushButton:pressed {
                background-color: #141416;
            }
            QPushButton:disabled {
                background-color: #0F0F12;
                color: #55555A;
                border-color: #1E1E24;
            }
        """)

        self.group_counter_label = QLabel("Группа 0 из 0")
        self.group_counter_label.setAlignment(Qt.AlignCenter)
        counter_font = QFont()
        counter_font.setPointSize(12)
        counter_font.setBold(True)
        self.group_counter_label.setFont(counter_font)

        self.next_group_btn = QPushButton("Следующая ▶")
        self.next_group_btn.clicked.connect(self._next_group)
        self.next_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E24;
                color: #C8C8D0;
                border: 1px solid #2A2A30;
                padding: 6px 16px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2A2A30;
                border-color: #5B8FEF;
            }
            QPushButton:pressed {
                background-color: #141416;
            }
            QPushButton:disabled {
                background-color: #0F0F12;
                color: #55555A;
                border-color: #1E1E24;
            }
        """)

        nav_layout.addWidget(self.prev_group_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.group_counter_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_group_btn)
        layout.addLayout(nav_layout)

        # === Основной контент: сплиттер (панели | список групп) ===
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2A2A30;
                width: 2px;
            }
        """)

        # --- Левая часть: две панели предпросмотра ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(6)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Внутренний сплиттер для оригинала и дубликата (горизонтально)
        self.preview_splitter = QSplitter(Qt.Horizontal)
        self.preview_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2A2A30;
                height: 2px;
            }
        """)

        # Верхняя панель — оригинал
        self.original_panel = PreviewPanel(tr("preview.original", "Оригинал"))
        self.preview_splitter.addWidget(self.original_panel)

        # Нижняя панель — дубликат
        self.dup_panel = PreviewPanel(tr("preview.duplicate", "Дубликат"))
        self.preview_splitter.addWidget(self.dup_panel)

        self.preview_splitter.setSizes([400, 400])
        left_layout.addWidget(self.preview_splitter, 1)

        main_splitter.addWidget(left_widget)

        # --- Правая часть: список всех групп ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(6)
        right_layout.setContentsMargins(8, 0, 0, 0)

        self.groups_header = QLabel("Все группы дубликатов")
        self.groups_header.setStyleSheet("font-weight: bold; font-size: 11pt; color: #E8E8ED;")
        right_layout.addWidget(self.groups_header)

        self.groups_list = QListWidget()
        self.groups_list.setStyleSheet("""
            QListWidget {
                background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 8px;
                padding: 4px;
                color: #C8C8D0;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 4px;
                border-bottom: 1px solid #2A2A30;
            }
            QListWidget::item:selected {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:1 #6366F1);
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #1E1E24;
            }
        """)
        self.groups_list.currentRowChanged.connect(self._on_group_selected)
        right_layout.addWidget(self.groups_list, 1)

        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([900, 300])

        layout.addWidget(main_splitter, 1)

        # === Нижняя панель: информация о текущей группе ===
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(12, 8, 12, 8)

        info_header_layout = QHBoxLayout()
        self.info_title = QLabel("Файлы в текущей группе:")
        self.info_title.setStyleSheet("font-weight: bold; font-size: 10pt; color: #E8E8ED;")
        info_header_layout.addWidget(self.info_title)
        info_header_layout.addStretch()

        self.info_count = QLabel("")
        self.info_count.setStyleSheet("font-size: 9pt; color: #8B8B95;")
        info_header_layout.addWidget(self.info_count)
        info_layout.addLayout(info_header_layout)

        # Таблица файлов текущей группы
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["", "Файл", "Размер", "Дата изменения", "Путь"])
        self.files_tree.setAlternatingRowColors(True)
        self.files_tree.setRootIsDecorated(False)
        self.files_tree.setAnimated(True)
        self.files_tree.setMaximumHeight(160)
        self.files_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0F0F12;
                alternate-background-color: #141416;
                border: 1px solid #2A2A30;
                border-radius: 6px;
                padding: 2px;
                color: #C8C8D0;
            }
            QTreeWidget::item {
                padding: 3px 6px;
            }
            QTreeWidget::item:selected {
                background-color: #5B8FEF;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #141416;
                color: #8B8B95;
                border: none;
                padding: 4px;
                font-weight: bold;
            }
        """)
        self.files_tree.itemClicked.connect(self._on_file_in_group_clicked)
        # Растягиваем колонки
        header = self.files_tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        info_layout.addWidget(self.files_tree)

        layout.addWidget(info_frame)

        # === Кнопка закрытия ===
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        self.close_btn = QPushButton("✕ Закрыть")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E1E24;
                color: #C8C8D0;
                border: 1px solid #2A2A30;
                padding: 8px 24px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2A2A30;
                border-color: #5B8FEF;
            }
            QPushButton:pressed {
                background-color: #141416;
            }
        """)
        close_layout.addWidget(self.close_btn)
        layout.addLayout(close_layout)

    def _populate_groups_list(self):
        """Заполняет список групп в правой панели."""
        self.groups_list.blockSignals(True)
        self.groups_list.clear()
        if self.preview_data:
            for idx, (hash_val, original, dups) in enumerate(self.preview_data):
                all_files = [original] + dups
                item_text = tr("preview.group_item", "Группа {idx}: {name} ({count} файлов)").format(
                    idx=idx + 1,
                    name=original.name,
                    count=len(all_files)
                )
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, idx)
                self.groups_list.addItem(item)
        self.groups_list.blockSignals(False)

    def _show_group(self, index: int):
        """Отображает группу дубликатов по индексу."""
        if not self.preview_data or index < 0 or index >= len(self.preview_data):
            return

        self.current_group = index
        hash_val, original, dups = self.preview_data[index]

        # Обновляем счётчик
        total = len(self.preview_data)
        self.group_counter_label.setText(
            tr("preview.group_counter", "Группа {current} из {total}").format(current=index + 1, total=total)
        )

        # Обновляем кнопки навигации
        self.prev_group_btn.setEnabled(index > 0)
        self.next_group_btn.setEnabled(index < total - 1)

        # Выделяем в списке групп
        if index < self.groups_list.count():
            self.groups_list.blockSignals(True)
            self.groups_list.setCurrentRow(index)
            self.groups_list.blockSignals(False)

        # Очищаем панели перед загрузкой нового содержимого
        self.original_panel.clear()
        self.dup_panel.clear()
        QApplication.processEvents()

        # Отображаем оригинал
        self.original_panel.display(original, is_original=True)

        # Отображаем первый дубликат
        self.current_dup_index = 0
        if dups:
            self.dup_panel.display(dups[0])
        else:
            self.dup_panel.info_label.setText(tr("preview.no_duplicates", "Нет дубликатов для отображения"))

        # Обновляем таблицу файлов группы
        self._update_files_table(original, dups)

    def _update_files_table(self, original: Path, dups: list):
        """Заполняет таблицу файлов текущей группы."""
        self.files_tree.clear()

        all_files = [original] + dups
        self.info_count.setText(
            tr("preview.total_files", "Всего файлов: {count}").format(count=len(all_files))
        )

        for i, f in enumerate(all_files):
            item = QTreeWidgetItem()
            if i == 0:
                item.setText(0, "★")
                item.setToolTip(0, tr("preview.original_tooltip", "Оригинал"))
            else:
                item.setText(0, "○")
                item.setToolTip(0, tr("preview.copy_tooltip", "Копия #{n}").format(n=i))

            item.setText(1, f.name)
            try:
                stat = f.stat()
                item.setText(2, format_size(stat.st_size))
                dt = datetime.fromtimestamp(stat.st_mtime)
                item.setText(3, dt.strftime("%d.%m.%Y %H:%M"))
            except Exception:
                item.setText(2, "—")
                item.setText(3, "—")
            item.setText(4, str(f.parent))

            # Храним путь для клика
            item.setData(0, Qt.UserRole, str(f))
            item.setData(0, Qt.UserRole + 1, i == 0)  # is_original

            self.files_tree.addTopLevelItem(item)

        # Автоширина
        for col in range(5):
            self.files_tree.resizeColumnToContents(col)

    def _on_file_in_group_clicked(self, item, column):
        """Обрабатывает клик по файлу в таблице группы."""
        path_str = item.data(0, Qt.UserRole)
        is_original = item.data(0, Qt.UserRole + 1)
        if path_str:
            path = Path(path_str)
            if is_original:
                self.original_panel.display(path, is_original=True)
            else:
                self.dup_panel.display(path)

    def _on_group_selected(self, row: int):
        """Обрабатывает выбор группы из списка справа."""
        if row >= 0 and row != self.current_group:
            self._show_group(row)

    def _prev_group(self):
        """Переходит к предыдущей группе."""
        if self.current_group > 0:
            self._show_group(self.current_group - 1)

    def _next_group(self):
        """Переходит к следующей группе."""
        if self.current_group < len(self.preview_data) - 1:
            self._show_group(self.current_group + 1)
