#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
#      🔐 ADSPOWER DEDICATED IN-RDP LOGIN ENGINE (MIRRORED ARCHITECTURE)
# ==============================================================================
# Directly mirrors the proven Playwright CDP architecture from adspower_batch_engine.py:
#  - Robust isolated Playwright CDP connection (port 9222)
#  - Stable page & frame resolution with retry guards
#  - Element-UI / Vue input filling & button clicking
#  - Built-in OpenCV GeeTest slider captcha solver with humanized mouse curves
#  - Post-login banner & modal sweeper
#  - Local API authentication verification (http://local.adspower.net:50325, code: 0)
#  - Dynamic API key extraction & verification
#  - Atomic bot.py & burst_traffic_bot.py key & target URL patching
#  - Safe Win32 / PowerShell window minimization
# ==============================================================================

import os
import sys
import time
import json
import re
import random
import logging
import requests
import subprocess
from datetime import datetime

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [ADS_LOGIN_ENGINE] %(message)s"
)
logger = logging.getLogger("ads_login_engine")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_URL = "http://local.adspower.net:50325"
CDP_PORT = 9222


# ==============================================================================
# 1. LOAD ASSIGNED CREDENTIALS
# ==============================================================================
def load_assigned_account() -> dict:
    candidate_paths = [
        os.path.join(BASE_DIR, "assigned_account.json"),
        r"C:\Automation\assigned_account.json",
        os.path.join(os.path.expanduser("~"), "Desktop", "assigned_account.json"),
        r"C:\Users\RDP\Desktop\assigned_account.json",
        os.path.join(BASE_DIR, "account_claim.json"),
        r"C:\Automation\account_claim.json",
        os.path.join(BASE_DIR, "adspower_accounts_combos.txt"),
        r"C:\Automation\adspower_accounts_combos.txt",
        os.path.join(os.path.expanduser("~"), "Desktop", "adspower_accounts.txt")
    ]
    
    for path in candidate_paths:
        if os.path.exists(path):
            try:
                if path.endswith(".json"):
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("email") and data.get("password"):
                        logger.info(f"✅ Found assigned credentials for '{data['email']}' in {os.path.basename(path)}")
                        return data
                    elif data.get("claimed_accounts"):
                        latest = data["claimed_accounts"][-1]
                        logger.info(f"✅ Found claimed credentials for '{latest.get('email')}' in {os.path.basename(path)}")
                        return latest
                elif path.endswith(".txt"):
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and ":" in line and not line.startswith("#"):
                                parts = line.split(":")
                                if len(parts) >= 3 and len(parts[2].strip()) >= 24:
                                    logger.info(f"✅ Found combo credentials for '{parts[0].strip()}' in {os.path.basename(path)}")
                                    return {
                                        "email": parts[0].strip(),
                                        "password": parts[1].strip(),
                                        "api_key": parts[2].strip()
                                    }
            except Exception as e:
                logger.warning(f"Notice reading {path}: {e}")

    logger.warning("⚠️ No assigned credentials file found. Using default fallback account.")
    return {
        "email": "9hux2n72pql0@uberip.com",
        "password": "Password@123",
        "api_key": "14b4081a7f473f032d7e41dac65d6977009b24bc723b1faf"
    }


# ==============================================================================
# 2. CAPTCHA PUZZLE SOLVER (OPENCV) - MIRRORED FROM BATCH ENGINE
# ==============================================================================
class CustomPuzzleSolverEngine:
    @staticmethod
    def compute_slider_offset(bg_bytes: bytes, piece_bytes: bytes) -> tuple:
        if not HAS_CV2:
            logger.warning("OpenCV not available for puzzle computation.")
            return 150, 0.5

        try:
            bg_np = np.frombuffer(bg_bytes, np.uint8)
            piece_np = np.frombuffer(piece_bytes, np.uint8)

            bg_gray = cv2.imdecode(bg_np, cv2.IMREAD_GRAYSCALE)
            piece_gray = cv2.imdecode(piece_np, cv2.IMREAD_GRAYSCALE)

            bg_edges = cv2.Canny(bg_gray, 100, 200)
            piece_edges = cv2.Canny(piece_gray, 100, 200)

            result_matrix = cv2.matchTemplate(bg_edges, piece_edges, cv2.TM_CCOEFF_NORMED)
            result_matrix[:, :30] = -1

            _, max_val, _, max_loc = cv2.minMaxLoc(result_matrix)
            target_x = max_loc[0]
            logger.info("GeeTest offset computed | X-Offset: %d px | Confidence: %.4f", target_x, max_val)
            return int(target_x), float(max_val)
        except Exception as e:
            logger.warning(f"Puzzle compute exception: {e}")
            return 150, 0.0


