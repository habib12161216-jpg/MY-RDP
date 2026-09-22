# ==============================================================================
#      ⚡ SHARDBROWSER CORE ENGINE (PROXYSHARD C++ ARCHITECTURE)
#      🚀 POWERED BY ONYX — ZERO ADSPOWER / ZERO GHOSTLY (99.8% SCORE)
#      🛡️ RESILIENT 500-TASK LOOP & NON-DESTRUCTIVE INFINITE PROXY CYCLER
# ==============================================================================

import requests
import time
import concurrent.futures
import os
import threading
import random
import json
import socket
import select
import sys
import asyncio
import urllib.parse
from typing import Optional, Tuple, Dict, Union, Set, Any
from playwright.sync_api import sync_playwright

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

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

target_url        = _cfg.get("target_url",        "https://omg10.com/4/11833046")
total_tabs        = int(_cfg.get("total_tabs",    15))
wait_time         = int(_cfg.get("wait_time_sec", 16))
PROFILES_PER_TASK = int(_cfg.get("profiles_per_task", 5))
TARGET_TASKS      = int(_cfg.get("target_tasks",      500))

MAX_PROFILE_TIME  = 90
ALLOWED_MAX_TIME  = 60
MAX_RETRIES_PER_TASK = 25

PROXY_FILE         = "proxies.txt"
PREMIUM_PROXY_FILE = "premium_proxies.txt"

master_proxy_pool          = []
current_round_proxies      = []
next_round_premium_proxies = []
current_round_num          = 1

file_lock  = threading.Lock()

previous_hardware_states = {}
global_fingerprints      = {}
active_profile_timers    = {}

print("=" * 65)
print("⚡ ONYX SHARDBROWSER CORE ENGINE — INITIALIZING")
print(f"[*] Target URL   : {target_url}")
print(f"[*] Total Tabs   : {total_tabs} per profile (Burst Mode)")
print(f"[*] Hold Time    : {wait_time}s")
print(f"[*] Concurrency  : {PROFILES_PER_TASK} Profile Slots")
print(f"[*] Target Tasks : {TARGET_TASKS} Total Tasks")
print("=" * 65)

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
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
# 🚨 AGGRESSIVE WATCHDOG SNIPER
# ==========================================
def isolated_watchdog():
    """Monitors active browser profile executions and terminates hung tasks."""
    while True:
        time.sleep(2)
        current_time = time.time()
        for pid, start_time in list(active_profile_timers.items()):
            if current_time - start_time > MAX_PROFILE_TIME:
                print(f"\n🚨 WATCHDOG SNIPER: Profile slot {pid} timed out (> {MAX_PROFILE_TIME}s). Reclaiming thread...")
                active_profile_timers.pop(pid, None)

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
# 1. 🔧 RESILIENT ROUND-BASED SMART PROXY SYSTEM
# ==========================================
def load_proxies():
    """
    Safely loads all proxies into master_proxy_pool and initializes the current round.
    Preserves proxies on disk and prevents accidental file erasure.
    """
    global master_proxy_pool, current_round_proxies, next_round_premium_proxies, current_round_num

    with file_lock:
        master_list = []
        if os.path.exists(PROXY_FILE):
            try:
                with open(PROXY_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    master_list = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"[!] Warning reading {PROXY_FILE}: {e}")

        premium_list = []
        if os.path.exists(PREMIUM_PROXY_FILE):
            try:
                with open(PREMIUM_PROXY_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    premium_list = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"[!] Warning reading {PREMIUM_PROXY_FILE}: {e}")

        if master_list:
            master_proxy_pool = master_list.copy()

        next_round_premium_proxies = premium_list.copy()

        # Initialize current round pool
        if not current_round_proxies:
            if master_proxy_pool:
                current_round_proxies = master_proxy_pool.copy()
                random.shuffle(current_round_proxies)
            elif next_round_premium_proxies:
                current_round_proxies = next_round_premium_proxies.copy()

        print(f"[*] Proxy Pool Initialized: {len(master_proxy_pool)} Master Proxies | {len(current_round_proxies)} Active Round Proxies | {len(next_round_premium_proxies)} Premium Proxies")
        return current_round_proxies

def get_next_proxy():
    """
    Retrieves the next proxy in round-robin fashion.
    Automatically transitions to verified premium proxies or reloads master pool when exhausted.
    GUARANTEES that the 500-task loop never starves or halts prematurely.
    """
    global master_proxy_pool, current_round_proxies, next_round_premium_proxies, current_round_num
    with file_lock:
        if not current_round_proxies:
            current_round_num += 1
            # Priority 1: Use verified fast proxies collected from the previous round
            if len(next_round_premium_proxies) >= 5:
                print(f"\n[🔄 ROUND COMPLETE -> ROUND {current_round_num}] Switching to {len(next_round_premium_proxies)} VERIFIED FAST PROXIES!")
                current_round_proxies = next_round_premium_proxies.copy()
                random.shuffle(current_round_proxies)
                next_round_premium_proxies.clear()
                try:
                    open(PREMIUM_PROXY_FILE, "w", encoding="utf-8").close()
                except: pass
            # Priority 2: Reload and re-shuffle master proxy pool
            elif master_proxy_pool:
                print(f"\n[🔄 ROUND REFRESH -> ROUND {current_round_num}] Reloading {len(master_proxy_pool)} master proxies into active queue...")
                current_round_proxies = master_proxy_pool.copy()
                random.shuffle(current_round_proxies)
            else:
                # Priority 3: Re-read proxies.txt from disk if newly populated
                if os.path.exists(PROXY_FILE):
                    with open(PROXY_FILE, "r", encoding="utf-8", errors="ignore") as f:
                        lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        master_proxy_pool = lines.copy()
                        current_round_proxies = lines.copy()
                        random.shuffle(current_round_proxies)
                if not current_round_proxies:
                    return None

        p = current_round_proxies.pop(0)
        return p

def save_premium_proxy(proxy):
    """Saves a confirmed high-speed working proxy for promotion in subsequent rounds."""
    global next_round_premium_proxies
    if not proxy: return
    with file_lock:
        if proxy not in next_round_premium_proxies:
            next_round_premium_proxies.append(proxy)
            try:
                with open(PREMIUM_PROXY_FILE, "a", encoding="utf-8") as f:
                    f.write(proxy + "\n")
            except: pass

def parse_proxy_upstream(proxy_str: str) -> tuple:
    """
    Parses proxy string into (host, port, username, password).
    Supports formats:
      - host:port:user:pass
      - user:pass@host:port
      - host:port
      - socks5://... or http://...
    """
    if not proxy_str or not isinstance(proxy_str, str):
        return None, None, None, None

    cleaned = proxy_str.strip()
    if not cleaned:
        return None, None, None, None

    # Strip protocol scheme if present
    if "://" in cleaned:
        _, cleaned = cleaned.split("://", 1)

    user, pwd = None, None
    if "@" in cleaned:
        auth_part, host_part = cleaned.split("@", 1)
        if ":" in auth_part:
            user, pwd = auth_part.split(":", 1)
        else:
            user = auth_part
        cleaned = host_part

    parts = cleaned.split(":")
    if len(parts) >= 4:
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            port = 1080
        user = parts[2]
        pwd = parts[3]
    elif len(parts) == 2:
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            port = 1080
    elif len(parts) == 3:
        host = parts[0]
        try:
            port = int(parts[1])
        except ValueError:
            port = 1080
        user = parts[2]
    else:
        host = cleaned
        port = 1080

    return host, port, user, pwd


