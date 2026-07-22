# Temp mail Cloudflare (simpel)

Script register butuh inbox buat kode verifikasi Grok. Sumber: [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) — **worker+db sudah di monorepo** folder `temp-mail/`.

---

## Cara termudah (TUI)

```bash
python scripts/manage.py
# menu 1) Setup temp-mail Worker
```

Atau: `python scripts/manage.py setup`

---

## Yang kamu butuh

1. Domain di Cloudflare (DNS active)  
2. Akun Cloudflare (wrangler login OK)  
3. Node/pnpm buat deploy Worker  

---

## Step kasar (CLI manual)

```bash
cd temp-mail/worker
pnpm install

# buat D1
npx wrangler d1 create temp-email-db
# catat database_id

# schema
npx wrangler d1 execute temp-email-db --remote --file=../db/schema.sql

cp wrangler.toml.template wrangler.toml
```

Isi `wrangler.toml` kira-kira:

```toml
name = "cloudflare_temp_email"
main = "src/worker.ts"
compatibility_date = "2025-04-01"
compatibility_flags = [ "nodejs_compat" ]

routes = [
  { pattern = "mail-api.domainkamu.com", custom_domain = true },
]

[vars]
PREFIX = "tmp"
DEFAULT_DOMAINS = ["domainkamu.com"]
DOMAINS = ["domainkamu.com"]
JWT_SECRET = "acak-panjang-pakai-openssl-rand-hex-32"
ENABLE_USER_CREATE_EMAIL = true
ENABLE_USER_DELETE_EMAIL = true

[[d1_databases]]
binding = "DB"
database_name = "temp-email-db"
database_id = "UUID-DARI-CREATE"
```

Deploy:

```bash
pnpm run deploy
```

Cek:

```bash
curl https://mail-api.domainkamu.com/health_check
# harus: OK
```

---

## Email Routing (wajib biar email masuk)

Di dashboard Cloudflare → domain kamu:

1. **Email** → **Email Routing** → Enable  
2. DNS records email (MX/TXT) ikut terpasang  
3. **Catch-all** → kirim ke Worker **`cloudflare_temp_email`**  

Tanpa catch-all, API create address jalan tapi **kode verifikasi Grok nggak pernah nyampe**.

---

## Sambungin ke register tool

Di `config.json` project ini:

```json
{
  "email_provider": "cloudflare",
  "cloudflare_api_base": "https://mail-api.domainkamu.com",
  "cloudflare_auth_mode": "none",
  "defaultDomains": "domainkamu.com"
}
```

Docs resmi lebih lengkap: https://temp-mail-docs.awsl.uk

---

## Admin mode (opsional)

Kalau create address anonymous kena Turnstile, pakai admin path + password.  
Lihat README upstream / `config.example.json` field `cloudflare_auth_mode` + `x-admin-auth`.
