#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
#      🚀 ADSPOWER SUNBROWSER MULTI-TAB TRAFFIC & IMPRESSION ENGINE
# ==============================================================================
# Full Integration with AdsPower Anti-Detect Browser (Local API: 127.0.0.1:50325)
# Features:
#   - Automated AdsPower profile creation, hardware mutation & CDP binding
#   - Zero WebRTC leaks (Native SunBrowser "webrtc": "proxy" routing)
#   - Tab 1 Live GeoIP Verification Dashboard (Country Flag, IP, City, ISP)
#   - 15 Concurrent Burst Tabs targeting OMG10 with 16-second strict dwell hold
#   - Full ad creative and impression loading (Unblocked images/fonts)
#   - Non-destructive sequential SOCKS5 proxy cycling across master pool
#   - True Nuclear Tab Killer v2 & CDP Storage Wiper (Zero residual tracking)
#   - Aggressive Watchdog Sniper Thread (Auto-kills hung profiles > 90s)
#   - Dynamic API key & configuration ingestion from orchestrator config
# ==============================================================================

import os
import sys
import time
import json
import random
import urllib.parse
import threading
import concurrent.futures
import requests
from typing import Optional, Dict, List, Tuple
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================
# ⚙️ 1. CONFIGURATION & RUNTIME SETTINGS
# ==========================================
DEFAULT_TARGET_URL = "https://omg10.com/4/11833046"
DEFAULT_TOTAL_TABS = 15
DEFAULT_WAIT_TIME = 16
DEFAULT_PROFILES_PER_TASK = 5
DEFAULT_TARGET_TASKS = 500
DEFAULT_API_URL = "http://local.adspower.net:50325"
DEFAULT_API_KEY = "8750c6512df828ca199ebc08a61f88b9009a97913cf6e860"

def load_runtime_config() -> dict:
    candidates = [
        os.path.join(BASE_DIR, "master_orchestrator", "orchestrator_config.json"),
        os.path.join(BASE_DIR, "orchestrator_config.json"),
        os.path.join(os.path.expanduser("~"), "Desktop", "master_orchestrator", "orchestrator_config.json"),
        os.path.join(os.path.expanduser("~"), "Desktop", "orchestrator_config.json"),
        r"C:\Automation\master_orchestrator\orchestrator_config.json",
        r"C:\Automation\orchestrator_config.json"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    print(f"[*] Loaded runtime config from {p}")
                    return cfg
            except Exception:
                pass
    return {}

runtime_cfg = load_runtime_config()

api_url = os.environ.get("ADSPOWER_API_URL", runtime_cfg.get("api_url", DEFAULT_API_URL)).rstrip("/")
api_key = os.environ.get("ADSPOWER_API_KEY", runtime_cfg.get("adspower_api_key", runtime_cfg.get("api_key", DEFAULT_API_KEY)))
target_url = os.environ.get("TARGET_URL", runtime_cfg.get("target_url", DEFAULT_TARGET_URL))
total_tabs = int(runtime_cfg.get("total_tabs", DEFAULT_TOTAL_TABS))
wait_time = int(runtime_cfg.get("wait_time_sec", runtime_cfg.get("wait_time", DEFAULT_WAIT_TIME)))
PROFILES_PER_TASK = int(runtime_cfg.get("profiles_per_task", DEFAULT_PROFILES_PER_TASK))
TARGET_TASKS = int(runtime_cfg.get("target_tasks", DEFAULT_TARGET_TASKS))

MAX_PROFILE_TIME = 90
ALLOWED_MAX_TIME = 60

PROXY_FILE = os.path.join(BASE_DIR, "proxies.txt")
PREMIUM_PROXY_FILE = os.path.join(BASE_DIR, "premium_proxies.txt")

headers = {
    "Authorization": f"Bearer {api_key}"
}

# ==========================================
# 🔒 SYNCHRONIZATION & STATE OBJECTS
# ==========================================
file_lock = threading.Lock()
api_lock = threading.Lock()
state_lock = threading.Lock()

master_proxy_pool: List[str] = []
proxy_cursor = 0
next_round_premium_proxies: List[str] = []

permanent_profiles: List[str] = []
previous_hardware_states: Dict[str, dict] = {}
global_fingerprints: Dict[str, dict] = {}
active_profile_timers: Dict[str, float] = {}

# ==========================================
# 🌐 OS-LEVEL HARDWARE RANDOMIZERS
# ==========================================
def generate_mac_address() -> str:
    return f"00-{random.randint(10,99):02X}-{random.choice(['FC','1E','1F'])}-{random.randint(10,99):02X}-{random.randint(10,99):02X}-{random.choice(['EB','7B','D7','E1','74'])}"

def generate_device_name() -> str:
    prefix = random.choice(["WIN", "LAPTOP", "DESKTOP", "PC"])
    suffix = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=7))
    return f"{prefix}-{suffix}"

