import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import inject_cpa_to_9router as injector
from scripts import manage


SCHEMA = """
CREATE TABLE providerConnections (
    id TEXT PRIMARY KEY, provider TEXT, authType TEXT, name TEXT, email TEXT,
    priority INTEGER, isActive INTEGER, data TEXT, createdAt TEXT, updatedAt TEXT
)
"""


class ManageTests(unittest.TestCase):
    def test_example_is_not_treated_as_active_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = root / "config.example.json"
            example.write_text('{"cloudflare_api_base":"https://temp-mail.example.com"}')
            with patch.object(manage, "CONFIG", root / "config.json"), patch.object(
                manage, "CONFIG_EXAMPLE", example
            ):
                self.assertEqual(manage.load_config(), {})

    def test_generated_wrangler_uses_secret_and_rate_limit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            manage, "WRANGLER_TOML", Path(tmp) / "wrangler.toml"
        ):
            manage.ensure_wrangler_toml("example.com", "mail.example.com", "db-id")
            config = manage.WRANGLER_TOML.read_text(encoding="utf-8")
            self.assertNotIn("JWT_SECRET", config)
            self.assertIn('name = "RATE_LIMITER"', config)

    def test_status_does_not_create_test_address(self):
        with patch.object(manage.sys, "argv", ["manage.py", "status"]), patch.object(
            manage, "print_status"
        ) as status, patch.object(manage, "cmd_check_mail") as check_mail:
            self.assertEqual(manage.main(), 0)
        status.assert_called_once_with()
        check_mail.assert_not_called()


class InjectorTests(unittest.TestCase):
    def _write_auth(self, folder: Path, email: str) -> None:
        (folder / f"xai-{email}.json").write_text(
            json.dumps({"email": email, "access_token": "a", "refresh_token": "r"}),
            encoding="utf-8",
        )

    def test_dry_run_validates_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auth = root / "auth"
            auth.mkdir()
            self._write_auth(auth, "a@example.com")
            db = root / "wrong.sqlite"
            sqlite3.connect(db).close()
            with self.assertRaisesRegex(RuntimeError, "schema 9router"):
                injector.inject(auth, db, dry_run=True)

    def test_dry_run_reads_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auth = root / "auth"
            auth.mkdir()
            self._write_auth(auth, "old@example.com")
            self._write_auth(auth, "new@example.com")
            db = root / "data.sqlite"
            with sqlite3.connect(db) as conn:
                conn.execute(SCHEMA)
                conn.execute(
                    "INSERT INTO providerConnections VALUES (?,?,?,?,?,?,?,?,?,?)",
                    ("1", "grok-cli", "oauth", "old", "old@example.com", 1, 1, "{}", "x", "x"),
                )

            result = injector.inject(auth, db, dry_run=True)

            self.assertEqual((result["inserted"], result["updated"]), (1, 1))
            with sqlite3.connect(db) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM providerConnections").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
