#!/usr/bin/env python3
"""
Enhanced Roblox Automation Tool (Rejoiner.py)
Supports: UGPHONE, VSPHONE, REDFINGER, Standard Android/Emulators
Author: Enhanced for multi-platform compatibility
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

# ======================
# CONFIGURATION
# ======================
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

# ======================
# PLATFORM DETECTION
# ======================
class PlatformDetector:
    def __init__(self):
        self.detected_platform = None
    
    def detect_platform(self):
        """Detect the current platform (UGPHONE, VSPHONE, REDFINGER, or standard Android)"""
        try:
            # Check for UGPHONE
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
            
            # Check for VSPHONE
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
            
            # Check for REDFINGER
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
            
            # Standard Android (emulator or physical device)
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
        """Check if running on UGPHONE"""
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
        """Check if running on VSPHONE"""
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
        """Check if running on REDFINGER"""
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
        """Get build.prop content"""
        try:
            result = subprocess.run(['cat', '/system/build.prop'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout
        except:
            return ""
    
    def _check_root_standard(self):
        """Check for root access on standard Android"""
        try:
            result = subprocess.run(['su', '-c', 'echo test'], 
                                  capture_output=True, text=True, timeout=5)
            return 'test' in result.stdout
        except:
            return False
    
    def _check_root_ugphone(self):
        """Check for root access on UGPHONE"""
        try:
            if self._check_root_standard():
                return True
            
            result = subprocess.run(['ugphone_su', '-c', 'echo test'], 
                                  capture_output=True, text=True, timeout=5)
            return 'test' in result.stdout
        except:
            return False
    
    def _check_root_vsphone(self):
        """Check for root access on VSPHONE"""
        try:
            if self._check_root_standard():
                return True
            
            result = subprocess.run(['vsphone_su', '-c', 'echo test'], 
                                  capture_output=True, text=True, timeout=5)
            return 'test' in result.stdout
        except:
            return False

# ======================
# CORE FUNCTIONS
# ======================
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
    """Execute shell command with platform-specific handling"""
    try:
        if platform_info and platform_info.get('use_adb') and platform_info.get('shell_prefix'):
            full_command = [platform_info['shell_prefix'].split()[0]] + platform_info['shell_prefix'].split()[1:] + [command]
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
    """Load configuration from JSON file"""
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
        "verbose_logging": False
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
            # Merge with defaults to ensure all keys exist
            merged_config = {**default_config, **config}
            return merged_config
    except Exception as e:
        print_formatted("ERROR", f"Config load error: {e}")
        return default_config

def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        run_shell_command(f"chmod 644 {CONFIG_FILE}", platform_info=platform_info)
        print_formatted("SUCCESS", "Config saved")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Config save error: {e}")
        return False

# ======================
# ROBLOX CONTROL FUNCTIONS
# ======================
def verify_roblox_installation():
    """Verify Roblox is installed"""
    try:
        output = run_shell_command(f"pm list packages {ROBLOX_PACKAGE}", platform_info=platform_info)
        if ROBLOX_PACKAGE not in output:
            print_formatted("ERROR", "Roblox not installed.")
            return False
        
        # Get version info
        version_output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep versionName", platform_info=platform_info)
        if version_output:
            version = version_output.split("versionName=")[1].split()[0] if "versionName=" in version_output else "Unknown"
            print_formatted("INFO", f"Roblox version: {version}")
        
        return True
    except Exception as e:
        print_formatted("ERROR", f"Roblox verification error: {e}")
        return False

def is_roblox_running():
    """Check if Roblox is currently running"""
    try:
        # Check processes
        process_output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE} | grep -v grep", platform_info=platform_info)
        process_running = bool(process_output.strip())
        
        # Check activities
        activity_output = run_shell_command(f"dumpsys activity | grep {ROBLOX_PACKAGE}", platform_info=platform_info)
        activity_running = ROBLOX_PACKAGE in activity_output and "mResumedActivity" in activity_output
        
        return process_running and activity_running
    except Exception as e:
        print_formatted("ERROR", f"Process check error: {str(e)}")
        return False

def close_roblox(config=None):
    """Close Roblox application"""
    try:
        print_formatted("INFO", "Closing Roblox...")
        
        # Send home key
        run_shell_command("input keyevent KEYCODE_HOME", platform_info=platform_info)
        time.sleep(2)
        
        # Force stop
        run_shell_command(f"am force-stop {ROBLOX_PACKAGE}", platform_info=platform_info)
        time.sleep(2)
        
        # Kill processes
        run_shell_command(f"killall -9 {ROBLOX_PACKAGE}", platform_info=platform_info)
        run_shell_command(f"pkill -9 -f {ROBLOX_PACKAGE}", platform_info=platform_info)
        
        force_kill_delay = config.get("force_kill_delay", 10) if config else 10
        time.sleep(force_kill_delay)
        
        # Verify closure
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
    """Get Roblox main activity name"""
    try:
        output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep -A 5 'android.intent.action.MAIN'", platform_info=platform_info)
        
        # Parse activity name
        match = re.search(r'com\.roblox\.client/(\.[A-Za-z0-9.]+)', output)
        if match:
            activity = match.group(1)
            print_formatted("INFO", f"Detected main activity: {activity}")
            return activity
        
        # Fallback activities
        fallbacks = ['.startup.ActivitySplash', '.MainActivity', '.HomeActivity']
        for fallback in fallbacks:
            test_output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep {fallback}", platform_info=platform_info)
            if fallback in test_output:
                return fallback
        
        return '.MainActivity'  # Default fallback
        
    except Exception as e:
        print_formatted("WARNING", f"Main activity detection error: {str(e)}")
        return '.MainActivity'

def build_game_url(game_id, private_server=''):
    """Build Roblox game URL"""
    try:
        base_url = "roblox://experiences/start?placeId="
        url = base_url + str(game_id)
        
        if private_server:
            code = extract_private_server_code(private_server)
            if code:
                url += f"&privateServerLinkCode={code}"
        
        return url
    except Exception as e:
        print_formatted("ERROR", f"URL build error: {e}")
        return f"roblox://experiences/start?placeId={game_id}"

def extract_private_server_code(link):
    """Extract private server code from link"""
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
        
        # Fallback: split by common separators
        for separator in ['privateServerLinkCode=', 'share?code=', '&linkCode=', '=']:
            if separator in link:
                code = link.split(separator)[1].split('&')[0].strip()
                if code:
                    return code
        
        return None
    except:
        return None

# ======================
# GAME LAUNCH FUNCTIONS
# ======================
def launch_via_deep_link(game_id, private_server=''):
    """Launch game using roblox:// deep link"""
    try:
        print_formatted("INFO", f"Launching via deep link: {game_id}")
        
        # Build URL
        url = build_game_url(game_id, private_server)
        
        # Launch using am start
        command = f'am start -a android.intent.action.VIEW -d "{url}"'
        result = run_shell_command(command, platform_info=platform_info)
        
        time.sleep(5)
        return is_roblox_running()
        
    except Exception as e:
        print_formatted("ERROR", f"Deep link launch failed: {str(e)}")
        return False

