#!/usr/bin/env python3
"""
Enhanced Roblox Automation Tool (Rejoiner.py)
Supports: UGPHONE, VSPHONE, REDFINGER, Standard Android/Emulators
Author: Optimized for reliable deep link joining
"""

import requests
import time
import os
import json
import subprocess
import urllib.parse
import re
import threading
import sys
from datetime import datetime

# Configuration
COLORS = {
    "RESET": "\033[0m",
    "INFO": "\033[94m",
    "SUCCESS": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "BOLD": "\033[1m",
    "CYAN": "\033[96m",
    "HEADER": "\033[95m"
}

CONFIG_FILE = "/sdcard/roblox_config.json"
ROBLOX_PACKAGE = "com.roblox.client"

# Global variables
automation_running = False
platform_info = None
last_game_join_time = None

# Platform Detection
class PlatformDetector:
    def __init__(self):
        self.detected_platform = None
    
    def detect_platform(self):
        try:
            if self._is_ugphone():
                self.detected_platform = {
                    'type': 'ugphone',
                    'name': 'UGPHONE',
                    'has_root': self._check_root_ugphone(),
                    'use_adb': False,
                    'shell_prefix': '',
                    'special_commands': True
                }
                print_formatted("INFO", f"Platform detected: {self.detected_platform['name']}")
                return self.detected_platform
            
            if self._is_vsphone():
                self.detected_platform = {
                    'type': 'vsphone',
                    'name': 'VSPHONE',
                    'has_root': self._check_root_vsphone(),
                    'use_adb': False,
                    'shell_prefix': '',
                    'special_commands': True
                }
                print_formatted("INFO", f"Platform detected: {self.detected_platform['name']}")
                return self.detected_platform
            
            if self._is_redfinger():
                self.detected_platform = {
                    'type': 'redfinger',
                    'name': 'REDFINGER',
                    'has_root': self._check_root_standard(),
                    'use_adb': True,
                    'shell_prefix': 'su -c',
                    'special_commands': False
                }
                print_formatted("INFO", f"Platform detected: {self.detected_platform['name']}")
                return self.detected_platform
            
            self.detected_platform = {
                'type': 'standard',
                'name': 'Standard Android',
                'has_root': self._check_root_standard(),
                'use_adb': True,
                'shell_prefix': 'su -c',
                'special_commands': False
            }
            print_formatted("INFO", f"Platform detected: {self.detected_platform['name']}")
            return self.detected_platform
            
        except Exception as e:
            print_formatted("ERROR", f"Platform detection error: {str(e)}")
            self.detected_platform = {
                'type': 'unknown',
                'name': 'Unknown Platform',
                'has_root': False,
                'use_adb': False,
                'shell_prefix': '',
                'special_commands': False
            }
            return self.detected_platform
    
    def _is_ugphone(self):
        try:
            indicators = [
                '/system/bin/ugphone',
                '/system/app/UGPhone',
                '/data/local/tmp/ugphone'
            ]
            for indicator in indicators:
                if os.path.exists(indicator):
                    return True
            build_info = self._get_build_prop()
            ugphone_patterns = ['ugphone', 'ug_phone', 'cloudphone']
            for pattern in ugphone_patterns:
                if pattern.lower() in build_info.lower():
                    return True
            return False
        except:
            return False
    
    def _is_vsphone(self):
        try:
            indicators = [
                '/system/bin/vsphone',
                '/system/app/VSPhone',
                '/data/local/tmp/vsphone'
            ]
            for indicator in indicators:
                if os.path.exists(indicator):
                    return True
            build_info = self._get_build_prop()
            vsphone_patterns = ['vsphone', 'vs_phone', 'virtualphone']
            for pattern in vsphone_patterns:
                if pattern.lower() in build_info.lower():
                    return True
            return False
        except:
            return False
    
    def _is_redfinger(self):
        try:
            indicators = [
                '/system/bin/redfinger',
                '/system/app/RedFinger',
                '/data/local/tmp/redfinger'
            ]
            for indicator in indicators:
                if os.path.exists(indicator):
                    return True
            build_info = self._get_build_prop()
            redfinger_patterns = ['redfinger', 'red_finger', 'redcloud']
            for pattern in redfinger_patterns:
                if pattern.lower() in build_info.lower():
                    return True
            return False
        except:
            return False
    
    def _get_build_prop(self):
        try:
            result = subprocess.run(['cat', '/system/build.prop'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout
        except:
            return ""
    
    def _check_root_standard(self):
        try:
            result = subprocess.run(['su', '-c', 'echo test'], 
                                  capture_output=True, text=True, timeout=5)
            return 'test' in result.stdout
        except:
            return False
    
    def _check_root_ugphone(self):
        try:
            if self._check_root_standard():
                return True
            result = subprocess.run(['ugphone_su', '-c', 'echo test'], 
                                  capture_output=True, text=True, timeout=5)
            return 'test' in result.stdout
        except:
            return False
    
    def _check_root_vsphone(self):
        try:
            if self._check_root_standard():
                return True
            result = subprocess.run(['vsphone_su', '-c', 'echo test'], 
                                  capture_output=True, text=True, timeout=5)
            return 'test' in result.stdout
        except:
            return False

# Core Functions
def print_formatted(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = {
        "INFO": "INFO",
        "SUCCESS": "OK",
        "WARNING": "WARN",
        "ERROR": "ERROR",
        "HEADER": "===="
    }.get(level, level)
    print(f"{COLORS[level]}{timestamp} [{prefix}] {message}{COLORS['RESET']}")

def run_shell_command(command, timeout=10, platform_info=None):
    try:
        if platform_info and platform_info.get('use_adb') and platform_info.get('shell_prefix'):
            full_command = platform_info['shell_prefix'].split() + [command]
        else:
            full_command = command.split()
        result = subprocess.run(full_command, capture_output=True, text=True, timeout=timeout)
        if result.stderr and "permission denied" not in result.stderr.lower():
            print_formatted("WARNING", f"Command stderr: {result.stderr.strip()}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print_formatted("WARNING", f"Command timeout: {command}")
        return ""
    except Exception as e:
        print_formatted("ERROR", f"Command failed: {command} - {str(e)}")
        return ""

def load_config():
    default_config = {
        "accounts": [],
        "game_id": "",
        "private_server": "",
        "check_delay": 45,
        "active_account": "",
        "check_method": "both",
        "max_retries": 3,
        "game_validation": True,
        "launch_delay": 300,
        "retry_delay": 15,
        "force_kill_delay": 10,
        "minimize_crashes": True,
        "launch_attempts": 1,
        "cooldown_period": 120,
        "auto_rejoin": True,
        "ui_timeout": 30,
        "verbose_logging": True
    }
    try:
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
            run_shell_command(f"chmod 644 {CONFIG_FILE}", platform_info=platform_info)
            print_formatted("INFO", "Created new config file")
            return default_config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            merged_config = {**default_config, **config}
            return merged_config
    except Exception as e:
        print_formatted("ERROR", f"Config load error: {e}")
        return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        run_shell_command(f"chmod 644 {CONFIG_FILE}", platform_info=platform_info)
        print_formatted("SUCCESS", "Config saved")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Config save error: {e}")
        return False

# Roblox Control Functions
def verify_roblox_installation():
    try:
        output = run_shell_command(f"pm list packages {ROBLOX_PACKAGE}", platform_info=platform_info)
        if ROBLOX_PACKAGE not in output:
            print_formatted("ERROR", "Roblox not installed.")
            return False
        version_output = run_shell_command(f"dumpsys package {ROBLOX_PACKAGE} | grep versionName", platform_info=platform_info)
        if version_output:
            version = version_output.split("versionName=")[1].split()[0] if "versionName=" in version_output else "Unknown"
            print_formatted("INFO", f"Roblox version: {version}")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Roblox verification error: {e}")
        return False

def is_roblox_running(retries=3, delay=2):
    try:
        for attempt in range(retries):
            process_output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE} | grep -v grep", platform_info=platform_info)
            process_running = bool(process_output.strip())
            activity_output = run_shell_command(f"dumpsys activity | grep {ROBLOX_PACKAGE}", platform_info=platform_info)
            activity_running = ROBLOX_PACKAGE in activity_output and "mResumedActivity" in activity_output
            if process_running and activity_running:
                print_formatted("INFO", "Roblox process and activity confirmed running")
                return True
            elif process_running:
                print_formatted("INFO", f"Roblox process running, attempt {attempt+1}/{retries}, retrying...")
            elif activity_running:
                print_formatted("INFO", f"Roblox activity detected, attempt {attempt+1}/{retries}, retrying...")
            time.sleep(delay)
        print_formatted("INFO", "Roblox not fully running after retries")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Process check error: {str(e)}")
        return False

def close_roblox(config=None):
    try:
        print_formatted("INFO", "Closing Roblox...")
        run_shell_command("input keyevent KEYCODE_HOME", platform_info=platform_info)
        time.sleep(2)
        run_shell_command(f"am force-stop {ROBLOX_PACKAGE}", platform_info=platform_info)
        time.sleep(2)
        run_shell_command(f"killall -9 {ROBLOX_PACKAGE}", platform_info=platform_info)
        run_shell_command(f"pkill -9 -f {ROBLOX_PACKAGE}", platform_info=platform_info)
        force_kill_delay = config.get("force_kill_delay", 10) if config else 10
        time.sleep(force_kill_delay)
        if is_roblox_running():
            print_formatted("WARNING", "Roblox still running, clearing cache...")
            run_shell_command(f"rm -rf /data/data/{ROBLOX_PACKAGE}/cache/*", platform_info=platform_info)
            time.sleep(5)
        success = not is_roblox_running()
        if success:
            print_formatted("SUCCESS", "Roblox closed successfully")
        else:
            print_formatted("ERROR", "Failed to close Roblox completely")
        return success
    except Exception as e:
        print_formatted("ERROR", f"Failed to close Roblox: {str(e)}")
        return False

def get_main_activity():
    try:
        output = run_shell_command(f"dumpsys package {ROBLOX_PACKAGE} | grep -A 5 'android.intent.action.MAIN'", platform_info=platform_info)
        match = re.search(r'com\.roblox\.client/(\.[A-Za-z0-9.]+)', output)
        if match:
            activity = match.group(1)
            print_formatted("INFO", f"Detected main activity: {activity}")
            return activity
        fallbacks = ['.startup.ActivitySplash', '.MainActivity', '.HomeActivity']
        for fallback in fallbacks:
            test_output = run_shell_command(f"dumpsys package {ROBLOX_PACKAGE} | grep {fallback}", platform_info=platform_info)
            if fallback in test_output:
                return fallback
        return '.MainActivity'
    except Exception as e:
        print_formatted("WARNING", f"Main activity detection error: {str(e)}")
        return '.MainActivity'

def build_game_url(game_id, private_server=''):
    try:
        base_url = "roblox://experiences/start?placeId="
        url = base_url + str(game_id)
        if private_server:
            code = extract_private_server_code(private_server)
            if code:
                url += f"&privateServerLinkCode={code}"
        print_formatted("INFO", f"Built game URL: {url}")
        return url
    except Exception as e:
        print_formatted("ERROR", f"URL build error: {e}")
        return f"roblox://experiences/start?placeId={game_id}"

def extract_private_server_code(link):
    try:
        patterns = [
            r'privateServerLinkCode=([^&]+)',
            r'share\?code=([^&]+)',
            r'linkCode=([^&]+)',
            r'code=([^&]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, link)
            if match:
                return match.group(1)
        for separator in ['privateServerLinkCode=', 'share?code=', '&linkCode=', '=']:
            if separator in link:
                code = link.split(separator)[1].split('&')[0].strip()
                if code:
                    return code
        return None
    except:
        return None

# Game Launch Functions
def launch_via_deep_link(game_id, private_server=''):
    try:
        print_formatted("INFO", f"Launching via deep link: Game ID {game_id}")
        url = build_game_url(game_id, private_server)
        command = f'am start -a android.intent.action.VIEW -d "{url}"'
        result = run_shell_command(command, platform_info=platform_info)
        time.sleep(20)  # Increased to 20 seconds for proper joining
        if is_roblox_running():
            print_formatted("SUCCESS", "Roblox launched via deep link")
            return True
        print_formatted("WARNING", "Deep link launched but Roblox not running after extended wait")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Deep link launch failed: {str(e)}")
        return False

def launch_via_intent(game_id, private_server=''):
    try:
        print_formatted("INFO", f"Launching via intent: Game ID {game_id}")
        main_activity = get_main_activity()
        command = f'am start -n {ROBLOX_PACKAGE}/{main_activity}'
        run_shell_command(command, platform_info=platform_info)
        time.sleep(5)
        url = build_game_url(game_id, private_server)
        intent_command = f'am start -a android.intent.action.VIEW -d "{url}" {ROBLOX_PACKAGE}'
        result = run_shell_command(intent_command, platform_info=platform_info)
        time.sleep(15)
        if is_roblox_running():
            print_formatted("SUCCESS", "Roblox launched via intent")
            return True
        print_formatted("WARNING", "Intent launched but Roblox not running")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Intent launch failed: {str(e)}")
        return False

def launch_via_browser_redirect(game_id, private_server=''):
    try:
        print_formatted("INFO", f"Launching via browser redirect: Game ID {game_id}")
        if private_server:
            web_url = f"https://www.roblox.com/games/{game_id}?privateServerLinkCode={extract_private_server_code(private_server)}"
        else:
            web_url = f"https://www.roblox.com/games/{game_id}"
        command = f'am start -a android.intent.action.VIEW -d "{web_url}"'
        run_shell_command(command, platform_info=platform_info)
        time.sleep(15)
        if is_roblox_running():
            print_formatted("SUCCESS", "Roblox launched via browser redirect")
            return True
        print_formatted("WARNING", "Browser redirect launched but Roblox not running")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Browser redirect launch failed: {str(e)}")
        return False

# Game State Detection
def is_in_game(game_id, private_server=''):
    try:
        run_shell_command("logcat -c", platform_info=platform_info)
        time.sleep(2)
        patterns = [
            f"place[._]?id.*{game_id}",
            f"game[._]?id.*{game_id}",
            f"joining.*{game_id}",
            f"placeId={game_id}",
            f"game[._]?join.*{game_id}"
        ]
        if private_server:
            code = extract_private_server_code(private_server)
            if code:
                patterns.extend([
                    f"linkCode={code}",
                    f"privateServer.*{code}"
                ])
        log_command = f"logcat -d | grep -iE '{'|'.join(patterns)}'"
        logs = run_shell_command(log_command, platform_info=platform_info)
        if logs.strip():
            activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
            if ROBLOX_PACKAGE in activity and is_game_activity(activity):
                print_formatted("INFO", f"Confirmed in game: {game_id}")
                return True
            print_formatted("INFO", "Game logs found but not in game activity")
        else:
            print_formatted("INFO", "No game logs found")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Game detection error: {str(e)}")
        return False

def is_game_activity(activity):
    game_indicators = [
        'GameActivity',
        'ExperienceActivity', 
        'SurfaceView',
        'UnityPlayerActivity',
        'GameView'
    ]
    return any(indicator in activity for indicator in game_indicators)

def check_error_states():
    try:
        run_shell_command("logcat -c", platform_info=platform_info)
        time.sleep(2)
        log_command = "logcat -d | grep -iE 'crash|fatal|disconnected|kicked|banned|anr|timeout|luaerror|processerror|sigsegv|segmentation fault|unexpected disconnect|error code|ban|kick|freeze|not responding|application not responding'"
        logs = run_shell_command(log_command, platform_info=platform_info)
        error_patterns = {
            'crash': ['crash', 'fatal', 'exception', 'sigsegv', 'segmentation fault'],
            'kicked': ['disconnected', 'kicked', 'banned', 'unexpected disconnect', 'error code', 'ban', 'kick'],
            'frozen': ['anr', 'not responding', 'application not responding', 'timeout', 'freeze'],
            'script_error': ['luaerror', 'processerror']
        }
        for error_type, patterns in error_patterns.items():
            if any(pattern in logs.lower() for pattern in patterns):
                print_formatted("WARNING", f"Detected error: {error_type} - Logs: {logs.strip()}")
                return error_type
        activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
        error_activities = ['ErrorActivity', 'CrashActivity', 'NotResponding', 'AlertDialog']
        if any(error_activity in activity for error_activity in error_activities):
            print_formatted("WARNING", f"Detected UI error in activity: {activity.strip()}")
            return 'ui_error'
        anr_check = run_shell_command("dumpsys activity | grep 'ANR'", platform_info=platform_info)
        if anr_check.strip():
            print_formatted("WARNING", f"Detected ANR: {anr_check.strip()}")
            return 'frozen'
        return None
    except Exception as e:
        print_formatted("ERROR", f"Error state check failed: {str(e)}")
        return None

# Main Automation Logic
def attempt_game_join(config):
    global last_game_join_time
    game_id = config.get('game_id')
    private_server = config.get('private_server', '')
    if not game_id:
        print_formatted("ERROR", "No game ID specified in config")
        return False
    print_formatted("INFO", f"Attempting to join game {game_id}")
    if not close_roblox(config):
        print_formatted("WARNING", "Failed to close Roblox properly")
    time.sleep(3)
    methods = [
        launch_via_deep_link,
        launch_via_intent,
        launch_via_browser_redirect
    ]
    for method in methods:
        try:
            print_formatted("INFO", f"Trying launch method: {method.__name__}")
            if method(game_id, private_server):
                if wait_for_game_join(config, timeout=60):
                    last_game_join_time = time.time()
                    print_formatted("SUCCESS", f"Successfully joined game using {method.__name__}")
                    return True
                else:
                    print_formatted("WARNING", f"Game join timeout with {method.__name__}")
            else:
                print_formatted("WARNING", f"Failed to launch with {method.__name__}")
            time.sleep(5)
        except Exception as e:
            print_formatted("ERROR", f"Error with {method.__name__}: {str(e)}")
            continue
    print_formatted("ERROR", "All launch methods failed")
    return False

def wait_for_game_join(config, timeout=60):
    start_time = time.time()
    game_id = config.get('game_id')
    private_server = config.get('private_server', '')
    while time.time() - start_time < timeout:
        if is_in_game(game_id, private_server):
            return True
        time.sleep(5)  # Increased to 5 seconds for better join detection
    print_formatted("INFO", "Game join timeout, checking error states")
    error_state = check_error_states()
    if error_state:
        print_formatted("WARNING", f"Detected error during join: {error_state}")
    return False

def should_attempt_launch(config):
    if not is_roblox_running():
        print_formatted("INFO", "Roblox not running, need to launch")
        return True
    game_id = config.get('game_id')
    private_server = config.get('private_server', '')
    if not is_in_game(game_id, private_server):
        print_formatted("INFO", "Not in correct game, need to rejoin")
        return True
    error_state = check_error_states()
    if error_state:
        print_formatted("WARNING", f"Error state detected: {error_state}")
        return True
    print_formatted("INFO", "Game is running normally, no action needed")
    return False

def automation_loop(config):
    global automation_running, last_game_join_time
    automation_running = True
    print_formatted("SUCCESS", "Automation started successfully!")
    while automation_running:
        try:
            if should_attempt_launch(config):
                attempt_game_join(config)
            else:
                print_formatted("INFO", "Monitoring continues...")
            check_delay = config.get('check_delay', 45)
            print_formatted("INFO", f"Waiting {check_delay} seconds before next check...")
            time.sleep(check_delay)
        except KeyboardInterrupt:
            print_formatted("INFO", "Automation interrupted by user")
            break
        except Exception as e:
            print_formatted("ERROR", f"Automation loop error: {str(e)}")
            time.sleep(10)
    automation_running = False
    print_formatted("INFO", "Automation stopped")

# Interactive Menu
def display_menu():
    print(f"\n{COLORS['HEADER']}{'='*50}")
    print(f"    ENHANCED ROBLOX AUTOMATION TOOL")
    print(f"{'='*50}{COLORS['RESET']}")
    if platform_info:
        print(f"{COLORS['INFO']}Platform: {platform_info['name']} ({platform_info['type']}){COLORS['RESET']}")
        print(f"{COLORS['INFO']}Root Access: {'Yes' if platform_info.get('has_root') else 'Limited'}{COLORS['RESET']}")
    print(f"\n{COLORS['CYAN']}1.{COLORS['RESET']} Configure Settings")
    print(f"{COLORS['CYAN']}2.{COLORS['RESET']} Start Automation")
    print(f"{COLORS['CYAN']}3.{COLORS['RESET']} Stop Automation")
    print(f"{COLORS['CYAN']}4.{COLORS['RESET']} Test Game Join")
    print(f"{COLORS['CYAN']}5.{COLORS['RESET']} View Current Config")
    print(f"{COLORS['CYAN']}6.{COLORS['RESET']} System Information")
    print(f"{COLORS['CYAN']}7.{COLORS['RESET']} Exit")
    if automation_running:
        print(f"\n{COLORS['SUCCESS']}Status: Automation is RUNNING{COLORS['RESET']}")
    else:
        print(f"\n{COLORS['WARNING']}Status: Automation is STOPPED{COLORS['RESET']}")
    if last_game_join_time:
        join_time = datetime.fromtimestamp(last_game_join_time).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{COLORS['INFO']}Last Game Join: {join_time}{COLORS['RESET']}")

def configure_settings():
    config = load_config()
    print(f"\n{COLORS['HEADER']}=== CONFIGURATION SETUP ==={COLORS['RESET']}")
    current_game_id = config.get('game_id', '')
    print(f"\nCurrent Game ID: {current_game_id if current_game_id else 'Not set'}")
    new_game_id = input("Enter new Game ID (or press Enter to keep current): ").strip()
    if new_game_id:
        config['game_id'] = new_game_id
    current_private_server = config.get('private_server', '')
    print(f"\nCurrent Private Server: {current_private_server if current_private_server else 'Not set'}")
    new_private_server = input("Enter Private Server link (or press Enter to keep current): ").strip()
    if new_private_server:
        config['private_server'] = new_private_server
    current_delay = config.get('check_delay', 45)
    print(f"\nCurrent Check Delay: {current_delay} seconds")
    new_delay = input("Enter new Check Delay in seconds (or press Enter to keep current): ").strip()
    if new_delay and new_delay.isdigit():
        config['check_delay'] = int(new_delay)
    current_retries = config.get('max_retries', 3)
    print(f"\nCurrent Max Retries: {current_retries}")
    new_retries = input("Enter new Max Retries (or press Enter to keep current): ").strip()
    if new_retries and new_retries.isdigit():
        config['max_retries'] = int(new_retries)
    current_rejoin = config.get('auto_rejoin', True)
    print(f"\nCurrent Auto Rejoin: {'Enabled' if current_rejoin else 'Disabled'}")
    new_rejoin = input("Enable Auto Rejoin? (y/n, or press Enter to keep current): ").strip().lower()
    if new_rejoin in ['y', 'yes']:
        config['auto_rejoin'] = True
    elif new_rejoin in ['n', 'no']:
        config['auto_rejoin'] = False
    if save_config(config):
        print_formatted("SUCCESS", "Configuration saved successfully!")
    else:
        print_formatted("ERROR", "Failed to save configuration!")
    input("\nPress Enter to continue...")

def view_current_config():
    config = load_config()
    print(f"\n{COLORS['HEADER']}=== CURRENT CONFIGURATION ==={COLORS['RESET']}")
    print(f"{COLORS['CYAN']}Game ID:{COLORS['RESET']} {config.get('game_id', 'Not set')}")
    print(f"{COLORS['CYAN']}Private Server:{COLORS['RESET']} {config.get('private_server', 'Not set')}")
    print(f"{COLORS['CYAN']}Check Delay:{COLORS['RESET']} {config.get('check_delay', 45)} seconds")
    print(f"{COLORS['CYAN']}Max Retries:{COLORS['RESET']} {config.get('max_retries', 3)}")
    print(f"{COLORS['CYAN']}Auto Rejoin:{COLORS['RESET']} {'Enabled' if config.get('auto_rejoin', True) else 'Disabled'}")
    print(f"{COLORS['CYAN']}Game Validation:{COLORS['RESET']} {'Enabled' if config.get('game_validation', True) else 'Disabled'}")
    print(f"{COLORS['CYAN']}Launch Delay:{COLORS['RESET']} {config.get('launch_delay', 300)} seconds")
    print(f"{COLORS['CYAN']}Retry Delay:{COLORS['RESET']} {config.get('retry_delay', 15)} seconds")
    input("\nPress Enter to continue...")

def test_game_join():
    config = load_config()
    game_id = config.get('game_id')
    if not game_id:
        print_formatted("ERROR", "No game ID configured. Please configure settings first.")
        input("Press Enter to continue...")
        return
    print_formatted("INFO", f"Testing game join for Game ID: {game_id}")
    print_formatted("INFO", "This will close Roblox and attempt to join the game...")
    confirm = input("Continue with test? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes']:
        return
    success = attempt_game_join(config)
    if success:
        print_formatted("SUCCESS", "Game join test completed successfully!")
    else:
        print_formatted("ERROR", "Game join test failed!")
    input("\nPress Enter to continue...")

def show_system_info():
    print(f"\n{COLORS['HEADER']}=== SYSTEM INFORMATION ==={COLORS['RESET']}")
    if platform_info:
        print(f"{COLORS['CYAN']}Platform Type:{COLORS['RESET']} {platform_info['type']}")
        print(f"{COLORS['CYAN']}Platform Name:{COLORS['RESET']} {platform_info['name']}")
        print(f"{COLORS['CYAN']}Root Access:{COLORS['RESET']} {'Available' if platform_info.get('has_root') else 'Limited'}")
        print(f"{COLORS['CYAN']}ADB Support:{COLORS['RESET']} {'Yes' if platform_info.get('use_adb') else 'No'}")
        print(f"{COLORS['CYAN']}Shell Prefix:{COLORS['RESET']} {platform_info.get('shell_prefix', 'None')}")
    roblox_installed = verify_roblox_installation()
    print(f"{COLORS['CYAN']}Roblox Installed:{COLORS['RESET']} {'Yes' if roblox_installed else 'No'}")
    if roblox_installed:
        roblox_running = is_roblox_running()
        print(f"{COLORS['CYAN']}Roblox Running:{COLORS['RESET']} {'Yes' if roblox_running else 'No'}")
    try:
        android_version = run_shell_command("getprop ro.build.version.release", platform_info=platform_info)
        print(f"{COLORS['CYAN']}Android Version:{COLORS['RESET']} {android_version if android_version else 'Unknown'}")
    except:
        pass
    try:
        device_model = run_shell_command("getprop ro.product.model", platform_info=platform_info)
        print(f"{COLORS['CYAN']}Device Model:{COLORS['RESET']} {device_model if device_model else 'Unknown'}")
    except:
        pass
    input("\nPress Enter to continue...")

# Main Function
def main():
    global platform_info, automation_running
    try:
        os.system('clear' if os.name == 'posix' else 'cls')
        print(f"{COLORS['HEADER']}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              ENHANCED ROBLOX AUTOMATION TOOL                 ║")
        print("║          Supports: UGPHONE, VSPHONE, REDFINGER              ║")
        print("║                    Standard Android & Emulators             ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"{COLORS['RESET']}")
        detector = PlatformDetector()
        platform_info = detector.detect_platform()
        if not verify_roblox_installation():
            print_formatted("ERROR", "Roblox is not installed or not accessible!")
            print_formatted("INFO", "Please install Roblox and ensure proper permissions.")
            sys.exit(1)
        automation_thread = None
        while True:
            try:
                display_menu()
                choice = input(f"\n{COLORS['CYAN']}Enter your choice (1-7): {COLORS['RESET']}").strip()
                if choice == '1':
                    configure_settings()
                elif choice == '2':
                    if automation_running:
                        print_formatted("WARNING", "Automation is already running!")
                        input("Press Enter to continue...")
                    else:
                        config = load_config()
                        if not config.get('game_id'):
                            print_formatted("ERROR", "No game ID configured! Please configure settings first.")
                            input("Press Enter to continue...")
                        else:
                            automation_thread = threading.Thread(target=automation_loop, args=(config,), daemon=True)
                            automation_thread.start()
                elif choice == '3':
                    if automation_running:
                        print_formatted("INFO", "Stopping automation...")
                        automation_running = False
                        if automation_thread:
                            automation_thread.join(timeout=5)
                        print_formatted("SUCCESS", "Automation stopped!")
                    else:
                        print_formatted("WARNING", "Automation is not running!")
                    input("Press Enter to continue...")
                elif choice == '4':
                    test_game_join()
                elif choice == '5':
                    view_current_config()
                elif choice == '6':
                    show_system_info()
                elif choice == '7':
                    if automation_running:
                        print_formatted("INFO", "Stopping automation before exit...")
                        automation_running = False
                        if automation_thread:
                            automation_thread.join(timeout=5)
                    print_formatted("INFO", "Thank you for using Enhanced Roblox Automation Tool!")
                    break
                else:
                    print_formatted("WARNING", "Invalid choice! Please enter 1-7.")
                    input("Press Enter to continue...")
            except KeyboardInterrupt:
                print_formatted("INFO", "\nExiting...")
                if automation_running:
                    automation_running = False
                break
            except Exception as e:
                print_formatted("ERROR", f"Menu error: {str(e)}")
                input("Press Enter to continue...")
    except Exception as e:
        print_formatted("ERROR", f"Critical error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()