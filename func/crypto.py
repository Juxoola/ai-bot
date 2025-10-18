import os
import base64
import logging
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes

# Ключ для шифрования в памяти (инициализируется лениво)
_ENCRYPTION_KEY_BYTES: Optional[bytes] = None


def get_encryption_key() -> bytes:
    global _ENCRYPTION_KEY_BYTES
    if _ENCRYPTION_KEY_BYTES is None:
        _ENCRYPTION_KEY_BYTES = AESGCM.generate_key(bit_length=256)
        logging.info("Сгенерирован эфемерный мастер-ключ для текущего запуска.")
    return _ENCRYPTION_KEY_BYTES


def _derive_user_key(master_key: bytes, user_id: int) -> bytes:
    try:
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"user_ctx_v1",
            info=str(user_id).encode("utf-8"),
        )
        return hkdf.derive(master_key)
    except Exception as e:
        logging.error(f"Ошибка деривации ключа для пользователя {user_id}: {e}")
        digest = hashes.Hash(hashes.SHA256())
        digest.update(master_key)
        digest.update(str(user_id).encode("utf-8"))
        return digest.finalize()

def encrypt_text_for_user(user_id: int, plaintext: Optional[str]) -> Optional[str]:
    if plaintext is None or plaintext == "":
        return plaintext
    try:
        master = get_encryption_key()
        key = _derive_user_key(master, user_id)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ct).decode("utf-8")
    except Exception as e:
        logging.error(f"Ошибка шифрования для пользователя {user_id}: {e}")
        return plaintext

def decrypt_text_for_user(user_id: int, ciphertext_b64: Optional[str]) -> Optional[str]:
    if ciphertext_b64 is None or ciphertext_b64 == "":
        return ciphertext_b64
    try:
        blob = base64.b64decode(ciphertext_b64)
        if len(blob) <= 12:
            return ciphertext_b64
        nonce, ct = blob[:12], blob[12:]
        master = get_encryption_key()
        key = _derive_user_key(master, user_id)
        aesgcm = AESGCM(key)
        pt = aesgcm.decrypt(nonce, ct, None)
        return pt.decode("utf-8")
    except Exception:
        return ciphertext_b64