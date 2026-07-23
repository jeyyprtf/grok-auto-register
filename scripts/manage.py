#!/usr/bin/env python3
"""TUI setup + manage fullset: temp-mail Worker, register Grok, inject 9router.

Stdlib only. Cross-platform (Linux / macOS / Windows).

  python scripts/manage.py          # menu
  python scripts/manage.py setup    # wizard setup
  python scripts/manage.py run      # register (pakai config)
  python scripts/manage.py inject   # inject TUI
"""
from __future__ import annotations

import getpass
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "config.json"
CONFIG_EXAMPLE = PROJECT / "config.example.json"
TEMP_MAIL = PROJECT / "temp-mail"
WORKER = TEMP_MAIL / "worker"
DB_SCHEMA = TEMP_MAIL / "db" / "schema.sql"
WRANGLER_TOML = WORKER / "wrangler.toml"
WRANGLER_TEMPLATE = WORKER / "wrangler.toml.template"
STATE_FILE = Path.home() / ".grok_manage.json"
INJECT_SCRIPT = PROJECT / "scripts" / "inject_cpa_to_9router.py"


# ── helpers ──────────────────────────────────────────────────────────


def prompt(msg: str, default: str = "") -> str:
    if default:
        raw = input(f"{msg} [{default}]: ").strip()
        return raw if raw else default
    return input(f"{msg}: ").strip()


def pause() -> None:
    try:
        input("\nEnter buat lanjut...")
    except EOFError:
        pass


