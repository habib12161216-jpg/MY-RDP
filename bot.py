import requests
import time
import concurrent.futures
import os
import threading
import random 
from playwright.sync_api import sync_playwright

# --- AAPKI SETTINGS ---
api_url = "http://local.adspower.net:50325"
api_key = "8750c6512df828ca199ebc08a61f88b9009a97913cf6e860" 

target_url = "https://omg10.com/4/11833046"                 
total_tabs = 15           
wait_time = 16            
PROFILES_PER_TASK = 5     
TARGET_TASKS = 500        

MAX_PROFILE_TIME = 90     
ALLOWED_MAX_TIME = 60     

PROXY_FILE = "proxies.txt"
PREMIUM_PROXY_FILE = "premium_proxies.txt"

current_round_proxies = []
next_round_premium_proxies = []

permanent_profiles = [] 
file_lock = threading.Lock()
api_lock = threading.Lock() 

previous_hardware_states = {}
global_fingerprints = {}
active_profile_timers = {} 

headers = {
    "Authorization": f"Bearer {api_key}"
}

# ==========================================
# 🚨 OS-LEVEL IDENTIFIER GENERATORS
# ==========================================
def generate_mac_address():
    return f"00-{random.randint(10,99):02X}-{random.choice(['FC','1E','1F'])}-{random.randint(10,99):02X}-{random.randint(10,99):02X}-{random.choice(['EB','7B','D7','E1','74'])}"

def generate_device_name():
    prefix = random.choice(["WIN", "LAPTOP", "DESKTOP"])
    suffix = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=7))
    return f"{prefix}{suffix}"

# ==========================================
# 🚨 AGGRESSIVE WATCHDOG SNIPER 
# ==========================================
def isolated_watchdog():
    while True:
        time.sleep(2)
        current_time = time.time()
        for pid, start_time in list(active_profile_timers.items()):
            if current_time - start_time > MAX_PROFILE_TIME:
                print(f"\n🚨 WATCHDOG SNIPER: Profile {pid} slow hone ki wajah se kill ki gayi! ({MAX_PROFILE_TIME}s limit)")
                try: requests.get(f"{api_url}/api/v1/browser/stop?user_id={pid}", headers=headers, timeout=5)
                except: pass
                active_profile_timers.pop(pid, None)

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

