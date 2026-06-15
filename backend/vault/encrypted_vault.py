import json
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

from backend.vault.key_derivation import derive_key, derive_key_from_passphrase, encode_salt, decode_salt
from backend.utils.logger import logger


class VaultError(Exception):
    pass


class InvalidPasswordError(VaultError):
    pass


class VaultCorruptedError(VaultError):
    pass


class EncryptedVault:
    VAULT_VERSION = "1"

    def __init__(self, vault_path: str | Path, password: str, salt: str | None = None):
        self.vault_path = Path(vault_path)
        self._fernet: Fernet | None = None
        self._salt_str = salt
        self._unlock(password, salt)

    def _unlock(self, password: str, salt_hint: str | None = None) -> None:
        if not password:
            raise VaultError("Vault password cannot be empty")

        if self.vault_path.exists():
            try:
                raw = self.vault_path.read_bytes()
                header, _, payload = raw.partition(b"\n")
                meta = json.loads(header.decode("utf-8"))
                salt_bytes = decode_salt(meta["salt"])
                key, _ = derive_key(password, salt_bytes)
                fernet = Fernet(key)
                fernet.decrypt(payload)
                self._fernet = fernet
                self._salt_str = meta["salt"]
                logger.info("Vault unlocked from existing file")
            except (InvalidToken, KeyError):
                raise InvalidPasswordError("Invalid vault password")
            except Exception as e:
                raise VaultCorruptedError(f"Vault file corrupted: {e}")
        else:
            if salt_hint:
                key = derive_key_from_passphrase(password, salt_hint)
            else:
                key, salt_bytes = derive_key(password)
                self._salt_str = encode_salt(salt_bytes)

            if salt_hint and not hasattr(self, "_salt_str_set"):
                import hashlib
                salt_raw = hashlib.sha256(salt_hint.encode()).digest()[:16]
                self._salt_str = encode_salt(salt_raw)

            self._fernet = Fernet(key)
            self._save_empty()
            logger.info("New vault created")

    def _save_empty(self) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        empty = self._fernet.encrypt(json.dumps({}).encode("utf-8"))
        meta = json.dumps({"version": self.VAULT_VERSION, "salt": self._salt_str}).encode("utf-8")
        self.vault_path.write_bytes(meta + b"\n" + empty)

    def _load_data(self) -> dict:
        try:
            raw = self.vault_path.read_bytes()
            _, _, payload = raw.partition(b"\n")
            decrypted = self._fernet.decrypt(payload)
            return json.loads(decrypted.decode("utf-8"))
        except InvalidToken:
            raise InvalidPasswordError("Cannot decrypt vault — wrong key")
        except Exception as e:
            raise VaultCorruptedError(f"Failed to read vault: {e}")

    def _save_data(self, data: dict) -> None:
        try:
            payload = self._fernet.encrypt(json.dumps(data).encode("utf-8"))
            meta = json.dumps({"version": self.VAULT_VERSION, "salt": self._salt_str}).encode("utf-8")
            self.vault_path.write_bytes(meta + b"\n" + payload)
        except Exception as e:
            raise VaultError(f"Failed to write vault: {e}")

    def set(self, key: str, value: str) -> None:
        data = self._load_data()
        data[key] = value
        self._save_data(data)
        logger.debug(f"Vault: set key '{key}'")

    def get(self, key: str, default: str | None = None) -> str | None:
        data = self._load_data()
        return data.get(key, default)

    def delete(self, key: str) -> bool:
        data = self._load_data()
        if key in data:
            del data[key]
            self._save_data(data)
            logger.debug(f"Vault: deleted key '{key}'")
            return True
        return False

    def list_keys(self) -> list[str]:
        data = self._load_data()
        return list(data.keys())

    def has(self, key: str) -> bool:
        data = self._load_data()
        return key in data

    def clear(self) -> None:
        self._save_data({})
        logger.warning("Vault cleared")

    def rotate_password(self, new_password: str) -> None:
        data = self._load_data()
        key, salt_bytes = derive_key(new_password)
        self._salt_str = encode_salt(salt_bytes)
        self._fernet = Fernet(key)
        self._save_data(data)
        logger.info("Vault password rotated")

    def encrypt_value(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt_value(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            raise InvalidPasswordError("Cannot decrypt value — wrong key or corrupted")
