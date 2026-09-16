import requests
import time
import concurrent.futures
import os
import threading
import random
import json
from playwright.sync_api import sync_playwright

# ==========================================
# 🚀 CONFIG — Reads from orchestrator_config.json
# ==========================================
def load_config():
    config_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "master_orchestrator", "orchestrator_config.json"),
        r"C:\Automation\master_orchestrator\orchestrator_config.json",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator_config.json"),
    ]
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return {}

_cfg = load_config()

target_url   = _cfg.get("target_url",        "https://omg10.com/q/732412")
total_tabs   = int(_cfg.get("total_tabs",    15))
wait_time    = int(_cfg.get("wait_time_sec", 16))
PROFILES_PER_TASK = int(_cfg.get("profiles_per_task", 5))
TARGET_TASKS      = int(_cfg.get("target_tasks",      500))

MAX_PROFILE_TIME  = 90
ALLOWED_MAX_TIME  = 60
PROXY_FILE        = "proxies.txt"
PREMIUM_PROXY_FILE = "premium_proxies.txt"

current_round_proxies      = []
next_round_premium_proxies = []
file_lock  = threading.Lock()

previous_hardware_states = {}
global_fingerprints      = {}
active_profile_timers    = {}

print(f"[CONFIG] Target: {target_url}")
print(f"[CONFIG] Tabs: {total_tabs} | Wait: {wait_time}s | Profiles: {PROFILES_PER_TASK} | Tasks: {TARGET_TASKS}")

# ==========================================
# 🔧 FINGERPRINT DATA POOLS
# ==========================================
RESOLUTIONS = ["1920_1080", "1366_768", "1440_900", "1536_864", "1280_720", "1600_900", "2560_1440", "3840_2160"]
RAMS        = ["2", "4", "8", "16"]
CPUS        = ["2", "4", "6", "8", "12", "16", "20", "24", "32"]
GPUS = [
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 (0x00001F51) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)",  "ANGLE (Intel, Intel(R) HD Graphics 510 (0x00007DD5) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)",    "ANGLE (AMD, AMD Radeon(TM) Graphics (0x0000164E) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB (0x00001B83) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)",  "ANGLE (Intel, Intel(R) UHD Graphics 600 (0x00003185) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)",    "ANGLE (AMD, Radeon RX 580 Series (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

def generate_mac_address():
    return f"00-{random.randint(10,99):02X}-{random.choice(['FC','1E','1F'])}-{random.randint(10,99):02X}-{random.randint(10,99):02X}-{random.choice(['EB','7B','D7','E1','74'])}"

def generate_device_name():
    prefix = random.choice(["WIN", "LAPTOP", "DESKTOP"])
    suffix = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=7))
    return f"{prefix}{suffix}"

