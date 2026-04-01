"""Secure credential storage for Hermes Agent.

Provides encrypted credential storage using the ``cryptography`` library
(Fernet symmetric encryption) with optional OS keychain integration via
``keyring``.  Also includes migration helpers to move plain-text secrets
from ``~/.hermes/.env`` into the secure store.

Usage:
    from tools.credential_storage import get_credential_store

    store = get_credential_store()
    store.set_secret("OPENAI_API_KEY", "sk-...")
    value = store.get_secret("OPENAI_API_KEY")
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CREDENTIALS_DIR_NAME = "credentials"
_KEY_FILE_NAME = "storage.key"
_STORE_FILE_NAME = "credentials.json"

# Env var names that are secrets (API keys, tokens, passwords).
# Derived from OPTIONAL_ENV_VARS entries with password=True.
_SECRET_ENV_NAMES = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_TOKEN",
        "OPENROUTER_API_KEY",
        "GLM_API_KEY",
        "ZAI_API_KEY",
        "Z_AI_API_KEY",
        "KIMI_API_KEY",
        "MINIMAX_API_KEY",
        "ELEVENLABS_API_KEY",
        "FIRECRAWL_API_KEY",
        "PARALLEL_API_KEY",
        "BROWSERBASE_API_KEY",
        "BROWSERBASE_PROJECT_ID",
        "TELEGRAM_BOT_TOKEN",
        "DISCORD_BOT_TOKEN",
        "SLACK_BOT_TOKEN",
        "SIGNAL_API_KEY",
        "DINGTALK_CLIENT_SECRET",
        "FEISHU_APP_SECRET",
        "FEISHU_ENCRYPT_KEY",
        "WECOM_SECRET",
        "MATRIX_PASSWORD",
        "HASS_TOKEN",
        "GROQ_API_KEY",
        "DEEPSEEK_API_KEY",
        "NOUS_API_KEY",
        "TOGETHER_API_KEY",
        "PERPLEXITY_API_KEY",
        "MISTRAL_API_KEY",
        "COHERE_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "FAL_KEY",
        "REPLICATE_API_TOKEN",
        "HF_TOKEN",
        "HUGGINGFACE_TOKEN",
        "DAYTONA_API_KEY",
        "MODAL_TOKEN",
        "MODAL_TOKEN_ID",
        "E2B_API_KEY",
    }
)


# ---------------------------------------------------------------------------
# EncryptedFileStore — Fernet-based local encryption
# ---------------------------------------------------------------------------


class EncryptedFileStore:
    """Encrypt/decrypt secrets using Fernet symmetric encryption.

    The encryption key is stored separately from the encrypted data file.
    On first use, a random key is generated and saved.
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._key_path = data_dir / _KEY_FILE_NAME
        self._store_path = data_dir / _STORE_FILE_NAME
        self._lock = threading.Lock()
        self._fernet = None

    def _get_fernet(self):
        """Lazy-init the Fernet cipher."""
        if self._fernet is not None:
            return self._fernet

        from cryptography.fernet import Fernet

        if not self._key_path.exists():
            key = Fernet.generate_key()
            self._key_path.write_bytes(key)
            os.chmod(self._key_path, 0o600)
            logger.info("Generated new encryption key at %s", self._key_path)
        else:
            key = self._key_path.read_bytes()

        self._fernet = Fernet(key)
        return self._fernet

    def encrypt_value(self, plaintext: str) -> str:
        """Encrypt a plaintext string, return base64-encoded ciphertext."""
        from cryptography.fernet import Fernet

        fernet = self._get_fernet()
        return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt_value(self, ciphertext: str) -> str:
        """Decrypt a base64-encoded ciphertext string."""
        from cryptography.fernet import Fernet, InvalidToken

        fernet = self._get_fernet()
        try:
            return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            raise ValueError(
                "Failed to decrypt — key may have changed or data is corrupt"
            )

    def save_store(self, data: Dict[str, str]) -> None:
        """Save encrypted data dict to disk."""
        from cryptography.fernet import Fernet

        fernet = self._get_fernet()
        encrypted = {}
        for k, v in data.items():
            encrypted[k] = fernet.encrypt(v.encode("utf-8")).decode("utf-8")

        tmp_path = self._store_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(encrypted, indent=2), encoding="utf-8")
        os.chmod(tmp_path, 0o600)
        tmp_path.replace(self._store_path)

    def load_store(self) -> Dict[str, str]:
        """Load and decrypt data from disk."""
        from cryptography.fernet import Fernet, InvalidToken

        if not self._store_path.exists():
            return {}

        fernet = self._get_fernet()
        raw = json.loads(self._store_path.read_text(encoding="utf-8"))
        decrypted = {}
        for k, v in raw.items():
            try:
                decrypted[k] = fernet.decrypt(v.encode("utf-8")).decode("utf-8")
            except InvalidToken:
                logger.warning("Could not decrypt credential for '%s' — skipping", k)
        return decrypted


