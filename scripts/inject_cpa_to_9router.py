#!/usr/bin/env python3
"""Inject cpa_auths/xai-*.json into 9router SQLite as grok-cli oauth connections.

Usage:
  python scripts/inject_cpa_to_9router.py
  python scripts/inject_cpa_to_9router.py --auth-dir ./cpa_auths --db ~/.9router/db/data.sqlite
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Inject CPA xai-*.json into 9router DB")
    ap.add_argument(
        "--auth-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "cpa_auths",
        help="Folder containing xai-*.json",
    )
    ap.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".9router" / "db" / "data.sqlite",
        help="Path to 9router data.sqlite",
    )
    ap.add_argument("--dry-run", action="store_true", help="Parse only, no DB write")
    args = ap.parse_args()

    auth_dir = args.auth_dir.expanduser().resolve()
    db_path = args.db.expanduser().resolve()
    files = sorted(auth_dir.glob("xai-*.json"))
    if not files:
        raise SystemExit(f"no xai-*.json in {auth_dir}")
    if not args.dry_run and not db_path.is_file():
        raise SystemExit(f"db not found: {db_path}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    conn = None if args.dry_run else sqlite3.connect(db_path)
    cur = None if args.dry_run else conn.cursor()

    inserted = updated = skipped = 0
    for p in files:
        try:
            cpa = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip {p.name}: {e}")
            skipped += 1
            continue
        email = (cpa.get("email") or "").strip()
        access = cpa.get("access_token")
        refresh = cpa.get("refresh_token")
        if not email or not access or not refresh:
            print(f"skip {p.name}: missing email/access/refresh")
            skipped += 1
            continue

        data = {
            "accessToken": access,
            "refreshToken": refresh,
            "expiresIn": int(cpa.get("expires_in") or 21600),
            "expiresAt": cpa.get("expired") or now,
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
                "importedFrom": str(p),
                "importedAt": now,
            },
        }

        if args.dry_run:
            print(f"dry-run ok: {email}")
            inserted += 1
            continue

        cur.execute(
            "SELECT id FROM providerConnections WHERE provider=? AND email=?",
            ("grok-cli", email),
        )
        row = cur.fetchone()
        payload = json.dumps(data)
        if row:
            cur.execute(
                "UPDATE providerConnections SET authType=?, name=?, isActive=1, data=?, updatedAt=? WHERE id=?",
                ("oauth", email, payload, now, row[0]),
            )
            updated += 1
            print(f"updated {email}")
        else:
            cur.execute(
                "SELECT COALESCE(MAX(priority),0) FROM providerConnections WHERE provider=?",
                ("grok-cli",),
            )
            priority = (cur.fetchone()[0] or 0) + 1
            cid = str(uuid.uuid4())
            cur.execute(
                """INSERT INTO providerConnections
                   (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (cid, "grok-cli", "oauth", email, email, priority, 1, payload, now, now),
            )
            inserted += 1
            print(f"inserted {email}")

    if conn is not None:
        conn.commit()
        cur.execute(
            "SELECT COUNT(*) FROM providerConnections WHERE provider='grok-cli' AND isActive=1"
        )
        active = cur.fetchone()[0]
        conn.close()
    else:
        active = "n/a"

    print(
        f"done inserted={inserted} updated={updated} skipped={skipped} active_grok_cli={active}"
    )


if __name__ == "__main__":
    main()