def launch_via_intent(game_id, private_server=''):
    """Launch game using Android intents"""
    try:
        print_formatted("INFO", f"Launching via intent: {game_id}")
        
        # First start Roblox main activity
        main_activity = get_main_activity()
        command = f'am start -n {ROBLOX_PACKAGE}/{main_activity}'
        run_shell_command(command, platform_info=platform_info)
        time.sleep(5)
        
        # Then send the game URL as an intent
        url = build_game_url(game_id, private_server)
        intent_command = f'am start -a android.intent.action.VIEW -d "{url}" {ROBLOX_PACKAGE}'
        result = run_shell_command(intent_command, platform_info=platform_info)
        
        time.sleep(5)
        return is_roblox_running()
        
    except Exception as e:
        print_formatted("ERROR", f"Intent launch failed: {str(e)}")
        return False

def launch_via_ui_automation(game_id, private_server=''):
    """Launch game using UI automation"""
    try:
        print_formatted("INFO", f"Launching via UI automation: {game_id}")
        
        # Start Roblox
        main_activity = get_main_activity()
        command = f'am start -n {ROBLOX_PACKAGE}/{main_activity}'
        run_shell_command(command, platform_info=platform_info)
        time.sleep(10)  # Wait for app to load
        
        # Navigate using UI automation
        return navigate_to_game_ui(game_id, private_server)
        
    except Exception as e:
        print_formatted("ERROR", f"UI automation launch failed: {str(e)}")
        return False