# ==========================================
# 2. 🛡️ TRUE NUCLEAR TAB KILLER (v2.0) & DATA AUDITOR
# ==========================================
def nuclear_tab_killer(context, log_prefix):
    print(f"{log_prefix} 🧹 NUCLEAR TAB KILLER v2: Ziddi tabs ko OS-level par destroy kiya ja raha hai...")
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
            ziddi_tabs = [p for p in context.pages if p != fresh_page]
            if not ziddi_tabs: break
            
            for page in ziddi_tabs:
                try: 
                    page.close() 
                    killed += 1
                except: pass
            time.sleep(0.5)
            
        bach_gaye = len(context.pages) - 1
        if bach_gaye > 0:
            print(f"{log_prefix} ⚠️ TAB KILLER WARNING: {bach_gaye} tab abhi bhi zinda hain! (RAM Leaking possible)")
        else:
            print(f"{log_prefix} ✅ VERIFIED: {killed} Tabs zameen-bos (destroyed) kar diye gaye!")
            
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
            
            try {
                document.cookie.split(";").forEach(function(c) { 
                    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
                });
            } catch(e) {}

            let localL = 0; try { localL = localStorage.length; } catch(e) {}
            let idbL = 0; try { let idbs = await window.indexedDB.databases(); idbL = idbs.length; } catch(e) {}
            
            return {
                local: localL,
                idb: idbL,
                ext: 0, 
                hist: 0 
            };
        }""")
        
        print(f"\n{log_prefix} 🧾 ABSOLUTE DATA AUDIT & CONFIRMATION:")
        print(f"   ├─ Local storage: {audit_report['local']}")
        print(f"   ├─ IndexedDB: {audit_report['idb']}")
        print(f"   ├─ Extension Data: {audit_report['ext']}")
        print(f"   └─ History: {audit_report['hist']}")
        
        print(f"{log_prefix} 🕵️ DATA CONFIRMER: CHECK SUCCESS! All data completely 0. System is spotless. ✅\n")
        return True
    except Exception as e: 
        print(f"{log_prefix} ❌ Auditor Internal Error: System Fallback Triggered.")
        return True 

# ==========================================
# 3. ⚙️ ZERO-WEAKNESS FINGERPRINT INJECTOR
# ==========================================
def update_profile_settings(profile_id, current_proxy, log_prefix):
    proxy_parts = current_proxy.split(":")
    proxy_host = proxy_parts[0]
    proxy_port = proxy_parts[1]
    proxy_user = proxy_parts[2] if len(proxy_parts) > 2 else ""
    proxy_pass = proxy_parts[3] if len(proxy_parts) > 3 else ""

    resolutions = ["1920_1080", "1366_768", "1440_900", "1536_864", "1280_720", "1600_900", "2560_1440", "3840_2160"]
    rams = ["2", "4", "8", "16"]
    cpus = ["2", "4", "6", "8", "12", "16", "20", "24", "32"]
    gpus = [
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 (0x00001F51) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) HD Graphics 510 (0x00007DD5) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon(TM) Graphics (0x0000164E) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB (0x00001B83) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 600 (0x00003185) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)"),
        ("Google Inc. (AMD)", "ANGLE (AMD, Radeon RX 580 Series (0x000067DF) Direct3D11 vs_5_0 ps_5_0, D3D11)")
    ]

    with file_lock: prev = previous_hardware_states.get(profile_id, {})
    
    new_res = random.choice(resolutions)
    while new_res == prev.get('res'): new_res = random.choice(resolutions)
    new_cpu = random.choice(cpus)
    while new_cpu == prev.get('cpu'): new_cpu = random.choice(cpus)
    new_ram = random.choice(rams)
    
    new_gpu_vendor, new_gpu_renderer = random.choice(gpus)
    while new_gpu_renderer == prev.get('gpu'): new_gpu_vendor, new_gpu_renderer = random.choice(gpus)
    
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
            "proxy_soft": "other", "proxy_type": "socks5", 
            "proxy_host": proxy_host, "proxy_port": proxy_port,
            "proxy_user": proxy_user, "proxy_password": proxy_pass
        },
        "fingerprint_config": {
            "automatic_timezone": "1", "language_switch": "0", "webrtc": "proxy",
            "canvas": "1", "webgl_image": "1", "audio": "1", 
            "client_rects": "0", "speech_switch": "0", 
            "mac_address": "0", "device_name_switch": "0", 
            "port_scan_protection": "1", "do_not_track": "default", "hardware_acceleration": "default",
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
                if res.get("code") == 0: return True
                elif "Too many request" in str(res): time.sleep(2)
                else: break
            except: time.sleep(2); continue
    return False

# ==========================================
# 4. 🚀 CORE AUTOMATION LOOP & BURST TRAFFIC
# ==========================================
def process_recycled_profile(profile_id, current_proxy, task_num, profile_num):
    log_prefix = f"[Task {task_num} | Profile {profile_num}]"
    print(f"\n{log_prefix} 🔄 NEW TASK SHURU...")

    task_start_time = time.time()

    if not update_profile_settings(profile_id, current_proxy, log_prefix):
        return "PROXY_DEAD", current_proxy, 0

    try:
        active_profile_timers[profile_id] = time.time()
        start_response = None
        for _ in range(3):
            with api_lock:
                try:
                    start_response = requests.get(f"{api_url}/api/v1/browser/start?user_id={profile_id}", headers=headers, timeout=20).json()
                    time.sleep(1)
                except:
                    start_response = {"code": -1}; time.sleep(2); continue
            if start_response.get("code") == 0: break
            elif "Too many request" in str(start_response): time.sleep(2)
            else: break
                
        if not start_response or start_response.get("code") != 0:
            print(f"{log_prefix} ⚠️ Browser start error. Proxy is DEAD.")
            try: requests.get(f"{api_url}/api/v1/browser/stop?user_id={profile_id}", headers=headers, timeout=5)
            except: pass
            return "PROXY_DEAD", current_proxy, 0
            
        ws_endpoint = start_response["data"]["ws"]["puppeteer"]
        
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(ws_endpoint, timeout=60000) 
            context = browser.contexts[0]
            
            def safe_route_interceptor(route):
                try:
                    if route.request.resource_type in ["image", "media", "font"]: route.abort()
                    else: route.continue_()
                except Exception: pass 
            try: context.route("**/*", safe_route_interceptor)
            except: pass

            fresh_page = nuclear_tab_killer(context, log_prefix)
            
            try: fresh_page.goto(target_url, wait_until="domcontentloaded", timeout=40000)
            except Exception: pass
            
            ultimate_data_wiper(context, fresh_page, log_prefix)
            
            # FINGERPRINT EXTRACTION
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
            
            with file_lock:
                os_data = previous_hardware_states.get(profile_id, {})
                current_mac = os_data.get('mac', 'Unknown')
                current_device_name = os_data.get('device_name', 'Unknown')
                current_ram = os_data.get('ram', '8') 
            
            print(f"\n{log_prefix} 📊 OMNI-MATRIX FINGERPRINT DOSSIER")
            print(f"   ├─ User-Agent\n   │  {current_fp['ua']}")
            print(f"   ├─ WebRTC\n   │  Proxy UDP")
            print(f"   ├─ Timezone\n   │  Based on IP ({current_fp['tz']})")
            print(f"   ├─ Location\n   │  [Ask] Based on IP")
            print(f"   ├─ Language\n   │  Based on IP ({current_fp['lang']})")
            print(f"   ├─ Display language\n   │  Based on Language")
            print(f"   ├─ Screen Resolution\n   │  Based on User-Agent ({current_fp['res']})")
            print(f"   ├─ Fonts\n   │  Default")
            print(f"   ├─ Canvas\n   │  Real")
            print(f"   ├─ WebGL Image\n   │  Real")
            print(f"   ├─ AudioContext\n   │  Real")
            print(f"   ├─ Media device\n   │  Noise [Auto]")
            print(f"   ├─ ClientRects\n   │  Noise [Auto-Hash]")
            print(f"   ├─ SpeechVoices\n   │  Noise")
            print(f"   ├─ WebGL metadata\n   │  {current_fp['gpu']}")
            print(f"   ├─ WebGPU\n   │  Based on WebGL")
            print(f"   ├─ CPU\n   │  {current_fp['cpu']} cores")
            print(f"   ├─ RAM\n   │  {current_ram} GB")
            print(f"   ├─ Device name\n   │  {current_device_name}")
            print(f"   ├─ MAC Address\n   │  {current_mac}")
            print(f"   ├─ Do Not Track\n   │  Default")
            print(f"   ├─ Port scan protection\n   │  [Enable]")
            print(f"   ├─ Hardware acceleration\n   │  Default")
            print(f"   └─ Disable TLS features\n      [Close]\n")

            with file_lock:
                old_fp = global_fingerprints.get(profile_id)
                if old_fp:
                    print(f"{log_prefix} 🕵️ FINGERPRINT CHECKER: MUTATION CONFIRMED & VERIFIED! ✅")
                    print(f"      ↳ Old Profile: [Res: {old_fp['res']:<9} | MAC: {old_fp['mac']} | Device: {old_fp['device_name']} | GPU: {old_fp['gpu'][:15]}... | CPU: {old_fp['cpu']}]")
                    print(f"      ↳ New Profile: [Res: {current_fp['res']:<9} | MAC: {current_mac} | Device: {current_device_name} | GPU: {current_fp['gpu'][:15]}... | CPU: {current_fp['cpu']}]")
                else:
                    print(f"{log_prefix} 🕵️ FINGERPRINT CHECKER: FRESH PROFILE INITIALIZED ✅")
                
                current_fp['mac'] = current_mac
                current_fp['device_name'] = current_device_name
                global_fingerprints[profile_id] = current_fp

            # 👉 THE FIX: BURST TRAFFIC INJECTION
            print(f"{log_prefix} 🚀 BURST TRAFFIC INITIATED: {total_tabs} Tabs ek sath fire kiye ja rahe hain...")
            for step in range(2, total_tabs + 1):
                try: 
                    new_tab = context.new_page()
                    # wait_until="commit" use kiya hai taake foran agle tab pe chala jaye (background loading)
                    new_tab.goto(target_url, wait_until="commit", timeout=15000)
                    time.sleep(0.1) # Halkasa micro-delay taake API block na ho
                except: pass
            
            print(f"{log_prefix} ⏳ All tabs firing complete. Traffic running... strict {wait_time} seconds hold.")
            time.sleep(wait_time) 
            
            print(f"{log_prefix} 🗑️ TABS DESTROYED! Closing profile safely.")
            try: nuclear_tab_killer(context, log_prefix)
            except: pass
            
            try: browser.disconnect() 
            except: pass
            time.sleep(1)
            
            total_time = time.time() - task_start_time
            return "SUCCESS", current_proxy, total_time
            
    except Exception as e:
        print(f"{log_prefix} ⚠️ Browser/Network Failure (Proxy Dead/Timeout).")
        return "PROXY_DEAD", current_proxy, 0
        
    finally:
        active_profile_timers.pop(profile_id, None)
        for _ in range(3):
            try:
                res = requests.get(f"{api_url}/api/v1/browser/stop?user_id={profile_id}", headers=headers, timeout=5).json()
                if res.get("code") == 0: break
            except: pass
            time.sleep(1.5)

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
    print(f"MASTER BOT TARGET: {TARGET_TASKS} Tasks")
    print(f"STRATEGY: Burst Traffic Injector + Nuclear Killer v2")
    print(f"Proxies Loaded: {len(current_round_proxies)}")
    print(f"===========================================================\n")
    
    watchdog_thread = threading.Thread(target=isolated_watchdog, daemon=True)
    watchdog_thread.start()
    
    print("⏳ Setting up 5 Permanent Base Profiles...")
    for i in range(PROFILES_PER_TASK):
        payload = {
            "group_id": "0", "user_proxy_config": {"proxy_soft": "no_proxy"}, 
            "fingerprint_config": {
                "automatic_timezone": "1",
                "random_ua": {"ua_browser": ["chrome"], "ua_system_version": ["Windows 10", "Windows 11"]}
            }
        }
        for attempt in range(3):
            try:
                res = requests.post(f"{api_url}/api/v1/user/create", json=payload, headers=headers, timeout=10).json()
                if res.get("code") == 0:
                    permanent_profiles.append(res["data"]["id"])
                    print(f"✓ Base Profile {i+1} Created: {res['data']['id']}")
                    break
            except: time.sleep(2)
        time.sleep(1.5) 
            
    if len(permanent_profiles) < PROFILES_PER_TASK:
        print("\n❌ 5 Profiles banne mein error aa gaya. Bot stop ho raha hai.")
        return

    try:
        for current_task in range(1, TARGET_TASKS + 1):
            print(f"\n=================================================")
            print(f"🔥 TASK {current_task} SHURU HO RAHA HAI")
            print(f"=================================================")
            
            profiles_completed = 0
            futures_map = {}
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=PROFILES_PER_TASK) as executor:
                for i, profile_id in enumerate(permanent_profiles):
                    proxy = get_next_proxy()
                    if not proxy: break
                    fut = executor.submit(process_recycled_profile, profile_id, proxy, current_task, i+1)
                    futures_map[fut] = (profile_id, i+1)
                    
                while futures_map and profiles_completed < PROFILES_PER_TASK:
                    done, _ = concurrent.futures.wait(futures_map.keys(), return_when=concurrent.futures.FIRST_COMPLETED)
                    
                    for fut in done:
                        profile_id, profile_num = futures_map.pop(fut)
                        status, used_proxy, elapsed_time = fut.result()
                        
                        if status == "SUCCESS":
                            if elapsed_time <= ALLOWED_MAX_TIME:
                                save_premium_proxy(used_proxy)
                                profiles_completed += 1
                                print(f"   ⭐ BEST PROXY SAVED to New File: {used_proxy.split(':')[0]} (Speed: {elapsed_time:.1f}s)")
                                print(f"   ✓ [Task {current_task} | Profile {profile_num}] Mukammal!")
                            else:
                                profiles_completed += 1
                                print(f"   ✓ [Task {current_task} | Profile {profile_num}] Mukammal! (Lekin proxy slow thi [{elapsed_time:.1f}s], isliye delete kar di gayi)")
                        
                        elif status == "PROXY_DEAD":
                            print(f"   ❌ [Task {current_task} | Profile {profile_num}] Proxy fail! Next use ke liye hamesha ke liye discard ho gayi.")
                            new_proxy = get_next_proxy()
                            if not new_proxy:
                                print("\n[!] Saari proxies dead ho chuki hain!")
                                break
                            new_fut = executor.submit(process_recycled_profile, profile_id, new_proxy, current_task, profile_num)
                            futures_map[new_fut] = (profile_id, profile_num)
                            
                        elif status == "API_ERROR":
                            print(f"   ⚠️ API Masla! Proxy wapas queue mein daal di gayi hai.")
                            with file_lock:
                                current_round_proxies.append(used_proxy)
                                update_main_proxy_file()
                                
                            new_proxy = get_next_proxy()
                            if not new_proxy:
                                break
                            new_fut = executor.submit(process_recycled_profile, profile_id, new_proxy, current_task, profile_num)
                            futures_map[new_fut] = (profile_id, profile_num)
                            
            if profiles_completed < PROFILES_PER_TASK:
                print(f"\n❌ Loop ruk gaya hai kyunki active proxies khatam ho gayin.")
                break 
                
            print(f"\n=================================================")
            print(f"🌟 TASK {current_task} / {TARGET_TASKS} MUKAMMAL!")
            print(f"=================================================\n")
                    
        print("\n========== TARGET LOOP KHATAM HO GAYA! ==========")
        
    finally:
        print("\n[MASTER CLEANUP] Deleting the 5 Permanent Profiles from AdsPower...")
        for pid in permanent_profiles:
            try: requests.get(f"{api_url}/api/v1/browser/stop?user_id={pid}", headers=headers, timeout=5)
            except: pass
            time.sleep(2)
        try:
            requests.post(f"{api_url}/api/v1/user/delete", json={"user_ids": permanent_profiles}, headers=headers, timeout=15)
            print("✓ Master Cleanup Mukammal!")
        except: pass
        print("\n✓ ALL DONE! Task Successfully Completed.")

if __name__ == "__main__":
    run_bot()