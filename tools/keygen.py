"""
Генератор лицензионных ключей AnyDuplicate Advanced Pro
Генерирует Ed25519 ключи и формирует строку ANY-PRO-{payload_b64}-{sig_b64}

Использование:
    python tools/keygen.py          # сгенерировать новую пару и ключ
    python tools/keygen.py --verify  # проверить существующий ключ из license.lic
"""
import os
import sys
import json
import hashlib
import uuid
import base64
from pathlib import Path

# Добавляем корень проекта в sys.path для импорта core.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


def _get_hwid() -> str:
    """Вычисляет HWID так же, как в license_manager.py"""
    return hashlib.sha256(
        f"{uuid.getnode()}_{os.getenv('PROCESSOR_IDENTIFIER', '')}_{os.name}".encode()
    ).hexdigest()[:16]


def generate_key_pair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Генерирует новую пару Ed25519 ключей."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def sign_hwid(private_key: Ed25519PrivateKey, hwid: str) -> str:
    """
    Подписывает HWID и возвращает строку ANY-PRO-{payload_b64}-{sig_b64}.
    """
    payload = json.dumps({"hwid": hwid})
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    # Подписываем payload_b64 (как в license_manager._verify)
    sig = private_key.sign(payload_b64.encode())
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")

    return f"ANY-PRO-{payload_b64}-{sig_b64}"


def verify_key(key_str: str, hwid: str, public_key_pem: bytes) -> bool:
    """Проверяет ключ (аналогично LicenseManager._verify)."""
    if not key_str.startswith("ANY-PRO-"):
        return False
    try:
        payload_b64, sig_b64 = key_str.replace("ANY-PRO-", "").split("-", 1)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        sig = base64.urlsafe_b64decode(sig_b64 + "==")
        if payload.get("hwid") != hwid:
            return False
        pub_key = serialization.load_pem_public_key(public_key_pem)
        pub_key.verify(sig, payload_b64.encode())
        return True
    except Exception:
        return False


def main():
    if "--verify" in sys.argv:
        # Проверка существующего ключа из license.lic
        from core.config_manager import APP_DATA_DIR
        lic_file = APP_DATA_DIR / "license.lic"
        if not lic_file.exists():
            print("Файл license.lic не найден.")
            return
        with open(lic_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        key_str = data["key"]
        hwid = data["hwid"]
        print(f"Ключ: {key_str}")
        print(f"HWID: {hwid}")
        # Используем публичный ключ из license_manager
        from core.license_manager import LicenseManager
        result = verify_key(key_str, hwid, LicenseManager.PUBLIC_KEY_PEM)
        print(f"Проверка: {'✓ УСПЕШНО' if result else '✗ НЕ ПРОШЛА'}")
        return

    # Генерация новой пары ключей
    print("=" * 60)
    print("  AnyDuplicate Advanced Pro — Генератор ключей")
    print("=" * 60)

    private_key, public_key = generate_key_pair()

    # Экспорт публичного ключа в PEM
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Экспорт приватного ключа в PEM
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    print("\n🔑 Пара ключей Ed25519 сгенерирована:\n")

    print("--- ПРИВАТНЫЙ КЛЮЧ (хранить в секрете!) ---")
    print(private_key_pem.decode().strip())
    print()

    print("--- ПУБЛИЧНЫЙ КЛЮЧ (встраивается в приложение) ---")
    print(public_key_pem.decode().strip())
    print()

    # Генерируем лицензионный ключ для текущего HWID
    hwid = _get_hwid()
    print(f"💻 HWID текущей машины: {hwid}")
    print()

    license_key = sign_hwid(private_key, hwid)
    print("📋 Лицензионный ключ для ЭТОЙ машины:")
    print(f"   {license_key}")
    print()

    # Проверка: верифицируем только что сгенерированный ключ
    assert verify_key(license_key, hwid, public_key_pem), "Ошибка: ключ не прошёл верификацию!"
    print("✓ Ключ успешно прошёл самопроверку.\n")

    # Дополнительно: показываем, как выглядит публичный ключ в формате для вставки
    print("--- Для вставки в license_manager.py (PUBLIC_KEY_PEM) ---")
    pem_lines = public_key_pem.decode().strip().split("\n")
    print(f'    PUBLIC_KEY_PEM = b"""{"".join(pem_lines)}"""')
    print()

    print("=" * 60)
    print("  Готово! Используйте ключ выше для активации Pro.")
    print("=" * 60)


if __name__ == "__main__":
    main()