def launch_via_browser_redirect(game_id, private_server=''):
    """Launch game via browser redirect"""
    try:
        print_formatted("INFO", f"Launching via browser redirect: {game_id}")
        
        # Create web URL that redirects to Roblox
        if private_server:
            web_url = f"https://www.roblox.com/games/{game_id}?privateServerLinkCode={extract_private_server_code(private_server)}"
        else:
            web_url = f"https://www.roblox.com/games/{game_id}"
        
        # Open in browser
        command = f'am start -a android.intent.action.VIEW -d "{web_url}"'
        run_shell_command(command, platform_info=platform_info)
        time.sleep(10)
        
        # Look for "Play" button and tap it
        return tap_play_button()
        
    except Exception as e:
        print_formatted("ERROR", f"Browser redirect launch failed: {str(e)}")
        return False

def navigate_to_game_ui(game_id, private_server=''):
    """Navigate to game using UI automation"""
    try:
        print_formatted("INFO", "Starting UI navigation to game...")
        time.sleep(10)  # Wait for Roblox to fully load
        
        # Try different navigation methods
        methods = [
            navigate_via_search,
            navigate_via_url_bar,
            navigate_via_menu
        ]
        
        for method in methods:
            try:
                if method(game_id, private_server):
                    return True
            except Exception as e:
                print_formatted("WARNING", f"Navigation method {method.__name__} failed: {str(e)}")
                continue
        
        return False
    except Exception as e:
        print_formatted("ERROR", f"UI navigation failed: {str(e)}")
        return False

def navigate_via_search(game_id, private_server=''):
    """Navigate using search functionality - CAREFUL with screen taps"""
    try:
        print_formatted("INFO", "🔍 Attempting navigation via search (reduced tapping)...")
        
        # Wait for UI to stabilize first
        time.sleep(5)
        
        # Try fewer, more targeted search positions
        search_positions = [
            (540, 200),   # Top-center search (most common)
            (540, 150),   # Slightly higher
        ]
        
        for attempt, (x, y) in enumerate(search_positions):
            print_formatted("INFO", f"🎯 Search attempt {attempt + 1}: tapping ({x}, {y})")
            
            run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
            time.sleep(3)
            
            # Type game ID carefully
            run_shell_command(f"input text {game_id}", platform_info=platform_info)
            time.sleep(3)
            
            # Press enter
            run_shell_command("input keyevent KEYCODE_ENTER", platform_info=platform_info)
            time.sleep(8)  # Longer wait for search results
            
            # Check if we can detect any game results in the current screen
            # Instead of blind tapping, check if we're in a search results state
            activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
            if "search" in activity.lower() or "result" in activity.lower():
                print_formatted("INFO", "🎯 Search results detected, attempting to select game...")
                
                # Try one careful tap in the center results area
                run_shell_command("input tap 540 450", platform_info=platform_info)
                time.sleep(5)
                
                # Check if we're now on a game page
                if check_game_page():
                    if tap_play_button():
                        return True
            
            # If failed, clear and try next position
            clear_search()
            time.sleep(2)
        
        return False
    except Exception as e:
        print_formatted("ERROR", f"❌ Search navigation failed: {str(e)}")
        return False

