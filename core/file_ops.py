"""
Операции с файлами AnyDuplicate Advanced
Перемещение, удаление в корзину, hardlink, верификация.
"""
import os, shutil, ctypes, threading
from pathlib import Path
from core.utils import calc_hash, smart_sort


def is_hardlink(path: str) -> bool:
    """Проверяет, является ли файл hardlink'ом (st_nlink > 1)."""
    try:
        return os.stat(path).st_nlink > 1
    except (OSError, FileNotFoundError):
        return False


class FileOperations:
    """Выполняет операции с дубликатами: перемещение, удаление, hardlink."""

    def __init__(self, config, duplicates, log_callback=None, progress_callback=None):
        self.config = config
        self.duplicates = duplicates
        self.log = log_callback or (lambda msg: None)
        self.progress = progress_callback or (lambda pct: None)
        self.is_running = False

    def execute(self, dest_path: str, action_type: str):
        """Запускает обработку дубликатов в отдельном потоке."""
        if self.is_running:
            return
        threading.Thread(target=self._move_thread, args=(dest_path, action_type), daemon=True).start()

    def stop(self):
        self.is_running = False

    def _move_to_recycle(self, path: Path) -> bool:
        """Удаляет файл в корзину Windows."""
        try:
            FO_DELETE = 0x3
            FOF_ALLOWUNDO = 0x40
            FOF_NOCONFIRMATION = 0x10
            pFrom = ctypes.c_wchar_p(str(path) + "\0")
            ctypes.windll.shell32.SHFileOperationW(
                ctypes.byref(ctypes.c_uint(FO_DELETE)),
                pFrom,
                ctypes.c_uint(FOF_ALLOWUNDO | FOF_NOCONFIRMATION),
            )
            return True
        except Exception:
            return False

    def _create_hardlink(self, original: Path, duplicate: Path) -> bool:
        """Создаёт hardlink вместо копии (экономия места)."""
        try:
            os.remove(str(duplicate))  # Удаляем дубликат
            os.link(str(original), str(duplicate))  # Создаём hardlink
            return True
        except Exception:
            return False

    def _move_thread(self, dest_path: str, action_type: str):
        self.is_running = True
        self.progress(0)
        moved = 0
        errors = 0

        is_move = "move" in action_type
        is_hardlink = self.config.get("use_hardlink", False) and not is_move

        dest_dir = Path(dest_path)
        if is_move:
            dest_folder = dest_dir / "found_duplicates"
            dest_folder.mkdir(parents=True, exist_ok=True)
        else:
            dest_folder = None

        # Подготавливаем список для обработки
        criteria = self.config.get("criteria", "date")
        to_process = []
        for h, files in self.duplicates.items():
            sorted_files = smart_sort(files, criteria)
            to_process.append((h, sorted_files[0], sorted_files[1:]))

        total = sum(len(d) for _, _, d in to_process)
        if total == 0:
            self.is_running = False
            self.log("Нет дубликатов для обработки.")
            return

        current = 0
        for h, original, dups in to_process:
            if not self.is_running:
                break

            self.log(f"Оригинал: {original.name}")

            for idx, dup_file in enumerate(dups):
                if not self.is_running:
                    break

                try:
                    if is_hardlink:
                        # Режим hardlink: файл остаётся на месте, но занимает 0 места
                        if self._create_hardlink(original, dup_file):
                            moved += 1
                            self.log(f"Hardlink: {dup_file.name} → {original.name}")
                        else:
                            errors += 1
                            self.log(f"Ошибка hardlink: {dup_file.name}")

                    elif is_move:
                        # Перемещение в папку
                        new_name = f"{dup_file.stem}_{h[:6]}_dup{idx + 1}{dup_file.suffix}"
                        new_path = dest_folder / new_name
                        counter = 1
                        while new_path.exists():
                            new_path = dest_folder / f"{dup_file.stem}_{h[:6]}_dup{idx + 1}_{counter}{dup_file.suffix}"
                            counter += 1

                        shutil.move(str(dup_file), str(new_path))

                        # Верификация
                        if calc_hash(new_path, self.config.get("hash_algorithm", "md5")) != h:
                            self.log(f"Ошибка верификации: {new_path.name}")
                            errors += 1
                        else:
                            moved += 1
                            self.log(f"{dup_file.name} → {new_path.name}")

                    else:
                        # Удаление в корзину
                        if self._move_to_recycle(dup_file):
                            moved += 1
                            self.log(f"{dup_file.name} → Корзина")
                        else:
                            errors += 1
                            self.log(f"Ошибка удаления: {dup_file.name}")

                    current += 1
                    self.progress(int((current / total) * 100))

                except Exception as e:
                    errors += 1
                    self.log(f"Ошибка: {dup_file.name} ({e})")
                    current += 1
                    self.progress(int((current / total) * 100))

        self.is_running = False
        self.progress(100)
        self.log(f"Готово. Обработано: {moved} | Ошибок: {errors}")
        return moved, errors
