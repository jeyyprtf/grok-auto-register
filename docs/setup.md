# Setup dari nol

Bahasa santai, step by step.

## Cara cepat (TUI)

```bash
git clone https://github.com/jeyyprtf/grok-auto-register.git
cd grok-auto-register
python3 scripts/manage.py
```

Menu: pilih **3** untuk auto-install dependency sistem (Node/npm/pnpm, xvfb, Chromium),
lalu **2** untuk membuat `.venv` dan install Python deps. Setelah itu setup temp-mail.

---

## 1. Clone & venv (manual)

```bash
git clone https://github.com/jeyyprtf/grok-auto-register.git
cd grok-auto-register
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Di Linux, menu TUI juga bisa memasang **Chrome/Chromium**, Node/npm/pnpm, dan xvfb
secara otomatis lewat menu **3**.

### Wrangler di VPS tanpa browser

Gunakan API Token, bukan OAuth login dari server. Buat token di
<https://dash.cloudflare.com/profile/api-tokens> dengan izin minimum yang dibutuhkan
Worker/D1 pada account dan zone terkait, lalu jalankan:

```bash
export CLOUDFLARE_API_TOKEN='token-kamu'
python3 scripts/manage.py setup
```

Wizard akan menjalankan `wrangler whoami` untuk memverifikasi token. Token hanya
dipakai dari environment proses dan tidak disimpan ke repo.

## 2. Config

```bash
cp config.example.json config.json
```

Edit minimal:

```json
{
  "email_provider": "cloudflare",
  "cloudflare_api_base": "https://mail-api.domainkamu.com",
  "cloudflare_auth_mode": "none",
  "defaultDomains": "domainkamu.com",
  "register_count": 5,
  "concurrent_count": 1,
  "cpa_export_enabled": true,
  "proxy": "",
  "cpa_proxy": ""
}
```

Temp mail: folder `temp-mail/` di monorepo, atau setup lewat TUI → [temp-mail.md](temp-mail.md).

## 3. Test API email (opsional)

```bash
python scripts/manage.py status
# atau
python cf_mail_debug.py --api-base "https://mail-api.domainkamu.com" --domain "domainkamu.com"
```

Kalau create address OK, lanjut.

## 4. Register

```bash
python grok_register_ttk.py cli
```

Di prompt `>` ketik:

```text
start
```

Browser akan kebuka — biarin. Jangan spam klik.

Stop: `Ctrl+C` (sekali minta stop, dua kali paksa keluar).

## 5. Cek hasil

```bash
ls cpa_auths/
ls accounts_*.txt
```

Ada `xai-....json` = CPA mint sukses.

## 6. Masukin ke 9router

```bash
python scripts/inject_cpa_to_9router.py
```

Muncul **menu TUI** (ganti path CPA / DB, dry-run, inject).  
Detail: [9router.md](9router.md).

## Tips laptop

- `concurrent_count: 1` — ringan  
- Internet & laptop tetap bisa dipake; cuma ada Chrome tambahan  
- WARP mode **Traffic and DNS (HTTPS)** OK  
- Cek `curl https://www.cloudflare.com/cdn-cgi/trace | grep '^warp='` → harus `warp=on`  
- Jangan isi free SOCKS di `proxy` kecuali kamu yakin formatnya HTTP & stabil  

## VPS (SSH only)

Pakai **Xvfb + headed Chrome**, bukan pure headless:

```bash
sudo apt install -y xvfb chromium-browser
# config.json: "browser_vps": true, "browser_headless": false
xvfb-run -a python grok_register_ttk.py cli
```

Panduan: [vps.md](vps.md)