def navigate_via_url_bar(game_id, private_server=''):
    """Navigate using URL bar if available"""
    try:
        print_formatted("INFO", "Attempting navigation via URL bar...")
        
        # Look for URL/address bar
        url_positions = [
            (540, 100),   # Top center
            (540, 150),   # Slightly lower
            (540, 200)    # Alternative position
        ]
        
        for x, y in url_positions:
            run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
            time.sleep(2)
            
            # Build URL
            if private_server:
                url = f"roblox://experiences/start?placeId={game_id}&privateServerLinkCode={extract_private_server_code(private_server)}"
            else:
                url = f"roblox://experiences/start?placeId={game_id}"
            
            # Type URL
            run_shell_command(f"input text '{url}'", platform_info=platform_info)
            time.sleep(2)
            
            # Press enter
            run_shell_command("input keyevent KEYCODE_ENTER", platform_info=platform_info)
            time.sleep(10)
            
            # Check if navigation worked
            if check_game_loading():
                return True
        
        return False
    except Exception as e:
        print_formatted("ERROR", f"URL bar navigation failed: {str(e)}")
        return False

def navigate_via_menu(game_id, private_server=''):
    """Navigate using menu options"""
    try:
        print_formatted("INFO", "Attempting navigation via menu...")
        
        # Look for menu button (hamburger menu, etc.)
        menu_positions = [
            (50, 100),    # Top-left menu
            (50, 200),    # Left menu
            (1020, 100),  # Top-right menu
            (540, 50)     # Top-center menu
        ]
        
        for x, y in menu_positions:
            run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
            time.sleep(3)
            
            # Look for "Games" or similar option
            if tap_games_option():
                time.sleep(3)
                
                # Try to find featured games or search
                if find_and_tap_game(game_id):
                    if tap_play_button():
                        return True
        
        return False
    except Exception as e:
        print_formatted("ERROR", f"Menu navigation failed: {str(e)}")
        return False

def tap_game_result():
    """Tap on game search result"""
    try:
        # Common positions for search results
        result_positions = [
            (540, 400),   # Center result
            (540, 500),   # Lower center
            (270, 400),   # Left result
            (810, 400)    # Right result
        ]
        
        for x, y in result_positions:
            run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
            time.sleep(3)
            
            # Check if game page loaded
            if check_game_page():
                return True
        
        return False
    except:
        return False

def tap_play_button():
    """Tap the play/join button - CAREFUL approach"""
    try:
        print_formatted("INFO", "🎮 Looking for Play button...")
        
        # Wait for page to stabilize
        time.sleep(3)
        
        # Try fewer, more precise positions for play button
        play_positions = [
            (540, 800),   # Center-bottom (most common)
            (540, 750),   # Slightly higher center
        ]
        
        for attempt, (x, y) in enumerate(play_positions):
            print_formatted("INFO", f"🎯 Play button attempt {attempt + 1}: tapping ({x}, {y})")
            
            run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
            time.sleep(8)  # Longer wait to see if game starts loading
            
            # Check if game started loading or Roblox launched
            if check_game_loading() or is_roblox_running():
                print_formatted("SUCCESS", "✓ Play button worked!")
                return True
        
        print_formatted("WARNING", "⚠️ Play button attempts failed")
        return False
    except Exception as e:
        print_formatted("ERROR", f"❌ Play button error: {str(e)}")
        return False

def clear_search():
    """Clear search field"""
    try:
        # Select all and delete
        run_shell_command("input keyevent KEYCODE_CTRL_LEFT", platform_info=platform_info)
        run_shell_command("input keyevent KEYCODE_A", platform_info=platform_info)
        run_shell_command("input keyevent KEYCODE_DEL", platform_info=platform_info)
        time.sleep(1)
    except:
        pass

def tap_games_option():
    """Tap on Games menu option"""
    try:
        # Look for "Games" text in various positions
        games_positions = [
            (200, 300),   # Left menu games
            (540, 300),   # Center games
            (200, 400),   # Lower left games
            (540, 400)    # Lower center games
        ]
        
        for x, y in games_positions:
            run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
            time.sleep(3)
            
            # Check if games section loaded
            if check_games_section():
                return True
        
        return False
    except:
        return False