# ==========================================
# 🚨 AGGRESSIVE WATCHDOG SNIPER THREAD
# ==========================================
def isolated_watchdog():
    while True:
        time.sleep(2)
        current_time = time.time()
        with state_lock:
            timers_copy = list(active_profile_timers.items())
        for pid, start_time in timers_copy:
            if current_time - start_time > MAX_PROFILE_TIME:
                print(f"\n🚨 WATCHDOG SNIPER: Profile {pid} slow hone ki wajah se kill ki gayi! ({MAX_PROFILE_TIME}s limit)")
                try:
                    requests.get(f"{api_url}/api/v1/browser/stop?user_id={pid}", headers=headers, timeout=5)
                except Exception:
                    pass
                with state_lock:
                    active_profile_timers.pop(pid, None)

# ==========================================
# 🔧 RESILIENT SOCKS5 PROXY POOL MANAGER
# ==========================================
def load_proxies():
    global master_proxy_pool, proxy_cursor
    master_proxy_pool = []
    
    candidate_paths = [
        PROXY_FILE,
        "proxies.txt",
        r"C:\Automation\proxies.txt",
        os.path.join(os.path.expanduser("~"), "Desktop", "proxies.txt")
    ]
    
    target_path = None
    for p in candidate_paths:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            target_path = p
            break
            
    if target_path:
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    master_proxy_pool.append(line)
        print(f"[*] Loaded {len(master_proxy_pool):,} proxies from {target_path}")
    else:
        print("[!] proxies.txt not found in candidate paths.")
        
    proxy_cursor = 0
    return master_proxy_pool

def get_next_proxy() -> Optional[str]:
    global proxy_cursor
    with file_lock:
        if not master_proxy_pool:
            return None
        proxy = master_proxy_pool[proxy_cursor % len(master_proxy_pool)]
        proxy_cursor += 1
        if proxy_cursor % len(master_proxy_pool) == 0:
            print(f"\n[🔄 MASTER POOL CYCLE] Completed full pass of {len(master_proxy_pool):,} proxies. Cycling again...")
        return proxy

def save_premium_proxy(proxy: str):
    with file_lock:
        if proxy not in next_round_premium_proxies:
            next_round_premium_proxies.append(proxy)
            try:
                with open(PREMIUM_PROXY_FILE, "a", encoding="utf-8") as f:
                    f.write(proxy + "\n")
            except Exception:
                pass

# ==========================================
# 🌍 GEOIP RESOLVER & SPLASH SCREEN
# ==========================================
def resolve_proxy_geoip(proxy_str: str) -> dict:
    parts = proxy_str.split(":")
    ip = parts[0]
    info = {
        "ip": ip,
        "country": "Protected",
        "countryCode": "US",
        "city": "Unknown",
        "isp": "Residential Network",
        "flag": "🌐"
    }
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,city,isp,query", timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                info["ip"] = data.get("query", ip)
                info["country"] = data.get("country", "Unknown")
                info["countryCode"] = data.get("countryCode", "US")
                info["city"] = data.get("city", "Unknown")
                info["isp"] = data.get("isp", "Residential Network")
                cc = info["countryCode"].upper()
                if len(cc) == 2:
                    info["flag"] = chr(ord(cc[0]) + 127397) + chr(ord(cc[1]) + 127397)
    except Exception:
        pass
    return info

