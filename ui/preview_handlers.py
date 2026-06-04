"""
Обработчики предпросмотра для различных типов файлов.
Каждая функция возвращает либо QPixmap (для изображений/PDF),
либо строку (для текстовых/DOCX/PPTX), либо список списков (для XLSX).
"""
from pathlib import Path
from PySide6.QtGui import QPixmap, QImage, QColor
from PySide6.QtCore import QByteArray, QBuffer
from io import StringIO
import traceback
import subprocess
import sys
import os
import tempfile
import time


# ──────────────────────────────────────────────
# PDF (через pypdfium2) — в отдельном процессе через subprocess
# для защиты от segfault в C++ слое
# ──────────────────────────────────────────────
def render_pdf_preview(file_path: Path, max_size: tuple = (800, 800)) -> QPixmap | None:
    """Рендерит первую страницу PDF в QPixmap.
    Запускает рендеринг в отдельном процессе через subprocess,
    чтобы segfault в pypdfium2 не убил основное приложение."""
    try:
        worker_script = Path(__file__).resolve().parent.parent / "core" / "pdf_render_worker.py"
        if not worker_script.exists():
            print(f"[ERROR] PDF worker script not found: {worker_script}")
            return None

        # Запускаем worker как отдельный процесс
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, str(worker_script), str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,  # таймаут 30 секунд
        )
        elapsed = time.time() - start_time

        if result.returncode != 0:
            # Процесс упал (возможно segfault или ошибка)
            stderr = result.stderr.strip()
            if stderr:
                print(f"[PDF] Worker error for {file_path.name}: {stderr}")
            return None

        # stdout содержит путь к временному PNG файлу
        tmp_path = result.stdout.strip()
        if not tmp_path or not os.path.isfile(tmp_path):
            return None

        # Загружаем PNG
        pixmap = QPixmap(tmp_path)
        
        # Удаляем временный файл
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        if not pixmap.isNull():
            return pixmap
        
        return None
        
    except subprocess.TimeoutExpired:
        print(f"[PDF] Timeout rendering {file_path.name}")
        return None
    except Exception:
        traceback.print_exc()
        return None


