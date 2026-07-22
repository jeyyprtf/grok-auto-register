# Register di VPS (SSH only, Ubuntu)

Register **tetap butuh Chromium**. Bukan pure-API. Di VPS tanpa monitor: pakai **Xvfb** (virtual display) + headed Chrome.

## 1. Install di Ubuntu

```bash
sudo apt update
sudo apt install -y xvfb chromium-browser fonts-liberation
# atau: google-chrome-stable (repo Google)

cd /path/ke/grok-auto-register
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
# edit cloudflare_api_base + defaultDomains
```

## 2. Config VPS

```json
{
  "browser_vps": true,
  "browser_headless": false,
  "cpa_headless": false,
  "proxy": "",
  "cpa_proxy": "",
  "concurrent_count": 1
}
```

| Key | Arti |
|-----|------|
| `browser_vps` | Flag VPS: `--no-sandbox`, path Chromium Linux, dll. Auto-on juga kalau Linux **tanpa** `DISPLAY` |
| `browser_headless` | True headless Chromium. **Rentan** CF/Turnstile — last resort |
| `cpa_headless` | Sama, cuma path mint CPA standalone |

**Rekomendasi:** `browser_vps: true`, `browser_headless: false`, jalanin lewat **xvfb-run**.

## 3. Jalanin

```bash
source .venv/bin/activate
xvfb-run -a python grok_register_ttk.py cli
# ketik: start
```

Log bagus kira-kira:

```text
[*] browser mode=headed vps=True DISPLAY=':99'
```

Tanpa Xvfb + tanpa headless → warning `no DISPLAY` di log.

## 4. True headless (opsional, fragile)

Kalau Xvfb tidak bisa:

```json
{
  "browser_vps": true,
  "browser_headless": true,
  "cpa_headless": true
}
```

```bash
python grok_register_ttk.py cli
```

Kalau CF block / Turnstile gagal → balik ke Xvfb + headed.

## 5. Inject 9router di VPS

```bash
python scripts/inject_cpa_to_9router.py -y \
  --auth-dir ./cpa_auths \
  --db ~/.9router/db/data.sqlite
```

Atau TUI: `python scripts/inject_cpa_to_9router.py`

## Tips

- IP datacenter sering kena CF lebih keras — residential / WARP (kalau tersedia di VPS) lebih baik
- `concurrent_count: 1` dulu
- Free SOCKS list: jangan
- RAM: Chromium + Xvfb ~0.5–1 GB per worker