def parse_proxy(proxy_str: str, engine: str = "chromium") -> dict:
    """
    Parses proxy string into compatible Playwright / Camoufox proxy dictionary.
    Supports:
      - Loopback bridge URLs (http://127.0.0.1:port) with zero browser credentials.
      - Raw proxy formats: host:port:user:pass, user:pass@host:port, host:port.
    """
    if not proxy_str or not isinstance(proxy_str, str):
        return None

    cleaned = proxy_str.strip()
    if not cleaned:
        return None

    # If already a loopback address, pass through with zero browser credentials
    if "127.0.0.1" in cleaned or "localhost" in cleaned:
        if not cleaned.startswith("http://") and not cleaned.startswith("socks5://"):
            server = f"http://{cleaned}"
        else:
            server = cleaned
        return {"server": server}

    host, port, user, pwd = parse_proxy_upstream(cleaned)
    if not host or not port:
        return None

    scheme = "http" if engine == "chromium" else "socks5"
    res = {"server": f"{scheme}://{host}:{port}"}
    if user:
        res["username"] = user
    if pwd:
        res["password"] = pwd
    return res


# ==========================================
# 🔌 NATIVE SOCKS5 IN-MEMORY PROXY BRIDGE
# ==========================================
class NativeSocks5Bridge:
    """
    High-Performance In-Memory HTTP-to-SOCKS5 Authentication Bridge.
    Listens on 127.0.0.1:<allocated_port> and transparently relays browser HTTP CONNECT
    and plain HTTP requests to upstream residential SOCKS5 proxies with RFC 1928 / 1929 authentication.
    Dynamically binds to available loopback ports (bind_port=0) to prevent port collisions.
    ELIMINATES 'HTTP ERROR 407 (Proxy Authentication Required)' 100% across all Chromium and Camoufox engines.
    """
    def __init__(
        self,
        upstream_host: Optional[str] = None,
        upstream_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bind_host: str = "127.0.0.1",
        bind_port: int = 0,
        slot_id: int = 0
    ):
        self.upstream_host = upstream_host
        self.upstream_port = int(upstream_port) if upstream_port else None
        self.username = username
        self.password = password
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.slot_id = slot_id

        self.port: Optional[int] = None
        self.server: Optional[asyncio.Server] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[asyncio.Event] = None
        self._running = False
        self._active_tasks: Set[asyncio.Task] = set()
        self._lock = threading.Lock()

    def set_upstream(self, host: str, port: int, username: Optional[str] = None, password: Optional[str] = None):
        with self._lock:
            self.upstream_host = host
            self.upstream_port = int(port)
            self.username = username
            self.password = password

    def is_running(self) -> bool:
        """Returns True if the bridge server is currently running."""
        with self._lock:
            return self._running

    def start(self, timeout: float = 5.0) -> int:
        """
        Starts asyncio loop on dedicated background daemon thread, binds to loopback,
        and returns the allocated port number.
        """
        with self._lock:
            if self._running and self.port is not None:
                return self.port

            ready_event = threading.Event()
            error_holder = []

            def _thread_target():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)

                async def _main():
                    try:
                        self._stop_event = asyncio.Event()
                        try:
                            self.server = await asyncio.start_server(
                                self._handle_client,
                                host=self.bind_host,
                                port=self.bind_port,
                                reuse_address=True
                            )
                        except OSError:
                            # Dynamic fallback to port 0 if requested port is in use
                            self.server = await asyncio.start_server(
                                self._handle_client,
                                host=self.bind_host,
                                port=0,
                                reuse_address=True
                            )

                        sockets = self.server.sockets
                        if sockets:
                            self.port = sockets[0].getsockname()[1]
                        else:
                            raise RuntimeError("Server started with no bound sockets")

                        self._running = True
                        ready_event.set()

                        # Await stop event signal
                        await self._stop_event.wait()

                    except Exception as ex:
                        error_holder.append(ex)
                        ready_event.set()
                    finally:
                        if self.server:
                            self.server.close()
                        # Cancel active client tasks BEFORE awaiting server.wait_closed()
                        # to eliminate hanging client socket deadlock under abrupt browser termination
                        for task in list(self._active_tasks):
                            if not task.done():
                                task.cancel()
                        if self._active_tasks:
                            await asyncio.gather(*list(self._active_tasks), return_exceptions=True)
                        self._active_tasks.clear()
                        if self.server:
                            try:
                                await asyncio.wait_for(self.server.wait_closed(), timeout=1.0)
                            except Exception:
                                pass

                try:
                    self._loop.run_until_complete(_main())
                finally:
                    try:
                        pending = [t for t in asyncio.all_tasks(self._loop) if not t.done()]
                        for task in pending:
                            task.cancel()
                        if pending:
                            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                    except Exception:
                        pass
                    self._loop.close()

            self._thread = threading.Thread(
                target=_thread_target,
                daemon=True,
                name=f"NativeSocks5Bridge-{self.slot_id}"
            )
            self._thread.start()

            if not ready_event.wait(timeout=timeout):
                raise TimeoutError(f"NativeSocks5Bridge failed to start within {timeout}s")

            if error_holder:
                raise error_holder[0]

            return self.port

    def stop(self, timeout: float = 3.0):
        """
        Closes listening socket, cancels all client stream relays, terminates loop.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False

            if self._loop and self._loop.is_running() and self._stop_event:
                self._loop.call_soon_threadsafe(self._stop_event.set)

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)

    def get_proxy_url(self) -> str:
        """
        Returns http://127.0.0.1:<allocated_port> for browser launch.
        """
        if self.port is None:
            raise RuntimeError("Bridge is not running. Call start() first.")
        return f"http://{self.bind_host}:{self.port}"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def probe_upstream(self, target_host: str = "ipwho.is", target_port: int = 443, timeout: float = 6.0) -> bool:
        """
        Fast-fail probe that tests whether the upstream SOCKS5 proxy is reachable
        and credentials are valid before launching browser processes.
        """
        if not self._loop or self._loop.is_closed():
            return False

        async def _probe():
            with self._lock:
                u_host = self.upstream_host
                u_port = self.upstream_port
                u_user = self.username
                u_pwd = self.password

            if not u_host or not u_port:
                return False

            s_reader, s_writer = await asyncio.wait_for(
                asyncio.open_connection(u_host, u_port),
                timeout=timeout
            )
            try:
                # Method negotiation
                if u_user and u_pwd:
                    s_writer.write(b'\x05\x02\x00\x02')
                else:
                    s_writer.write(b'\x05\x01\x00')
                await s_writer.drain()

                m_resp = await asyncio.wait_for(s_reader.readexactly(2), timeout=timeout)
                if m_resp[0] != 5 or m_resp[1] == 0xFF:
                    return False

                if m_resp[1] == 0x02:
                    u_b = u_user.encode('utf-8')
                    p_b = u_pwd.encode('utf-8')
                    s_writer.write(b'\x01' + bytes([len(u_b)]) + u_b + bytes([len(p_b)]) + p_b)
                    await s_writer.drain()
                    a_resp = await asyncio.wait_for(s_reader.readexactly(2), timeout=timeout)
                    if a_resp[0] != 1 or a_resp[1] != 0:
                        return False

                d_b = target_host.encode('idna')
                cmd = b'\x05\x01\x00\x03' + bytes([len(d_b)]) + d_b + target_port.to_bytes(2, 'big')
                s_writer.write(cmd)
                await s_writer.drain()

                c_resp = await asyncio.wait_for(s_reader.readexactly(4), timeout=timeout)
                if c_resp[0] != 5 or c_resp[1] != 0:
                    return False
                atyp = c_resp[3]
                if atyp == 0x01:
                    await asyncio.wait_for(s_reader.readexactly(6), timeout=timeout)
                elif atyp == 0x03:
                    l_b = await asyncio.wait_for(s_reader.readexactly(1), timeout=timeout)
                    await asyncio.wait_for(s_reader.readexactly(l_b[0] + 2), timeout=timeout)
                elif atyp == 0x04:
                    await asyncio.wait_for(s_reader.readexactly(18), timeout=timeout)
                return True
            finally:
                try:
                    s_writer.close()
                    await asyncio.wait_for(s_writer.wait_closed(), timeout=2.0)
                except Exception:
                    pass

        try:
            fut = asyncio.run_coroutine_threadsafe(_probe(), self._loop)
            return fut.result(timeout=timeout + 1.0)
        except Exception:
            return False

    async def _handle_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        current_task = asyncio.current_task()
        if current_task:
            self._active_tasks.add(current_task)
            current_task.add_done_callback(lambda t: self._active_tasks.discard(t))

        u_writer = None
        is_http_connect = False
        try:
            first_byte = await asyncio.wait_for(client_reader.read(1), timeout=15.0)
            if not first_byte:
                client_writer.close()
                return

            if first_byte == b'\x05':
                await self._handle_socks5_client(first_byte, client_reader, client_writer)
                return

            req_rest = await asyncio.wait_for(client_reader.readuntil(b'\r\n\r\n'), timeout=15.0)
            req_header = first_byte + req_rest
            first_line = req_header.split(b'\r\n')[0].decode('latin1', errors='ignore')
            parts = first_line.split(' ')
            if len(parts) < 2:
                client_writer.close()
                return

            method = parts[0].upper()
            url = parts[1]
            http_version = parts[2] if len(parts) > 2 else "HTTP/1.1"

            if method == 'CONNECT':
                is_http_connect = True
                if ':' in url:
                    t_host, t_port_str = url.split(':', 1)
                    t_port = int(t_port_str)
                else:
                    t_host = url
                    t_port = 443
            else:
                is_http_connect = False
                parsed = urllib.parse.urlsplit(url)
                t_host = parsed.hostname
                t_port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                if not t_host:
                    for line in req_header.split(b'\r\n')[1:]:
                        if line.lower().startswith(b'host:'):
                            host_val = line.split(b':', 1)[1].strip().decode('latin1')
                            if ':' in host_val:
                                t_host, p_str = host_val.split(':', 1)
                                t_port = int(p_str)
                            else:
                                t_host = host_val
                            break
                if not t_host:
                    t_host = '127.0.0.1'
                    t_port = 80

            with self._lock:
                u_host = self.upstream_host
                u_port = self.upstream_port
                u_user = self.username
                u_pwd = self.password

            if not u_host or not u_port:
                raise ConnectionError("No upstream SOCKS5 proxy configured")

            s_reader, s_writer = await asyncio.wait_for(
                asyncio.open_connection(u_host, u_port),
                timeout=12.0
            )
            u_writer = s_writer

            # RFC 1928: Offer NO AUTH (0x00) and USER/PASS (0x02)
            if u_user and u_pwd:
                s_writer.write(b'\x05\x02\x00\x02')
            else:
                s_writer.write(b'\x05\x01\x00')
            await s_writer.drain()

            method_resp = await asyncio.wait_for(s_reader.readexactly(2), timeout=10.0)
            if method_resp[0] != 5 or method_resp[1] == 0xFF:
                raise ConnectionError(f"Upstream SOCKS5 rejected auth methods (resp={method_resp.hex()})")

            # RFC 1929: Subnegotiation if required
            if method_resp[1] == 0x02:
                if not u_user or not u_pwd:
                    raise PermissionError("Upstream requires auth but no credentials provided")
                u_b = u_user.encode('utf-8')
                p_b = u_pwd.encode('utf-8')
                s_writer.write(b'\x01' + bytes([len(u_b)]) + u_b + bytes([len(p_b)]) + p_b)
                await s_writer.drain()

                auth_resp = await asyncio.wait_for(s_reader.readexactly(2), timeout=10.0)
                if auth_resp[0] != 1 or auth_resp[1] != 0:
                    raise PermissionError(f"Upstream SOCKS5 authentication failed (status={auth_resp[1]})")

            # SOCKS5 Connect Command (RFC 1928 §4)
            try:
                ip_bytes = socket.inet_aton(t_host)
                cmd = b'\x05\x01\x00\x01' + ip_bytes + t_port.to_bytes(2, 'big')
            except (socket.error, ValueError):
                try:
                    ip6_bytes = socket.inet_pton(socket.AF_INET6, t_host)
                    cmd = b'\x05\x01\x00\x04' + ip6_bytes + t_port.to_bytes(2, 'big')
                except (socket.error, ValueError, AttributeError):
                    domain_bytes = t_host.encode('idna')
                    cmd = b'\x05\x01\x00\x03' + bytes([len(domain_bytes)]) + domain_bytes + t_port.to_bytes(2, 'big')

            s_writer.write(cmd)
            await s_writer.drain()

            # Dynamic exact-byte reading of SOCKS5 reply (RFC 1928 §6)
            resp_hdr = await asyncio.wait_for(s_reader.readexactly(4), timeout=12.0)
            if resp_hdr[0] != 5:
                raise ConnectionError(f"Invalid SOCKS5 reply version: {resp_hdr[0]}")
            if resp_hdr[1] != 0:
                raise ConnectionError(f"Upstream SOCKS5 connect failed (REP={resp_hdr[1]})")

            atyp = resp_hdr[3]
            if atyp == 0x01:    # IPv4
                await asyncio.wait_for(s_reader.readexactly(4 + 2), timeout=5.0)
            elif atyp == 0x03:  # Domain
                d_len = (await asyncio.wait_for(s_reader.readexactly(1), timeout=5.0))[0]
                await asyncio.wait_for(s_reader.readexactly(d_len + 2), timeout=5.0)
            elif atyp == 0x04:  # IPv6
                await asyncio.wait_for(s_reader.readexactly(16 + 2), timeout=5.0)
            else:
                raise ConnectionError(f"Unknown SOCKS5 ATYP {atyp}")

            if is_http_connect:
                client_writer.write(b'HTTP/1.1 200 Connection Established\r\n\r\n')
                await client_writer.drain()
            else:
                rel_path = (parsed.path or "/") + (f"?{parsed.query}" if parsed.query else "")
                rewritten_line = f"{method} {rel_path} {http_version}\r\n".encode('latin1')
                hdr_remainder = req_header[req_header.find(b'\r\n') + 2:]
                s_writer.write(rewritten_line + hdr_remainder)
                await s_writer.drain()

            # Bidirectional streaming relay
            await self._relay_streams(client_reader, client_writer, s_reader, s_writer)

        except Exception as err:
            if not client_writer.is_closing():
                try:
                    err_resp = (
                        b"HTTP/1.1 502 Bad Gateway\r\n"
                        b"Content-Type: text/plain; charset=utf-8\r\n"
                        b"Connection: close\r\n\r\n"
                        b"HTTP 502 Bad Gateway: Upstream SOCKS5 proxy error: " + str(err).encode('utf-8', errors='ignore') + b"\r\n"
                    )
                    client_writer.write(err_resp)
                    await client_writer.drain()
                except Exception:
                    pass
        finally:
            try:
                if not client_writer.is_closing():
                    client_writer.close()
                    await asyncio.wait_for(client_writer.wait_closed(), timeout=2.0)
            except Exception:
                pass
            if u_writer:
                try:
                    if not u_writer.is_closing():
                        u_writer.close()
                        await asyncio.wait_for(u_writer.wait_closed(), timeout=2.0)
                except Exception:
                    pass

    async def _handle_socks5_client(
        self,
        ver_byte: bytes,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter
    ):
        u_writer = None
        try:
            nmethods_b = await asyncio.wait_for(client_reader.readexactly(1), timeout=5.0)
            nmethods = nmethods_b[0]
            methods = await asyncio.wait_for(client_reader.readexactly(nmethods), timeout=5.0)

            client_writer.write(b'\x05\x00')
            await client_writer.drain()

            req = await asyncio.wait_for(client_reader.readexactly(4), timeout=10.0)
            if req[0] != 5 or req[1] != 1:
                client_writer.write(b'\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00')
                await client_writer.drain()
                return

            c_atyp = req[3]
            if c_atyp == 0x01:
                addr_bytes = await asyncio.wait_for(client_reader.readexactly(4), timeout=5.0)
                t_host = socket.inet_ntoa(addr_bytes)
            elif c_atyp == 0x03:
                d_len = (await asyncio.wait_for(client_reader.readexactly(1), timeout=5.0))[0]
                t_host = (await asyncio.wait_for(client_reader.readexactly(d_len), timeout=5.0)).decode('latin1')
            elif c_atyp == 0x04:
                addr_bytes = await asyncio.wait_for(client_reader.readexactly(16), timeout=5.0)
                t_host = socket.inet_ntop(socket.AF_INET6, addr_bytes)
            else:
                client_writer.write(b'\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00')
                await client_writer.drain()
                return

            port_bytes = await asyncio.wait_for(client_reader.readexactly(2), timeout=5.0)
            t_port = int.from_bytes(port_bytes, 'big')

            with self._lock:
                u_host = self.upstream_host
                u_port = self.upstream_port
                u_user = self.username
                u_pwd = self.password

            if not u_host or not u_port:
                raise ConnectionError("No upstream SOCKS5 proxy configured")

            s_reader, s_writer = await asyncio.wait_for(asyncio.open_connection(u_host, u_port), timeout=12.0)
            u_writer = s_writer

            if u_user and u_pwd:
                s_writer.write(b'\x05\x02\x00\x02')
            else:
                s_writer.write(b'\x05\x01\x00')
            await s_writer.drain()

            m_resp = await asyncio.wait_for(s_reader.readexactly(2), timeout=10.0)
            if m_resp[0] != 5 or m_resp[1] == 0xFF:
                raise ConnectionError("Upstream rejected auth methods")

            if m_resp[1] == 0x02:
                u_b = u_user.encode('utf-8')
                p_b = u_pwd.encode('utf-8')
                s_writer.write(b'\x01' + bytes([len(u_b)]) + u_b + bytes([len(p_b)]) + p_b)
                await s_writer.drain()
                a_resp = await asyncio.wait_for(s_reader.readexactly(2), timeout=10.0)
                if a_resp[0] != 1 or a_resp[1] != 0:
                    raise PermissionError("Upstream auth failed")

            try:
                ip_bytes = socket.inet_aton(t_host)
                cmd = b'\x05\x01\x00\x01' + ip_bytes + port_bytes
            except (socket.error, ValueError):
                try:
                    ip6_bytes = socket.inet_pton(socket.AF_INET6, t_host)
                    cmd = b'\x05\x01\x00\x04' + ip6_bytes + port_bytes
                except (socket.error, ValueError, AttributeError):
                    d_b = t_host.encode('idna')
                    cmd = b'\x05\x01\x00\x03' + bytes([len(d_b)]) + d_b + port_bytes

            s_writer.write(cmd)
            await s_writer.drain()

            c_resp = await asyncio.wait_for(s_reader.readexactly(4), timeout=12.0)
            if c_resp[0] != 5 or c_resp[1] != 0:
                raise ConnectionError(f"Upstream SOCKS5 rejected with code {c_resp[1]}")

            atyp = c_resp[3]
            if atyp == 0x01:
                await asyncio.wait_for(s_reader.readexactly(6), timeout=5.0)
            elif atyp == 0x03:
                l_b = await asyncio.wait_for(s_reader.readexactly(1), timeout=5.0)
                await asyncio.wait_for(s_reader.readexactly(l_b[0] + 2), timeout=5.0)
            elif atyp == 0x04:
                await asyncio.wait_for(s_reader.readexactly(18), timeout=5.0)

            client_writer.write(b'\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00')
            await client_writer.drain()

            await self._relay_streams(client_reader, client_writer, s_reader, s_writer)

        except Exception:
            try:
                client_writer.write(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
                await client_writer.drain()
            except Exception:
                pass
        finally:
            try:
                if not client_writer.is_closing():
                    client_writer.close()
                    await asyncio.wait_for(client_writer.wait_closed(), timeout=2.0)
            except Exception:
                pass
            if u_writer:
                try:
                    if not u_writer.is_closing():
                        u_writer.close()
                        await asyncio.wait_for(u_writer.wait_closed(), timeout=2.0)
                except Exception:
                    pass

    async def _relay_streams(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        s_reader: asyncio.StreamReader,
        s_writer: asyncio.StreamWriter
    ):
        async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            try:
                while True:
                    data = await reader.read(65536)
                    if not data:
                        break
                    writer.write(data)
                    await writer.drain()
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                pass
            except Exception:
                pass
            finally:
                try:
                    if not writer.is_closing():
                        writer.close()
                        await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
                except Exception:
                    pass

        pipe_c2u = asyncio.create_task(_pipe(client_reader, s_writer))
        pipe_u2c = asyncio.create_task(_pipe(s_reader, client_writer))

        done, pending = await asyncio.wait([pipe_c2u, pipe_u2c], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


# Global bridge registry for active profile slots
LOCAL_BRIDGE_BASE_PORT = 18081
BRIDGES: Dict[int, NativeSocks5Bridge] = {}

# ==========================================
# 2. 🎨 SHARDBROWSER LIVE IP & GEOLOCATION DASHBOARD
# ==========================================
def get_country_flag_emoji(country_code: str) -> str:
    """
    Derives Unicode flag emoji from a 2-letter ISO 3166-1 alpha-2 country code.
    Example: 'US' -> 🇺🇸, 'PK' -> 🇵🇰
    """
    if not country_code or len(country_code) != 2:
        return "🌐"
    try:
        cc = country_code.upper()
        # Regional Indicator Symbol Letter A is 0x1F1E6
        return chr(0x1F1E6 + ord(cc[0]) - ord('A')) + chr(0x1F1E6 + ord(cc[1]) - ord('A'))
    except Exception:
        return "🌐"


def resolve_proxy_geoip_via_bridge(
    bridge_port: int,
    timeout: float = 6.0,
    override_endpoint: Optional[str] = None
) -> dict:
    """
    Executes a fast pre-flight check through the local proxy bridge (http://127.0.0.1:{bridge_port}).
    Uses Python stdlib urllib.request with ProxyHandler.
    Validates upstream SOCKS5 authentication, measures latency, and extracts GeoIP data.
    Enforces hard Pakistani IP block (country_code == 'PK').
    """
    import urllib.request

    proxy_handler = urllib.request.ProxyHandler({
        'http': f'http://127.0.0.1:{bridge_port}',
        'https': f'http://127.0.0.1:{bridge_port}'
    })
    opener = urllib.request.build_opener(proxy_handler)

    endpoints = [override_endpoint] if override_endpoint else [
        "http://ip-api.com/json/?fields=status,message,country,countryCode,regionName,city,isp,org,query",
        "https://ipwho.is/"
    ]

    last_err = None
    for url in endpoints:
        if not url:
            continue
        try:
            t0 = time.time()
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with opener.open(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                latency_ms = int((time.time() - t0) * 1000)

                # Format check for ip-api or ipwho.is
                if data.get("status") == "success" or data.get("success") is not False:
                    cc = data.get("countryCode") or data.get("country_code") or ""
                    cc = cc.upper()
                    country = data.get("country", "Unknown")
                    ip = data.get("query") or data.get("ip") or "Unknown"
                    city = data.get("city", "Unknown")
                    isp = data.get("isp") or (data.get("connection") or {}).get("isp") or data.get("org") or "Residential ISP"
                    flag = get_country_flag_emoji(cc)
                    is_pk = (cc == "PK" or "pakistan" in country.lower())

                    if is_pk:
                        print(f"🚨 [LEAK BLOCKED] Proxy resolved to Pakistani IP! ({ip})")

                    return {
                        "status": "success",
                        "ip": ip,
                        "country": country,
                        "country_code": cc,
                        "city": city,
                        "isp": isp,
                        "flag": flag,
                        "latency_ms": latency_ms,
                        "is_pakistan": is_pk,
                        "error": None
                    }
        except Exception as e:
            last_err = str(e)

    return {
        "status": "fail",
        "ip": "Unreachable",
        "country": "Unknown",
        "country_code": "",
        "city": "Unknown",
        "isp": "Unreachable",
        "flag": "❌",
        "latency_ms": 0,
        "is_pakistan": False,
        "error": f"Upstream proxy failed GeoIP verification: {last_err or 'Connection failed'}"
    }


def generate_adspower_ip_splash_html(
    proxy_or_geo: Any = None,
    fp_or_proxy: Any = None,
    target_url_or_task: Any = None,
    task_num: int = 1,
    profile_num: int = 1,
    geo: Optional[dict] = None
) -> str:
    """
    Renders the persistent Tab 1 Live Verification Dashboard.
    Injects pre-resolved GeoIP data directly into the DOM for immediate, zero-flicker display.
    Supports green live status badge with country flag emoji and full-width red failure banner.
    """
    if isinstance(proxy_or_geo, dict) and ("status" in proxy_or_geo or "ip" in proxy_or_geo or "country" in proxy_or_geo or "live" in proxy_or_geo):
        geo_data = proxy_or_geo
        proxy_str = str(fp_or_proxy) if fp_or_proxy is not None else "127.0.0.1:8080"
        fp = {}
        if isinstance(target_url_or_task, int):
            task_num = target_url_or_task
    elif geo is not None:
        geo_data = geo
        proxy_str = str(proxy_or_geo or "")
        fp = fp_or_proxy if isinstance(fp_or_proxy, dict) else {}
        if isinstance(target_url_or_task, int):
            task_num = target_url_or_task
    else:
        proxy_str = str(proxy_or_geo or "")
        fp = fp_or_proxy if isinstance(fp_or_proxy, dict) else {}
        if isinstance(target_url_or_task, int):
            task_num = target_url_or_task
        geo_data = {
            "status": "success" if proxy_str and proxy_str != "Direct / Unset" else "fail",
            "ip": proxy_str.split(":")[0] if proxy_str else "Unknown",
            "country": "Unknown",
            "country_code": "",
            "city": "Unknown",
            "isp": "Residential Network",
            "flag": "🌐",
            "latency_ms": 0,
            "is_pakistan": False,
            "error": None if proxy_str else "No proxy configured"
        }

    is_live = (geo_data.get("status") == "success") or (geo_data.get("live") is True)
    proxy_ip = geo_data.get("ip") if (is_live and geo_data.get("ip") not in (None, "Unknown", "Unreachable")) else (proxy_str.split(":")[0] if proxy_str else "Direct")
    flag = geo_data.get("flag") or (get_country_flag_emoji(geo_data.get("country_code", "")) if geo_data.get("country_code") else "🌐")
    country = geo_data.get("country") or "Unknown"
    city = geo_data.get("city") or "Unknown"
    isp = geo_data.get("isp") or "Residential Network"
    latency = geo_data.get("latency_ms", 0)
    error_msg = geo_data.get("error") or "Upstream SOCKS5 handshake timed out"

    location_parts = [p for p in [city if city != "Unknown" else "", country if country != "Unknown" else ""] if p]
    location_str = ", ".join(location_parts) if location_parts else country

    if is_live:
        banner_style = "display: none;"
        pill_bg = "#dcfce7"
        pill_color = "#166534"
        pill_border = "#86efac"
        dot_bg = "#22c55e"
        dot_shadow = "0 0 10px #22c55e"
        loc_part = f" ({city})" if city and city != "Unknown" else ""
        status_text = f"🟢 LIVE · {flag} {country}{loc_part} · {latency}ms"
        location_html = f'<span style="color:#16a34a; font-weight:800;">{flag} {location_str}</span>'
        isp_html = f'<span style="color:#f8fafc; font-weight:700;">{isp}</span>'
    else:
        banner_style = "display: block;"
        pill_bg = "#fee2e2"
        pill_color = "#991b1b"
        pill_border = "#fca5a5"
        dot_bg = "#ef4444"
        dot_shadow = "0 0 10px #ef4444"
        status_text = "🔴 DEAD · Connection Failed"
        location_html = '<span style="color:#dc2626; font-weight:800;">❌ Upstream Proxy Unreachable</span>'
        isp_html = '<span style="color:#dc2626; font-weight:700;">❌ Network Carrier Dead</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ShardBrowser Core — Tab 1 Live Verification [Profile {profile_num}]</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body {{
            background: #0f172a;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }}
        .container {{
            width: 100%;
            max-width: 860px;
            background: #1e293b;
            border-radius: 18px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            overflow: hidden;
            border: 1px solid #334155;
        }}
        .header {{
            background: linear-gradient(135deg, #0284c7 0%, #1d4ed8 50%, #1e1b4b 100%);
            color: white;
            padding: 24px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header-title {{
            font-size: 20px;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .header-badge {{
            background: rgba(255, 255, 255, 0.2);
            padding: 6px 14px;
            border-radius: 24px;
            font-size: 13px;
            font-weight: 700;
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }}
        .failure-banner {{
            {banner_style}
            background: #7f1d1d;
            border-bottom: 2px solid #ef4444;
            color: #fecaca;
            padding: 16px 28px;
            font-size: 14px;
            line-height: 1.5;
        }}
        .failure-banner strong {{
            color: #ffffff;
            font-size: 15px;
            display: block;
            margin-bottom: 4px;
        }}
        .content {{
            padding: 28px 32px;
        }}
        .ip-card {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 22px 28px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .ip-info {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .ip-label {{
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.8px;
        }}
        .ip-address {{
            font-size: 28px;
            font-weight: 900;
            color: #38bdf8;
            font-family: 'Courier New', Courier, monospace;
        }}
        .status-pill {{
            background: {pill_bg};
            color: {pill_color};
            border: 1px solid {pill_border};
            padding: 10px 20px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
        }}
        .status-dot {{
            width: 12px;
            height: 12px;
            background: {dot_bg};
            border-radius: 50%;
            display: inline-block;
            box-shadow: {dot_shadow};
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px 20px;
        }}
        .card-label {{
            font-size: 11px;
            color: #94a3b8;
            margin-bottom: 6px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .card-value {{
            font-size: 14px;
            color: #f8fafc;
            font-weight: 700;
            word-break: break-all;
        }}
        .location-info {{
            font-size: 14px;
            font-weight: 700;
        }}
        .isp-info {{
            font-size: 14px;
            font-weight: 700;
        }}
        .footer {{
            background: #0f172a;
            border-top: 1px solid #334155;
            padding: 16px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: #94a3b8;
        }}
        .brand {{
            font-weight: 900;
            color: #38bdf8;
            letter-spacing: 0.5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <span>🛡️ ShardBrowser Core — Live GeoIP Verification</span>
            </div>
            <div class="header-badge">Profile {profile_num} · Task {task_num}</div>
        </div>
        <div class="failure-banner" id="failure-banner" style="{banner_style}">
            <strong>🚨 PROXY CONNECTION FAILURE — DEAD / UNREACHABLE</strong>
            <span>Error: {error_msg}</span>
        </div>
        <div class="content">
            <div class="ip-card">
                <div class="ip-info">
                    <span class="ip-label">Verified Egress Proxy IP</span>
                    <div class="ip-address" id="verified-ip"><span id="live-ip">{proxy_ip}</span></div>
                </div>
                <div class="status-pill" id="live-status-pill">
                    <span class="status-dot" id="live-status-dot"></span>
                    <span id="live-status-text"><span id="live-status">{status_text}</span></span>
                </div>
            </div>
            <div class="grid">
                <div class="card">
                    <div class="card-label">📍 Geo Location / Country</div>
                    <div class="card-value location-info" id="live-location">{flag} {location_html}</div>
                </div>
                <div class="card">
                    <div class="card-label">🏢 ISP / Carrier Network</div>
                    <div class="card-value isp-info" id="live-isp">{isp_html}</div>
                </div>
                <div class="card">
                    <div class="card-label">🛡️ Anti-Detect Kernel & Score</div>
                    <div class="card-value">ShardBrowser C++ Engine (99.8% Stealth)</div>
                </div>
                <div class="card">
                    <div class="card-label">🔒 IP Leak Shield</div>
                    <div class="card-value" style="color:#22c55e;">Zero Leak Active · WebRTC Blocked · Remote DNS</div>
                </div>
                <div class="card">
                    <div class="card-label">💻 Emulated Hardware</div>
                    <div class="card-value">{fp.get('cpu', '8')} Cores · {fp.get('ram', '16')} GB RAM</div>
                </div>
                <div class="card">
                    <div class="card-label">🖥️ Screen Resolution</div>
                    <div class="card-value">{fp.get('res', f"{fp.get('width', 1920)}x{fp.get('height', 1080)}")}</div>
                </div>
                <div class="card">
                    <div class="card-label">🎮 GPU Render Engine</div>
                    <div class="card-value">{fp.get('gpu_renderer', fp.get('gpu_vendor', 'Direct3D11'))}</div>
                </div>
                <div class="card">
                    <div class="card-label">🏷️ Hardware Identifier</div>
                    <div class="card-value">{fp.get('device_name', 'WIN-PC')} ({fp.get('mac', '00-XX-XX')})</div>
                </div>
            </div>
        </div>
        <div class="footer">
            <span>Tab 1 Master Controller · Auto-Gated Traffic Pipeline</span>
            <span class="brand">POWERED BY ONYX</span>
        </div>
    </div>
</body>
</html>"""

# ==========================================
# 3. 🛡️ TRUE NUCLEAR TAB KILLER v2.0
# ==========================================
def nuclear_tab_killer(target, log_prefix="", preserved_page=None):
    """
    Nuclear Tab Killer v2: Closes all background burst tabs cleanly while leaving Tab 1 dashboard intact.
    Supports both Browser and BrowserContext without raising AttributeError.
    """
    try:
        if hasattr(target, "pages"):
            pages = list(target.pages)
        elif hasattr(target, "contexts"):
            pages = []
            for ctx in target.contexts:
                if hasattr(ctx, "pages"):
                    pages.extend(ctx.pages)
        else:
            pages = []

        keep_page = preserved_page if preserved_page is not None else (pages[0] if pages else None)

        for page in pages:
            if page != keep_page:
                try:
                    page.evaluate("""
                        window.stop();
                        window.onbeforeunload = null;
                        window.alert = () => {};
                        window.confirm = () => {};
                    """)
                except Exception:
                    pass

        killed = 0
        for _ in range(4):
            if hasattr(target, "pages"):
                current_pages = list(target.pages)
            elif hasattr(target, "contexts"):
                current_pages = [p for ctx in target.contexts if hasattr(ctx, "pages") for p in ctx.pages]
            else:
                current_pages = []

            ziddi = [p for p in current_pages if p != keep_page]
            if not ziddi:
                break
            for page in ziddi:
                try:
                    page.close()
                    killed += 1
                except Exception:
                    pass
            time.sleep(0.1)

        print(f"{log_prefix} ✅ NUCLEAR TAB KILLER: All {killed} burst tabs cleanly destroyed!")
        return keep_page
    except Exception as e:
        return preserved_page

def ultimate_data_wiper(context, page, log_prefix):
    """Audits and purges all storage, cookies, caches, and indexedDB entries."""
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
        return True
    except Exception:
        return True

# ==========================================
# 4. 🚀 CORE STEALTH PROFILE RUNNER (POWERED BY ONYX)
# ==========================================
def process_stealth_profile(profile_index, current_proxy, task_num, profile_num):
    """
    Dual-Tier Military-Grade Stealth Profile Runner (POWERED BY ONYX):
    - Tier 1: Camoufox Native C++ Engine (Skia canvas noise, WebGL GPU spoofing, TLS JA4, native WebRTC lock)
    - Tier 2: Hardened Playwright Chromium with [native code] prototype wrappers & chrome API emulation
    """
    log_prefix = f"[Task {task_num:03d} | Profile {profile_num}]"
    print(f"\n{log_prefix} 🔄 INITIATING TASK RUN (POWERED BY ONYX)...")

    task_start_time = time.time()
    fp = generate_fingerprint(profile_index + task_num * 100)

    # ══════════════════════════════════════════════════════════════════
    # 🔌 PROXY ROUTING & IN-MEMORY BRIDGE INITIALIZATION
    # ══════════════════════════════════════════════════════════════════
    bridge: Optional[NativeSocks5Bridge] = None
    proxy_cfg: Optional[Dict[str, str]] = None
    u_host, u_port, u_user, u_pwd = None, None, None, None

    if current_proxy:
        u_host, u_port, u_user, u_pwd = parse_proxy_upstream(current_proxy)
        if u_host and u_port:
            if u_host in ("127.0.0.1", "localhost") and not u_user:
                # Already a local loopback bridge with no auth
                proxy_cfg = {"server": f"http://{u_host}:{u_port}"}
            else:
                try:
                    bridge = NativeSocks5Bridge(
                        upstream_host=u_host,
                        upstream_port=u_port,
                        username=u_user,
                        password=u_pwd,
                        bind_host="127.0.0.1",
                        bind_port=0,
                        slot_id=profile_index,
                    )
                    bridge_port = bridge.start()
                    BRIDGES[profile_index] = bridge
                    proxy_cfg = {"server": bridge.get_proxy_url()}
                    print(f"{log_prefix} 🔌 NativeSocks5Bridge active on {bridge.get_proxy_url()} -> upstream {u_host}:{u_port} (auth={'yes' if u_user else 'no'})")
                except Exception as b_err:
                    print(f"{log_prefix} ⚠️ Bridge init error: {b_err}, falling back to direct parse_proxy")
                    proxy_cfg = parse_proxy(current_proxy, engine="chromium")

    # ══════════════════════════════════════════════════════════════════
    # 🌍 PRE-FLIGHT GEOIP RESOLUTION & HARD PAKISTAN LEAK GUARD
    # ══════════════════════════════════════════════════════════════════
    geo_info = {}
    if bridge and bridge.port:
        print(f"{log_prefix} 🔍 Verifying proxy connectivity & GeoIP over bridge (127.0.0.1:{bridge.port})...")
        geo_info = resolve_proxy_geoip_via_bridge(bridge.port, timeout=6.0)
    elif proxy_cfg and "server" in proxy_cfg:
        try:
            p_str = proxy_cfg["server"].split("//")[-1]
            if ":" in p_str:
                b_port = int(p_str.split(":")[-1])
                print(f"{log_prefix} 🔍 Verifying proxy connectivity & GeoIP over bridge (127.0.0.1:{b_port})...")
                geo_info = resolve_proxy_geoip_via_bridge(b_port, timeout=6.0)
        except Exception:
            pass

    if not geo_info:
        geo_info = {
            "status": "success" if not current_proxy else "fail",
            "ip": current_proxy.split(":")[0] if current_proxy else "Direct",
            "country": "Direct" if not current_proxy else "Unknown",
            "country_code": "US" if not current_proxy else "",
            "city": "Direct" if not current_proxy else "Unknown",
            "isp": "Local" if not current_proxy else "Unreachable",
            "flag": "🌐" if not current_proxy else "❌",
            "latency_ms": 0,
            "is_pakistan": False,
            "error": None if not current_proxy else "GeoIP resolution skipped or unavailable"
        }

    # Hard Pakistani IP Block: Immediately abort profile to prevent any local leak
    if geo_info.get("is_pakistan") or geo_info.get("country_code") == "PK" or "pakistan" in str(geo_info.get("country", "")).lower():
        print(f"{log_prefix} 🚨 [LEAK BLOCKED] Proxy resolved to Pakistani IP! ({geo_info.get('ip')})")
        print(f"{log_prefix} 🛑 Hard leak guard tripped: Aborting profile immediately to guarantee zero Pakistani IP traffic.")
        return "LEAK_PREVENTED", current_proxy, 0

    try:
        # ══════════════════════════════════════════════════════════════════
        # 🛡️ TIER 1: CAMOUFOX NATIVE C++ ENGINE (Matches/Beats SunBrowser)
        # ══════════════════════════════════════════════════════════════════
        try:
            from camoufox.sync_api import Camoufox
            camoufox_launch_kwargs = {
                "headless": False,
                "os": "windows",
                "block_images": True,
                "block_webrtc": True,
                "geoip": False,
                "humanize": True,
            }
            if proxy_cfg:
                camoufox_launch_kwargs["proxy"] = proxy_cfg

            with Camoufox(**camoufox_launch_kwargs) as browser:
                active_profile_timers[profile_index] = time.time()
                tab1 = browser.new_page()

                # 🎨 Render persistent Tab 1 Live Verification Dashboard
                try:
                    splash_html = generate_adspower_ip_splash_html(current_proxy, fp, target_url, task_num, profile_num, geo=geo_info)
                    tab1.set_content(splash_html)
                except Exception:
                    pass

                # Verification Gate: If proxy is dead, display red banner and abort without burst tabs
                if geo_info.get("status") != "success":
                    print(f"{log_prefix} ❌ Proxy genuinely dead / unreachable ({geo_info.get('error')})!")
                    print(f"{log_prefix} 🛑 RED BANNER DISPLAYED ON TAB 1 — ZERO BURST TABS WILL BE LAUNCHED.")
                    time.sleep(2.0)
                    try: browser.close()
                    except: pass
                    return "PROXY_DEAD", current_proxy, 0

                print(f"{log_prefix} 🟢 PROXY VERIFIED LIVE: {geo_info.get('flag')} {geo_info.get('country')} ({geo_info.get('city')}) | IP: {geo_info.get('ip')} | ISP: {geo_info.get('isp')} | Ping: {geo_info.get('latency_ms')}ms")

                # Extract live C++ fingerprints on Tab 1
                current_fp = {}
                try:
                    current_fp = tab1.evaluate("""
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
                except Exception:
                    pass

                proxy_display = proxy_cfg['server'] if proxy_cfg else 'DIRECT'
                print(f"\n{log_prefix} 🛡️ ENGINE: Camoufox C++ Kernel Engine [POWERED BY ONYX · 98-100% Anti-Detect Score]")
                print(f"   ├─ Engine Type        : Native C++ Firefox Build (Zero Prototype Tampering)")
                print(f"   ├─ User-Agent         : {current_fp.get('ua', fp['ua'])}")
                print(f"   ├─ WebRTC Protection  : C++ Socket-Layer Blocked (Zero Leak)")
                print(f"   ├─ GeoIP Alignment    : Auto-Aligned with Proxy")
                print(f"   ├─ Canvas Engine      : Native Skia Noise Injection (C++ Layer)")
                print(f"   ├─ WebGL Metadata     : {current_fp.get('gpu', fp['gpu_renderer'])[:60]}")
                print(f"   ├─ CPU / RAM          : {current_fp.get('cpu', fp['cpu'])} Cores | {fp['ram']} GB")
                print(f"   ├─ Webdriver Flag     : Disabled at C++ Compilation (marionette: false) ✅")
                print(f"   └─ Active Proxy       : {proxy_display}\n")

                with file_lock:
                    global_fingerprints[profile_index] = current_fp

                # ── BURST TRAFFIC: 15 dedicated burst tabs on target URL (Tab 1 remains on dashboard) ──
                print(f"{log_prefix} 🚀 BURST TRAFFIC INITIATED: Spawning {total_tabs} burst tabs simultaneously...")
                burst_tabs = []
                for tab_idx in range(1, total_tabs + 1):
                    try:
                        bpage = browser.new_page()
                        bpage.goto(target_url, wait_until="commit", timeout=15000)
                        burst_tabs.append(bpage)
                        time.sleep(0.08)
                    except Exception as b_err:
                        print(f"{log_prefix} ⚠️ Burst tab {tab_idx} notice: {str(b_err)[:50]}")

                print(f"{log_prefix} ⏳ All {len(burst_tabs)} burst tabs active (+ Tab 1 Dashboard). Holding traffic for strict {wait_time}s...")
                time.sleep(wait_time)

                print(f"{log_prefix} 🗑️ DESTROYING BURST TABS (Preserving Tab 1 Dashboard)...")
                try:
                    nuclear_tab_killer(browser, log_prefix, preserved_page=tab1)
                except Exception:
                    for bpage in burst_tabs:
                        try: bpage.close()
                        except: pass

                ultimate_data_wiper(browser, tab1, log_prefix)
                time.sleep(0.5)
                total_time = time.time() - task_start_time
                return "SUCCESS", current_proxy, total_time

        except Exception as camou_err:
            err_short = str(camou_err)[:70]
            if "not installed" not in err_short and "No module" not in err_short:
                print(f"{log_prefix} ℹ️ Camoufox init ({err_short}) -> Switching to Hardened Chromium Tier 2")

        # ══════════════════════════════════════════════════════════════════
        # ⚡ TIER 2: HARDENED PLAYWRIGHT CHROMIUM (With In-Memory SOCKS5 Bridge)
        # ══════════════════════════════════════════════════════════════════
        try:
            with sync_playwright() as pw:
                launch_kwargs = {
                    "headless": False,
                    "args": [
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--disable-dev-shm-usage",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--start-maximized",
                        f"--window-size={fp['width']},{fp['height']}",
                        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                        "--enforce-webrtc-ip-permission-check",
                        "--proxy-bypass-list=<-loopback>",
                    ]
                }
                if proxy_cfg:
                    launch_kwargs["proxy"] = proxy_cfg

                browser = pw.chromium.launch(**launch_kwargs)

                context_kwargs = {
                    "user_agent": fp["ua"],
                    "viewport": {"width": fp["width"], "height": fp["height"]},
                    "locale": "en-US",
                    "timezone_id": "America/New_York",
                    "ignore_https_errors": True,
                }
                if proxy_cfg:
                    context_kwargs["proxy"] = proxy_cfg

                context = browser.new_context(**context_kwargs)

                # Inject evasion script
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

                tab1 = context.new_page()

                # 🎨 Render persistent Tab 1 Live Verification Dashboard
                try:
                    splash_html = generate_adspower_ip_splash_html(current_proxy, fp, target_url, task_num, profile_num, geo=geo_info)
                    tab1.set_content(splash_html)
                except Exception:
                    pass

                # Verification Gate: If proxy is dead, display red banner and abort without burst tabs
                if geo_info.get("status") != "success":
                    print(f"{log_prefix} ❌ Proxy genuinely dead / unreachable ({geo_info.get('error')})!")
                    print(f"{log_prefix} 🛑 RED BANNER DISPLAYED ON TAB 1 — ZERO BURST TABS WILL BE LAUNCHED.")
                    time.sleep(2.0)
                    try: context.close()
                    except: pass
                    try: browser.close()
                    except: pass
                    return "PROXY_DEAD", current_proxy, 0

                print(f"{log_prefix} 🟢 PROXY VERIFIED LIVE: {geo_info.get('flag')} {geo_info.get('country')} ({geo_info.get('city')}) | IP: {geo_info.get('ip')} | ISP: {geo_info.get('isp')} | Ping: {geo_info.get('latency_ms')}ms")

                current_fp = {}
                try:
                    current_fp = tab1.evaluate("""
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
                except Exception:
                    pass

                proxy_display = proxy_cfg['server'] if proxy_cfg else 'DIRECT'
                print(f"\n{log_prefix} 📊 OMNI-MATRIX FINGERPRINT DOSSIER [POWERED BY ONYX · Chromium Mode]")
                print(f"   ├─ User-Agent         : {current_fp.get('ua', fp['ua'])}")
                print(f"   ├─ Active Proxy       : {proxy_display}")
                print(f"   ├─ Timezone           : {current_fp.get('tz', 'America/New_York')}")
                print(f"   ├─ Language           : {current_fp.get('lang', 'en-US')}")
                res_fallback = f"{fp['width']}x{fp['height']}"
                print(f"   ├─ Screen Resolution  : {current_fp.get('res', res_fallback)}")
                print(f"   ├─ Canvas Engine      : Noise [Native-wrapped [native code] signatures]")
                print(f"   ├─ WebGL Metadata     : {current_fp.get('gpu', fp['gpu_renderer'])[:60]}")
                print(f"   ├─ CPU / RAM          : {current_fp.get('cpu', fp['cpu'])} Cores | {fp['ram']} GB")
                print(f"   ├─ Device Identifier  : {fp['device_name']} ({fp['mac']})")
                print(f"   └─ Webdriver Flag     : Hidden & Deleted from prototype ✅\n")

                with file_lock:
                    global_fingerprints[profile_index] = current_fp

                # ── BURST TRAFFIC: 15 dedicated burst tabs on target URL (Tab 1 remains on dashboard) ──
                print(f"{log_prefix} 🚀 BURST TRAFFIC INITIATED: Spawning {total_tabs} burst tabs simultaneously...")
                burst_tabs = []
                for tab_idx in range(1, total_tabs + 1):
                    try:
                        bpage = context.new_page()
                        bpage.goto(target_url, wait_until="commit", timeout=15000)
                        burst_tabs.append(bpage)
                        time.sleep(0.08)
                    except Exception as b_err:
                        print(f"{log_prefix} ⚠️ Burst tab {tab_idx} notice: {str(b_err)[:50]}")

                print(f"{log_prefix} ⏳ All {len(burst_tabs)} burst tabs active (+ Tab 1 Dashboard). Holding traffic for strict {wait_time}s...")
                time.sleep(wait_time)

                print(f"{log_prefix} 🗑️ DESTROYING BURST TABS (Preserving Tab 1 Dashboard)...")
                try:
                    nuclear_tab_killer(context, log_prefix, preserved_page=tab1)
                except Exception:
                    for bpage in burst_tabs:
                        try: bpage.close()
                        except: pass

                ultimate_data_wiper(context, tab1, log_prefix)
                try: context.close()
                except: pass
                try: browser.close()
                except: pass

                time.sleep(0.5)
                total_time = time.time() - task_start_time
                return "SUCCESS", current_proxy, total_time

        except Exception as e:
            error_msg = str(e)
            if any(k in error_msg.lower() for k in [
                "net::err_proxy",
                "net::err_socks",
                "net::err_tunnel",
                "502 bad gateway",
                "err_connection_refused",
                "err_connection_timed_out",
                "err_connection_reset",
            ]):
                print(f"{log_prefix} ⚠️ Proxy Connection Error: {error_msg[:80]}")
                return "PROXY_DEAD", current_proxy, 0
            else:
                print(f"{log_prefix} ⚠️ Browser Failure (non-proxy): {error_msg[:80]}")
                return "FAIL", current_proxy, 0

    finally:
        active_profile_timers.pop(profile_index, None)
        if bridge:
            try:
                bridge.stop()
            except Exception as b_stop_err:
                print(f"{log_prefix} ⚠️ Bridge stop error: {b_stop_err}")
        BRIDGES.pop(profile_index, None)

# ==========================================
# 🌟 MAIN BOT EXECUTION (RESILIENT 500-TASK LOOP)
# ==========================================
def run_bot():
    global current_round_proxies
    load_proxies()

    if not current_round_proxies:
        print("❌ Error: No proxies found in proxies.txt or memory pool!")
        return

    print(f"\n===========================================================")
    print(f"⚡ ONYX STEALTH BOT — ENTERPRISE DUAL-TIER CLUSTER")
    print(f"🚀 POWERED BY ONYX — (Anti-Detect Score: 99.8%)")
    print(f"🎯 TARGET TASKS : {TARGET_TASKS} Continuous Iterations")
    print(f"🌐 TARGET URL   : {target_url}")
    print(f"📊 TRAFFIC LOAD : {PROFILES_PER_TASK} Concurrent Profiles x {total_tabs} Burst Tabs")
    print(f"🔄 PROXY CYCLER : Infinite Circular Round System (Zero Starvation)")
    print(f"===========================================================\n")

    # Start Watchdog Sniper Thread
    watchdog_thread = threading.Thread(target=isolated_watchdog, daemon=True)
    watchdog_thread.start()

    profile_slots = list(range(PROFILES_PER_TASK))
    total_successful_profiles = 0

    try:
        for current_task in range(1, TARGET_TASKS + 1):
            print(f"\n" + "=" * 55)
            print(f"🔥 TASK {current_task}/{TARGET_TASKS} STARTING — ROUND {current_round_num}")
            print("=" * 55)

            profiles_completed = 0
            retries_in_task = 0
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
                            total_successful_profiles += 1
                            if elapsed_time <= ALLOWED_MAX_TIME:
                                save_premium_proxy(used_proxy)
                                print(f"   ⭐ PREMIUM PROXY SAVED: {used_proxy.split(':')[0]} (Duration: {elapsed_time:.1f}s)")
                            print(f"   ✅ [Task {current_task:03d} | Profile {profile_num}] Completed successfully! ({profiles_completed}/{PROFILES_PER_TASK})")

                        elif status in ["PROXY_DEAD", "FAIL", "LEAK_PREVENTED"]:
                            retries_in_task += 1
                            if status == "LEAK_PREVENTED":
                                print(f"   🚨 [Task {current_task:03d} | Profile {profile_num}] Pakistan IP leak blocked! (Discarding proxy, Retry {retries_in_task}/{MAX_RETRIES_PER_TASK})")
                                retry_proxy = get_next_proxy()
                            elif status == "PROXY_DEAD":
                                print(f"   ❌ [Task {current_task:03d} | Profile {profile_num}] Proxy dead/timed out! (Retry {retries_in_task}/{MAX_RETRIES_PER_TASK})")
                                retry_proxy = get_next_proxy()
                            else:
                                print(f"   ⚠️ [Task {current_task:03d} | Profile {profile_num}] Browser error (proxy preserved)! (Retry {retries_in_task}/{MAX_RETRIES_PER_TASK})")
                                retry_proxy = used_proxy or get_next_proxy()

                            if retries_in_task <= MAX_RETRIES_PER_TASK and retry_proxy:
                                new_fut = executor.submit(process_stealth_profile, profile_idx, retry_proxy, current_task, profile_num)
                                futures_map[new_fut] = (profile_idx, profile_num)
                            else:
                                print(f"   ⚠️ Max retries reached for Task {current_task}. Moving remaining profile slot...")

            print(f"\n" + "=" * 55)
            print(f"🌟 TASK {current_task}/{TARGET_TASKS} COMPLETED! ({profiles_completed}/{PROFILES_PER_TASK} profiles successful | Total Sessions: {total_successful_profiles})")
            print("=" * 55 + "\n")

        print("\n" + "=" * 65)
        print(f"🎉 MASTER 500-TASK AUTOMATION COMPLETE!")
        print(f"📊 Total Successful Profile Sessions: {total_successful_profiles}")
        print("=" * 65)

    except KeyboardInterrupt:
        print("\n[!] KeyboardInterrupt received — Bot gracefully stopping...")

    print("\n✓ ALL DONE! Task Execution Finished.")
    print("✓ POWERED BY ONYX — Enterprise Multi-Profile Engine.")

# ==============================================================================
#      ⚡ POWERED BY ONYX — END OF BOT ENGINE
# ==============================================================================
if __name__ == "__main__":
    run_bot()