# ──────────────────────────────────────────────
# Текстовые файлы (TXT, MD, PY, JS, HTML, CSS, JSON, XML, CSV, LOG, INI, CFG)
# ──────────────────────────────────────────────
def render_text_preview(file_path: Path, max_chars: int = 50000) -> str | None:
    """Читает текстовый файл и возвращает его содержимое (обрезанное)."""
    try:
        # Пробуем UTF-8, затем UTF-16, затем системную кодировку
        for enc in ("utf-8", "utf-16", "cp1251", "latin-1"):
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read(max_chars)
                if len(content) == max_chars:
                    content += "\n\n... (файл обрезан до {} символов)".format(max_chars)
                return content
            except (UnicodeDecodeError, UnicodeError):
                continue
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# DOCX (через python-docx)
# ──────────────────────────────────────────────
def render_docx_preview(file_path: Path, max_chars: int = 50000) -> str | None:
    """Извлекает текст из .docx файла."""
    try:
        from docx import Document
        doc = Document(str(file_path))
        paragraphs = []
        total = 0
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                total += len(text)
                if total > max_chars:
                    text = text[:max_chars - (total - len(text))]
                    paragraphs.append(text)
                    paragraphs.append("\n\n... (текст обрезан)")
                    break
                paragraphs.append(text)
        return "\n\n".join(paragraphs) if paragraphs else None
    except ImportError:
        # python-docx не установлен
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# XLSX (через openpyxl)
# ──────────────────────────────────────────────
def render_xlsx_preview(file_path: Path, max_rows: int = 100, max_cols: int = 20) -> list[list[str]] | None:
    """Извлекает данные из первого листа .xlsx файла."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            wb.close()
            return None
        rows = []
        for i, row in enumerate(ws.iter_rows(max_row=max_rows, max_col=max_cols, values_only=True)):
            rows.append([str(cell) if cell is not None else "" for cell in row])
        wb.close()
        return rows if rows else None
    except ImportError:
        # openpyxl не установлен
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# PPTX (через python-pptx)
# ──────────────────────────────────────────────
def render_pptx_preview(file_path: Path, max_chars: int = 50000) -> str | None:
    """Извлекает текст из .pptx файла."""
    try:
        from pptx import Presentation
        prs = Presentation(str(file_path))
        parts = []
        total = 0
        for slide_num, slide in enumerate(prs.slides, 1):
            slide_texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_texts.append(text)
            if slide_texts:
                slide_content = "--- Слайд {} ---\n{}".format(slide_num, "\n".join(slide_texts))
                total += len(slide_content)
                if total > max_chars:
                    parts.append(slide_content[:max_chars - (total - len(slide_content))])
                    parts.append("\n\n... (текст обрезан)")
                    break
                parts.append(slide_content)
        return "\n\n".join(parts) if parts else None
    except ImportError:
        # python-pptx не установлен
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# Аудио — получение метаданных через QtMultimedia
# ──────────────────────────────────────────────
def get_audio_info(file_path: Path) -> str | None:
    """Возвращает строку с информацией об аудиофайле (длительность, битрейт, частота).
    Использует QMediaPlayer для чтения метаданных."""
    try:
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
        from PySide6.QtCore import QUrl, QEventLoop, QTimer

        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)

        player.setSource(QUrl.fromLocalFile(str(file_path)))

        # Ждём, пока метаданные загрузятся
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)

        def on_media_status_changed(status):
            if status == QMediaPlayer.MediaStatus.LoadedMedia:
                loop.quit()

        player.mediaStatusChanged.connect(on_media_status_changed)
        timer.start(3000)  # таймаут 3 секунды
        loop.exec()

        timer.stop()
        player.mediaStatusChanged.disconnect(on_media_status_changed)

        # Собираем метаданные
        meta = player.metaData()
        parts = []

        # Длительность
        duration = player.duration()
        if duration > 0:
            secs = duration // 1000
            m, s = divmod(secs, 60)
            h, m = divmod(m, 60)
            if h > 0:
                parts.append(f"{h}:{m:02d}:{s:02d}")
            else:
                parts.append(f"{m}:{s:02d}")

        # Битрейт
        bitrate = meta.value(QMediaMetaData.AudioBitRate)
        if bitrate and bitrate > 0:
            parts.append(f"{bitrate // 1000} kbps")

        # Частота дискретизации
        sample_rate = meta.value(QMediaMetaData.SampleRate)
        if sample_rate and sample_rate > 0:
            parts.append(f"{sample_rate // 1000} kHz")

        # Кодек
        codec = meta.value(QMediaMetaData.AudioCodec)
        if codec:
            parts.append(str(codec))

        # Каналы
        channels = meta.value(QMediaMetaData.ChannelCount)
        if channels:
            parts.append(f"{channels} ch")

        player.stop()
        del player
        del audio_output

        if parts:
            return " | ".join(parts)
        return None

    except Exception:
        return None


# ──────────────────────────────────────────────
# Видео — получение метаданных через QtMultimedia
# ──────────────────────────────────────────────
def get_video_info(file_path: Path) -> str | None:
    """Возвращает строку с информацией о видеофайле (разрешение, длительность, FPS, кодек).
    Использует QMediaPlayer для чтения метаданных."""
    try:
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData
        from PySide6.QtCore import QUrl, QEventLoop, QTimer

        player = QMediaPlayer()
        audio_output = QAudioOutput()
        player.setAudioOutput(audio_output)

        player.setSource(QUrl.fromLocalFile(str(file_path)))

        # Ждём, пока метаданные загрузятся
        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)

        def on_media_status_changed(status):
            if status == QMediaPlayer.MediaStatus.LoadedMedia:
                loop.quit()

        player.mediaStatusChanged.connect(on_media_status_changed)
        timer.start(3000)  # таймаут 3 секунды
        loop.exec()

        timer.stop()
        player.mediaStatusChanged.disconnect(on_media_status_changed)

        # Собираем метаданные
        meta = player.metaData()
        parts = []

        # Длительность
        duration = player.duration()
        if duration > 0:
            secs = duration // 1000
            m, s = divmod(secs, 60)
            h, m = divmod(m, 60)
            if h > 0:
                parts.append(f"{h}:{m:02d}:{s:02d}")
            else:
                parts.append(f"{m}:{s:02d}")

        # Разрешение
        res = meta.value(QMediaMetaData.Resolution)
        if res and res.width() > 0 and res.height() > 0:
            parts.append(f"{res.width()}x{res.height()}")

        # Видео кодек
        vcodec = meta.value(QMediaMetaData.VideoCodec)
        if vcodec:
            parts.append(str(vcodec))

        # FPS
        fps = meta.value(QMediaMetaData.VideoFrameRate)
        if fps and fps > 0:
            parts.append(f"{fps:.1f} fps")

        # Битрейт видео
        bitrate = meta.value(QMediaMetaData.VideoBitRate)
        if bitrate and bitrate > 0:
            parts.append(f"{bitrate // 1000} kbps")

        # Аудио кодек
        acodec = meta.value(QMediaMetaData.AudioCodec)
        if acodec:
            parts.append(f"audio: {acodec}")

        player.stop()
        del player
        del audio_output

        if parts:
            return " | ".join(parts)
        return None

    except Exception:
        return None
