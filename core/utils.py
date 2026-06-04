"""
Утилиты AnyDuplicate Advanced
Общие вспомогательные функции: хэширование, фильтры, исключения, работа с файлами.
"""
import os, hashlib, threading, time
from pathlib import Path
from collections import defaultdict

# Системные файлы/папки для пропуска
EXCLUDE_NAMES = {"Thumbs.db", "desktop.ini", ".DS_Store", "thumbs.db", "Desktop.ini", ".ds_store"}
EXCLUDE_DIRS = {"$RECYCLE.BIN", "System Volume Information", "node_modules", ".git", ".svn", "WindowsApps"}

# Пресеты фильтров (русские)
FILTERS_RU = {
    "Изображения (JPG, PNG, HEIC)": [".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp"],
    "Фото + RAW": [".jpg", ".jpeg", ".png", ".heic", ".nef", ".cr2", ".arw", ".dng", ".raw", ".tiff"],
    "Документы": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".rtf"],
    "Видео": [".mp4", ".mov", ".avi", ".mkv", ".wmv"],
    "Аудио": [".mp3", ".flac", ".wav", ".m4a", ".aac"],
    "Все файлы": [],
    "Свои расширения...": "CUSTOM",
}

# Пресеты фильтров (английские)
FILTERS_EN = {
    "Images (JPG, PNG, HEIC)": [".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp"],
    "Photo + RAW": [".jpg", ".jpeg", ".png", ".heic", ".nef", ".cr2", ".arw", ".dng", ".raw", ".tiff"],
    "Documents": [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".rtf"],
    "Video": [".mp4", ".mov", ".avi", ".mkv", ".wmv"],
    "Audio": [".mp3", ".flac", ".wav", ".m4a", ".aac"],
    "All files": [],
    "Custom extensions...": "CUSTOM",
}

# Для обратной совместимости
FILTERS = FILTERS_RU

# Расширения изображений для предпросмотра
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".bmp", ".tiff", ".raw", ".nef", ".cr2", ".arw", ".dng"}

# Расширения для встроенного просмотра (Pro)
TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".csv", ".log", ".ini", ".cfg"}
AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".wma"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".rtf"}


def get_extensions(filter_name: str, custom_ext: str = "") -> list:
    """Возвращает список расширений для выбранного фильтра."""
    if filter_name in ("Свои расширения...", "Custom extensions..."):
        return [e.strip().lower() for e in custom_ext.split(",") if e.strip()]
    return FILTERS_RU.get(filter_name, FILTERS_EN.get(filter_name, []))


def is_image(path: Path) -> bool:
    """Проверяет, является ли файл изображением."""
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_pdf(path: Path) -> bool:
    """Проверяет, является ли файл PDF."""
    return path.suffix.lower() == ".pdf"


def is_text(path: Path) -> bool:
    """Проверяет, является ли файл текстовым (для встроенного просмотра)."""
    return path.suffix.lower() in TEXT_EXTENSIONS


def is_docx(path: Path) -> bool:
    """Проверяет, является ли файл DOCX."""
    return path.suffix.lower() == ".docx"


def is_xlsx(path: Path) -> bool:
    """Проверяет, является ли файл XLSX."""
    return path.suffix.lower() == ".xlsx"


def is_pptx(path: Path) -> bool:
    """Проверяет, является ли файл PPTX."""
    return path.suffix.lower() == ".pptx"


def is_audio(path: Path) -> bool:
    """Проверяет, является ли файл аудио."""
    return path.suffix.lower() in AUDIO_EXTENSIONS


def is_video(path: Path) -> bool:
    """Проверяет, является ли файл видео."""
    return path.suffix.lower() in VIDEO_EXTENSIONS


def calc_hash(filepath: Path, algorithm: str = "md5") -> str | None:
    """Вычисляет хэш файла указанным алгоритмом.
    
    Поддерживаемые алгоритмы: md5, sha256, sha512, blake3.
    BLAKE3 — современная замена SHA-512: быстрее в 10-15x при той же безопасности.
    """
    try:
        if algorithm == "md5":
            h = hashlib.md5()
        elif algorithm == "sha256":
            h = hashlib.sha256()
        elif algorithm == "sha512":
            h = hashlib.sha512()
        elif algorithm == "blake3":
            try:
                import blake3
                h = blake3.blake3()
            except ImportError:
                # Fallback на hashlib.blake2b если blake3 не установлен
                h = hashlib.blake2b()
        else:
            h = hashlib.md5()

        with open(filepath, "rb") as f:
            while chunk := f.read(65536):  # 64KB буфер
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None



def smart_sort(files: list, criteria: str) -> list:
    """Сортирует файлы по выбранному критерию для определения оригинала."""
    def safe_key(f):
        try:
            stat = f.stat()
            if "date" in criteria:  # По дате (новее)
                return (-stat.st_mtime, len(str(f)))
            elif "size" in criteria:  # По размеру (больше)
                return (-stat.st_size, -stat.st_mtime)
            else:  # По пути (короче)
                return (len(str(f)), -stat.st_mtime)
        except (OSError, PermissionError):
            return (0, len(str(f)))
    return sorted(files, key=safe_key)


def collect_files(source: Path, exclude_system: bool = True) -> list:
    """Собирает все файлы в директории рекурсивно, исключая системные."""
    files = []
    try:
        for p in source.rglob("*"):
            if not p.is_file():
                continue
            if p.name in EXCLUDE_NAMES:
                continue
            if exclude_system and any(x in p.parts for x in EXCLUDE_DIRS):
                continue
            files.append(p)
    except (PermissionError, OSError):
        pass
    return files


def format_size(size_bytes: int) -> str:
    """Форматирует размер в человекочитаемый вид."""
    for unit in ["Б", "КБ", "МБ", "ГБ", "ТБ"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} ПБ"


def format_date(date_str: str) -> str:
    """Форматирует дату в читаемый вид."""
    if not date_str:
        return "—"
    try:
        from datetime import datetime
        # Пробуем разные форматы
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y %H:%M:%S"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%d.%m.%Y %H:%M")
            except ValueError:
                continue
        return date_str[:16]
    except:
        return date_str[:16] if date_str else "—"


def get_file_type_category(filepath: str) -> str:
    """Определяет категорию файла по расширению."""
    if not filepath:
        return "other"
    ext = Path(filepath).suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    if ext in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"}:
        return "archive"
    return "other"


class ProgressTracker:
    """Потокобезопасный трекер прогресса с оценкой времени."""

    def __init__(self, total: int, callback=None):
        self.total = total
        self.current = 0
        self.callback = callback
        self.lock = threading.Lock()
        self.start_time = time.time()

    def update(self, n: int = 1):
        with self.lock:
            self.current += n
            pct = min(100, int((self.current / self.total) * 100)) if self.total > 0 else 0
            if self.callback:
                self.callback(pct)

    def get_eta(self) -> str:
        with self.lock:
            if self.current == 0:
                return "--:--"
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed if elapsed > 0 else 0
            remaining = (self.total - self.current) / rate if rate > 0 else 0
            m, s = divmod(int(remaining), 60)
            return f"{m:02d}:{s:02d}"
