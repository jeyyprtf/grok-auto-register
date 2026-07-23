# Grok Auto Register (fullset)

Tool Python buat **auto-daftar akun Grok**, ambil kode dari **temp mail Cloudflare**, mint credential **Grok Build (CPA / xAI)**, terus inject ke **9router** (laptop atau VPS).

> Fork dari project open-source register Grok. Ditambah alur CPA → 9router + panduan temp mail.  
> Pakai buat belajar / testing pribadi. Patuhi ToS xAI & hukum setempat.

---

## Alur singkat

```text
1. Deploy temp mail (Cloudflare Worker + domain)
2. Register akun Grok (script ini + browser Chrome)
3. Dapat file cpa_auths/xai-email.json  (Grok Build)
4. Inject ke 9router → model gcli/grok-4.5
```

**Bukan** jalur grok2api (SSO cookie). Yang dipakai di sini = **Grok CLI / Grok Build**.

---

## Butuh apa

- Python 3.9+ (disarankan 3.12/3.13; 3.14 jalan tapi ada warning)
- Google Chrome / Chromium
- Domain di Cloudflare (buat temp mail)
- [9router](https://github.com/decolua/9router) (opsional, buat pakai model di coding tool)

---

## Install cepat

```bash
git clone https://github.com/jeyyprtf/grok-auto-register.git
cd grok-auto-register

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# TUI all-in-one (setup mail → deps → register → inject)
python scripts/manage.py
```

Atau manual: `cp config.example.json config.json` lalu isi `cloudflare_api_base` + `defaultDomains`.

---

## Config yang penting

| Field | Isi |
|--------|-----|
| `email_provider` | `cloudflare` |
| `cloudflare_api_base` | URL Worker API, mis. `https://mail-api.domainkamu.com` |
| `defaultDomains` | Domain email, mis. `domainkamu.com` |
| `register_count` | Berapa akun per run |
| `concurrent_count` | `1` dulu (aman di laptop) |
| `cpa_export_enabled` | `true` (wajib buat Grok Build) |
| `proxy` / `cpa_proxy` | **Kosong** kalau pakai Cloudflare WARP |

Detail: [docs/setup.md](docs/setup.md)

---

## Jalanin register

```bash
source .venv/bin/activate
python grok_register_ttk.py cli
# ketik: start
# stop: Ctrl+C
```

**VPS Ubuntu SSH-only** (virtual display — recommended):

```bash
sudo apt install -y xvfb chromium-browser
# config: browser_vps true, browser_headless false
xvfb-run -a python grok_register_ttk.py cli
```

Detail: [docs/vps.md](docs/vps.md)

Hasil:

- `accounts_*.txt` — email / password / SSO  
- `cpa_auths/xai-*.json` — credential Grok Build  
- `tokens.txt` — SSO web (bukan buat gcli)

---

## Inject ke 9router

**Menu interaktif** (Linux / Windows / macOS) — tinggal pilih path:

```bash
python scripts/inject_cpa_to_9router.py
```

Atau CLI:

```bash
python scripts/inject_cpa_to_9router.py -y --auth-dir ./cpa_auths --db ~/.9router/db/data.sqlite
```

- Email **baru** → insert  
- Email **sudah ada** → update token  
- **Jangan hapus** akun lama di DB kalau cuma nambah batch baru  

Pakai di client:

```text
Base URL : http://localhost:20128/v1   (atau IP VPS)
API Key  : dari dashboard 9router
Model    : gcli/grok-4.5
```

Detail: [docs/9router.md](docs/9router.md)

---

## Temp mail Cloudflare

Worker **sudah di repo** (`temp-mail/worker` + `temp-mail/db`), dari [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email).

```bash
python scripts/manage.py setup   # domain → D1 → wrangler deploy → update config
```

Untuk clone baru di Linux, jalankan `python scripts/manage.py` lalu pilih menu **3**
(auto-install Node/npm/pnpm, xvfb, Chromium) dan menu **2** (venv + Python deps).
Di VPS tanpa browser, set `CLOUDFLARE_API_TOKEN` sebelum memilih setup Worker;
OAuth Wrangler hanya cocok dijalankan dari laptop.

Masih wajib: Email Routing catch-all di domain → Worker.  
Panduan: [docs/temp-mail.md](docs/temp-mail.md)

---

## Proxy & WARP

| Setup | Rekomendasi |
|--------|-------------|
| 10–20 akun | **WARP on**, `proxy` kosong |
| Free SOCKS list | Sering **gagal** di Chrome/DrissionPage — jangan andalkan |
| Batch besar | Proxy HTTP/S residential berbayar (bukan free list) |

Pastikan WARP benar-benar aktif sebelum run:

```bash
curl https://www.cloudflare.com/cdn-cgi/trace | grep '^warp='
# harus: warp=on
```

---

## Struktur folder

```text
.
├── grok_register_ttk.py      # main GUI/CLI
├── cpa_export.py / cpa_xai/  # mint Grok Build
├── temp-mail/                # Worker CF (worker+db vendored)
├── scripts/
│   ├── manage.py             # TUI setup + run + inject
│   └── inject_cpa_to_9router.py
├── docs/
├── config.example.json
├── requirements.txt
└── AGENTS.md
```

---

## Yang jangan di-commit

- `config.json`  
- `cpa_auths/`  
- `accounts_*.txt`, `tokens.txt`, `mail_credentials.txt`  
- secret / password  

Sudah masuk `.gitignore`.

---

## Docs

| File | Isi |
|------|-----|
| [docs/setup.md](docs/setup.md) | Install & config dari nol |
| [docs/temp-mail.md](docs/temp-mail.md) | Deploy temp mail CF |
| [docs/9router.md](docs/9router.md) | Inject & pakai Grok Build |
| [docs/faq.md](docs/faq.md) | Masalah umum |

---

## License

MIT (lihat [LICENSE](LICENSE)). Upstream original: project grok-register open-source.