# ---------------------------------------------------------------------------
# CredentialStore — unified interface with keyring fallback
# ---------------------------------------------------------------------------


class CredentialStore:
    """Unified credential storage with OS keyring preference and encrypted file fallback.

    Priority:
    1. OS keychain (via keyring library) — if available and working
    2. Encrypted file store (Fernet) — always available

    Secrets are also injected into os.environ so the rest of Hermes
    continues to work without changes (os.getenv("KEY") still works).
    """

    def __init__(self, data_dir: Optional[Path] = None):
        from core.hermes_constants import get_hermes_home

        self._data_dir = data_dir or (get_hermes_home() / _CREDENTIALS_DIR_NAME)
        self._file_store = EncryptedFileStore(self._data_dir)
        self._keyring_available = False
        self._cache: Dict[str, str] = {}
        self._lock = threading.Lock()

        self._probe_keyring()
        self._load_cache()

    def _probe_keyring(self) -> None:
        """Check if keyring is functional."""
        try:
            import keyring

            keyring.get_password("__hermes_probe__", "probe")
            self._keyring_available = True
            logger.debug("OS keyring is available")
        except Exception:
            self._keyring_available = False
            logger.debug("OS keyring unavailable, falling back to encrypted file store")

    def _load_cache(self) -> None:
        """Load all secrets into memory cache at startup."""
        if self._keyring_available:
            import keyring

            for name in _SECRET_ENV_NAMES:
                val = keyring.get_password("hermes-agent", name)
                if val:
                    self._cache[name] = val
        else:
            self._cache = self._file_store.load_store()

        # Inject into environment
        for name, val in self._cache.items():
            if name not in os.environ:
                os.environ[name] = val

    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a secret by name.

        Checks: in-memory cache → OS keyring → encrypted file → os.environ.
        """
        with self._lock:
            if name in self._cache:
                return self._cache[name]

            # Try OS keyring
            if self._keyring_available:
                try:
                    import keyring

                    val = keyring.get_password("hermes-agent", name)
                    if val:
                        self._cache[name] = val
                        return val
                except Exception:
                    pass

            # Try encrypted file
            try:
                store = self._file_store.load_store()
                if name in store:
                    self._cache[name] = store[name]
                    return store[name]
            except Exception:
                pass

            # Fallback to environment (plain text — legacy)
            return os.environ.get(name)

    def set_secret(self, name: str, value: str) -> None:
        """Store a secret securely.

        Tries OS keyring first, falls back to encrypted file.
        Also updates in-memory cache and os.environ.
        """
        with self._lock:
            self._cache[name] = value
            os.environ[name] = value

            if self._keyring_available:
                try:
                    import keyring

                    keyring.set_password("hermes-agent", name, value)
                    logger.info("Stored '%s' in OS keyring", name)
                    return
                except Exception as e:
                    logger.warning("Keyring set failed for '%s': %s", name, e)

            # Fallback: encrypted file
            self._file_store.save_store(self._cache)
            logger.info("Stored '%s' in encrypted file store", name)

    def delete_secret(self, name: str) -> bool:
        """Remove a secret from all stores."""
        with self._lock:
            removed = False

            self._cache.pop(name, None)
            os.environ.pop(name, None)
            removed = True

            if self._keyring_available:
                try:
                    import keyring

                    keyring.delete_password("hermes-agent", name)
                except Exception:
                    pass

            try:
                store = self._file_store.load_store()
                if name in store:
                    del store[name]
                    self._file_store.save_store(store)
            except Exception:
                pass

            return removed

    def list_stored_secrets(self) -> List[str]:
        """Return names of all stored secrets."""
        with self._lock:
            return sorted(self._cache.keys())

    def has_secret(self, name: str) -> bool:
        """Check if a secret exists in any store."""
        return self.get_secret(name) is not None

    @property
    def backend(self) -> str:
        """Return the active storage backend name."""
        return "keyring" if self._keyring_available else "encrypted_file"

    # -- Migration --

    def migrate_from_env_file(self, env_path: Optional[Path] = None) -> Dict[str, str]:
        """Migrate secrets from a plain-text .env file to secure storage.

        Returns a dict of migrated {name: value} pairs.
        Does NOT modify the original .env file — the caller should remove
        migrated entries after verifying the migration succeeded.
        """
        if env_path is None:
            from core.hermes_constants import get_hermes_home

            env_path = get_hermes_home() / ".env"

        if not env_path.exists():
            return {}

        migrated = {}
        try:
            from dotenv import dotenv_values

            env_vars = dotenv_values(env_path)
        except Exception:
            # Manual parse as fallback
            env_vars = {}
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env_vars[key.strip()] = val.strip().strip("\"'")

        for name, value in env_vars.items():
            if name in _SECRET_ENV_NAMES and value:
                self.set_secret(name, value)
                migrated[name] = value

        if migrated:
            logger.info(
                "Migrated %d secrets from %s to secure storage (%s)",
                len(migrated),
                env_path,
                self.backend,
            )
        return migrated


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_store: Optional[CredentialStore] = None
_store_lock = threading.Lock()


def get_credential_store(data_dir: Optional[Path] = None) -> CredentialStore:
    """Get or create the global CredentialStore singleton."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = CredentialStore(data_dir)
    return _store


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def _check_credential_storage() -> bool:
    """Tool is always available."""
    return True