def find_and_tap_game(game_id):
    """Find and tap specific game"""
    try:
        # Scroll through games and look for the target
        for scroll_count in range(5):
            # Try tapping various game positions
            game_positions = [
                (270, 500), (540, 500), (810, 500),  # Row 1
                (270, 700), (540, 700), (810, 700),  # Row 2
                (270, 900), (540, 900), (810, 900)   # Row 3
            ]
            
            for x, y in game_positions:
                run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
                time.sleep(2)
                
                if check_game_page():
                    return True
            
            # Scroll down for more games
            run_shell_command("input swipe 540 800 540 400 500", platform_info=platform_info)
            time.sleep(2)
        
        return False
    except:
        return False

def check_game_loading():
    """Check if game is loading"""
    try:
        # Look for loading indicators in logcat
        run_shell_command("logcat -c", platform_info=platform_info)
        time.sleep(3)
        
        logs = run_shell_command("logcat -d -t 50 | grep -i 'loading\\|joining\\|connecting'", platform_info=platform_info)
        return bool(logs.strip())
    except:
        return False

def check_game_page():
    """Check if on a game page"""
    try:
        # Check current activity for game page indicators
        activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
        game_page_indicators = ['GameDetail', 'GamePage', 'Experience']
        return any(indicator in activity for indicator in game_page_indicators)
    except:
        return False

def check_games_section():
    """Check if in games section"""
    try:
        activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
        games_indicators = ['Games', 'Discover', 'Browse']
        return any(indicator in activity for indicator in games_indicators)
    except:
        return False

# ======================
# GAME STATE DETECTION
# ======================
def is_in_game(game_id, private_server=''):
    """Check if currently in the specified game"""
    try:
        # Don't clear logcat - just check recent logs
        time.sleep(1)
        
        # Check logcat for game join patterns
        patterns = [
            f"place[._]?id.*{game_id}",
            f"game[._]?id.*{game_id}",
            f"joining.*{game_id}",
            f"placeId={game_id}",
            f"game[._]?join.*{game_id}",
            f"loadPlace.*{game_id}",
            f"teleport.*{game_id}"
        ]
        
        if private_server:
            code = extract_private_server_code(private_server)
            if code:
                patterns.extend([
                    f"linkCode={code}",
                    f"privateServer.*{code}"
                ])
        
        # Check recent logs (last 100 lines to avoid missing logs)
        log_command = f"logcat -d -t 100 | grep -iE '{'|'.join(patterns)}'"
        logs = run_shell_command(log_command, platform_info=platform_info)
        
        # Also check current activity
        activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
        
        # More reliable detection: check both log presence AND activity
        has_log_evidence = bool(logs.strip())
        in_roblox_activity = ROBLOX_PACKAGE in activity
        in_game_activity = is_game_activity(activity)
        
        # Additional check: ensure we're not in main menu
        not_in_menu = not any(menu_indicator in activity for menu_indicator in ['MainActivity', 'HomeActivity', 'StartActivity'])
        
        if has_log_evidence and in_roblox_activity and (in_game_activity or not_in_menu):
            return True
        
        # Backup check: if Roblox is running and we find game evidence in logs from last 5 minutes
        if in_roblox_activity:
            recent_logs = run_shell_command("logcat -d -t 500 | grep -iE 'place.*id|game.*join|loadPlace'", platform_info=platform_info)
            if game_id in recent_logs:
                return True
        
        return False
    except Exception as e:
        print_formatted("ERROR", f"Game detection error: {str(e)}")
        return False

def is_game_activity(activity):
    """Check if activity indicates being in a game"""
    game_indicators = [
        'GameActivity',
        'ExperienceActivity', 
        'SurfaceView',
        'UnityPlayerActivity',
        'GameView'
    ]
    return any(indicator in activity for indicator in game_indicators)

