# Catatan project (agent / maintainer)

## Apa ini
Tool register Grok + mint CPA xAI (`xai-*.json`) + inject ke 9router. Bukan grok2api.

## Setup lokal tipikal
- Venv: `.venv/` → `source .venv/bin/activate`
- Run: `python grok_register_ttk.py cli` → `start`
- Config: `config.json` (gitignored), template `config.example.json`
- Temp mail: Worker CF terpisah; isi `cloudflare_api_base` + `defaultDomains`
- WARP OK; biarkan `proxy` / `cpa_proxy` kosong. Free SOCKS list sering gagal di DrissionPage.

## VPS / headless
- **Bukan** pure-API: tetap Chromium (DrissionPage)
- Recommended: `browser_vps: true` + `xvfb-run -a python grok_register_ttk.py cli` (headed di virtual display)
- `browser_headless: true` = true headless; CF/Turnstile fragile — last resort
- Auto VPS flags bila Linux tanpa `DISPLAY`/`WAYLAND_DISPLAY`
- Docs: `docs/vps.md`

## CPA → 9router
- Output: `cpa_auths/xai-<email>.json` jika `cpa_export_enabled: true`
- Injector: `scripts/inject_cpa_to_9router.py`
  - **TUI default** (tanpa flag): menu interaktif pilih auth-dir / DB / dry-run / inject
  - CLI: `--auth-dir` `--db` `--dry-run` `-y` / `--yes` `--tui`
  - Cross-platform (Linux / Windows / macOS), stdlib only
  - State path terakhir: `~/.grok_inject_9router.json`
  - Deteksi DB: `~/.9router/db/data.sqlite`, Windows `%APPDATA%\9router\...`
- Upsert by email; re-run = insert baru + update lama. Jangan hapus akun lama.
- Model: `gcli/grok-4.5` via `http://HOST:20128/v1`

## Docs user
- `README.md` + `docs/*.md` (Bahasa Indonesia)
  - `docs/setup.md`, `docs/temp-mail.md`, `docs/9router.md` (TUI + PowerShell), `docs/faq.md`

## Fullset (keputusan arsitektur)
- Monorepo **tooling**: register + CPA + inject + docs
- Temp mail **tidak** di-nest di repo; deploy terpisah (cloudflare_temp_email), URL di config

## Remote
- `origin` = https://github.com/jeyyprtf/grok-auto-register.git (push di sini)
- `upstream` = https://github.com/maxucheng0/grok-auto-register.git (baca / PR opsional)

## Yang jangan di-commit
config.json, cpa_auths/, accounts_*.txt, tokens.txt, proxies_alive.txt, log, .wrangler/, secret
