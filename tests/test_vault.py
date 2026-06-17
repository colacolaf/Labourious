import pytest
from backend.vault.encrypted_vault import EncryptedVault, InvalidPasswordError


def test_encrypt_decrypt(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    plaintext = "BTC_API_KEY_ABC123"
    encrypted = vault.encrypt_value(plaintext)
    assert encrypted != plaintext
    decrypted = vault.decrypt_value(encrypted)
    assert decrypted == plaintext


def test_wrong_password_raises(temp_vault_path, tmp_path):
    vault1 = EncryptedVault(temp_vault_path, "Password#1")
    encrypted = vault1.encrypt_value("secret")

    vault2_path = str(tmp_path / "vault2.db")
    vault2 = EncryptedVault(vault2_path, "WrongPassword#1")
    with pytest.raises((InvalidPasswordError, ValueError)):
        vault2.decrypt_value(encrypted)


def test_set_and_get(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    vault.set("api_key", "my_secret_value")
    assert vault.get("api_key") == "my_secret_value"


def test_delete_key(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    vault.set("to_delete", "value")
    assert vault.has("to_delete")
    vault.delete("to_delete")
    assert not vault.has("to_delete")


def test_list_keys(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    vault.set("key_a", "val_a")
    vault.set("key_b", "val_b")
    keys = vault.list_keys()
    assert "key_a" in keys
    assert "key_b" in keys