def check_error_states():
    """Check for error states that require restart"""
    try:
        # Check logcat for errors
        log_command = "logcat -d -t 100 | grep -iE 'crash|fatal|disconnected|kicked|banned|anr|timeout|luaerror|processerror'"
        logs = run_shell_command(log_command, platform_info=platform_info)
        
        error_patterns = {
            'crash': ['crash', 'fatal', 'exception'],
            'kicked': ['disconnected', 'kicked', 'banned'],
            'frozen': ['anr', 'notresponding', 'timeout'],
            'script_error': ['luaerror', 'processerror']
        }
        
        for error_type, patterns in error_patterns.items():
            if any(pattern in logs.lower() for pattern in patterns):
                return error_type
        
        # Check current activity for error states
        activity = run_shell_command("dumpsys window windows | grep mCurrentFocus", platform_info=platform_info)
        error_activities = ['ErrorActivity', 'CrashActivity', 'NotResponding']
        
        if any(error_activity in activity for error_activity in error_activities):
            return 'ui_error'
        
        return None
    except Exception as e:
        print_formatted("ERROR", f"Error state check failed: {str(e)}")
        return None

# ======================
# MAIN AUTOMATION LOGIC
# ======================
def attempt_game_join(config):
    """Attempt to join the specified game using multiple methods"""
    global last_game_join_time
    
    game_id = config.get('game_id')
    private_server = config.get('private_server', '')
    
    if not game_id:
        print_formatted("ERROR", "No game ID specified in config")
        return False
    
    print_formatted("INFO", f"🎮 Attempting to join game {game_id}")
    
    # Close Roblox first only if it's running
    if is_roblox_running():
        print_formatted("INFO", "Closing existing Roblox session...")
        if not close_roblox(config):
            print_formatted("WARNING", "Failed to close Roblox properly, continuing anyway...")
        time.sleep(3)
    
    # Try launch methods in order of reliability
    methods = [
        ("Deep Link", launch_via_deep_link),
        ("Android Intent", launch_via_intent),
        ("Browser Redirect", launch_via_browser_redirect),
        ("UI Automation", launch_via_ui_automation)  # Last resort due to screen clicking
    ]
    
    for method_name, method_func in methods:
        try:
            print_formatted("INFO", f"🔄 Trying {method_name} method...")
            
            if method_func(game_id, private_server):
                print_formatted("SUCCESS", f"✓ {method_name} launched successfully!")
                
                # Wait for game to load and verify join
                print_formatted("INFO", "⏳ Waiting for game to load...")
                if wait_for_game_join(config, timeout=45):
                    last_game_join_time = time.time()
                    print_formatted("SUCCESS", f"🎉 Successfully joined game using {method_name}!")
                    return True
                else:
                    print_formatted("WARNING", f"⚠️ Game join timeout with {method_name}")
            else:
                print_formatted("WARNING", f"❌ {method_name} failed to launch")
            
            # Brief delay between attempts (reduced from 5s to 3s)
            time.sleep(3)
            
        except Exception as e:
            print_formatted("ERROR", f"❌ Error with {method_name}: {str(e)}")
            continue
    
    print_formatted("ERROR", "❌ All launch methods failed")
    return False

def wait_for_game_join(config, timeout=45):
    """Wait for game to load and confirm join"""
    start_time = time.time()
    game_id = config.get('game_id')
    private_server = config.get('private_server', '')
    
    print_formatted("INFO", f"🔍 Checking game join status (timeout: {timeout}s)...")
    
    # Check every 3 seconds instead of 2 to reduce system load
    check_interval = 3
    last_status_time = 0
    
    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        
        # Show progress every 10 seconds
        if elapsed - last_status_time >= 10:
            remaining = timeout - elapsed
            print_formatted("INFO", f"⏱️ Still waiting for game join... {remaining}s remaining")
            last_status_time = elapsed
        
        if is_in_game(game_id, private_server):
            print_formatted("SUCCESS", f"✓ Game join confirmed after {elapsed}s!")
            return True
        
        time.sleep(check_interval)
    
    print_formatted("WARNING", f"⚠️ Game join timeout after {timeout}s")
    return False

def should_attempt_launch(config):
    """Determine if we should attempt to launch/rejoin the game"""
    # Check if Roblox is running
    if not is_roblox_running():
        print_formatted("INFO", "Roblox not running, need to launch")
        return True
    
    # Check if we're in the correct game
    game_id = config.get('game_id')
    private_server = config.get('private_server', '')
    if not is_in_game(game_id, private_server):
        print_formatted("INFO", "Not in correct game, need to rejoin")
        return True
    
    # Check for error states
    error_state = check_error_states()
    if error_state:
        print_formatted("WARNING", f"Error state detected: {error_state}")
        return True
    
    return False