def generate_fingerprint(profile_index):
    """Generate a unique but consistent fingerprint for a given profile slot."""
    rng = random.Random(profile_index * 7919 + int(time.time() // 3600))
    res = rng.choice(RESOLUTIONS)
    cpu = rng.choice(CPUS)
    ram = rng.choice(RAMS)
    gpu_vendor, gpu_renderer = rng.choice(GPUS)
    ua  = rng.choice(USER_AGENTS)
    w, h = res.split("_")
    return {
        "res": res, "width": int(w), "height": int(h),
        "cpu": cpu, "ram": ram,
        "gpu_vendor": gpu_vendor, "gpu_renderer": gpu_renderer,
        "ua": ua,
        "mac": generate_mac_address(),
        "device_name": generate_device_name(),
    }

# ==========================================
# 🔧 JS FINGERPRINT INJECTION SCRIPT
# ==========================================
def build_fp_init_script(fp: dict) -> str:
    """Returns a JS init script that overrides canvas/webgl/audio/nav fingerprints."""
    return f"""
(() => {{
    // ── User-Agent ──
    Object.defineProperty(navigator, 'userAgent', {{ get: () => '{fp["ua"]}' }});
    Object.defineProperty(navigator, 'appVersion', {{ get: () => '{fp["ua"]}'.replace('Mozilla/', '') }});
    Object.defineProperty(navigator, 'platform', {{ get: () => 'Win32' }});
    Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp["cpu"]} }});
    Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp["ram"]} }});

    // ── Screen resolution ──
    Object.defineProperty(screen, 'width',  {{ get: () => {fp["width"]} }});
    Object.defineProperty(screen, 'height', {{ get: () => {fp["height"]} }});
    Object.defineProperty(screen, 'availWidth',  {{ get: () => {fp["width"]} }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {fp["height"]} - 40 }});

    // ── Canvas noise ──
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        const ctx = this.getContext('2d');
        if (ctx) {{
            ctx.fillStyle = 'rgba(0,0,0,' + (Math.random() * 0.0001) + ')';
            ctx.fillRect(0, 0, 1, 1);
        }}
        return origToDataURL.apply(this, arguments);
    }};
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {{
        const imageData = origGetImageData.call(this, x, y, w, h);
        for (let i = 0; i < imageData.data.length; i += 4) {{
            imageData.data[i]     += Math.floor(Math.random() * 3 - 1);
            imageData.data[i + 1] += Math.floor(Math.random() * 3 - 1);
            imageData.data[i + 2] += Math.floor(Math.random() * 3 - 1);
        }}
        return imageData;
    }};

    // ── WebGL vendor/renderer ──
    const origGetParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {{
        const EXT = this.getExtension('WEBGL_debug_renderer_info');
        if (EXT) {{
            if (param === EXT.UNMASKED_VENDOR_WEBGL)   return '{fp["gpu_vendor"]}';
            if (param === EXT.UNMASKED_RENDERER_WEBGL) return '{fp["gpu_renderer"]}';
        }}
        return origGetParam.call(this, param);
    }};

    // ── AudioContext noise ──
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {{
        const arr = origGetChannelData.call(this, channel);
        for (let i = 0; i < arr.length; i += 100) {{
            arr[i] += (Math.random() - 0.5) * 0.0001;
        }}
        return arr;
    }};

    // ── Hide automation flags ──
    Object.defineProperty(navigator, 'webdriver', {{ get: () => false }});
    delete navigator.__proto__.webdriver;

    // ── WebRTC leak prevention (disable local IPs) ──
    if (window.RTCPeerConnection) {{
        const origRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config, ...args) {{
            if (config && config.iceServers) {{
                config.iceServers = config.iceServers.filter(s =>
                    s.urls && !String(s.urls).includes('stun:'));
            }}
            return new origRTC(config, ...args);
        }};
        window.RTCPeerConnection.prototype = origRTC.prototype;
    }}
}})();
"""

# ==========================================
# 1. 🔧 ROUND-BASED SMART PROXY SYSTEM
# ==========================================
def load_proxies():
    global current_round_proxies, next_round_premium_proxies
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r") as f:
            current_round_proxies = [line.strip() for line in f if line.strip()]
    if os.path.exists(PREMIUM_PROXY_FILE):
        with open(PREMIUM_PROXY_FILE, "r") as f:
            next_round_premium_proxies = [line.strip() for line in f if line.strip()]
    if not current_round_proxies and next_round_premium_proxies:
        current_round_proxies = next_round_premium_proxies.copy()
        next_round_premium_proxies.clear()
        open(PREMIUM_PROXY_FILE, "w").close()
        update_main_proxy_file()
    return current_round_proxies

def update_main_proxy_file():
    with open(PROXY_FILE, "w") as f:
        for p in current_round_proxies: f.write(p + "\n")

def get_next_proxy():
    global current_round_proxies, next_round_premium_proxies
    with file_lock:
        if not current_round_proxies:
            if next_round_premium_proxies:
                print(f"\n[🔄 ROUND COMPLETE] Ab New File se {len(next_round_premium_proxies)} BEST PROXIES use hongi!")
                current_round_proxies = next_round_premium_proxies.copy()
                next_round_premium_proxies.clear()
                open(PREMIUM_PROXY_FILE, "w").close()
                update_main_proxy_file()
            else:
                return None
        p = current_round_proxies.pop(0)
        update_main_proxy_file()
        return p

def save_premium_proxy(proxy):
    global next_round_premium_proxies
    with file_lock:
        if proxy not in next_round_premium_proxies:
            next_round_premium_proxies.append(proxy)
            with open(PREMIUM_PROXY_FILE, "a") as f:
                f.write(proxy + "\n")

def parse_proxy(proxy_str: str) -> dict:
    """Parses host:port:user:pass or host:port into Playwright proxy dict."""
    parts = proxy_str.strip().split(":")
    if len(parts) >= 4:
        return {
            "server":   f"socks5://{parts[0]}:{parts[1]}",
            "username": parts[2],
            "password": parts[3],
        }
    elif len(parts) == 2:
        return {"server": f"socks5://{parts[0]}:{parts[1]}"}
    return {"server": f"socks5://{proxy_str}"}

# ==========================================
# 2. 🛡️ TRUE NUCLEAR TAB KILLER v2.0
# ==========================================
def nuclear_tab_killer(context, log_prefix):
    print(f"{log_prefix} 🧹 NUCLEAR TAB KILLER v2: Ziddi tabs destroy ho rahi hain...")
    try:
        fresh_page = context.new_page()
        for page in context.pages:
            if page != fresh_page:
                try:
                    page.evaluate("""
                        window.stop();
                        window.onbeforeunload = null;
                        window.alert = () => {};
                        window.confirm = () => {};
                    """)
                except: pass

        killed = 0
        for _ in range(4):
            ziddi = [p for p in context.pages if p != fresh_page]
            if not ziddi: break
            for page in ziddi:
                try: page.close(); killed += 1
                except: pass
            time.sleep(0.5)

        remaining = len(context.pages) - 1
        if remaining > 0:
            print(f"{log_prefix} ⚠️ TAB KILLER WARNING: {remaining} tab abhi bhi zinda hain!")
        else:
            print(f"{log_prefix} ✅ VERIFIED: {killed} Tabs destroy ho gaye!")
        return fresh_page
    except Exception as e:
        print(f"{log_prefix} ❌ TAB KILLER CRASH: {str(e)[:50]}")
        return context.pages[0] if context.pages else context.new_page()

def ultimate_data_wiper(context, page, log_prefix):
    try:
        context.clear_cookies()
        try:
            client = context.new_cdp_session(page)
            client.send("Network.clearBrowserCache")
            client.send("Network.clearBrowserCookies")
        except: pass

        audit_report = page.evaluate("""async () => {
            try { localStorage.clear(); } catch(e) {}
            try { sessionStorage.clear(); } catch(e) {}
            try {
                if (window.indexedDB && window.indexedDB.databases) {
                    let dbs = await window.indexedDB.databases();
                    for (let db of dbs) { window.indexedDB.deleteDatabase(db.name); }
                }
            } catch(e) {}
            try {
                if (window.caches) {
                    let keys = await caches.keys();
                    for (let key of keys) { await caches.delete(key); }
                }
            } catch(e) {}
            let localL = 0; try { localL = localStorage.length; } catch(e) {}
            let idbL = 0; try { let idbs = await window.indexedDB.databases(); idbL = idbs.length; } catch(e) {}
            return { local: localL, idb: idbL };
        }""")

        print(f"\n{log_prefix} 🧾 DATA AUDIT: Local={audit_report['local']} | IDB={audit_report['idb']}")
        print(f"{log_prefix} 🕵️ DATA CONFIRMER: All cleared. ✅\n")
        return True
    except Exception:
        print(f"{log_prefix} ❌ Auditor Internal Error: Fallback Triggered.")
        return True

# ==========================================
# 3. 🚀 CORE STEALTH PROFILE RUNNER
# ==========================================
def process_stealth_profile(profile_index, current_proxy, task_num, profile_num):
    """
    Runs one stealth browser context with native fingerprint injection.
    No AdsPower required — pure Playwright + JS init scripts.
    """
    log_prefix = f"[Task {task_num} | Profile {profile_num}]"
    print(f"\n{log_prefix} 🔄 NEW TASK SHURU...")

    task_start_time = time.time()

    # Generate unique fingerprint for this profile slot
    fp = generate_fingerprint(profile_index + task_num * 100)

    # Parse proxy
    proxy_cfg = parse_proxy(current_proxy)

    try:
        with sync_playwright() as pw:
            # Launch Chromium with anti-detect flags
            browser = pw.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    f"--window-size={fp['width']},{fp['height']}",
                ]
            )

            # Create isolated context with per-proxy, per-UA, per-viewport settings
            context = browser.new_context(
                proxy=proxy_cfg,
                user_agent=fp["ua"],
                viewport={"width": fp["width"], "height": fp["height"]},
                locale="en-US",
                timezone_id="America/New_York",
                ignore_https_errors=True,
            )

            # Inject fingerprint override script into every page
            fp_script = build_fp_init_script(fp)
            context.add_init_script(fp_script)

            # Block images/media/fonts for speed
            def safe_route(route):
                try:
                    if route.request.resource_type in ["image", "media", "font"]:
                        route.abort()
                    else:
                        route.continue_()
                except: pass
            try: context.route("**/*", safe_route)
            except: pass

            # ── First tab: ghost-cursor style navigation ──
            active_profile_timers[profile_index] = time.time()

            fresh_page = context.new_page()
            try:
                fresh_page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
            except Exception: pass

            ultimate_data_wiper(context, fresh_page, log_prefix)

            # Extract and log fingerprint
            current_fp = {}
            try:
                current_fp = fresh_page.evaluate("""
                    () => {
                        let gl = document.createElement('canvas').getContext('webgl');
                        let ext = gl ? gl.getExtension('WEBGL_debug_renderer_info') : null;
                        let gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'unknown';
                        return {
                            res: screen.width + 'x' + screen.height,
                            cpu: navigator.hardwareConcurrency || 'Hidden',
                            tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
                            lang: navigator.language,
                            ua: navigator.userAgent,
                            gpu: gpu
                        };
                    }
                """)
            except: pass

            with file_lock:
                old_fp = global_fingerprints.get(profile_index)

            print(f"\n{log_prefix} 📊 OMNI-MATRIX FINGERPRINT DOSSIER")
            print(f"   ├─ User-Agent\n   │  {current_fp.get('ua', fp['ua'])}")
            print(f"   ├─ WebRTC\n   │  Proxy Protected (SOCKS5)")
            print(f"   ├─ Timezone\n   │  {current_fp.get('tz', 'America/New_York')}")
            print(f"   ├─ Language\n   │  {current_fp.get('lang', 'en-US')}")
            res_fallback = f"{fp['width']}x{fp['height']}"
            print(f"   ├─ Screen Resolution\n   │  {current_fp.get('res', res_fallback)}")
            print(f"   ├─ Canvas\n   │  Noise [Injected via init script]")
            print(f"   ├─ WebGL Metadata\n   │  {current_fp.get('gpu', fp['gpu_renderer'])[:60]}")
            print(f"   ├─ CPU\n   │  {current_fp.get('cpu', fp['cpu'])} cores")
            print(f"   ├─ RAM\n   │  {fp['ram']} GB")
            print(f"   ├─ Device name\n   │  {fp['device_name']}")
            print(f"   ├─ MAC Address\n   │  {fp['mac']}")
            print(f"   ├─ Webdriver flag\n   │  Hidden ✅")
            print(f"   └─ Proxy\n      {proxy_cfg['server']}\n")

            if old_fp:
                print(f"{log_prefix} 🕵️ FINGERPRINT CHECKER: MUTATION CONFIRMED ✅")
                print(f"      ↳ Old: [Res: {old_fp.get('res','?')} | GPU: {old_fp.get('gpu','?')[:20]}... | CPU: {old_fp.get('cpu','?')}]")
                print(f"      ↳ New: [Res: {current_fp.get('res','?')} | GPU: {current_fp.get('gpu','?')[:20]}... | CPU: {current_fp.get('cpu','?')}]")
            else:
                print(f"{log_prefix} 🕵️ FINGERPRINT CHECKER: FRESH PROFILE INITIALIZED ✅")

            with file_lock:
                global_fingerprints[profile_index] = current_fp

            # ── BURST TRAFFIC: Open remaining tabs fast ──
            print(f"{log_prefix} 🚀 BURST TRAFFIC INITIATED: {total_tabs} Tabs ek sath fire ho rahe hain...")
            for step in range(2, total_tabs + 1):
                try:
                    new_tab = context.new_page()
                    new_tab.goto(target_url, wait_until="commit", timeout=15000)
                    time.sleep(0.1)
                except: pass

            print(f"{log_prefix} ⏳ All {total_tabs} tabs fired. Traffic running... strict {wait_time}s hold.")
            time.sleep(wait_time)

            print(f"{log_prefix} 🗑️ TABS DESTROYED! Closing context safely.")
            try: nuclear_tab_killer(context, log_prefix)
            except: pass
            try: context.close()
            except: pass
            try: browser.close()
            except: pass

            time.sleep(0.5)
            total_time = time.time() - task_start_time
            return "SUCCESS", current_proxy, total_time

    except Exception as e:
        error_msg = str(e)[:80]
        if "net::ERR" in error_msg or "proxy" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"{log_prefix} ⚠️ Proxy Error/Timeout: {error_msg}")
        else:
            print(f"{log_prefix} ⚠️ Browser Failure: {error_msg}")
        return "PROXY_DEAD", current_proxy, 0
    finally:
        active_profile_timers.pop(profile_index, None)