def yn(msg: str, default: bool = False) -> bool:
    d = "Y/n" if default else "y/N"
    raw = input(f"{msg} [{d}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "ya")


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def wrangler_args(tools: dict, *args: str) -> list[str]:
    if tools["pnpm"]:
        return [tools["pnpm"], "exec", "wrangler", *args]
    return ["npx", "wrangler", *args]


def print_api_token_guide(domain: str) -> None:
    print("\n  --- Panduan API Token (server/VPS) ---")
    print("  1) Buka https://dash.cloudflare.com/profile/api-tokens")
    print("  2) Pilih Create Custom Token")
    print("  3) Tambahkan permission Account (Edit):")
    print("       Workers Scripts → Edit")
    print("       D1 → Edit")
    print("  4) Account Resources: Include hanya account yang dipakai")
    print(f"  5) Tambahkan permission Zone untuk {domain}:")
    print("       Workers Routes → Edit")
    print("       Zone → Read")
    print("  6) DNS → Edit hanya jika Wrangler perlu mengubah DNS custom domain")
    print("  7) Buat token, lalu paste saat diminta (token tidak disimpan ke file).")


def check_wrangler_login(tools: dict, domain: str = "example.com") -> bool:
    print("\n  Metode autentikasi Wrangler:")
    print("    1) OAuth browser (laptop / ada browser)")
    print("    2) API Token (server/VPS tanpa browser)")
    default = "2" if is_linux() and not has_display() else "1"
    mode = prompt("Pilih metode", default)

    if mode == "2":
        print_api_token_guide(domain)
        if not os.environ.get("CLOUDFLARE_API_TOKEN"):
            token = getpass.getpass("  CLOUDFLARE_API_TOKEN (hidden): ").strip()
            if token:
                os.environ["CLOUDFLARE_API_TOKEN"] = token
        else:
            print("  CLOUDFLARE_API_TOKEN sudah ada di environment.")
        if not os.environ.get("CLOUDFLARE_API_TOKEN"):
            print("  Token kosong; setup dibatalkan.")
            return False
        result = run(wrangler_args(tools, "whoami"), cwd=WORKER)
        if result.returncode != 0:
            print("  Token tidak valid atau permission kurang; setup dibatalkan.")
            return False
        return True

    if is_linux() and not has_display():
        print("  OAuth membutuhkan browser. Pilih mode 2 untuk server/VPS.")
        return False
    login = run(wrangler_args(tools, "login"), cwd=WORKER)
    if login.returncode != 0:
        print("  Login OAuth gagal; setup dibatalkan.")
        return False
    verified = run(wrangler_args(tools, "whoami"), cwd=WORKER)
    if verified.returncode != 0:
        print("  Login belum terverifikasi; setup dibatalkan.")
        return False
    return True


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config() -> dict:
    if not CONFIG.is_file():
        return {}
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"config.json tidak valid ({CONFIG}): {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"config.json harus berisi JSON object: {CONFIG}")
    return data


def save_config(cfg: dict) -> None:
    save_json(CONFIG, cfg)


def load_state() -> dict:
    return load_json(STATE_FILE)


def save_state(st: dict) -> None:
    try:
        save_json(STATE_FILE, st)
        STATE_FILE.chmod(0o600)
    except Exception:
        pass


_UA = "grok-manage/1.0 (+https://github.com/jeyyprtf/grok-auto-register)"


def http_get(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except Exception as e:
        return 0, str(e)


def http_post_json(url: str, payload: dict, timeout: int = 20) -> tuple[int, str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": _UA},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except Exception as e:
        return 0, str(e)


def has_display() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def is_linux() -> bool:
    return sys.platform.startswith("linux")


# ── status checks ────────────────────────────────────────────────────


def project_python() -> str:
    name = "python.exe" if sys.platform == "win32" else "python"
    candidate = PROJECT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin") / name
    return str(candidate) if candidate.is_file() else sys.executable


def check_python_deps() -> list[str]:
    modules = ("requests", "DrissionPage", "curl_cffi")
    script = (
        "import importlib, json\n"
        f"mods={modules!r}\n"
        "missing=[]\n"
        "for mod in mods:\n"
        " try: importlib.import_module(mod)\n"
        " except Exception: missing.append(mod)\n"
        "print(json.dumps(missing))\n"
    )
    try:
        result = subprocess.run(
            [project_python(), "-c", script], capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        return list(modules)


def check_tools() -> dict:
    return {
        "python": project_python(),
        "node": which("node"),
        "pnpm": which("pnpm"),
        "npx": which("npx"),
        "wrangler": which("wrangler"),
        "xvfb-run": which("xvfb-run"),
        "chrome": which("google-chrome") or which("google-chrome-stable") or which("chromium") or which("chromium-browser"),
    }


def print_status() -> None:
    cfg = load_config()
    tools = check_tools()
    missing = check_python_deps()
    api = (cfg.get("cloudflare_api_base") or "").rstrip("/")
    domain = cfg.get("defaultDomains") or ""
    print()
    print("=" * 56)
    print("  Grok fullset — status")
    print("=" * 56)
    print(f"  Project     : {PROJECT}")
    print(f"  config.json : {'ada' if CONFIG.is_file() else 'BELUM (copy dari example)'}")
    print(f"  API base    : {api or '(kosong)'}")
    print(f"  Domain email: {domain or '(kosong)'}")
    print(f"  register_count / concurrent: {cfg.get('register_count', '?')} / {cfg.get('concurrent_count', '?')}")
    print(f"  browser_vps / headless: {cfg.get('browser_vps')} / {cfg.get('browser_headless')}")
    print(f"  cpa_export  : {cfg.get('cpa_export_enabled')}")
    print(f"  temp-mail/  : {'ada' if WORKER.is_dir() else 'HILANG'}")
    print(f"  wrangler.toml: {'ada' if WRANGLER_TOML.is_file() else 'belum (setup dulu)'}")
    print(f"  node/pnpm   : {bool(tools['node'])} / {bool(tools['pnpm'] or tools['npx'])}")
    print(f"  xvfb-run    : {bool(tools['xvfb-run'])}  chrome: {bool(tools['chrome'])}")
    print(f"  DISPLAY     : {os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY') or '(none)'}")
    print(f"  pip deps    : {'OK' if not missing else 'kurang: ' + ', '.join(missing)}")
    if api:
        code, body = http_get(f"{api}/health_check")
        ok = code == 200 and "OK" in (body or "").upper()
        print(f"  API health  : {'OK' if ok else f'FAIL ({code}) {body[:60]}'}")
    print()


# ── temp-mail setup ──────────────────────────────────────────────────


def ensure_wrangler_toml(domain: str, api_host: str, database_id: str) -> None:
    """Write minimal wrangler.toml from template + user values."""
    # ponytail: minimal vars only; full template stays for advanced users
    content = f'''name = "cloudflare_temp_email"
main = "src/worker.ts"
compatibility_date = "2025-04-01"
compatibility_flags = [ "nodejs_compat" ]
keep_vars = false

routes = [
  {{ pattern = "{api_host}", custom_domain = true }},
]

[vars]
PREFIX = "tmp"
DEFAULT_DOMAINS = ["{domain}"]
DOMAINS = ["{domain}"]
ENABLE_USER_CREATE_EMAIL = true
ENABLE_USER_DELETE_EMAIL = true
ENABLE_AUTO_REPLY = false
BLACK_LIST = ""

[[d1_databases]]
binding = "DB"
database_name = "temp-email-db"
database_id = "{database_id}"

[[ratelimits]]
name = "RATE_LIMITER"
namespace_id = "1001"

  [ratelimits.simple]
  limit = 30
  period = 60
'''
    WRANGLER_TOML.write_text(content, encoding="utf-8")
    print(f"  tulis {WRANGLER_TOML}")


def parse_d1_create_output(text: str) -> str | None:
    # database_id = "uuid" or database_id = 'uuid'
    m = re.search(r"database_id\s*=\s*[\"']([0-9a-fA-F-]{30,})[\"']", text)
    if m:
        return m.group(1)
    m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", text)
    return m.group(1) if m else None


def list_d1_databases(tools: dict) -> list[dict] | None:
    result = subprocess.run(
        wrangler_args(tools, "d1", "list", "--json"),
        cwd=str(WORKER), capture_output=True, text=True,
    )
    if result.returncode != 0:
        print((result.stdout or "") + (result.stderr or ""))
        return None
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else []


def d1_id(entry: dict) -> str:
    return str(entry.get("uuid") or entry.get("database_id") or entry.get("id") or "")


def cmd_setup_temp_mail() -> None:
    print()
    print("--- Setup temp-mail Worker (Cloudflare) ---")
    if not WORKER.is_dir():
        print(f"  Folder {WORKER} tidak ada. Clone monorepo lengkap / restore temp-mail/.")
        return

    tools = check_tools()
    if not tools["node"]:
        print("  Node.js belum ada.")
        if not (is_linux() and yn("Auto-install dependency sistem sekarang?", True)):
            print("  Install Node.js + npm lalu ulangi setup.")
            return
        cmd_install_system()
        tools = check_tools()
        if not tools["node"]:
            return
    if not tools["pnpm"] and not tools["npx"]:
        npm = which("npm")
        if npm and yn("pnpm belum ada. Install pnpm sekarang?", True):
            if run([npm, "install", "-g", "pnpm"]).returncode == 0:
                tools = check_tools()
        if not tools["pnpm"] and not tools["npx"]:
            print("  pnpm/npm tidak tersedia; ulangi setelah dependency terpasang.")
            return

    domain = prompt("Domain email (xxx@DOMAIN)", load_config().get("defaultDomains") or "example.com")
    domain = domain.strip().lstrip("@")
    default_api = f"mail-api.{domain}"
    api_host = prompt("Hostname API Worker (custom domain)", default_api).strip()
    api_host = re.sub(r"^https?://", "", api_host).rstrip("/")

    print()
    print("  Pastikan di Cloudflare dashboard:")
    print(f"    1) Domain {domain} sudah di CF (DNS active)")
    print(f"    2) Nanti: Email Routing ON + catch-all → Worker cloudflare_temp_email")
    print(f"    3) Custom domain API: {api_host} (Worker route)")
    if not yn("Lanjut deploy?", True):
        return

    # pnpm install
    print("\n[1/5] pnpm install di temp-mail/worker ...")
    pnpm = tools["pnpm"] or "pnpm"
    if not tools["pnpm"]:
        # try corepack / npx
        if tools["npx"]:
            r = run(["npx", "pnpm", "install"], cwd=WORKER)
        else:
            print("  pnpm tidak ada")
            return
    else:
        r = run([pnpm, "install"], cwd=WORKER)
    if r.returncode != 0:
        print("  pnpm install gagal")
        return

    # wrangler whoami
    print("\n[2/5] Cek login Cloudflare (wrangler whoami) ...")
    if not check_wrangler_login(tools, domain):
        return

    # D1
    print("\n[3/5] D1 database ...")
    database_id = ""
    d1_list = list_d1_databases(tools)
    if d1_list is None:
        print("  Daftar D1 tidak dapat diverifikasi. Pastikan token punya permission D1 Edit.")
        return
    named_d1 = next((entry for entry in d1_list if entry.get("name") == "temp-email-db"), None)
    if named_d1:
        database_id = d1_id(named_d1)
        print(f"  pakai D1 temp-email-db: {database_id}")
    if not database_id:
        if yn("Buat D1 baru (temp-email-db)?", True):
            r = subprocess.run(
                wrangler_args(tools, "d1", "create", "temp-email-db"),
                cwd=str(WORKER), capture_output=True, text=True,
            )
            out = (r.stdout or "") + (r.stderr or "")
            print(out)
            database_id = parse_d1_create_output(out) or ""
            if not database_id:
                print("  D1 gagal dibuat; jangan gunakan Account ID sebagai database_id.")
                return
        else:
            database_id = prompt("database_id UUID existing")
            if d1_list is not None and database_id not in {d1_id(entry) for entry in d1_list}:
                print("  database_id tidak ditemukan di akun Cloudflare; setup dibatalkan")
                return
    if not database_id:
        print("  database_id kosong, batal")
        return

    state = load_state()
    jwt = str(state.get("worker_jwt_secret") or "")
    if WRANGLER_TOML.is_file():
        match = re.search(r'JWT_SECRET\s*=\s*"([^"]+)"', WRANGLER_TOML.read_text(encoding="utf-8"))
        jwt = jwt or (match.group(1) if match else "")
    jwt = jwt or secrets.token_hex(32)
    state["worker_jwt_secret"] = jwt
    save_state(state)
    ensure_wrangler_toml(domain, api_host, database_id)

    # schema
    print("\n[4/5] Apply schema D1 remote ...")
    if not DB_SCHEMA.is_file():
        print(f"  schema tidak ada: {DB_SCHEMA}")
        return
    schema_rel = os.path.relpath(DB_SCHEMA, WORKER)
    r = run(wrangler_args(tools, "d1", "execute", "temp-email-db", "--remote", "--yes", f"--file={schema_rel}"), cwd=WORKER)
    if r.returncode != 0:
        print("  schema execute gagal; deploy dibatalkan supaya tidak menghasilkan Worker rusak")
        return

    # deploy
    print("\n[5/5] Deploy Worker ...")
    r = run([pnpm, "run", "deploy"] if tools["pnpm"] else ["npx", "wrangler", "deploy", "--minify"], cwd=WORKER)
    if r.returncode != 0:
        print("  deploy gagal — coba ulang: cd temp-mail/worker && pnpm run deploy")
        return

    print("\n  Simpan JWT_SECRET sebagai Worker secret ...")
    secret_cmd = wrangler_args(tools, "secret", "put", "JWT_SECRET")
    secret_result = subprocess.run(
        secret_cmd,
        cwd=str(WORKER),
        input=jwt + "\n",
        text=True,
    )
    if secret_result.returncode != 0:
        print("  gagal menyimpan JWT_SECRET; deploy belum siap dipakai")
        return

    api_base = f"https://{api_host}"
    print("\n  Cek health ...")
    code, body = http_get(f"{api_base}/health_check")
    print(f"  GET {api_base}/health_check → {code} {body[:40]}")

    # config.json
    cfg = load_config()
    if not cfg and CONFIG_EXAMPLE.is_file():
        cfg = load_json(CONFIG_EXAMPLE)
    cfg["email_provider"] = "cloudflare"
    cfg["cloudflare_api_base"] = api_base
    cfg["defaultDomains"] = domain
    cfg["cloudflare_auth_mode"] = cfg.get("cloudflare_auth_mode") or "none"
    save_config(cfg)
    print(f"  config.json di-update: api={api_base} domain={domain}")

    print()
    print("  WAJIB di dashboard Cloudflare (domain email):")
    print(f"    Email → Email Routing → Enable")
    print(f"    Catch-all → Worker cloudflare_temp_email")
    print()
    if yn("Test create address sekarang?", True):
        code, body = http_post_json(f"{api_base}/api/new_address", {"domain": domain})
        print(f"  create → {code} {body[:120]}")
        if code == 200:
            print("  OK — email bisa dibuat. Catch-all tetap harus ON biar OTP masuk.")
    st = load_state()
    st["domain"] = domain
    st["api_base"] = api_base
    save_state(st)


def cmd_check_mail() -> None:
    cfg = load_config()
    api = (cfg.get("cloudflare_api_base") or "").rstrip("/")
    domain = (cfg.get("defaultDomains") or "").split(",")[0].strip()
    if not api:
        print("  cloudflare_api_base kosong — setup dulu")
        return
    code, body = http_get(f"{api}/health_check")
    print(f"  health: {code} {body[:60]}")
    if domain:
        code, body = http_post_json(f"{api}/api/new_address", {"domain": domain})
        print(f"  create @{domain}: {code} {body[:160]}")


# ── python / system deps ─────────────────────────────────────────────


def cmd_install_python() -> None:
    venv = PROJECT / ".venv"
    py = sys.executable
    if not venv.is_dir():
        print("  buat .venv ...")
        run([py, "-m", "venv", str(venv)])
    pip = venv / ("Scripts" if sys.platform == "win32" else "bin") / "pip"
    if not pip.is_file():
        pip = Path(which("pip") or "pip")
    run([str(pip), "install", "-r", str(PROJECT / "requirements.txt")], cwd=PROJECT)
    missing = check_python_deps()
    print(f"  deps: {'OK' if not missing else 'masih kurang: ' + ', '.join(missing)}")
    print(f"  activate: source {venv}/bin/activate" if not sys.platform == "win32" else f"  {venv}\\Scripts\\activate")


def cmd_install_system() -> None:
    """Install the small set of system tools needed by the VPS workflow."""
    if not is_linux():
        print("  Auto-install hanya tersedia untuk Linux; gunakan package manager OS ini.")
        return
    apt = which("apt-get")
    if not apt:
        print("  apt-get tidak ditemukan; install nodejs, npm, xvfb, dan chromium manual.")
        return
    prefix = [] if os.geteuid() == 0 else ([which("sudo")] if which("sudo") else None)
    if prefix is None:
        print("  Butuh root atau sudo untuk install paket sistem.")
        return
    packages = ["nodejs", "npm", "xvfb", "fonts-liberation"]
    apt_cache = which("apt-cache")
    if apt_cache and subprocess.run([apt_cache, "show", "chromium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        packages.append("chromium")
    elif apt_cache and subprocess.run([apt_cache, "show", "chromium-browser"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        packages.append("chromium-browser")
    print("  Install paket sistem: " + ", ".join(packages))
    if not yn("Lanjut?", True):
        return
    if run(prefix + [apt, "update"]).returncode != 0:
        return
    if run(prefix + [apt, "install", "-y", *packages]).returncode != 0:
        return
    npm = which("npm") or "/usr/bin/npm"
    if run([npm, "install", "-g", "pnpm"]).returncode != 0:
        print("  pnpm gagal di-install; jalankan npm install -g pnpm setelah memperbaiki npm.")
    print("  Dependensi sistem selesai. Wrangler login akan ditawarkan saat setup Worker.")


def cmd_hint_system() -> None:
    print()
    print("  Pilih menu ini untuk auto-install Linux (nodejs, npm, pnpm, xvfb, chromium).")
    print("  Wrangler login dijalankan interaktif dari menu Setup Worker.")


# ── register run ─────────────────────────────────────────────────────


def cmd_configure_run() -> dict:
    cfg = load_config()
    if not cfg:
        print("  config.json kosong — jalankan setup / copy config.example.json")
        return cfg
    print()
    print("--- Konfigurasi run ---")
    n = prompt("Berapa akun (register_count)", str(cfg.get("register_count", 1)))
    try:
        cfg["register_count"] = max(1, int(n))
    except ValueError:
        pass
    c = prompt("Concurrent", str(cfg.get("concurrent_count", 1)))
    try:
        cfg["concurrent_count"] = max(1, int(c))
    except ValueError:
        pass

    print("  Mode browser:")
    print("    1) headed (ada display / lokal)")
    print("    2) xvfb (VPS, recommended)")
    mode = prompt("Pilih", "2" if is_linux() and not has_display() else "1")
    mode = "2" if mode == "2" else "1"
    if mode == "2":
        cfg["browser_headless"] = False
        cfg["browser_vps"] = True
        cfg["cpa_headless"] = False
    else:
        cfg["browser_headless"] = False
        cfg["browser_vps"] = False
        cfg["cpa_headless"] = False

    auto_inject = yn("Auto inject ke 9router setelah register?", False)
    cfg["cpa_export_enabled"] = True if auto_inject or cfg.get("cpa_export_enabled", True) else cfg.get("cpa_export_enabled", True)

    st = load_state()
    st["auto_inject"] = auto_inject
    st["browser_mode"] = mode
    save_state(st)
    save_config(cfg)
    print("  config disimpan.")
    return cfg


def cmd_run_register() -> None:
    cfg = load_config()
    if not CONFIG.is_file():
        print("  Belum ada config.json — setup dulu")
        return
    missing = check_python_deps()
    if missing:
        print(f"  pip deps kurang: {missing}")
        if yn("Install requirements sekarang?", True):
            cmd_install_python()
        else:
            return

    st = load_state()
    if st.get("browser_mode") not in ("1", "2"):
        cfg = cmd_configure_run()
        st = load_state()

    mode = st.get("browser_mode") or ("2" if is_linux() and not has_display() else "1")
    use_xvfb = mode == "2" or (is_linux() and not has_display() and not cfg.get("browser_headless"))

    tools = check_tools()
    if not tools["chrome"]:
        print("  Browser Chrome/Chromium belum terpasang.")
        if is_linux() and yn("Auto-install browser sekarang?", True):
            cmd_install_system()
            tools = check_tools()
        if not tools["chrome"]:
            print("  Install Chromium lalu ulangi menu 6:")
            print("    sudo apt update && sudo apt install -y chromium")
            return
    if use_xvfb and not tools["xvfb-run"]:
        print("  xvfb-run tidak ada. Pilih menu 3 atau install: sudo apt install -y xvfb")
        return

    cmd = [project_python(), str(PROJECT / "grok_register_ttk.py"), "cli"]
    if use_xvfb:
        cmd = ["xvfb-run", "-a"] + cmd

    print()
    print(f"  Jalankan: {' '.join(cmd)}")
    print("  Di prompt ketik: start")
    print("  Stop: Ctrl+C")
    print()
    # feed start automatically if user wants
    if yn("Auto-ketik 'start'?", True):
        env = os.environ.copy()
        p = subprocess.Popen(
            cmd,
            cwd=str(PROJECT),
            stdin=subprocess.PIPE,
            env=env,
            text=True,
        )
        try:
            p.communicate(input="start\n")
        except KeyboardInterrupt:
            p.send_signal(2)
            p.wait()
    else:
        run(cmd, cwd=PROJECT)

    if st.get("auto_inject"):
        print("\n  Auto inject ...")
        cmd_inject(tui=False)


def cmd_inject(tui: bool = True) -> None:
    if not INJECT_SCRIPT.is_file():
        print(f"  script hilang: {INJECT_SCRIPT}")
        return
    args = [sys.executable, str(INJECT_SCRIPT)]
    if not tui:
        args += ["--dry-run"] if yn("Dry-run dulu?", False) else ["-y"]
    run(args, cwd=PROJECT)


# ── main menu ────────────────────────────────────────────────────────


def menu() -> int:
    while True:
        print_status()
        print("  SETUP")
        print("    1) Setup temp-mail Worker (domain → wrangler → deploy)")
        print("    2) Install Python deps (.venv + requirements)")
        print("    3) Auto-install system deps (node / pnpm / xvfb / chromium)")
        print("    4) Cek API temp-mail (health + create address)")
        print()
        print("  RUN")
        print("    5) Configure run (jumlah akun, headed/xvfb, auto-inject)")
        print("    6) Jalankan register")
        print("    7) Inject CPA → 9router (TUI terpisah)")
        print()
        print("    0) Keluar")
        print()
        try:
            choice = input("Pilih: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if choice == "0":
            print("Bye.")
            return 0
        if choice == "1":
            cmd_setup_temp_mail()
            pause()
        elif choice == "2":
            cmd_install_python()
            pause()
        elif choice == "3":
            cmd_install_system()
            pause()
        elif choice == "4":
            cmd_check_mail()
            pause()
        elif choice == "5":
            cmd_configure_run()
            pause()
        elif choice == "6":
            cmd_run_register()
            pause()
        elif choice == "7":
            cmd_inject(tui=True)
            pause()
        else:
            print("  menu tidak dikenal")
            pause()


def main() -> int:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass

    argv = sys.argv[1:]
    if not argv:
        return menu()
    cmd = argv[0].lower()
    if cmd in ("setup", "setup-mail"):
        cmd_setup_temp_mail()
        return 0
    if cmd in ("run", "register"):
        cmd_run_register()
        return 0
    if cmd == "inject":
        cmd_inject(tui=True)
        return 0
    if cmd == "status":
        print_status()
        return 0
    if cmd == "check":
        print_status()
        cmd_check_mail()
        return 0
    if cmd in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    print(f"unknown: {cmd}  (setup|run|inject|status|help)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
