# Setup dari nol

Bahasa santai, step by step.

## 1. Clone & venv

```bash
git clone https://github.com/jeyyprtf/grok-auto-register.git
cd grok-auto-register
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Pastikan **Chrome/Chromium** sudah terpasang.

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

Temp mail harus **sudah jalan** dulu → lihat [temp-mail.md](temp-mail.md).

## 3. Test API email (opsional)

```bash
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

Lihat [9router.md](9router.md).

## Tips laptop

- `concurrent_count: 1` — ringan  
- Internet & laptop tetap bisa dipake; cuma ada Chrome tambahan  
- WARP mode **Traffic and DNS (HTTPS)** OK  
- Jangan isi free SOCKS di `proxy` kecuali kamu yakin formatnya HTTP & stabil  