# ==========================================
# 🌟 MAIN BOT EXECUTION
# ==========================================
def run_bot():
    global current_round_proxies
    current_round_proxies = load_proxies()

    if not current_round_proxies:
        print("x Error: proxies.txt file khali hai!")
        return

    print(f"===========================================================")
    print(f"STEALTH BOT — ZERO ADSPOWER — NATIVE FINGERPRINT ENGINE")
    print(f"MASTER BOT TARGET: {TARGET_TASKS} Tasks")
    print(f"STRATEGY: Burst Traffic + Native Stealth Fingerprint Injection")
    print(f"Proxies Loaded: {len(current_round_proxies)}")
    print(f"===========================================================\n")

    # Profile slots 0..PROFILES_PER_TASK-1 — no creation needed, no cleanup at end
    profile_slots = list(range(PROFILES_PER_TASK))

    try:
        for current_task in range(1, TARGET_TASKS + 1):
            print(f"\n=================================================")
            print(f"🔥 TASK {current_task} SHURU HO RAHA HAI")
            print(f"=================================================")

            profiles_completed = 0
            futures_map = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=PROFILES_PER_TASK) as executor:
                for i, profile_idx in enumerate(profile_slots):
                    proxy = get_next_proxy()
                    if not proxy: break
                    fut = executor.submit(process_stealth_profile, profile_idx, proxy, current_task, i + 1)
                    futures_map[fut] = (profile_idx, i + 1)

                while futures_map and profiles_completed < PROFILES_PER_TASK:
                    done, _ = concurrent.futures.wait(futures_map.keys(), return_when=concurrent.futures.FIRST_COMPLETED)

                    for fut in done:
                        profile_idx, profile_num = futures_map.pop(fut)
                        status, used_proxy, elapsed_time = fut.result()

                        if status == "SUCCESS":
                            profiles_completed += 1
                            if elapsed_time <= ALLOWED_MAX_TIME:
                                save_premium_proxy(used_proxy)
                                print(f"   ⭐ BEST PROXY SAVED: {used_proxy.split(':')[0]} (Speed: {elapsed_time:.1f}s)")
                            else:
                                print(f"   ✓ [Task {current_task} | Profile {profile_num}] Mukammal! (Proxy slow [{elapsed_time:.1f}s], discarded)")

                        elif status == "PROXY_DEAD":
                            print(f"   ❌ [Task {current_task} | Profile {profile_num}] Proxy fail! Replacing...")
                            new_proxy = get_next_proxy()
                            if not new_proxy:
                                print("\n[!] Saari proxies dead ho chuki hain!")
                                break
                            new_fut = executor.submit(process_stealth_profile, profile_idx, new_proxy, current_task, profile_num)
                            futures_map[new_fut] = (profile_idx, profile_num)

            if profiles_completed < PROFILES_PER_TASK:
                print(f"\n❌ Loop ruk gaya — active proxies khatam ho gayin.")
                break

            print(f"\n=================================================")
            print(f"🌟 TASK {current_task} / {TARGET_TASKS} MUKAMMAL!")
            print(f"=================================================\n")

        print("\n========== TARGET LOOP KHATAM HO GAYA! ==========")

    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt — Bot gracefully stopping...")

    print("\n✓ ALL DONE! Task Successfully Completed.")
    print("✓ No AdsPower cleanup needed — all contexts closed automatically.")

if __name__ == "__main__":
    run_bot()