def automation_loop(config):
    """Main automation loop"""
    global automation_running, last_game_join_time
    
    automation_running = True
    print_formatted("SUCCESS", "Automation started successfully!")
    
    # Initial game join attempt
    if not attempt_game_join(config):
        print_formatted("ERROR", "Failed to join game initially. Will keep trying...")
    
    consecutive_checks = 0
    in_game_time = 0
    
    while automation_running:
        try:
            game_id = config.get('game_id')
            private_server = config.get('private_server', '')
            
            # Check current status
            roblox_running = is_roblox_running()
            in_correct_game = is_in_game(game_id, private_server) if roblox_running else False
            error_state = check_error_states()
            
            # Clear status reporting
            if roblox_running and in_correct_game and not error_state:
                consecutive_checks += 1
                in_game_time += config.get('check_delay', 45)
                
                if consecutive_checks == 1:
                    print_formatted("SUCCESS", f"✓ Successfully in game {game_id}")
                    print_formatted("INFO", "Monitoring game status... (automation will only restart if there's a problem)")
                elif consecutive_checks % 4 == 0:  # Every 4 checks (~3 minutes)
                    minutes = in_game_time // 60
                    print_formatted("INFO", f"✓ Still in game - Running for {minutes} minutes")
                
            else:
                # Reset counters when not in game
                if consecutive_checks > 0:
                    print_formatted("WARNING", "No longer in game - investigating...")
                consecutive_checks = 0
                in_game_time = 0
                
                # Determine what action to take
                if error_state:
                    print_formatted("ERROR", f"✗ Problem detected: {error_state}")
                    print_formatted("INFO", "Restarting due to error...")
                    if attempt_game_join(config):
                        print_formatted("SUCCESS", "✓ Successfully rejoined after error")
                elif not roblox_running:
                    print_formatted("WARNING", "✗ Roblox not running")
                    print_formatted("INFO", "Launching Roblox...")
                    if attempt_game_join(config):
                        print_formatted("SUCCESS", "✓ Successfully launched Roblox")
                elif not in_correct_game:
                    print_formatted("WARNING", f"✗ Not in correct game {game_id}")
                    print_formatted("INFO", "Attempting to join correct game...")
                    if attempt_game_join(config):
                        print_formatted("SUCCESS", "✓ Successfully joined correct game")
            
            # Wait before next check
            check_delay = config.get('check_delay', 45)
            if consecutive_checks == 0:  # Only show countdown when not stable in game
                print_formatted("INFO", f"Next check in {check_delay} seconds...")
            
            time.sleep(check_delay)
            
        except KeyboardInterrupt:
            print_formatted("INFO", "Automation interrupted by user")
            break
        except Exception as e:
            print_formatted("ERROR", f"Automation loop error: {str(e)}")
            time.sleep(10)
    
    automation_running = False
    print_formatted("INFO", "Automation stopped")

