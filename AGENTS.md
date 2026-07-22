# Catatan project (agent / maintainer)

## Apa ini
Tool register Grok + mint CPA xAI (`xai-*.json`) + inject ke 9router. Bukan grok2api.

## Setup lokal tipikal
- Venv: `.venv/` → `source .venv/bin/activate`
- Run: `python grok_register_ttk.py cli` → `start`
- Config: `config.json` (gitignored), template `config.example.json`
- Temp mail: Worker CF terpisah; isi `cloudflare_api_base` + `defaultDomains`
- WARP OK; biarkan `proxy` / `cpa_proxy` kosong. Free SOCKS list sering gagal di DrissionPage.

## CPA → 9router
- Output: `cpa_auths/xai-<email>.json` jika `cpa_export_enabled: true`
- Injector: `scripts/inject_cpa_to_9router.py`
- Upsert by email; re-run = insert baru + update lama. Jangan hapus akun lama.
- Model: `gcli/grok-4.5` via `http://HOST:20128/v1`

## Docs user
- `README.md` + `docs/*.md` (Bahasa Indonesia)

## Remote
- `origin` = fork maintainer (push di sini)
- `upstream` = repo sumber (baca / PR opsional)
