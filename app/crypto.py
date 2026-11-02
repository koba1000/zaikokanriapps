"""個人情報（従業員住所）の列暗号化。AES-256-GCM。

鍵は環境変数 ENCRYPTION_KEY（base64, 32バイト）。DBとは別管理にする。
"""

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from flask import current_app

NONCE_SIZE = 12


class DecryptionError(Exception):
    pass


def _aead() -> AESGCM:
    key = base64.b64decode(current_app.config["ENCRYPTION_KEY"])
    if len(key) != 32:
        raise RuntimeError("ENCRYPTION_KEY must be 32 bytes (base64)")
    return AESGCM(key)


def encrypt(plaintext: str) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    return nonce + _aead().encrypt(nonce, plaintext.encode("utf-8"), None)


def decrypt(token: bytes) -> str:
    nonce, ciphertext = token[:NONCE_SIZE], token[NONCE_SIZE:]
    try:
        return _aead().decrypt(nonce, ciphertext, None).decode("utf-8")
    except InvalidTag as exc:
        raise DecryptionError("cannot decrypt") from exc


def generate_key() -> str:
    return base64.b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii")
