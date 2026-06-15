import os
import base64
import hashlib
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


ITERATIONS = 600_000
KEY_LENGTH = 32
HASH_ALGORITHM = hashes.SHA256


def derive_key(password: str, salt: bytes | str | None = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    elif isinstance(salt, str):
        salt = salt.encode("utf-8")

    kdf = PBKDF2HMAC(
        algorithm=HASH_ALGORITHM(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=ITERATIONS,
        backend=default_backend(),
    )

    key_bytes = kdf.derive(password.encode("utf-8"))
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return fernet_key, salt


def derive_key_from_passphrase(passphrase: str, salt_str: str) -> bytes:
    salt = hashlib.sha256(salt_str.encode("utf-8")).digest()[:16]
    key, _ = derive_key(passphrase, salt)
    return key


def verify_password(password: str, salt: bytes, expected_key: bytes) -> bool:
    derived, _ = derive_key(password, salt)
    return hmac_compare(derived, expected_key)


def hmac_compare(a: bytes, b: bytes) -> bool:
    import hmac
    return hmac.compare_digest(a, b)


def encode_salt(salt: bytes) -> str:
    return base64.urlsafe_b64encode(salt).decode("utf-8")


def decode_salt(salt_str: str) -> bytes:
    return base64.urlsafe_b64decode(salt_str.encode("utf-8"))