# ======================
# INTERACTIVE MENU
# ======================
def display_menu():
    """Display main menu"""
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
    """Interactive configuration setup"""
    config = load_config()
    
    print(f"\n{COLORS['HEADER']}=== CONFIGURATION SETUP ==={COLORS['RESET']}")
    
    # Game ID
    current_game_id = config.get('game_id', '')
    print(f"\nCurrent Game ID: {current_game_id if current_game_id else 'Not set'}")
    new_game_id = input("Enter new Game ID (or press Enter to keep current): ").strip()
    if new_game_id:
        config['game_id'] = new_game_id
    
    # Private Server
    current_private_server = config.get('private_server', '')
    print(f"\nCurrent Private Server: {current_private_server if current_private_server else 'Not set'}")
    new_private_server = input("Enter Private Server link (or press Enter to keep current): ").strip()
    if new_private_server:
        config['private_server'] = new_private_server
    
    # Check Delay
    current_delay = config.get('check_delay', 45)
    print(f"\nCurrent Check Delay: {current_delay} seconds")
    new_delay = input("Enter new Check Delay in seconds (or press Enter to keep current): ").strip()
    if new_delay and new_delay.isdigit():
        config['check_delay'] = int(new_delay)
    
    # Max Retries
    current_retries = config.get('max_retries', 3)
    print(f"\nCurrent Max Retries: {current_retries}")
    new_retries = input("Enter new Max Retries (or press Enter to keep current): ").strip()
    if new_retries and new_retries.isdigit():
        config['max_retries'] = int(new_retries)
    
    # Auto Rejoin
    current_rejoin = config.get('auto_rejoin', True)
    print(f"\nCurrent Auto Rejoin: {'Enabled' if current_rejoin else 'Disabled'}")
    new_rejoin = input("Enable Auto Rejoin? (y/n, or press Enter to keep current): ").strip().lower()
    if new_rejoin in ['y', 'yes']:
        config['auto_rejoin'] = True
    elif new_rejoin in ['n', 'no']:
        config['auto_rejoin'] = False
    
    # Save configuration
    if save_config(config):
        print_formatted("SUCCESS", "Configuration saved successfully!")
    else:
        print_formatted("ERROR", "Failed to save configuration!")
    
    input("\nPress Enter to continue...")

def view_current_config():
    """Display current configuration"""
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
    """Test game joining functionality"""
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
    """Display system information"""
    print(f"\n{COLORS['HEADER']}=== SYSTEM INFORMATION ==={COLORS['RESET']}")
    
    if platform_info:
        print(f"{COLORS['CYAN']}Platform Type:{COLORS['RESET']} {platform_info['type']}")
        print(f"{COLORS['CYAN']}Platform Name:{COLORS['RESET']} {platform_info['name']}")
        print(f"{COLORS['CYAN']}Root Access:{COLORS['RESET']} {'Available' if platform_info.get('has_root') else 'Limited'}")
        print(f"{COLORS['CYAN']}ADB Support:{COLORS['RESET']} {'Yes' if platform_info.get('use_adb') else 'No'}")
        print(f"{COLORS['CYAN']}Shell Prefix:{COLORS['RESET']} {platform_info.get('shell_prefix', 'None')}")
    
    # Check Roblox installation
    roblox_installed = verify_roblox_installation()
    print(f"{COLORS['CYAN']}Roblox Installed:{COLORS['RESET']} {'Yes' if roblox_installed else 'No'}")
    
    if roblox_installed:
        roblox_running = is_roblox_running()
        print(f"{COLORS['CYAN']}Roblox Running:{COLORS['RESET']} {'Yes' if roblox_running else 'No'}")
    
    # Android version
    try:
        android_version = run_shell_command("getprop ro.build.version.release", platform_info=platform_info)
        print(f"{COLORS['CYAN']}Android Version:{COLORS['RESET']} {android_version if android_version else 'Unknown'}")
    except:
        pass
    
    # Device model
    try:
        device_model = run_shell_command("getprop ro.product.model", platform_info=platform_info)
        print(f"{COLORS['CYAN']}Device Model:{COLORS['RESET']} {device_model if device_model else 'Unknown'}")
    except:
        pass
    
    input("\nPress Enter to continue...")

# ======================
# MAIN FUNCTION
# ======================
def main():
    """Main function"""
    global platform_info, automation_running
    
    try:
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{COLORS['HEADER']}")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║              ENHANCED ROBLOX AUTOMATION TOOL                 ║")
        print("║          Supports: UGPHONE, VSPHONE, REDFINGER              ║")
        print("║                    Standard Android & Emulators             ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print(f"{COLORS['RESET']}")
        
        # Initialize platform detection
        detector = PlatformDetector()
        platform_info = detector.detect_platform()
        
        # Verify Roblox installation
        if not verify_roblox_installation():
            print_formatted("ERROR", "Roblox is not installed or not accessible!")
            print_formatted("INFO", "Please install Roblox and ensure proper permissions.")
            sys.exit(1)
        
        automation_thread = None
        
        # Main menu loop
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