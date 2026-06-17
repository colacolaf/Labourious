#!/usr/bin/env python3
"""Run this to verify Phase 1 installation is working."""
import sys
import os

# Ensure project root is on path so `backend` package resolves
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def check(label: str, fn):
    try:
        fn()
        print(f"  OK  {label}")
        return True
    except Exception as e:
        print(f"  FAIL  {label}: {e}")
        return False


def main():
    print("\n=== Labourious Install Verification ===\n")
    results = []

    results.append(check("Python >= 3.11", lambda: (
        None if sys.version_info >= (3, 11) else (
            (_ for _ in ()).throw(RuntimeError(f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.11"))
        )
    )))

    results.append(check("fastapi importable", lambda: __import__("fastapi")))
    results.append(check("sqlalchemy importable", lambda: __import__("sqlalchemy")))
    results.append(check("cryptography importable", lambda: __import__("cryptography")))
    results.append(check("pydantic importable", lambda: __import__("pydantic")))
    results.append(check("pytest importable", lambda: __import__("pytest")))

    results.append(check("backend.config importable", lambda: __import__("backend.config")))
    results.append(check("backend.main importable", lambda: __import__("backend.main")))
    results.append(check(
        "backend.vault.encrypted_vault importable",
        lambda: __import__("backend.vault.encrypted_vault", fromlist=["EncryptedVault"])
    ))

    results.append(check("data/ directory created", lambda: os.makedirs("data", exist_ok=True)))

    def vault_roundtrip():
        mod = __import__("backend.vault.encrypted_vault", fromlist=["EncryptedVault"])
        import tempfile, os as _os
        tmp_dir = tempfile.mkdtemp()
        path = os.path.join(tmp_dir, "test_vault.db")
        try:
            vault = mod.EncryptedVault(path, "TestPass#1")
            enc = vault.encrypt_value("hello")
            assert vault.decrypt_value(enc) == "hello", "roundtrip mismatch"
        finally:
            if _os.path.exists(path):
                _os.unlink(path)
            _os.rmdir(tmp_dir)

    results.append(check("vault encrypt/decrypt roundtrip", vault_roundtrip))

    ok = sum(results)
    total = len(results)
    print(f"\n{ok}/{total} checks passed")
    if ok < total:
        print("Fix failures above before proceeding to Phase 2.")
        sys.exit(1)
    else:
        print("Phase 1 installation verified")


if __name__ == "__main__":
    main()
