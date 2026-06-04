"""
Проверка обновлений AnyDuplicate Advanced
HTTP-запрос к GitHub API для получения последней версии.
"""
import json
import ssl
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional
from core import __version__


GITHUB_API_URL = "https://api.github.com/repos/anyduplicate/anyduplicate-advanced/releases/latest"
"""URL для получения последнего релиза с GitHub."""


@dataclass
class UpdateInfo:
    """Информация о доступном обновлении."""
    latest_version: str
    current_version: str
    download_url: str
    release_notes: str
    is_available: bool


class UpdateChecker:
    """
    Проверяет наличие обновлений через GitHub API.
    Для Pro-пользователей проверка выполняется при запуске.
    """

    def __init__(self, timeout: int = 5):
        """
        Args:
            timeout: таймаут HTTP-запроса в секундах
        """
        self.timeout = timeout

    def check(self) -> Optional[UpdateInfo]:
        """
        Проверяет последнюю версию на GitHub.

        Returns:
            UpdateInfo если обновление доступно, None при ошибке или если версия актуальна.
        """
        try:
            # Создаём контекст SSL без проверки сертификата (для Windows)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    "User-Agent": "AnyDuplicate-Advanced/3.0",
                    "Accept": "application/vnd.github.v3+json",
                }
            )

            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                data = json.loads(response.read().decode("utf-8"))

            latest_version = data.get("tag_name", "").lstrip("v")
            download_url = data.get("html_url", "")
            release_notes = data.get("body", "")

            if not latest_version:
                return None

            # Сравниваем версии
            is_available = self._compare_versions(latest_version, __version__) > 0

            return UpdateInfo(
                latest_version=latest_version,
                current_version=__version__,
                download_url=download_url,
                release_notes=release_notes[:500] if release_notes else "",
                is_available=is_available,
            )

        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, ssl.SSLError, OSError):
            return None

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """
        Сравнивает две семантические версии.

        Returns:
            1 если v1 > v2, -1 если v1 < v2, 0 если равны.
        """
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]

        # Выравниваем длину
        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for a, b in zip(parts1, parts2):
            if a > b:
                return 1
            if a < b:
                return -1
        return 0
