# Temp mail (worker only)

Vendored dari [cloudflare_temp_email](https://github.com/dreamhunter2333/cloudflare_temp_email) — **worker + db** saja.

Lihat `UPSTREAM.txt` untuk pin versi.

## Deploy (manual)

```bash
cd temp-mail/worker
pnpm install
npx wrangler login
npx wrangler d1 create temp-email-db   # catat database_id
# edit wrangler.toml (copy dari wrangler.toml.template)
npx wrangler d1 execute temp-email-db --remote --file=../db/schema.sql
pnpm run deploy
```

Atau pakai TUI monorepo:

```bash
python scripts/manage.py setup
```

`wrangler.toml` (berisi JWT + database_id) **gitignored** — jangan commit.
