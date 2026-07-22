# FAQ (bahasa santai)

## CLI kok buka browser?

Memang. “CLI” = tanpa jendela Tk GUI. Register & Turnstile tetap butuh Chrome beneran.

## Laptop lag / internet mati?

Nggak mati. Cuma ada browser ekstra. `concurrent_count: 1` biasanya ringan. Browsing biasa tetap jalan.

## Proxy di config = ganti IP seluruh laptop?

Nggak. Cuma traffic script/Chrome yang dibuka tool. Chrome kamu, WA, YouTube = IP normal / WARP kamu.

## Free SOCKS di `proxies_alive.txt`?

Sering lelet / error “socks not supported” / gagal ke temp mail.  
Buat batch kecil: **WARP + proxy kosong** lebih waras.

## 1 akun gagal “tidak ada email input”?

Biasa. Refresh/retry. Kadang halaman x.ai aneh sesaat. Lihat log, lanjut batch.

## CPA mint `rate_limited`?

xAI lagi nahan device auth. Tunggu / batch lebih pelan. Kadang tetap sukses setelah retry di log.

## Inject VPS error `unrecognized arguments`?

Jangan ada spasi setelah `\` di bash.  
Contoh salah: `script.py \ --auth-dir`  
Benar: `script.py --auth-dir ...` satu baris, atau `\` di akhir baris tanpa spasi setelahnya.

## Inject ke `~` di gvfs SFTP?

`~` = home mesin yang ngejalanin Python. Kalau Python di laptop, `~` laptop.  
Inject di **SSH VPS** biar `~` = home ubuntu di server.

## Mau nambah 10 akun lagi — hapus yang lama?

**Jangan.** Inject ulang semua file. Lama di-update, baru di-insert.

## Push ke GitHub?

Push ke **fork kamu** (`origin`). Jangan force-push ke `upstream` orang.  
Jangan commit `config.json` / `cpa_auths` / accounts.
