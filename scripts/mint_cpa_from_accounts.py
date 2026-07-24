#!/usr/bin/env python3
"""Mint CPA xai-*.json from durable accounts_*.txt (email----password----sso).

Workflow split:
  1) register  → accounts_YYYYMMDD_HHMMSS.txt  (durable)
  2) this script → cpa_auths/xai-*.json         (fresh OAuth, short-lived)
  3) inject_cpa_to_9router.py

Stdlib + project cpa_export. Example:
  python scripts/mint_cpa_from_accounts.py
  python scripts/mint_cpa_from_accounts.py --accounts accounts_20260724_004441.txt
  python scripts/mint_cpa_from_accounts.py --accounts accounts_*.txt --delay 45 --skip-existing
  python scripts/mint_cpa_from_accounts.py --limit 3 --dry-run
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))


def _load_config() -> dict:
    try:
        from grok_register_ttk import load_config

        return load_config() or {}
    except Exception:
        cfg_path = PROJECT / "config.json"
        if cfg_path.is_file():
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        return {}


def _parse_accounts(paths: list[Path]) -> list[tuple[str, str, str]]:
    from cpa_xai.accounts import parse_accounts_file

    seen: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for p in paths:
        for a in parse_accounts_file(p):
            key = a.email.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((a.email, a.password, a.sso))
    return out


def _resolve_accounts_args(patterns: list[str] | None) -> list[Path]:
    if not patterns:
        # newest accounts_*.txt in project root
        files = sorted(PROJECT.glob("accounts_*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            raise SystemExit("tidak ada accounts_*.txt — register dulu atau --accounts PATH")
        return [files[0]]
    found: list[Path] = []
    for pat in patterns:
        hits = [Path(p) for p in glob.glob(pat)]
        if not hits:
            p = Path(pat).expanduser()
            if p.is_file():
                hits = [p]
        found.extend(hits)
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        key = str(p.resolve())
        if key not in seen and p.is_file():
            seen.add(key)
            out.append(p)
    if not out:
        raise SystemExit(f"tidak ketemu file: {patterns}")
    return out


def _auth_dir(cfg: dict) -> Path:
    raw = (cfg.get("cpa_auth_dir") or "cpa_auths").strip()
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (PROJECT / p).resolve()
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description="Mint CPA xai-*.json dari accounts_*.txt")
    ap.add_argument(
        "--accounts",
        nargs="*",
        default=None,
        help="path/glob accounts_*.txt (default: accounts_*.txt terbaru)",
    )
    ap.add_argument("--auth-dir", default="", help="output cpa_auths (default: config/cpa_auths)")
    ap.add_argument("--delay", type=float, default=30.0, help="jeda detik antar mint (default 30)")
    ap.add_argument("--limit", type=int, default=0, help="max akun (0=all)")
    ap.add_argument("--skip-existing", action="store_true", default=True, help="skip email yang sudah ada xai-*.json")
    ap.add_argument("--force", action="store_true", help="mint ulang meski file sudah ada")
    ap.add_argument("--dry-run", action="store_true", help="list saja, tidak mint")
    ap.add_argument("-y", "--yes", action="store_true", help="tanpa konfirmasi")
    args = ap.parse_args()

    cfg = _load_config()
    cfg["cpa_export_enabled"] = True
    paths = _resolve_accounts_args(args.accounts)
    accounts = _parse_accounts(paths)
    if not accounts:
        print("  (kosong) tidak ada baris email----password di file accounts")
        return 1

    out_dir = Path(args.auth_dir).expanduser() if args.auth_dir else _auth_dir(cfg)
    if not out_dir.is_absolute():
        out_dir = (PROJECT / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg["cpa_auth_dir"] = str(out_dir)

    from cpa_xai.accounts import existing_cpa_emails

    existing = existing_cpa_emails(out_dir) if not args.force else set()
    todo = []
    skipped = 0
    for email, pw, sso in accounts:
        if not args.force and email.lower() in existing:
            skipped += 1
            continue
        todo.append((email, pw, sso))
    if args.limit and args.limit > 0:
        todo = todo[: args.limit]

    print(f"  accounts file : {', '.join(str(p) for p in paths)}")
    print(f"  parsed        : {len(accounts)} unik")
    print(f"  skip existing : {skipped}")
    print(f"  will mint     : {len(todo)}")
    print(f"  auth dir      : {out_dir}")
    print(f"  delay         : {args.delay}s")
    if not todo:
        print("  tidak ada yang perlu di-mint (semua sudah ada xai-*.json, atau --force)")
        return 0
    if args.dry_run:
        for i, (email, _, _) in enumerate(todo, 1):
            print(f"  [{i}] {email}")
        return 0
    if not args.yes:
        try:
            ans = input(f"  Mint {len(todo)} akun? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if ans not in ("y", "yes"):
            print("  batal")
            return 1

    # VPS: headed chrome needs DISPLAY (caller should wrap xvfb-run if needed)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("  WARN: DISPLAY kosong — di VPS pakai: xvfb-run -a python scripts/mint_cpa_from_accounts.py ...")

    from cpa_export import export_cpa_xai_for_account

    ok = fail = 0
    for i, (email, password, sso) in enumerate(todo, 1):
        print(f"\n=== [{i}/{len(todo)}] {email} ===", flush=True)

        def _log(msg: str, _email=email) -> None:
            print(f"  {_email}: {msg}", flush=True)

        try:
            result = export_cpa_xai_for_account(
                email,
                password,
                sso=sso or None,
                config=cfg,
                log_callback=_log,
            )
        except Exception as e:  # noqa: BLE001
            result = {"ok": False, "error": str(e)}
            print(f"  FAIL exception: {e}", flush=True)

        if result.get("ok") and result.get("path"):
            ok += 1
            print(f"  OK -> {result.get('path')}", flush=True)
        else:
            fail += 1
            print(f"  FAIL: {result.get('error') or result}", flush=True)

        if i < len(todo) and args.delay > 0:
            print(f"  sleep {args.delay}s ...", flush=True)
            time.sleep(args.delay)

    print(f"\n  selesai: ok={ok} fail={fail} auth_dir={out_dir}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
