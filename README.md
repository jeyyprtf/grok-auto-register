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

cp config.example.json config.json
# edit config.json — isi cloudflare_api_base + defaultDomains
```

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

Hasil:

- `accounts_*.txt` — email / password / SSO  
- `cpa_auths/xai-*.json` — credential Grok Build  
- `tokens.txt` — SSO web (bukan buat gcli)

---

## Inject ke 9router

```bash
# laptop
python scripts/inject_cpa_to_9router.py

# VPS (setelah scp folder cpa_auths + script)
python3 scripts/inject_cpa_to_9router.py \
  --auth-dir ~/path/cpa_auths \
  --db ~/.9router/db/data.sqlite
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

Script butuh API temp mail (project [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email)).

Ringkas:

1. Deploy Worker + D1  
2. Email Routing catch-all → Worker  
3. Isi `cloudflare_api_base` + `defaultDomains` di `config.json`

Panduan: [docs/temp-mail.md](docs/temp-mail.md)

---

## Proxy & WARP

| Setup | Rekomendasi |
|--------|-------------|
| 10–20 akun | **WARP on**, `proxy` kosong |
| Free SOCKS list | Sering **gagal** di Chrome/DrissionPage — jangan andalkan |
| Batch besar | Proxy HTTP/S residential berbayar (bukan free list) |

---

## Struktur folder

```text
.
├── grok_register_ttk.py      # main GUI/CLI
├── cpa_export.py / cpa_xai/  # mint Grok Build
├── scripts/
│   └── inject_cpa_to_9router.py
├── docs/                     # panduan Indo
├── config.example.json
├── requirements.txt
└── AGENTS.md                 # catatan agent / setup lokal
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
