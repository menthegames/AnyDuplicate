"""
Менеджер лицензий AnyDuplicate Advanced
Проверяет и активирует Pro-ключи с использованием Ed25519 подписи.
"""
import os, json, hashlib, uuid, base64
from pathlib import Path
from core.config_manager import APP_DATA_DIR

class LicenseManager:
    FILE = APP_DATA_DIR / "license.lic"
    PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAdyggJcsefc1kbXPoZNJEfsjxXedXbAPEyaChu8ZchO8=
-----END PUBLIC KEY-----"""

    def __init__(self):
        self.is_pro = False
        self._load()

    def _load(self):
        if self.FILE.exists():
            try:
                with open(self.FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if self._verify(data["key"], data["hwid"]):
                    self.is_pro = True
            except Exception:
                pass

    def activate(self, key_str: str) -> bool:
        hwid = self._get_hwid()
        if not self._verify(key_str, hwid):
            return False
        with open(self.FILE, "w", encoding="utf-8") as f:
            json.dump({"key": key_str, "hwid": hwid}, f, indent=2)
        self.is_pro = True
        return True

    def _verify(self, key_str: str, hwid: str) -> bool:
        if not key_str.startswith("ANY-PRO-"):
            return False
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.hazmat.primitives import serialization
            from cryptography.exceptions import InvalidSignature

            payload_b64, sig_b64 = key_str.replace("ANY-PRO-", "").split("-", 1)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            sig = base64.urlsafe_b64decode(sig_b64)
            if payload.get("hwid") != hwid:
                return False
            pub_key = serialization.load_pem_public_key(self.PUBLIC_KEY_PEM)
            pub_key.verify(sig, payload_b64.encode())
            return True
        except Exception:
            return False

    def _get_hwid(self) -> str:
        return hashlib.sha256(
            f"{uuid.getnode()}_{os.getenv('PROCESSOR_IDENTIFIER', '')}_{os.name}".encode()
        ).hexdigest()[:16]

    def deactivate(self):
        self.FILE.unlink(missing_ok=True)
        self.is_pro = False