def generate_adspower_ip_splash_html(geo: dict, status_text: str = "CONNECTED & PROTECTED") -> str:
    flag = geo.get("flag", "🌐")
    country = geo.get("country", "Protected")
    city = geo.get("city", "Unknown")
    ip = geo.get("ip", "Unknown")
    isp = geo.get("isp", "Residential Network")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AdsPower SunBrowser — Verification</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{
            background: linear-gradient(135deg, #0a0f1d 0%, #0d1b2a 50%, #1b263b 100%);
            color: #ffffff;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .card {{
            background: rgba(16, 28, 48, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(0, 150, 255, 0.25);
            border-radius: 20px;
            padding: 40px 50px;
            width: 580px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(0, 150, 255, 0.15);
            text-align: center;
        }}
        .badge {{
            display: inline-block;
            background: rgba(0, 230, 118, 0.15);
            color: #00e676;
            border: 1px solid #00e676;
            padding: 6px 16px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
            margin-bottom: 20px;
            text-transform: uppercase;
        }}
        .flag {{
            font-size: 64px;
            margin-bottom: 12px;
            filter: drop-shadow(0 4px 10px rgba(0,0,0,0.4));
        }}
        .country {{
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 6px;
        }}
        .city {{
            font-size: 16px;
            color: #00b4d8;
            margin-bottom: 25px;
            font-weight: 600;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            text-align: left;
            background: rgba(255, 255, 255, 0.03);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            margin-bottom: 25px;
        }}
        .item-label {{
            font-size: 11px;
            color: #8d99ae;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        .item-val {{
            font-size: 14px;
            font-weight: 700;
            color: #edf2f4;
            word-break: break-all;
        }}
        .engine {{
            font-size: 12px;
            color: #90e0ef;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .pulse {{
            width: 8px;
            height: 8px;
            background: #00e676;
            border-radius: 50%;
            box-shadow: 0 0 10px #00e676;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">{status_text}</div>
        <div class="flag">{flag}</div>
        <div class="country">{country}</div>
        <div class="city">{city}</div>
        
        <div class="grid">
            <div>
                <div class="item-label">Proxy IP</div>
                <div class="item-val">{ip}</div>
            </div>
            <div>
                <div class="item-label">ISP / Org</div>
                <div class="item-val">{isp}</div>
            </div>
            <div>
                <div class="item-label">WebRTC Protection</div>
                <div class="item-val" style="color: #00e676;">Zero-Leak Proxy</div>
            </div>
            <div>
                <div class="item-label">Engine</div>
                <div class="item-val" style="color: #00b4d8;">SunBrowser v128+</div>
            </div>
        </div>
        
        <div class="engine">
            <span class="pulse"></span> AdsPower Native Anti-Detect • Automated Traffic Ingestion
        </div>
    </div>
</body>
</html>"""
    return html

# ==========================================
# 🧹 2. TRUE NUCLEAR TAB KILLER & DATA WIPER
# ==========================================
def nuclear_tab_killer(context, log_prefix):
    try:
        fresh_page = context.new_page()
        for page in context.pages:
            if page != fresh_page:
                try:
                    page.evaluate("""() => {
                        window.stop();
                        window.onbeforeunload = null;
                        window.alert = () => {};
                        window.confirm = () => {};
                    }""")
                except Exception:
                    pass

        for _ in range(4):
            ziddi_tabs = [p for p in context.pages if p != fresh_page]
            if not ziddi_tabs:
                break
            for page in ziddi_tabs:
                try:
                    page.close()
                except Exception:
                    pass
            time.sleep(0.3)
            
        return fresh_page
    except Exception as e:
        print(f"{log_prefix} ❌ TAB KILLER NOTICE: {str(e)[:50]}")
        return context.pages[0] if context.pages else context.new_page()

def ultimate_data_wiper(context, page, log_prefix):
    try:
        context.clear_cookies()
        try:
            client = context.new_cdp_session(page)
            client.send("Network.clearBrowserCache")
            client.send("Network.clearBrowserCookies")
        except Exception:
            pass
        
        page.evaluate("""async () => {
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
            try {
                document.cookie.split(";").forEach(function(c) {
                    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
                });
            } catch(e) {}
        }""")
        return True
    except Exception:
        return True

# ==========================================
# ⚙️ 3. ZERO-WEAKNESS FINGERPRINT MUTATOR
# ==========================================
def update_profile_settings(profile_id: str, current_proxy: str, log_prefix: str) -> bool:
    proxy_parts = current_proxy.split(":")
    proxy_host = proxy_parts[0]
    proxy_port = proxy_parts[1]
    proxy_user = proxy_parts[2] if len(proxy_parts) > 2 else ""
    proxy_pass = proxy_parts[3] if len(proxy_parts) > 3 else ""

    resolutions = ["1920_1080", "1366_768", "1440_900", "1536_864", "1280_720", "1600_900", "2560_1440"]
    rams = ["4", "8", "16"]
    cpus = ["4", "6", "8", "12", "16"]
    gpus = [
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 (0x00001F51) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) HD Graphics 510 (0x00007DD5) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon(TM) Graphics (0x0000164E) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB (0x00001B83) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 600 (0x00003185) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 580 Series (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)")
    ]

    with file_lock:
        prev = previous_hardware_states.get(profile_id, {})
    
    new_res = random.choice(resolutions)
    new_cpu = random.choice(cpus)
    new_ram = random.choice(rams)
    new_gpu_vendor, new_gpu_renderer = random.choice(gpus)
    new_mac = generate_mac_address()
    new_device_name = generate_device_name()

    with file_lock:
        previous_hardware_states[profile_id] = {
            'res': new_res, 'cpu': new_cpu, 'ram': new_ram, 'gpu': new_gpu_renderer, 
            'mac': new_mac, 'device_name': new_device_name
        }

    update_payload = {
        "user_id": profile_id,
        "user_proxy_config": {
            "proxy_soft": "other",
            "proxy_type": "socks5", 
            "proxy_host": proxy_host,
            "proxy_port": proxy_port,
            "proxy_user": proxy_user,
            "proxy_password": proxy_pass
        },
        "fingerprint_config": {
            "automatic_timezone": "1",
            "language_switch": "0",
            "webrtc": "proxy",
            "canvas": "1",
            "webgl_image": "1",
            "audio": "1", 
            "client_rects": "0",
            "speech_switch": "0", 
            "mac_address": "0",
            "device_name_switch": "0", 
            "port_scan_protection": "1",
            "do_not_track": "default",
            "hardware_acceleration": "default",
            "screen_resolution": new_res, 
            "device_memory": new_ram, 
            "hardware_concurrency": new_cpu, 
            "webgl_vendor": new_gpu_vendor,
            "webgl_renderer": new_gpu_renderer,
            "random_ua": {"ua_browser": ["chrome"], "ua_system_version": ["Windows 10", "Windows 11"]}
        }
    }
    
    for attempt in range(3):
        with api_lock:
            try:
                res = requests.post(f"{api_url}/api/v1/user/update", json=update_payload, headers=headers, timeout=10).json()
                time.sleep(1)
                if res.get("code") == 0:
                    return True
                elif "Too many request" in str(res):
                    time.sleep(2)
                else:
                    break
            except Exception:
                time.sleep(2)
                continue
    return False

# ==========================================
# 🚀 4. CORE RECYCLED PROFILE WORKER & BURST TABS
# ==========================================
def process_recycled_profile(profile_id: str, current_proxy: str, task_num: int, profile_num: int) -> Tuple[str, str, float]:
    log_prefix = f"[Task {task_num} | Profile {profile_num}]"
    print(f"\n{log_prefix} 🔄 INITIALIZING ADSPOWER PROFILE...")

    task_start_time = time.time()

    if not update_profile_settings(profile_id, current_proxy, log_prefix):
        print(f"{log_prefix} ❌ Failed to configure AdsPower profile proxy settings.")
        return "PROXY_DEAD", current_proxy, 0.0

    try:
        with state_lock:
            active_profile_timers[profile_id] = time.time()
            
        start_response = None
        for _ in range(3):
            with api_lock:
                try:
                    start_response = requests.get(f"{api_url}/api/v1/browser/start?user_id={profile_id}", headers=headers, timeout=25).json()
                    time.sleep(1)
                except Exception:
                    start_response = {"code": -1}
                    time.sleep(2)
                    continue
            if start_response.get("code") == 0:
                break
            elif "Too many request" in str(start_response):
                time.sleep(2)
            else:
                break
                
        if not start_response or start_response.get("code") != 0:
            print(f"{log_prefix} ⚠️ Browser start error (Code {start_response.get('code') if start_response else 'None'}). Proxy unreachable.")
            try:
                requests.get(f"{api_url}/api/v1/browser/stop?user_id={profile_id}", headers=headers, timeout=5)
            except Exception:
                pass
            return "PROXY_DEAD", current_proxy, 0.0
            
        ws_endpoint = start_response["data"]["ws"]["puppeteer"]
        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(ws_endpoint, timeout=60000)
            context = browser.contexts[0]
            
            # Allow all standard resources so ad creatives and verification scripts load seamlessly
            def safe_route_interceptor(route):
                try:
                    route.continue_()
                except Exception:
                    pass
            try:
                context.route("**/*", safe_route_interceptor)
            except Exception:
                pass

            fresh_page = nuclear_tab_killer(context, log_prefix)
            
            # --- TAB 1: GEOIP LIVE VERIFICATION SPLASH ---
            geo_info = resolve_proxy_geoip(current_proxy)
            print(f"{log_prefix} 📍 Country: {geo_info['flag']} {geo_info['country']} ({geo_info['city']}) | IP: {geo_info['ip']} | ISP: {geo_info['isp']}")
            splash_html = generate_adspower_ip_splash_html(geo_info)
            try:
                fresh_page.goto("data:text/html;charset=utf-8," + urllib.parse.quote(splash_html), timeout=10000)
                time.sleep(2.0)  # Brief live verification display for RDP inspection
            except Exception:
                pass

            # Transition Tab 1 to target URL
            try:
                fresh_page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
            except Exception:
                pass
            
            ultimate_data_wiper(context, fresh_page, log_prefix)

            # --- BURST TRAFFIC TABS (Tabs 2 to 15) ---
            print(f"{log_prefix} 🚀 BURST TRAFFIC INITIATED: {total_tabs} Tabs launching on target URL...")
            for step in range(2, total_tabs + 1):
                try:
                    new_tab = context.new_page()
                    new_tab.goto(target_url, wait_until="commit", timeout=15000)
                    time.sleep(0.1)
                except Exception:
                    pass
            
            print(f"{log_prefix} ⏳ All {total_tabs} tabs firing complete. Maintaining active traffic... strict {wait_time}s dwell.")
            time.sleep(wait_time)
            
            print(f"{log_prefix} 🗑️ Burst hold completed. Closing profile safely.")
            try:
                nuclear_tab_killer(context, log_prefix)
            except Exception:
                pass
            
            try:
                browser.disconnect()
            except Exception:
                pass
            time.sleep(1)
            
            total_time = time.time() - task_start_time
            return "SUCCESS", current_proxy, total_time
            
    except Exception as e:
        print(f"{log_prefix} ⚠️ Exception encountered: {str(e)[:60]}")
        return "PROXY_DEAD", current_proxy, 0.0
        
    finally:
        with state_lock:
            active_profile_timers.pop(profile_id, None)
        for _ in range(3):
            try:
                res = requests.get(f"{api_url}/api/v1/browser/stop?user_id={profile_id}", headers=headers, timeout=5).json()
                if res.get("code") == 0:
                    break
            except Exception:
                pass
            time.sleep(1.5)

# ==========================================
# 🌟 5. MAIN ORCHESTRATION LOOP
# ==========================================
def run_bot():
    print(f"===========================================================")
    print(f"👑 ADSPOWER SUNBROWSER MASTER AUTOMATION")
    print(f"===========================================================")
    print(f"Target URL:        {target_url}")
    print(f"Target Tasks:      {TARGET_TASKS}")
    print(f"Profiles Per Task: {PROFILES_PER_TASK}")
    print(f"Tabs Per Profile:  {total_tabs}")
    print(f"Dwell / Hold Time: {wait_time}s")
    print(f"AdsPower API:      {api_url}")
    print(f"===========================================================\n")

    proxies = load_proxies()
    if not proxies:
        print("❌ Error: proxies.txt is empty or missing! Please provide proxies.")
        return

    # Check local AdsPower API status before proceeding
    print("🔍 Testing connection to AdsPower Local API (port 50325)...")
    api_ready = False
    for attempt in range(5):
        try:
            test_res = requests.get(f"{api_url}/api/v1/manager/active", headers=headers, timeout=5).json()
            if test_res.get("code") == 0 or "status" in test_res or "data" in test_res:
                api_ready = True
                print("✅ AdsPower Local API is LIVE and responsive!")
                break
        except Exception:
            pass
        print(f"   Waiting for AdsPower Local API... (Attempt {attempt+1}/5)")
        time.sleep(3)
        
    if not api_ready:
        print("⚠️ Warning: AdsPower Local API did not respond on /api/v1/manager/active.")
        print("   Proceeding with profile initialization attempts...")

    watchdog_thread = threading.Thread(target=isolated_watchdog, daemon=True)
    watchdog_thread.start()

    print("\n⏳ Initializing 5 Permanent Base Profiles in AdsPower...")
    for i in range(PROFILES_PER_TASK):
        payload = {
            "group_id": "0",
            "user_proxy_config": {"proxy_soft": "no_proxy"},
            "fingerprint_config": {
                "automatic_timezone": "1",
                "webrtc": "proxy",
                "random_ua": {"ua_browser": ["chrome"], "ua_system_version": ["Windows 10", "Windows 11"]}
            }
        }
        created = False
        for attempt in range(4):
            try:
                res = requests.post(f"{api_url}/api/v1/user/create", json=payload, headers=headers, timeout=12).json()
                if res.get("code") == 0:
                    pid = res["data"]["id"]
                    permanent_profiles.append(pid)
                    print(f"✓ Base Profile {i+1} Created in AdsPower: ID {pid}")
                    created = True
                    break
                elif "Too many request" in str(res):
                    time.sleep(2.5)
            except Exception:
                time.sleep(2)
        time.sleep(1.5)

    if len(permanent_profiles) < PROFILES_PER_TASK:
        print(f"\n❌ Error: Failed to initialize all {PROFILES_PER_TASK} base profiles (Created {len(permanent_profiles)}).")
        print("   Please verify AdsPower Desktop is logged in and API is enabled.")
        return

    print(f"\n🚀 ALL {len(permanent_profiles)} BASE PROFILES READY. STARTING 500-TASK LOOP!\n")

    try:
        for current_task in range(1, TARGET_TASKS + 1):
            print(f"\n=================================================")
            print(f"🔥 TASK {current_task} / {TARGET_TASKS} INITIATED")
            print(f"=================================================")

            profiles_completed = 0
            futures_map = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=PROFILES_PER_TASK) as executor:
                for i, profile_id in enumerate(permanent_profiles):
                    proxy = get_next_proxy()
                    if not proxy:
                        break
                    fut = executor.submit(process_recycled_profile, profile_id, proxy, current_task, i + 1)
                    futures_map[fut] = (profile_id, i + 1)

                while futures_map and profiles_completed < PROFILES_PER_TASK:
                    done, _ = concurrent.futures.wait(futures_map.keys(), return_when=concurrent.futures.FIRST_COMPLETED)

                    for fut in done:
                        profile_id, profile_num = futures_map.pop(fut)
                        try:
                            status, used_proxy, elapsed_time = fut.result()
                        except Exception as e:
                            status, used_proxy, elapsed_time = "PROXY_DEAD", "unknown", 0.0

                        if status == "SUCCESS":
                            profiles_completed += 1
                            if elapsed_time <= ALLOWED_MAX_TIME:
                                save_premium_proxy(used_proxy)
                                print(f"   ⭐ SPEED RECORD: Proxy saved to premium pool: {used_proxy.split(':')[0]} ({elapsed_time:.1f}s)")
                            print(f"   ✓ [Task {current_task} | Profile {profile_num}] Completed successfully! ({elapsed_time:.1f}s)")

                        elif status == "PROXY_DEAD":
                            print(f"   ❌ [Task {current_task} | Profile {profile_num}] Proxy failed/timed out. Discarding and rotating...")
                            new_proxy = get_next_proxy()
                            if new_proxy:
                                new_fut = executor.submit(process_recycled_profile, profile_id, new_proxy, current_task, profile_num)
                                futures_map[new_fut] = (profile_id, profile_num)

            print(f"\n=================================================")
            print(f"🌟 TASK {current_task} / {TARGET_TASKS} COMPLETED!")
            print(f"=================================================\n")

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user.")

    finally:
        print("\n[MASTER CLEANUP] Reclaiming AdsPower resources and deleting base profiles...")
        for pid in permanent_profiles:
            try:
                requests.get(f"{api_url}/api/v1/browser/stop?user_id={pid}", headers=headers, timeout=5)
            except Exception:
                pass
            time.sleep(1.0)
        try:
            requests.post(f"{api_url}/api/v1/user/delete", json={"user_ids": permanent_profiles}, headers=headers, timeout=15)
            print("✓ Deleted temporary base profiles from AdsPower.")
        except Exception:
            pass
        print("✓ All cleanup completed cleanly.")

if __name__ == "__main__":
    run_bot()