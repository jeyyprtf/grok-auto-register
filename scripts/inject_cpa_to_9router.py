#!/usr/bin/env python3
"""Inject cpa_auths/xai-*.json into 9router SQLite (grok-cli oauth).

Cross-platform:
  - Interactive TUI (default when no flags):  python scripts/inject_cpa_to_9router.py
  - CLI / automation:  python scripts/inject_cpa_to_9router.py --auth-dir ... --db ... [--dry-run]

Works on Linux, macOS, Windows (Python 3.9+). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROVIDER = "grok-cli"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTH = PROJECT_ROOT / "cpa_auths"
# Remember last paths (per user, not in git)
STATE_FILE = Path.home() / ".grok_inject_9router.json"


def default_db_candidates() -> list[Path]:
    """Likely 9router DB locations per OS (+ shallow home scan)."""
    home = Path.home()
    cands: list[Path] = [
        home / ".9router" / "db" / "data.sqlite",
        home / ".9router" / "data.sqlite",
        home / "9router" / "db" / "data.sqlite",
        home / "9router" / "data.sqlite",
        Path("/mnt/data/9router/db/data.sqlite"),
        Path("/opt/9router/db/data.sqlite"),
        Path("/var/lib/9router/db/data.sqlite"),
    ]
    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if appdata:
        cands.append(Path(appdata) / "9router" / "db" / "data.sqlite")
        cands.append(Path(appdata) / "9router" / "data.sqlite")
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        cands.append(Path(xdg) / "9router" / "db" / "data.sqlite")
    # env override
    env_db = os.environ.get("NINEROUTER_DB") or os.environ.get("NINE_ROUTER_DB")
    if env_db:
        cands.insert(0, Path(env_db).expanduser())
    # shallow: */.9router/db/data.sqlite under home (depth 2)
    try:
        for p in home.glob("*/.9router/db/data.sqlite"):
            cands.append(p)
        for p in home.glob(".*/.9router/db/data.sqlite"):
            cands.append(p)
    except Exception:
        pass
    seen: set[str] = set()
    out: list[Path] = []
    for p in cands:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def find_default_db() -> Path:
    for p in default_db_candidates():
        if p.is_file():
            return p
    return default_db_candidates()[0]


def default_auth_candidates() -> list[Path]:
    """Likely cpa_auths folders."""
    home = Path.home()
    cands = [
        DEFAULT_AUTH,
        PROJECT_ROOT / "cpa_auths",
        home / "cpa_auths",
        home / "grok-auto-register" / "cpa_auths",
        Path("/mnt/data/grok/grok-auto-register/cpa_auths"),
    ]
    env = os.environ.get("GROK_CPA_AUTH_DIR")
    if env:
        cands.insert(0, Path(env).expanduser())
    seen: set[str] = set()
    out: list[Path] = []
    for p in cands:
        key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def find_default_auth() -> Path:
    for p in default_auth_candidates():
        if p.is_dir() and list(p.glob("xai-*.json")):
            return p
    for p in default_auth_candidates():
        if p.is_dir():
            return p
    return DEFAULT_AUTH


def load_state() -> dict:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(auth_dir: Path, db_path: Path) -> None:
    try:
        STATE_FILE.write_text(
            json.dumps(
                {"auth_dir": str(auth_dir), "db": str(db_path)},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass


def resolve_path(raw: str, base: Path | None = None) -> Path:
    s = (raw or "").strip().strip('"').strip("'")
    if not s:
        raise ValueError("path kosong")
    p = Path(s).expanduser()
    if not p.is_absolute() and base is not None:
        p = (base / p).resolve()
    else:
        p = p.resolve()
    return p


def list_cpa_files(auth_dir: Path) -> list[Path]:
    if not auth_dir.is_dir():
        return []
    return sorted(auth_dir.glob("xai-*.json"))


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_payload(cpa: dict, source: Path, imported_at: str) -> dict | None:
    email = (cpa.get("email") or "").strip()
    access = cpa.get("access_token")
    refresh = cpa.get("refresh_token")
    if not email or not access or not refresh:
        return None
    return {
        "accessToken": access,
        "refreshToken": refresh,
        "expiresIn": int(cpa.get("expires_in") or 21600),
        "expiresAt": cpa.get("expired") or imported_at,
        "scope": "openid profile email offline_access grok-cli:access api:access",
        "email": email,
        "displayName": email,
        "testStatus": "active",
        "providerSpecificData": {
            "authMethod": "device_code",
            "idToken": cpa.get("id_token"),
            "email": email,
            "userId": cpa.get("sub"),
            "hasGrokCodeAccess": True,
            "baseUrl": cpa.get("base_url"),
            "headers": cpa.get("headers") or {},
            "importedFrom": str(source),
            "importedAt": imported_at,
        },
    }


def inject(auth_dir: Path, db_path: Path, *, dry_run: bool = False) -> dict:
    files = list_cpa_files(auth_dir)
    if not files:
        raise FileNotFoundError(f"Tidak ada xai-*.json di: {auth_dir}")
    if not dry_run:
        if not db_path.is_file():
            raise FileNotFoundError(f"DB 9router tidak ketemu: {db_path}")

    imported_at = now_iso()
    conn = None if dry_run else sqlite3.connect(str(db_path))
    cur = None if dry_run else conn.cursor()

    inserted = updated = skipped = 0
    lines: list[str] = []

    for p in files:
        try:
            cpa = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            skipped += 1
            lines.append(f"  skip {p.name}: {e}")
            continue
        data = build_payload(cpa, p, imported_at)
        if not data:
            skipped += 1
            lines.append(f"  skip {p.name}: email/token kurang")
            continue
        email = data["email"]

        if dry_run:
            inserted += 1
            lines.append(f"  dry-run ok: {email}")
            continue

        cur.execute(
            "SELECT id FROM providerConnections WHERE provider=? AND email=?",
            (PROVIDER, email),
        )
        row = cur.fetchone()
        payload = json.dumps(data)
        if row:
            cur.execute(
                "UPDATE providerConnections SET authType=?, name=?, isActive=1, data=?, updatedAt=? WHERE id=?",
                ("oauth", email, payload, imported_at, row[0]),
            )
            updated += 1
            lines.append(f"  updated {email}")
        else:
            cur.execute(
                "SELECT COALESCE(MAX(priority),0) FROM providerConnections WHERE provider=?",
                (PROVIDER,),
            )
            priority = (cur.fetchone()[0] or 0) + 1
            cid = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO providerConnections
                   (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    cid,
                    PROVIDER,
                    "oauth",
                    email,
                    email,
                    priority,
                    1,
                    payload,
                    imported_at,
                    imported_at,
                ),
            )
            inserted += 1
            lines.append(f"  inserted {email}")

    active: int | str = "n/a"
    if conn is not None:
        conn.commit()
        cur.execute(
            "SELECT COUNT(*) FROM providerConnections WHERE provider=? AND isActive=1",
            (PROVIDER,),
        )
        active = cur.fetchone()[0]
        conn.close()

    return {
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "active": active,
        "files": len(files),
        "lines": lines,
    }


def prompt(msg: str, default: str = "") -> str:
    if default:
        raw = input(f"{msg} [{default}]: ").strip()
        return raw if raw else default
    return input(f"{msg}: ").strip()


def pause() -> None:
    try:
        input("\nEnter buat lanjut...")
    except EOFError:
        pass


def print_header() -> None:
    print()
    print("=" * 52)
    print("  Inject CPA → 9router  (Grok Build / grok-cli)")
    print("  Linux / macOS / Windows  |  model: gcli/grok-4.5")
    print("=" * 52)


def print_status(auth_dir: Path, db_path: Path) -> None:
    files = list_cpa_files(auth_dir)
    auth_ok = "OK" if auth_dir.is_dir() else "FOLDER TIDAK ADA"
    db_ok = "OK" if db_path.is_file() else "FILE TIDAK ADA"
    print()
    print(f"  Auth dir : {auth_dir}")
    print(f"             ({len(files)} file xai-*.json) [{auth_ok}]")
    print(f"  DB 9router: {db_path}")
    print(f"             [{db_ok}]")
    print()


def pick_from_list(title: str, options: list[str]) -> str | None:
    print(f"\n{title}")
    for i, o in enumerate(options, 1):
        mark = "  (ada)" if Path(o).expanduser().is_file() or Path(o).expanduser().is_dir() else ""
        print(f"  {i}. {o}{mark}")
    print(f"  0. ketik path manual")
    choice = input("Pilih nomor: ").strip()
    if choice == "0" or choice == "":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass
    print("  pilihan tidak valid")
    return None


def tui() -> int:
    state = load_state()
    auth_dir = Path(state["auth_dir"]).expanduser() if state.get("auth_dir") else find_default_auth()
    db_path = Path(state["db"]).expanduser() if state.get("db") else find_default_db()
    try:
        auth_dir = auth_dir.resolve()
    except Exception:
        auth_dir = find_default_auth()
    try:
        db_path = db_path.resolve()
    except Exception:
        db_path = find_default_db()

    while True:
        print_header()
        print_status(auth_dir, db_path)
        print("  1) Ganti folder CPA (xai-*.json)")
        print("  2) Ganti path DB 9router (data.sqlite)")
        print("  3) Deteksi otomatis (DB + cpa_auths)")
        print("  4) Dry-run (cek file, tidak tulis DB)")
        print("  5) Inject sekarang")
        print("  6) Lihat daftar file CPA")
        print("  0) Keluar")
        print()
        try:
            choice = input("Pilih: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if choice == "0":
            print("Bye.")
            return 0

        if choice == "1":
            cands = [str(p) for p in default_auth_candidates()]
            picked = pick_from_list("Folder CPA kandidat:", cands)
            if picked is None:
                raw = prompt("Path folder cpa_auths", str(auth_dir))
            else:
                raw = picked
            try:
                auth_dir = resolve_path(raw)
                save_state(auth_dir, db_path)
                print(f"  → auth_dir = {auth_dir}")
            except Exception as e:
                print(f"  error: {e}")
            pause()
            continue

        if choice == "2":
            cands = [str(p) for p in default_db_candidates()]
            picked = pick_from_list("DB kandidat:", cands)
            if picked is None:
                raw = prompt("Path lengkap data.sqlite", str(db_path))
            else:
                raw = picked
            try:
                db_path = resolve_path(raw)
                save_state(auth_dir, db_path)
                print(f"  → db = {db_path}")
            except Exception as e:
                print(f"  error: {e}")
            pause()
            continue

        if choice == "3":
            found_db = [p for p in default_db_candidates() if p.is_file()]
            found_auth = [p for p in default_auth_candidates() if p.is_dir() and list(p.glob("xai-*.json"))]
            if found_auth:
                print("  CPA folder ketemu:")
                for i, p in enumerate(found_auth, 1):
                    print(f"    {i}. {p} ({len(list(p.glob('xai-*.json')))} file)")
                if len(found_auth) == 1:
                    auth_dir = found_auth[0]
                else:
                    n = input("  Pakai auth nomor? ").strip()
                    try:
                        auth_dir = found_auth[int(n) - 1]
                    except Exception:
                        print("  auth: skip")
            else:
                print("  Tidak ketemu folder cpa_auths berisi xai-*.json")
            if not found_db:
                print("  Tidak ketemu data.sqlite di lokasi default.")
                print("  Coba buka 9router sekali, atau pilih menu 2 (path manual).")
                print("  Override: export NINEROUTER_DB=/path/to/data.sqlite")
            else:
                print("  DB ketemu:")
                for i, p in enumerate(found_db, 1):
                    print(f"    {i}. {p}")
                if len(found_db) == 1:
                    db_path = found_db[0]
                else:
                    n = input("  Pakai DB nomor? ").strip()
                    try:
                        db_path = found_db[int(n) - 1]
                    except Exception:
                        print("  DB: batal")
                        pause()
                        continue
            save_state(auth_dir, db_path)
            print(f"  → auth_dir = {auth_dir}")
            print(f"  → db = {db_path}")
            pause()
            continue

        if choice == "4":
            try:
                result = inject(auth_dir, db_path, dry_run=True)
                for line in result["lines"]:
                    print(line)
                print(
                    f"\n  dry-run: files={result['files']} ok={result['inserted']} "
                    f"skip={result['skipped']}"
                )
            except Exception as e:
                print(f"  GAGAL: {e}")
            pause()
            continue

        if choice == "5":
            print()
            print(f"  Inject {len(list_cpa_files(auth_dir))} file")
            print(f"  ke DB: {db_path}")
            conf = input("  Yakin? [y/N]: ").strip().lower()
            if conf not in ("y", "yes", "ya"):
                print("  dibatalkan")
                pause()
                continue
            try:
                result = inject(auth_dir, db_path, dry_run=False)
                for line in result["lines"]:
                    print(line)
                print(
                    f"\n  SELESAI inserted={result['inserted']} updated={result['updated']} "
                    f"skipped={result['skipped']} active_grok_cli={result['active']}"
                )
                print("  Model di 9router: gcli/grok-4.5")
                save_state(auth_dir, db_path)
            except Exception as e:
                print(f"  GAGAL: {e}")
            pause()
            continue

        if choice == "6":
            files = list_cpa_files(auth_dir)
            if not files:
                print("  (kosong)")
            else:
                for p in files:
                    try:
                        em = json.loads(p.read_text(encoding="utf-8")).get("email", "?")
                    except Exception:
                        em = "?"
                    print(f"  - {p.name}  ({em})")
                print(f"  total: {len(files)}")
            pause()
            continue

        print("  menu tidak dikenal")
        pause()


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Inject CPA xai-*.json ke 9router (TUI atau CLI)",
    )
    ap.add_argument(
        "--auth-dir",
        type=str,
        default=None,
        help="Folder berisi xai-*.json",
    )
    ap.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path data.sqlite 9router",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Cek saja, tidak tulis DB",
    )
    ap.add_argument(
        "--tui",
        action="store_true",
        help="Paksa mode menu interaktif",
    )
    ap.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="CLI inject tanpa konfirmasi",
    )
    return ap


def main() -> int:
    # Windows console UTF-8 best-effort
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = build_parser()
    args = ap.parse_args()

    # No path flags → TUI (unless only --dry-run without paths still can tui)
    use_tui = args.tui or (args.auth_dir is None and args.db is None and not args.dry_run)

    # Explicit: only --dry-run with defaults = still allow CLI dry-run via defaults
    if args.dry_run and args.auth_dir is None and args.db is None and not args.tui:
        # treat as CLI with defaults
        use_tui = False

    if use_tui:
        return tui()

    state = load_state()
    auth_raw = args.auth_dir or state.get("auth_dir") or str(find_default_auth())
    db_raw = args.db or state.get("db") or str(find_default_db())
    auth_dir = resolve_path(auth_raw)
    db_path = resolve_path(db_raw)

    if not args.dry_run and not args.yes:
        print(f"auth-dir: {auth_dir} ({len(list_cpa_files(auth_dir))} files)")
        print(f"db:       {db_path}")
        conf = input("Inject? [y/N]: ").strip().lower()
        if conf not in ("y", "yes", "ya"):
            print("batal")
            return 1

    try:
        result = inject(auth_dir, db_path, dry_run=args.dry_run)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    for line in result["lines"]:
        print(line)
    print(
        f"done inserted={result['inserted']} updated={result['updated']} "
        f"skipped={result['skipped']} active_grok_cli={result['active']}"
    )
    if not args.dry_run:
        save_state(auth_dir, db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
