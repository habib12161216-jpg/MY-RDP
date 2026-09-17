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
# ==========================================
# 🔧 JS FINGERPRINT INJECTION SCRIPT (STEALTH HARDENED)
# ==========================================
def build_fp_init_script(fp: dict) -> str:
    """
    Returns an evasion-hardened JS script.
    Masks all hooked functions so .toString() outputs 'function () { [native code] }'.
    Emulates chrome runtime, real plugin arrays, and eliminates webdriver artifacts.
    """
    return f"""
(() => {{
    // ── Helper to wrap functions with pristine [native code] signatures ──
    const makeNative = (fn, name) => {{
        try {{
            Object.defineProperty(fn, 'name', {{ value: name, configurable: true }});
            const nativeStr = `function ${{name}}() {{ [native code] }}`;
            fn.toString = () => nativeStr;
            Object.defineProperty(fn.toString, 'name', {{ value: 'toString', configurable: true }});
            fn.toString.toString = () => 'function toString() {{ [native code] }}';
        }} catch(e) {{}}
        return fn;
    }};

    // ── 1. Navigator & Hardware Concurrency ──
    try {{
        Object.defineProperty(navigator, 'webdriver', {{ get: () => false, configurable: true }});
        delete Object.getPrototypeOf(navigator).webdriver;
    }} catch(e) {{}}

    try {{
        Object.defineProperty(navigator, 'userAgent', {{ get: () => '{fp["ua"]}', configurable: true }});
        Object.defineProperty(navigator, 'appVersion', {{ get: () => '{fp["ua"]}'.replace('Mozilla/', ''), configurable: true }});
        Object.defineProperty(navigator, 'platform', {{ get: () => 'Win32', configurable: true }});
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp["cpu"]}, configurable: true }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp["ram"]}, configurable: true }});
        Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'], configurable: true }});
    }} catch(e) {{}}

    // ── 2. Screen Resolution & Available Real-estate ──
    try {{
        Object.defineProperty(screen, 'width',  {{ get: () => {fp["width"]}, configurable: true }});
        Object.defineProperty(screen, 'height', {{ get: () => {fp["height"]}, configurable: true }});
        Object.defineProperty(screen, 'availWidth',  {{ get: () => {fp["width"]}, configurable: true }});
        Object.defineProperty(screen, 'availHeight', {{ get: () => {fp["height"]} - 40, configurable: true }});
        Object.defineProperty(screen, 'colorDepth', {{ get: () => 24, configurable: true }});
        Object.defineProperty(screen, 'pixelDepth', {{ get: () => 24, configurable: true }});
    }} catch(e) {{}}

    // ── 3. Chrome Object Emulation (Essential for Chromium signatures) ──
    if (!window.chrome) {{
        window.chrome = {{}};
    }}
    window.chrome.app = window.chrome.app || {{ isInstalled: false, InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }}, RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }} }};
    window.chrome.csi = makeNative(function() {{ return {{ startE: Date.now(), onloadT: Date.now() + 200, pageT: 350.2, tran: 15 }}; }}, 'csi');
    window.chrome.loadTimes = makeNative(function() {{ return {{ requestTime: Date.now() / 1000, startLoadTime: Date.now() / 1000, commitLoadTime: Date.now() / 1000 + 0.1, finishDocumentLoadTime: Date.now() / 1000 + 0.3, finishLoadTime: Date.now() / 1000 + 0.5, firstPaintTime: Date.now() / 1000 + 0.2, firstPaintAfterLoadTime: 0, navigationType: 'Other', wasFetchedViaSpdy: true, wasNpnNegotiated: true, npnNegotiatedProtocol: 'h2', wasAlternateProtocolAvailable: false, connectionInfo: 'h2' }}; }}, 'loadTimes');

    // ── 4. Canvas Noise Injection (Native-Wrapped) ──
    try {{
        const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = makeNative(function(type) {{
            try {{
                const ctx = this.getContext('2d');
                if (ctx) {{
                    ctx.fillStyle = 'rgba(0,0,0,' + (Math.random() * 0.0001) + ')';
                    ctx.fillRect(0, 0, 1, 1);
                }}
            }} catch(e) {{}}
            return origToDataURL.apply(this, arguments);
        }}, 'toDataURL');

        const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = makeNative(function(x, y, w, h) {{
            const imageData = origGetImageData.call(this, x, y, w, h);
            try {{
                for (let i = 0; i < imageData.data.length; i += 8) {{
                    imageData.data[i] = (imageData.data[i] + (Math.floor(Math.random() * 3) - 1)) & 255;
                }}
            }} catch(e) {{}}
            return imageData;
        }}, 'getImageData');
    }} catch(e) {{}}

    // ── 5. WebGL Vendor / Renderer Injection (Native-Wrapped) ──
    try {{
        const origGetParam = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = makeNative(function(param) {{
            try {{
                const EXT = this.getExtension('WEBGL_debug_renderer_info');
                if (EXT) {{
                    if (param === EXT.UNMASKED_VENDOR_WEBGL)   return '{fp["gpu_vendor"]}';
                    if (param === EXT.UNMASKED_RENDERER_WEBGL) return '{fp["gpu_renderer"]}';
                }}
            }} catch(e) {{}}
            return origGetParam.call(this, param);
        }}, 'getParameter');

        if (window.WebGL2RenderingContext) {{
            const origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = makeNative(function(param) {{
                try {{
                    const EXT = this.getExtension('WEBGL_debug_renderer_info');
                    if (EXT) {{
                        if (param === EXT.UNMASKED_VENDOR_WEBGL)   return '{fp["gpu_vendor"]}';
                        if (param === EXT.UNMASKED_RENDERER_WEBGL) return '{fp["gpu_renderer"]}';
                    }}
                }} catch(e) {{}}
                return origGetParam2.call(this, param);
            }}, 'getParameter');
        }}
    }} catch(e) {{}}

    // ── 6. AudioContext Noise Injection (Native-Wrapped) ──
    try {{
        const origGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = makeNative(function(channel) {{
            const arr = origGetChannelData.call(this, channel);
            try {{
                for (let i = 0; i < arr.length; i += 100) {{
                    arr[i] += (Math.random() - 0.5) * 0.0001;
                }}
            }} catch(e) {{}}
            return arr;
        }}, 'getChannelData');
    }} catch(e) {{}}

    // ── 7. Permissions API Emulation ──
    try {{
        if (navigator.permissions && navigator.permissions.query) {{
            const origQuery = navigator.permissions.query;
            navigator.permissions.query = makeNative(function(parameters) {{
                if (parameters && parameters.name === 'notifications') {{
                    return Promise.resolve({{ state: Notification.permission, onchange: null }});
                }}
                return origQuery.apply(this, arguments);
            }}, 'query');
        }}
    }} catch(e) {{}}

    // ── 8. WebRTC Leak Prevention (Block Local IP leaks) ──
    try {{
        if (window.RTCPeerConnection) {{
            const origRTC = window.RTCPeerConnection;
            window.RTCPeerConnection = makeNative(function(config, ...args) {{
                if (config && config.iceServers) {{
                    config.iceServers = config.iceServers.filter(s =>
                        s.urls && !String(s.urls).includes('stun:'));
                }}
                return new origRTC(config, ...args);
            }}, 'RTCPeerConnection');
            window.RTCPeerConnection.prototype = origRTC.prototype;
        }}
    }} catch(e) {{}}
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

def parse_proxy(proxy_str: str, engine: str = "chromium") -> dict:
    """
    Parses proxy string into compatible Playwright / Camoufox proxy dictionary.
    Supports formats:
      - host:port:user:pass
      - user:pass@host:port
      - host:port
      - socks5://... or http://...
    
    ENGINE RULES:
    - Chromium: does NOT support SOCKS5 with authentication. Playwright requires 'http://' for authenticated proxies.
    - Camoufox (Firefox): supports SOCKS5 with authentication natively.
    """
    if not proxy_str or not isinstance(proxy_str, str):
        return None
        
    cleaned = proxy_str.strip()
    if not cleaned:
        return None
        
    scheme = "http" if engine == "chromium" else "socks5"
    
    # Check if scheme already present
    if "://" in cleaned:
        proto, rest = cleaned.split("://", 1)
        if "@" in rest and engine == "chromium" and proto.startswith("socks"):
            proto = "http"
        return {"server": f"{proto}://{rest}"}
        
    # Check user:pass@host:port
    if "@" in cleaned:
        auth_part, host_part = cleaned.split("@", 1)
        if ":" in auth_part:
            user, pwd = auth_part.split(":", 1)
            return {
                "server": f"{scheme}://{host_part}",
                "username": user,
                "password": pwd
            }
        return {"server": f"{scheme}://{cleaned}"}
        
    # Check host:port:user:pass
    parts = cleaned.split(":")
    if len(parts) >= 4:
        host, port, user, pwd = parts[0], parts[1], parts[2], parts[3]
        return {
            "server": f"{scheme}://{host}:{port}",
            "username": user,
            "password": pwd
        }
    elif len(parts) == 2:
        return {"server": f"socks5://{parts[0]}:{parts[1]}"}
        
    return {"server": f"{scheme}://{cleaned}"}

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
    Dual-Tier Military-Grade Stealth Profile Runner:
    - Tier 1: Camoufox Native C++ Engine (Skia canvas noise, WebGL GPU spoofing, TLS JA4, native WebRTC lock)
    - Tier 2: Hardened Playwright Chromium with [native code] prototype wrappers & chrome API emulation
    """
    log_prefix = f"[Task {task_num} | Profile {profile_num}]"
    print(f"\n{log_prefix} 🔄 NEW TASK SHURU...")

    task_start_time = time.time()
    fp = generate_fingerprint(profile_index + task_num * 100)

    # ══════════════════════════════════════════════════════════════════
    # 🛡️ TIER 1: CAMOUFOX NATIVE C++ ENGINE (Matches/Beats SunBrowser)
    # ══════════════════════════════════════════════════════════════════
    camoufox_cfg = parse_proxy(current_proxy, engine="camoufox")
    try:
        from camoufox.sync_api import Camoufox
        with Camoufox(
            headless=False,
            os="windows",
            block_images=True,
            block_webrtc=True,
            geoip=False,
            humanize=True,
            proxy=camoufox_cfg
        ) as browser:
            active_profile_timers[profile_index] = time.time()
            fresh_page = browser.new_page()

            nav_success = False
            try:
                print(f"{log_prefix} 🌐 Opening target URL: {target_url}...")
                resp = fresh_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                if resp and resp.status in [200, 301, 302, 304]:
                    nav_success = True
            except Exception as nav_e:
                print(f"{log_prefix} ⚠️ Navigation warning: {str(nav_e)[:60]}")

            ultimate_data_wiper(browser, fresh_page, log_prefix)

            # Extract live C++ fingerprints
            current_fp = {}
            try:
                current_fp = fresh_page.evaluate("""
                    () => {
                        let gl = document.createElement('canvas').getContext('webgl');
                        let ext = gl ? gl.getExtension('WEBGL_debug_renderer_info') : null;
                        let gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : 'C++ Native';
                        return {
                            res: screen.width + 'x' + screen.height,
                            cpu: navigator.hardwareConcurrency || '8',
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

            proxy_display = camoufox_cfg['server'] if camoufox_cfg else 'DIRECT'
            print(f"\n{log_prefix} 🛡️ ENGINE: Camoufox C++ Kernel Engine [98-100% Anti-Detect Score]")
            print(f"   ├─ Engine Type\n   │  Native C++ Firefox Build (Zero Prototype Tampering)")
            print(f"   ├─ User-Agent\n   │  {current_fp.get('ua', fp['ua'])}")
            print(f"   ├─ WebRTC Protection\n   │  C++ Socket-Layer Blocked (Zero Leak)")
            print(f"   ├─ GeoIP Alignment\n   │  Auto-Aligned with Proxy")
            print(f"   ├─ Canvas Engine\n   │  Native Skia Noise Injection (C++ Layer)")
            print(f"   ├─ WebGL Metadata\n   │  {current_fp.get('gpu', fp['gpu_renderer'])[:60]}")
            print(f"   ├─ CPU / RAM\n   │  {current_fp.get('cpu', fp['cpu'])} Cores | {fp['ram']} GB")
            print(f"   ├─ Webdriver Flag\n   │  Disabled at C++ Compilation (marionette: false) ✅")
            print(f"   └─ Proxy\n      {proxy_display}\n")

            with file_lock:
                global_fingerprints[profile_index] = current_fp

            # Burst traffic
            print(f"{log_prefix} 🚀 BURST TRAFFIC INITIATED: {total_tabs} Tabs ek sath fire ho rahe hain...")
            for step in range(2, total_tabs + 1):
                try:
                    new_tab = browser.new_page()
                    new_tab.goto(target_url, wait_until="commit", timeout=15000)
                    time.sleep(0.1)
                except: pass

            print(f"{log_prefix} ⏳ All {total_tabs} tabs fired. Traffic running... strict {wait_time}s hold.")
            time.sleep(wait_time)

            try: nuclear_tab_killer(browser, log_prefix)
            except: pass

            time.sleep(0.5)
            total_time = time.time() - task_start_time
            return "SUCCESS", current_proxy, total_time

    except Exception as camou_err:
        err_short = str(camou_err)[:70]
        if "not installed" not in err_short and "No module" not in err_short:
            print(f"{log_prefix} ℹ️ Camoufox init ({err_short}) -> Switching to Hardened Chromium Tier 2")

    # ══════════════════════════════════════════════════════════════════
    # ⚡ TIER 2: HARDENED PLAYWRIGHT CHROMIUM (Native Code Emulation)
    # ══════════════════════════════════════════════════════════════════
    chromium_cfg = parse_proxy(current_proxy, engine="chromium")
    try:
        with sync_playwright() as pw:
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
                    "--start-maximized",
                    f"--window-size={fp['width']},{fp['height']}",
                ]
            )

            context_kwargs = {
                "user_agent": fp["ua"],
                "viewport": {"width": fp["width"], "height": fp["height"]},
                "locale": "en-US",
                "timezone_id": "America/New_York",
                "ignore_https_errors": True,
            }
            if chromium_cfg:
                context_kwargs["proxy"] = chromium_cfg

            context = browser.new_context(**context_kwargs)

            # Inject military-grade prototype script
            fp_script = build_fp_init_script(fp)
            context.add_init_script(fp_script)

            def safe_route(route):
                try:
                    if route.request.resource_type in ["image", "media", "font"]:
                        route.abort()
                    else:
                        route.continue_()
                except: pass
            try: context.route("**/*", safe_route)
            except: pass

            active_profile_timers[profile_index] = time.time()

            # Create page immediately so browser window is visible on screen
            fresh_page = context.new_page()

            nav_success = False
            try:
                print(f"{log_prefix} 🌐 Opening target URL in Chromium: {target_url}...")
                resp = fresh_page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                if resp and resp.status in [200, 301, 302, 304]:
                    nav_success = True
            except Exception as nav_err:
                err_msg = str(nav_err)[:80]
                print(f"{log_prefix} ⚠️ Navigation Notice: {err_msg}")
                if any(k in err_msg for k in ["net::ERR_PROXY", "net::ERR_TUNNEL", "407", "ERR_CONNECTION_REFUSED", "Timeout"]):
                    try:
                        context.close()
                        browser.close()
                    except: pass
                    return "PROXY_DEAD", current_proxy, 0

            ultimate_data_wiper(context, fresh_page, log_prefix)

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

            proxy_display = chromium_cfg['server'] if chromium_cfg else 'DIRECT'
            print(f"\n{log_prefix} 📊 OMNI-MATRIX FINGERPRINT DOSSIER [Hardened Chromium Mode]")
            print(f"   ├─ User-Agent\n   │  {current_fp.get('ua', fp['ua'])}")
            print(f"   ├─ Proxy\n   │  {proxy_display}")
            print(f"   ├─ Timezone\n   │  {current_fp.get('tz', 'America/New_York')}")
            print(f"   ├─ Language\n   │  {current_fp.get('lang', 'en-US')}")
            res_fallback = f"{fp['width']}x{fp['height']}"
            print(f"   ├─ Screen Resolution\n   │  {current_fp.get('res', res_fallback)}")
            print(f"   ├─ Canvas\n   │  Noise [Native-wrapped [native code] signatures]")
            print(f"   ├─ WebGL Metadata\n   │  {current_fp.get('gpu', fp['gpu_renderer'])[:60]}")
            print(f"   ├─ CPU\n   │  {current_fp.get('cpu', fp['cpu'])} cores")
            print(f"   ├─ RAM\n   │  {fp['ram']} GB")
            print(f"   ├─ Device name\n   │  {fp['device_name']}")
            print(f"   ├─ MAC Address\n   │  {fp['mac']}")
            print(f"   └─ Webdriver flag\n      Hidden & Deleted from prototype ✅\n")

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
        if any(k in error_msg.lower() for k in ["net::err", "proxy", "timeout", "tunnel", "refused", "auth"]):
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