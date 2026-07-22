# 9router + Grok Build

Credential dari register tool = file `cpa_auths/xai-email.json`.  
Itu buat **Grok CLI (Grok Build)**, model di 9router: **`gcli/grok-4.5`**.

---

## Install 9router (kalau belum)

```bash
npm i -g 9router
9router
# dashboard: http://localhost:20128
```

Data default: `~/.9router/db/data.sqlite`

---

## Inject credential (tanpa DBeaver)

### Cara gampang — menu TUI (Linux / macOS / Windows)

```bash
python scripts/inject_cpa_to_9router.py
```

Muncul menu:

1. ganti folder CPA  
2. ganti path DB 9router  
3. deteksi DB otomatis  
4. dry-run  
5. inject  
6. list file  

Path terakhir disimpan di `~/.grok_inject_9router.json` (Windows: home user).

### CLI (otomatisasi / script)

```bash
# dry-run
python scripts/inject_cpa_to_9router.py --dry-run --auth-dir ./cpa_auths --db ~/.9router/db/data.sqlite

# inject langsung
python scripts/inject_cpa_to_9router.py -y --auth-dir ./cpa_auths --db ~/.9router/db/data.sqlite
```

Windows PowerShell contoh:

```powershell
python scripts\inject_cpa_to_9router.py
# atau
python scripts\inject_cpa_to_9router.py -y --auth-dir .\cpa_auths --db "$env:USERPROFILE\.9router\db\data.sqlite"
```

### Batch baru (total 20, dll.)

- **Jangan hapus** akun lama di 9router  
- Copy/sync folder `cpa_auths` (semua file)  
- Jalankan inject lagi  

Hasilnya: email baru di-insert, email lama di-update token-nya.

---

## VPS

```bash
# dari laptop
scp -r cpa_auths user@vps:~/grok-account/
scp scripts/inject_cpa_to_9router.py user@vps:~/grok-account/scripts/

# di VPS (SSH, bukan lewat gvfs path aneh)
ssh user@vps
cd ~/grok-account
python3 scripts/inject_cpa_to_9router.py \
  --auth-dir ~/grok-account/cpa_auths \
  --db ~/.9router/db/data.sqlite
```

**Tips:** jalanin inject **di dalam SSH VPS**. Kalau dari mount SFTP/gvfs, path `~` sering ke home laptop, bukan VPS.

---

## Pakai di coding tool

```text
Base URL : http://localhost:20128/v1
           http://IP-VPS:20128/v1
API Key  : dari dashboard 9router (bukan key xAI berbayar)
Model    : gcli/grok-4.5
```

9router bisa round-robin multi akun `grok-cli`.

---

## Bukan grok2api

| Jalur | File | Model / stack |
|--------|------|----------------|
| **Ini** | `cpa_auths/xai-*.json` | `gcli/grok-4.5` Grok Build |
| Lain | `tokens.txt` SSO | grok2api / grok-web |

Jangan campur.

---

## Token expire

Access token ~6 jam. Ada `refresh_token` — 9router biasanya auto-refresh.  
Kalau banyak error auth, inject ulang dari file CPA terbaru.