def credential_storage_tool(
    action: str = "list",
    name: str = "",
    value: str = "",
    migrate: bool = False,
    task_id: str = None,
) -> str:
    """Manage secure credential storage.

    Args:
        action: One of "list", "get", "set", "delete", "migrate", "status".
        name: Credential name (e.g. "OPENAI_API_KEY").
        value: Credential value (for "set" action).
        migrate: If True, migrate secrets from ~/.hermes/.env.
    """
    try:
        store = get_credential_store()

        if action == "list":
            secrets = store.list_stored_secrets()
            return json.dumps(
                {
                    "success": True,
                    "data": {
                        "backend": store.backend,
                        "count": len(secrets),
                        "secrets": secrets,
                    },
                }
            )

        elif action == "get":
            if not name:
                return json.dumps(
                    {"success": False, "error": "Credential name required"}
                )
            val = store.get_secret(name)
            if val is None:
                return json.dumps(
                    {"success": False, "error": f"No credential found for '{name}'"}
                )
            # Never return full value — show masked
            masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
            return json.dumps(
                {"success": True, "data": {"name": name, "value": masked}}
            )

        elif action == "set":
            if not name or not value:
                return json.dumps(
                    {"success": False, "error": "Both name and value are required"}
                )
            store.set_secret(name, value)
            return json.dumps(
                {
                    "success": True,
                    "message": f"Stored '{name}' securely ({store.backend})",
                }
            )

        elif action == "delete":
            if not name:
                return json.dumps(
                    {"success": False, "error": "Credential name required"}
                )
            if store.delete_secret(name):
                return json.dumps({"success": True, "message": f"Deleted '{name}'"})
            return json.dumps({"success": False, "error": f"Could not delete '{name}'"})

        elif action == "migrate":
            migrated = store.migrate_from_env_file()
            return json.dumps(
                {
                    "success": True,
                    "data": {
                        "migrated": list(migrated.keys()),
                        "count": len(migrated),
                        "backend": store.backend,
                    },
                }
            )

        elif action == "status":
            return json.dumps(
                {
                    "success": True,
                    "data": {
                        "backend": store.backend,
                        "keyring_available": store._keyring_available,
                        "stored_count": len(store.list_stored_secrets()),
                    },
                }
            )

        else:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unknown action: {action}. Valid: list, get, set, delete, migrate, status",
                }
            )

    except Exception as e:
        logger.exception("credential_storage_tool error: %s", e)
        return json.dumps({"success": False, "error": str(e)})


registry.register(
    name="credential_storage",
    toolset="credential_storage",
    schema={
        "name": "credential_storage",
        "description": (
            "Manage secure credential storage. Store, retrieve, and migrate API keys "
            "and secrets from plain-text .env files to encrypted storage. "
            "Use action='migrate' to move secrets from ~/.hermes/.env to secure storage. "
            "Use action='status' to check the current storage backend."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "get", "set", "delete", "migrate", "status"],
                    "description": "Action to perform",
                },
                "name": {
                    "type": "string",
                    "description": "Credential name (e.g. 'OPENAI_API_KEY')",
                },
                "value": {
                    "type": "string",
                    "description": "Credential value (for 'set' action only)",
                },
            },
            "required": ["action"],
        },
    },
    handler=lambda args, **kw: credential_storage_tool(
        action=args.get("action", "list"),
        name=args.get("name", ""),
        value=args.get("value", ""),
        migrate=args.get("migrate", False),
        task_id=kw.get("task_id"),
    ),
    check_fn=_check_credential_storage,
    requires_env=[],
    description="Secure credential storage and migration from plain-text .env",
    emoji="🔐",
)
