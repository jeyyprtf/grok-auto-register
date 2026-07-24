# Catatan project (agent / maintainer)

## Apa ini
Monorepo tooling: **temp-mail Worker** + **register Grok** + **mint CPA xAI** + **inject 9router**. Bukan grok2api.

## Setup lokal tipikal
- Venv: `.venv/` → `source .venv/bin/activate`
- **TUI all-in-one:** `python scripts/manage.py` (setup mail → deps → run → inject)
- Run manual: `python grok_register_ttk.py cli` → `start`
- Config: `config.json` (gitignored), template `config.example.json`
- Temp mail: folder `temp-mail/` (worker+db vendored); URL di `cloudflare_api_base` + `defaultDomains`
- WARP OK; biarkan `proxy` / `cpa_proxy` kosong. Free SOCKS list sering gagal di DrissionPage.

## VPS / headless
- **Bukan** pure-API: tetap Chromium (DrissionPage)
- Recommended: `browser_vps: true` + `xvfb-run -a python grok_register_ttk.py cli` (atau menu manage → xvfb)
- `browser_headless: true` = true headless; CF/Turnstile fragile — last resort
- Auto VPS flags bila Linux tanpa `DISPLAY`/`WAYLAND_DISPLAY`
- Docs: `docs/vps.md`

## CPA → 9router
- Durable: `accounts_*.txt` = `email----password----sso` (bukan OAuth token)
- OAuth CPA (`cpa_auths/xai-*.json`) short-lived — mint saat mau pakai, jangan stockpile
- Split workflow (recommended):
  1. register (`cpa_export_enabled: false`) → `accounts_*.txt`
  2. `python scripts/mint_cpa_from_accounts.py` (atau manage menu 7) → `cpa_auths/`
  3. inject 9router (manage menu 8)
- Output mint: `cpa_auths/xai-<email>.json` (juga bisa on-register jika `cpa_export_enabled: true`)
- Injector: `scripts/inject_cpa_to_9router.py` (tetap terpisah, stdlib)
  - **TUI default** (tanpa flag): menu interaktif
  - CLI: `--auth-dir` `--db` `--dry-run` `-y` / `--yes` `--tui`
  - Deteksi DB: `~/.9router/db/data.sqlite`, Windows `%APPDATA%\9router\...`, env `NINEROUTER_DB`
  - Deteksi auth: `./cpa_auths`, env `GROK_CPA_AUTH_DIR`
  - State: `~/.grok_inject_9router.json`
- Upsert by email; re-run = insert baru + update lama. Jangan hapus akun lama.
- Model: `gcli/grok-4.5` via `http://HOST:20128/v1`

## Docs user
- `README.md` + `docs/*.md` (Bahasa Indonesia)
  - `docs/setup.md`, `docs/temp-mail.md`, `docs/9router.md`, `docs/faq.md`

## Fullset (arsitektur)
- Monorepo: register + CPA + inject + **temp-mail/worker+db** + docs
- Worker: vendored dari cloudflare_temp_email (pin di `temp-mail/UPSTREAM.txt`)
- `temp-mail/worker/wrangler.toml` **gitignored** (JWT + database_id)
- Deploy Worker butuh Node/pnpm + `wrangler login` (bisa dari laptop; VPS cuma butuh API URL di config)

## Remote
- `origin` = https://github.com/jeyyprtf/grok-auto-register.git (push di sini)
- `upstream` = https://github.com/maxucheng0/grok-auto-register.git (baca / PR opsional)

## Yang jangan di-commit
config.json, cpa_auths/, accounts_*.txt, tokens.txt, proxies_alive.txt, log, .wrangler/, temp-mail/worker/wrangler.toml, node_modules, secret