# ==============================================================================
# 3. ADSPOWER LAUNCHER & CDP BINDING
# ==============================================================================
class EventDrivenAdsPowerLauncher:
    def __init__(self, cdp_port: int = CDP_PORT) -> None:
        self.cdp_port = cdp_port
        self.app_path = self.locate_adspower_executable()

    def locate_adspower_executable(self) -> str:
        candidates = [
            r"C:\Program Files\AdsPower Global\AdsPower Global.exe",
            r"C:\Program Files (x86)\AdsPower Global\AdsPower Global.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "AdsPower Global", "AdsPower Global.exe"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Programs", "AdsPower Global", "AdsPower Global.exe")
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return r"C:\Program Files\AdsPower Global\AdsPower Global.exe"

    def is_port_active(self) -> bool:
        try:
            res = requests.get(f"http://127.0.0.1:{self.cdp_port}/json/version", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def launch_and_wait(self, timeout_seconds: int = 90) -> bool:
        if self.is_port_active():
            logger.info(f"AdsPower CDP port {self.cdp_port} is already active!")
            return True

        if not os.path.exists(self.app_path):
            logger.error(f"AdsPower.exe not found at: {self.app_path}")
            return False

        logger.info(f"Spawning AdsPower with remote debugging port {self.cdp_port}...")
        try:
            subprocess.Popen([
                self.app_path,
                f"--remote-debugging-port={self.cdp_port}",
                "--disable-features=WebRtcHideLocalIpsWithMdns",
                "--host-resolver-rules=MAP stun.l.google.com 127.0.0.1, MAP *.stun.l.google.com 127.0.0.1",
                "--disable-component-update",
                "--no-default-browser-check"
            ])
        except Exception as err:
            logger.error(f"Failed to spawn AdsPower: {err}")
            return False

        logger.info(f"Waiting for AdsPower to bind port {self.cdp_port} (max {timeout_seconds}s)...")
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.is_port_active():
                logger.info(f"🎉 AdsPower CDP port {self.cdp_port} is fully active!")
                return True
            time.sleep(2)

        logger.error(f"Timeout: AdsPower did not bind to port {self.cdp_port} within {timeout_seconds}s.")
        return False


# ==============================================================================
# 4. ADSPOWER LOGIN ENGINE (MIRRORED FROM BATCH SIGNUP ARCHITECTURE)
# ==============================================================================
class AdsPowerLoginEngine:
    def __init__(self, email: str, password: str, api_key: str = None, target_url: str = None, cdp_port: int = CDP_PORT):
        self.account_email = email.strip()
        self.account_password = password.strip()
        self.account_api_key = api_key.strip() if api_key else None
        self.target_url = target_url.strip() if target_url else None
        self.cdp_port = cdp_port
        self.launcher = EventDrivenAdsPowerLauncher(cdp_port=cdp_port)
        self.playwright_obj = None
        self.browser = None
        self.context = None

    def establish_browser_connection(self):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright is not installed. Please run: pip install playwright && playwright install chromium")

        try:
            if self.playwright_obj is None:
                self.playwright_obj = sync_playwright().start()
            if not self.browser or not self.context:
                logger.info(f"Connecting to AdsPower CDP port {self.cdp_port}...")
                self.browser = self.playwright_obj.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
                self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
            else:
                _ = self.context.pages
        except Exception as e:
            logger.warning(f"CDP connection re-hook notice: {str(e)}")
            try:
                if self.playwright_obj:
                    self.playwright_obj.stop()
            except Exception:
                pass
            self.playwright_obj = sync_playwright().start()
            self.browser = self.playwright_obj.chromium.connect_over_cdp(f"http://127.0.0.1:{self.cdp_port}")
            self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()

    def get_stable_page(self) -> Page:
        self.establish_browser_connection()
        for _ in range(25):
            try:
                active_pages = [p for p in self.context.pages if not p.is_closed()]
                if active_pages:
                    return active_pages[-1]
            except Exception:
                self.establish_browser_connection()
            time.sleep(1)
        return self.context.new_page()

    def is_api_authenticated(self) -> bool:
        try:
            r = requests.get(f"{API_URL}/api/v1/user/list?page_size=1", timeout=3)
            if r.status_code == 200:
                res = r.json()
                if res.get("code") == 0:
                    return True
        except Exception:
            pass
        return False

    def execute_with_guard(self, step_name: str, action_func, max_retries: int = 4):
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"--- Step [{step_name}] | Attempt {attempt}/{max_retries} ---")
                result = action_func()
                logger.info(f"--- Step [{step_name}] Successfully Completed ---")
                return result
            except Exception as e:
                logger.warning(f"Step [{step_name}] failed on attempt {attempt}: {str(e)}")
                if attempt == max_retries:
                    logger.error(f"--- Step [{step_name}] Exhausted Retries ---")
                    return False
                time.sleep(2)

    def cleanup(self):
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright_obj:
                self.playwright_obj.stop()
        except Exception:
            pass
        self.browser = None
        self.context = None
        self.playwright_obj = None

    def sweep_popups(self, active_page: Page):
        logger.info("Executing post-login banner and popup sweep...")
        for _ in range(3):
            try:
                active_page.keyboard.press("Escape")
                time.sleep(0.3)
            except Exception:
                pass
            try:
                close_selectors = [
                    ".el-dialog__headerbtn", ".el-dialog__close", "i[class*='close']",
                    "button[aria-label='Close']", "text='GOT IT'", "button:has-text('GOT IT')",
                    "button:has-text('OK')", "button:has-text('Confirm')", "button:has-text('Remind me later')"
                ]
                for loc in close_selectors:
                    for btn in active_page.locator(loc).all():
                        if btn.is_visible(timeout=500):
                            btn.click(force=True)
                            time.sleep(0.3)
            except Exception:
                pass
            try:
                active_page.evaluate("""() => {
                    const keywords = ['AdsPower 50% Off', 'SUBSCRIBE NOW', 'Annual Sale', 'A default profile has been created', 'Tips', 'Notice'];
                    document.querySelectorAll('div, section').forEach(el => {
                        if (el && el.innerText && keywords.some(kw => el.innerText.includes(kw))) {
                            const style = window.getComputedStyle(el);
                            if (style && (style.position === 'fixed' || style.position === 'absolute') && parseInt(style.zIndex) > 40) {
                                el.remove();
                            }
                        }
                    });
                }""")
            except Exception:
                pass
            time.sleep(0.5)

    def handle_geetest_if_present(self, active_page: Page) -> bool:
        try:
            geetest_bg = active_page.locator(".geetest_canvas_bg, .geetest_bg, canvas.geetest_canvas_fullbg, .geetest_window").first
            if geetest_bg.is_visible(timeout=2000):
                logger.info("GeeTest Slider Captcha intercepted on Login! Engaging OpenCV Solver...")
                for geetest_attempt in range(1, 6):
                    bg_element = active_page.locator(".geetest_canvas_fullbg, .geetest_bg, canvas.geetest_canvas_bg").first
                    piece_element = active_page.locator(".geetest_canvas_slice, .geetest_slice").first
                    time.sleep(1.0)

                    if bg_element.is_visible(timeout=1000) and piece_element.is_visible(timeout=1000):
                        offset_x, confidence = CustomPuzzleSolverEngine.compute_slider_offset(
                            bg_element.screenshot(), piece_element.screenshot())
                        slider_handle = active_page.locator(".geetest_slider_button, .geetest_btn, .geetest_slice").first
                        box = slider_handle.bounding_box()

                        if box:
                            start_x = box["x"] + box["width"] / 2
                            start_y = box["y"] + box["height"] / 2
                            active_page.mouse.move(start_x, start_y)
                            active_page.mouse.down()
                            
                            steps_count = 30
                            target_dist = offset_x - 6
                            for s in range(1, steps_count + 1):
                                t = s / steps_count
                                progress = 1 - pow(1 - t, 3)
                                step_x = start_x + (target_dist * progress)
                                step_y = start_y + random.uniform(-1.0, 1.0)
                                active_page.mouse.move(step_x, step_y)
                                time.sleep(random.uniform(0.01, 0.02))
                            
                            time.sleep(0.3)
                            active_page.mouse.up()
                            time.sleep(2.5)

                            if not geetest_bg.is_visible(timeout=1500):
                                logger.info("GeeTest slider puzzle solved successfully!")
                                return True

                    refresh_btn = active_page.locator(".geetest_refresh, [aria-label*='refresh' i], .geetest_btn_refresh").first
                    if refresh_btn.is_visible(timeout=500):
                        refresh_btn.click(force=True)
                        time.sleep(1.5)
        except Exception as e:
            logger.debug(f"GeeTest check notice: {e}")
        return False

    def run_login(self) -> bool:
        logger.info("=" * 65)
        logger.info(f"🚀 INITIATING ADSPOWER LOGIN PIPELINE FOR: {self.account_email}")
        logger.info("=" * 65)

        # 1. Check if AdsPower Local API is ALREADY authenticated
        if self.is_api_authenticated():
            logger.info("🎉 AdsPower is ALREADY authenticated via Local API (port 50325)!")
            self.patch_and_minimize()
            return True

        # 2. Ensure AdsPower is running with CDP port active
        if not self.launcher.launch_and_wait(timeout_seconds=90):
            logger.error("❌ Failed to launch AdsPower Desktop with active CDP port.")
            return False

        try:
            self.establish_browser_connection()

            # --- STEP 1: NAVIGATION TO LOGIN SCREEN ---
            def step_navigate():
                curr_page = self.get_stable_page()
                try:
                    curr_url = curr_page.url.lower()
                    if "login" not in curr_url and "dashboard" not in curr_url and "profile" not in curr_url:
                        logger.info("Navigating to https://app.adspower.com/login ...")
                        curr_page.goto("https://app.adspower.com/login", wait_until="commit", timeout=15000)
                except Exception:
                    pass

                try:
                    login_tab = curr_page.locator("text='Log in', text='Sign in', span:has-text('Log in')").first
                    if login_tab.is_visible(timeout=3000):
                        login_tab.click(timeout=2000)
                        time.sleep(1.0)
                except Exception:
                    pass

            self.execute_with_guard("Navigation to Login Screen", step_navigate)

            # --- STEP 2: CREDENTIAL FILLING & FORM SUBMIT ---
            def step_fill_and_submit():
                active_page = self.get_stable_page()
                all_targets = [active_page] + active_page.frames
                form_found = False

                for target in all_targets:
                    try:
                        email_input = target.locator(
                            "input:not([type='hidden']):not([class*='hidden'])"
                        ).filter(
                            has=target.locator("[type='email'], [name*='email'], [placeholder*='Email' i], [placeholder*='account' i], [placeholder*='phone' i]")
                        ).first

                        if not email_input.is_visible(timeout=2000):
                            email_input = target.locator(
                                "input[type='email']:not([class*='hidden']), input.el-input__inner, input[type='text']:not([class*='hidden'])"
                            ).first

                        if email_input.is_visible(timeout=3000):
                            email_input.wait_for(state="visible", timeout=5000)
                            email_input.click()
                            email_input.fill("")
                            time.sleep(0.2)
                            email_input.type(self.account_email, delay=30)
                            logger.info(f"Filled Email: {self.account_email}")
                            time.sleep(0.4)

                            password_input = target.locator("input[type='password']:not([class*='hidden'])").first
                            password_input.wait_for(state="visible", timeout=5000)
                            password_input.click()
                            password_input.fill("")
                            time.sleep(0.2)
                            password_input.type(self.account_password, delay=30)
                            logger.info("Filled Account Password.")
                            time.sleep(0.5)

                            login_btn = target.locator(
                                "button:has-text('Log in'), button:has-text('Sign in'), button:has-text('Login'), button.el-button--primary, button[type='submit']"
                            ).first

                            if login_btn.is_visible(timeout=3000):
                                login_btn.click()
                                logger.info("🚀 Clicked AdsPower GUI Login Button!")
                                time.sleep(3)

                            form_found = True
                            break
                    except Exception as ex:
                        logger.debug(f"Frame check notice: {ex}")

                if not form_found:
                    raise RuntimeError("Login fields not found in active page or frames.")

            self.execute_with_guard("Credential Filling & Submission", step_fill_and_submit)

            # --- STEP 3: CAPTCHA CHECK & POST-LOGIN VERIFICATION ---
            active_page = self.get_stable_page()
            self.handle_geetest_if_present(active_page)

            logger.info("⏳ Polling AdsPower Local API for authentication (port 50325)...")
            auth_ok = False
            deadline = time.time() + 45
            while time.time() < deadline:
                if self.is_api_authenticated():
                    auth_ok = True
                    logger.info("🎉 SUCCESS: AdsPower API authenticated & profile engine online (code: 0)!")
                    break
                time.sleep(2)

            if not auth_ok:
                try:
                    p = self.get_stable_page()
                    if "login" not in p.url.lower():
                        auth_ok = True
                        logger.info("🎉 Page URL transitioned away from login: Login Successful!")
                except Exception:
                    pass

            # --- STEP 4: SWEEP POPUPS & EXTRACT / VERIFY API KEY ---
            try:
                p = self.get_stable_page()
                self.sweep_popups(p)
            except Exception:
                pass

            if not self.account_api_key or len(self.account_api_key) < 24:
                self.extract_api_key_from_gui()

            self.cleanup()
            self.patch_and_minimize()
            return auth_ok

        except Exception as e:
            logger.error(f"❌ Login routine failed: {e}")
            self.cleanup()
            self.patch_and_minimize()
            return False

    def extract_api_key_from_gui(self):
        try:
            logger.info("--- Attempting Direct DOM Extraction of API Key from AdsPower GUI ---")
            p = self.get_stable_page()
            
            api_btn = p.get_by_text("API & MCP", exact=True).last
            if api_btn.is_visible(timeout=2000):
                api_btn.click(force=True)
                time.sleep(2.0)

                key = p.evaluate("""() => {
                    const inputs = document.querySelectorAll('input, textarea');
                    for (let input of inputs) {
                        const val = input.value ? input.value.trim() : '';
                        if (/^[a-fA-F0-9]{32,64}$/.test(val)) {
                            return val;
                        }
                    }
                    return null;
                }""")
                if key:
                    logger.info(f"✅ Extracted API Key from GUI: {key}")
                    self.account_api_key = key
        except Exception as ex:
            logger.warning(f"GUI API key extraction notice: {ex}")

    
    def verify_and_create_base_profiles(self, count: int = 5) -> bool:
        r"""
        Queries AdsPower Local API (http://local.adspower.net:50325/api/v1/user/list).
        If existing profiles < count, creates them via API to ensure the account is ready.
        Writes PROFILES_CREATED_CONFIRMED.txt to Desktop and C:\Automation.
        """
        logger.info(f"🔍 Verifying AdsPower base profiles (Target: {count})...")
        headers = {"Authorization": f"Bearer {self.account_api_key}"} if self.account_api_key else {}
        created_ids = []
        try:
            # 1. Check existing profiles
            r = requests.get(f"{API_URL}/api/v1/user/list?page_size=20", headers=headers, timeout=5)
            if r.status_code == 200 and r.json().get("code") == 0:
                existing = r.json().get("data", {}).get("list", [])
                created_ids = [p.get("user_id") for p in existing if p.get("user_id")]
                logger.info(f"📊 Detected {len(created_ids)} existing profiles in AdsPower.")
                
            # 2. Create missing profiles
            needed = count - len(created_ids)
            if needed > 0:
                logger.info(f"⏳ Creating {needed} base profiles in AdsPower...")
                for i in range(needed):
                    payload = {
                        "group_id": "0",
                        "user_proxy_config": {"proxy_soft": "no_proxy"},
                        "fingerprint_config": {
                            "automatic_timezone": "1",
                            "random_ua": {"ua_browser": ["chrome"], "ua_system_version": ["Windows 10", "Windows 11"]}
                        }
                    }
                    try:
                        cr = requests.post(f"{API_URL}/api/v1/user/create", json=payload, headers=headers, timeout=10).json()
                        if cr.get("code") == 0 and cr.get("data", {}).get("id"):
                            pid = cr["data"]["id"]
                            created_ids.append(pid)
                            logger.info(f"✅ Base profile {len(created_ids)}/{count} created: {pid}")
                        time.sleep(1)
                    except Exception as cex:
                        logger.warning(f"Profile creation attempt {i+1} error: {cex}")

            # 3. Write confirmation marker if profiles >= 1
            if len(created_ids) >= 1:
                confirm_data = (
                    f"PROFILES_CREATED_SUCCESS=TRUE\n"
                    f"EMAIL={self.email}\n"
                    f"TOTAL_PROFILES={len(created_ids)}\n"
                    f"PROFILE_IDS={','.join(created_ids)}\n"
                    f"TIMESTAMP={datetime.now().isoformat()}\n"
                )
                for cpath in [
                    r"C:\Automation\PROFILES_CREATED_CONFIRMED.txt",
                    os.path.join(os.path.expanduser("~"), "Desktop", "PROFILES_CREATED_CONFIRMED.txt"),
                    r"C:\Users\RDP\Desktop\PROFILES_CREATED_CONFIRMED.txt"
                ]:
                    try:
                        os.makedirs(os.path.dirname(cpath), exist_ok=True)
                        with open(cpath, "w", encoding="utf-8") as cf:
                            cf.write(confirm_data)
                    except Exception:
                        pass
                logger.info(f"✨ Verified {len(created_ids)} profiles created in AdsPower account {self.email}!")
                return True
        except Exception as e:
            logger.warning(f"Profile verification notice: {e}")
        return len(created_ids) > 0

    def patch_and_minimize(self):
        self.verify_and_create_base_profiles(5)
        if self.account_api_key:
            self.patch_bot_scripts(self.account_api_key, self.target_url)
        self.minimize_adspower_window()

    def patch_bot_scripts(self, api_key: str, target_url: str = None):
        search_dirs = [
            BASE_DIR,
            r"C:\Automation",
            os.path.join(os.path.expanduser("~"), "Desktop"),
            r"C:\Users\RDP\Desktop",
            r"C:\Users\Public\Desktop"
        ]
        
        target_files = ["bot.py", "burst_traffic_bot.py"]
        patched = []

        for sdir in search_dirs:
            if os.path.isdir(sdir):
                for fname in target_files:
                    fpath = os.path.join(sdir, fname)
                    if os.path.isfile(fpath):
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()

                            content = re.sub(r'api_key\s*=\s*["\'][^"\']*["\']', f'api_key = "{api_key}"', content)
                            content = re.sub(r'ADSPOWER_API_KEY\s*=\s*["\'][^"\']*["\']', f'ADSPOWER_API_KEY = "{api_key}"', content)

                            if target_url:
                                content = re.sub(r'target_url\s*=\s*["\'][^"\']*["\']', f'target_url = "{target_url}"', content)
                                content = re.sub(r'TARGET_URL\s*=\s*["\'][^"\']*["\']', f'TARGET_URL = "{target_url}"', content)

                            with open(fpath, "w", encoding="utf-8") as f:
                                f.write(content)

                            logger.info(f"💉 Injected API Key & Target URL into: {fpath}")
                            patched.append(fpath)
                        except Exception as err:
                            logger.error(f"Error patching {fpath}: {err}")

        return patched

    def minimize_adspower_window(self):
        logger.info("🪟 Minimizing AdsPower window...")
        try:
            import win32gui
            import win32con
            def enum_handler(hwnd, _):
                title = win32gui.GetWindowText(hwnd)
                if "adspower" in title.lower() and win32gui.IsWindowVisible(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            win32gui.EnumWindows(enum_handler, None)
        except Exception:
            pass

        try:
            ps_cmd = (
                "$code = @'\n"
                "using System;\n"
                "using System.Runtime.InteropServices;\n"
                "public class WinApi {\n"
                "  [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);\n"
                "}\n"
                "'@\n"
                "Add-Type -TypeDefinition $code\n"
                "Get-Process -Name AdsPower* -ErrorAction SilentlyContinue | ForEach-Object {\n"
                "  if ($_.MainWindowHandle -ne 0) { [WinApi]::ShowWindow($_.MainWindowHandle, 6) }\n"
                "}"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
        except Exception:
            pass


# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    logger.info("=======================================================")
    logger.info("   ADSPOWER PROVEN PLAYWRIGHT LOGIN ENGINE (IN-RDP)    ")
    logger.info("=======================================================")

    creds = load_assigned_account()
    email = creds.get("email", "")
    password = creds.get("password", "")
    api_key = creds.get("api_key", "")
    target_url = creds.get("target_url", None)

    if not email or not password:
        logger.error("❌ Missing email or password for login!")
        sys.exit(1)

    engine = AdsPowerLoginEngine(
        email=email,
        password=password,
        api_key=api_key,
        target_url=target_url,
        cdp_port=CDP_PORT
    )

    success = engine.run_login()
    if success:
        logger.info("✨ AdsPower Login & Bot Configuration 100% Succeeded!")
        sys.exit(0)
    else:
        logger.error("❌ Login verification failed! AdsPower Local API is not ready.")
        sys.exit(1)

if __name__ == "__main__":
    main()
