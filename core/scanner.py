"""
Движок сканирования AnyDuplicate Advanced
Поиск дубликатов: группировка по размеру → хэширование → умный выбор оригинала.
"""
import threading
from pathlib import Path
from collections import defaultdict
from core.i18n import tr
from core.utils import calc_hash, smart_sort, collect_files, get_extensions, ProgressTracker


class Scanner:
    """Движок поиска дубликатов. Работает в отдельном потоке."""

    def __init__(self, config, log_callback=None, progress_callback=None):
        self.config = config
        self.log = log_callback or (lambda msg: None)
        self.progress = progress_callback or (lambda pct: None)
        self.is_running = False
        self.duplicates = {}  # hash -> [files]
        self.preview_data = []  # [(hash, original, [dups])]

    def scan(self, source_path: str, extensions: list = None, hash_algorithm: str = "md5",
             criteria: str = "date", exclude_system: bool = True, threads: int = 4,
             on_complete=None):
        """Запускает сканирование в отдельном потоке."""
        if self.is_running:
            return
        self.is_running = True
        self._on_complete = on_complete
        threading.Thread(
            target=self._scan_thread,
            args=(source_path, extensions, hash_algorithm, criteria, exclude_system, threads),
            daemon=True
        ).start()

    def stop(self):
        self.is_running = False

    def _scan_thread(self, source_path: str, extensions: list = None, hash_algorithm: str = "md5",
                     criteria: str = "date", exclude_system: bool = True, threads: int = 4):
        src = Path(source_path)
        if not src.is_dir():
            self.log(tr("scanner.folder_not_found", "Ошибка: Папка не найдена."))
            self._call_complete()
            return

        self.is_running = True
        self.duplicates.clear()
        self.preview_data = []
        self.progress(0)

        # Шаг 1: Сбор файлов
        self.log(tr("scanner.collecting", "Сбор файлов..."))
        all_files = collect_files(src, exclude_system)
        total = len(all_files)
        self.log(tr("scanner.files_found", "Найдено файлов: {count}").format(count=total))

        if total == 0:
            self.is_running = False
            self.log(tr("scanner.no_files", "Нет файлов для сканирования."))
            self._call_complete()
            return

        # Шаг 2: Группировка по размеру
        self.log(tr("scanner.step1", "Шаг 1: Группировка по размеру..."))
        size_groups = defaultdict(list)
        tracker = ProgressTracker(total, self.progress)

        for i, p in enumerate(all_files):
            if not self.is_running:
                self._call_complete()
                return
            try:
                size_groups[p.stat().st_size].append(p)
            except Exception:
                pass
            if i % 500 == 0:
                tracker.update(500)

        # Оставляем только группы с >1 файлом
        potential = {s: f for s, f in size_groups.items() if len(f) > 1}
        self.log(tr("scanner.potential", "Потенциальных дубликатов: {count}").format(count=sum(len(v) for v in potential.values())))

        if not potential:
            self.is_running = False
            self.log(tr("scanner.no_dups_size", "Дубликаты не найдены (все файлы уникальны по размеру)."))
            self._call_complete()
            return

        # Применяем фильтр расширений
        pot_files = []
        if extensions:
            for fs in potential.values():
                pot_files.extend([f for f in fs if f.suffix.lower() in extensions])
            self.log(tr("scanner.filter_applied", "Фильтр применён. Осталось: {count}").format(count=len(pot_files)))
        else:
            pot_files = [f for g in potential.values() for f in g]

        if not pot_files:
            self.is_running = False
            self.log(tr("scanner.filter_empty", "После фильтрации не осталось файлов."))
            self._call_complete()
            return

        # Шаг 3: Хэширование
        self.log(tr("scanner.step2", "Шаг 2: Хэширование ({algo})...").format(algo=hash_algorithm.upper()))
        hash_tracker = ProgressTracker(len(pot_files), lambda p: self.progress(30 + int(p * 0.6)))

        for i, f in enumerate(pot_files, 1):
            if not self.is_running:
                self._call_complete()
                return
            h = calc_hash(f, hash_algorithm)
            if h:
                self.duplicates.setdefault(h, []).append(f)
            if i % 100 == 0:
                hash_tracker.update(100)

        # Формируем результат
        real_dups = {k: v for k, v in self.duplicates.items() if len(v) > 1}
        for h, files in real_dups.items():
            sorted_files = smart_sort(files, criteria)
            self.preview_data.append((h, sorted_files[0], sorted_files[1:]))

        self.duplicates = real_dups
        self.is_running = False
        self.progress(100)

        total_dups = sum(len(v) - 1 for v in self.duplicates.values())
        self.log(tr("scanner.done", "Готово. Групп дубликатов: {groups} | Копий: {copies}").format(groups=len(self.duplicates), copies=total_dups))
        if total_dups == 0:
            self.log(tr("scanner.no_dups_final", "Дубликаты не найдены."))
        self._call_complete()

    def _call_complete(self):
        """Вызывает callback завершения, если он задан."""
        if hasattr(self, '_on_complete') and self._on_complete:
            self._on_complete()

    def save_session(self, path: str):
        """Сохраняет результаты сканирования в JSON-файл."""
        import json
        data = []
        for h, original, dups in self.preview_data:
            group = {
                "hash": h,
                "original": str(original),
                "duplicates": [str(d) for d in dups]
            }
            data.append(group)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_session(self, path: str):
        """Загружает результаты сканирования из JSON-файла."""
        import json
        from pathlib import Path
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.duplicates = {}
        self.preview_data = []
        for group in data:
            h = group["hash"]
            original = Path(group["original"])
            dups = [Path(d) for d in group["duplicates"]]
            self.duplicates[h] = [original] + dups
            self.preview_data.append((h, original, dups))
        return len(self.preview_data)

    def calculate_stats(self):
        """Возвращает статистику: количество файлов и общий размер."""
        total_files = 0
        total_size = 0
        for _, _, dups in self.preview_data:
            total_files += len(dups)
            for d in dups:
                try:
                    total_size += d.stat().st_size
                except Exception:
                    pass
        return total_files, total_size
