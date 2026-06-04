"""
Менеджер конфигурации AnyDuplicate Advanced
Сохраняет настройки пользователя в %APPDATA%/AnyDuplicate Advanced/config.json
"""
import os, json
from pathlib import Path

APP_NAME = "AnyDuplicate Advanced"
APP_DATA_DIR = Path(os.getenv("APPDATA")) / APP_NAME

class ConfigManager:
    _instance = None
    _initialized = False

    FILE = APP_DATA_DIR / "config.json"
    DEFAULTS = {
        "source_path": "",
        "dest_path": "",
        "last_filter": "Изображения (JPG, PNG, HEIC)",
        "is_pro": False,
        "criteria": "date",
        "action_type": "move",
        "hash_algorithm": "md5",
        "threads": 4,
        "use_hardlink": False,
        "language": "ru",
        "exclude_system": True,
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
            self.data = self.DEFAULTS.copy()
            self._load()

    def _load(self):
        if self.FILE.exists():
            try:
                with open(self.FILE, "r", encoding="utf-8") as f:
                    self.data.update(json.load(f))
            except Exception:
                pass

    def save(self):
        with open(self.FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get(self, k, default=None):
        return self.data.get(k, default)

    def set(self, k, v):
        self.data[k] = v
        self.save()
