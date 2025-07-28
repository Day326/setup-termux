import requests
import time
import os
import json
import subprocess
from datetime import datetime
from ppadb.client import Client as AdbClient
from prettytable import PrettyTable

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
    "CYAN": "\033[96m"
}

CONFIG_FILE = "/sdcard/Download/roblox_config.json"
ROBLOX_PACKAGE = "com.roblox.client"
ADB_PORT = 5037
ADB_HOST = "127.0.0.1"

# ======================
# CORE FUNCTIONS
# ======================
def print_formatted(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = COLORS.get(level, COLORS["RESET"])
    table = PrettyTable()
    table.field_names = ["Timestamp", "Level", "Message"]
    table.align = "l"
    table.add_row([timestamp, level, message])
    print(f"{color}{table}{COLORS['RESET']}")

def is_root_available():
    try:
        result = subprocess.run(["su", "-c", "echo test"], 
                              capture_output=True, 
                              text=True)
        return "test" in result.stdout
    except:
        return False

def load_config():
    default_config = {
        "accounts": [],
        "game_id": "",
        "private_server": "",
        "check_delay": 30,
        "active_account": "",
        "check_method": "both",
        "auto_clear_cache": True,
        "max_retries": 3,
        "game_validation": True
    }
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        print_formatted("INFO", "Creating new config file...")
        return default_config
    except Exception as e:
        print_formatted("ERROR", f"Config load error: {e}")
        return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print_formatted("SUCCESS", "Config saved")
    except Exception as e:
        print_formatted("ERROR", f"Config save error: {e}")

# ======================
# ADB FUNCTIONS
# ======================
def check_adb():
    try:
        adb = AdbClient(host=ADB_HOST, port=ADB_PORT)
        devices = adb.devices()
        
        if not devices:
            print_formatted("WARNING", "No devices found. Restarting ADB...")
            os.system("adb kill-server")
            os.system("adb start-server")
            time.sleep(2)
            devices = adb.devices()
            
        if devices:
            device = devices[0]
            print_formatted("SUCCESS", f"Connected to {device.serial}")
            return device
            
        print_formatted("ERROR", "No ADB devices available")
        return None
    except Exception as e:
        print_formatted("ERROR", f"ADB connection failed: {e}")
        return None

# ======================
# ROBLOX STATUS FUNCTIONS
# ======================
def is_roblox_running(device):
    try:
        # Check multiple ways Roblox might be running
        proc = device.shell("ps -A | grep com.roblox.client | grep -v grep").strip()
        activity = device.shell("dumpsys activity activities | grep com.roblox.client").strip()
        surface = device.shell("dumpsys SurfaceFlinger --list | grep com.roblox.client").strip()
        
        return bool(proc) or bool(activity) or bool(surface)
    except Exception as e:
        print_formatted("ERROR", f"Process check error: {e}")
        return False

def is_roblox_in_main_menu(device):
    try:
        output = device.shell("dumpsys window windows | grep mCurrentFocus")
        return "com.roblox.client" in output and ("MainActivity" in output or "HomeActivity" in output)
    except Exception as e:
        print_formatted("ERROR", f"Main menu check error: {e}")
        return False

def is_game_joined(device, game_id, private_server):
    """Improved game detection with multiple methods"""
    try:
        # Method 1: Check logs for game patterns
        patterns = [
            f"place[._]?id.*{game_id}",
            f"game[._]?id.*{game_id}",
            f"joining.*{game_id}",
            "entered.*game",
            "joined.*place"
        ]
        
        if private_server:
            if "privateServerLinkCode=" in private_server:
                code = private_server.split("privateServerLinkCode=")[1].split("&")[0]
            else:
                code = private_server.split("share?code=")[1].split("&")[0]
            patterns.extend([
                f"private.*server.*{code}",
                f"server.*code.*{code}"
            ])
        
        log_cmd = f"logcat -d -t 200 | grep -iE '{'|'.join(patterns)}'"
        logs = device.shell(log_cmd)
        if logs.strip():
            return True
            
        # Method 2: Check current activity
        activity = device.shell("dumpsys window windows | grep mCurrentFocus")
        if "com.roblox.client" in activity and ("GameActivity" in activity or "ExperienceActivity" in activity):
            return True
            
        return False
    except Exception as e:
        print_formatted("ERROR", f"Game detection error: {e}")
        return False

def close_roblox(device):
    """Force stop Roblox completely"""
    try:
        if is_root_available():
            device.shell("su -c 'am force-stop com.roblox.client'")
        else:
            device.shell("am force-stop com.roblox.client")
        time.sleep(3)
        return True
    except Exception as e:
        print_formatted("ERROR", f"Failed to close Roblox: {e}")
        return False

# ======================
# GAME LAUNCH FUNCTIONS
# ======================
def prepare_roblox(device, config):
    """Prepare Roblox for clean launch"""
    try:
        print_formatted("INFO", "Preparing Roblox for launch...")
        
        # 1. Stop Roblox gently first
        close_roblox(device)
        
        # 2. Clear cache if enabled
        if config.get("auto_clear_cache", True):
            clear_roblox_cache(device)
        
        # 3. Reset permissions
        device.shell("pm reset-permissions com.roblox.client")
        time.sleep(1)
        
        return True
    except Exception as e:
        print_formatted("ERROR", f"Preparation error: {e}")
        return False

def clear_roblox_cache(device):
    """Completely clear Roblox cache and data"""
    try:
        if is_root_available():
            device.shell("su -c 'pm clear com.roblox.client'")
            device.shell("su -c 'rm -rf /data/data/com.roblox.client/cache'")
            device.shell("su -c 'rm -rf /data/data/com.roblox.client/files'")
            print_formatted("SUCCESS", "Deep cache cleared (root)")
        else:
            device.shell("pm clear com.roblox.client")
            print_formatted("SUCCESS", "Basic cache cleared")
        time.sleep(2)
        return True
    except Exception as e:
        print_formatted("ERROR", f"Cache clear error: {e}")
        return False

def launch_game(config, device):
    """Launch Roblox with proper game/private server"""
    try:
        # Prepare launch URL
        if config["private_server"]:
            # Handle both private server link formats
            if "privateServerLinkCode=" in config["private_server"]:
                code = config["private_server"].split("privateServerLinkCode=")[1].split("&")[0]
                url = f"roblox://placeId={config['game_id']}&privateServerLinkCode={code}"
            elif "share?code=" in config["private_server"]:
                code = config["private_server"].split("share?code=")[1].split("&")[0]
                url = f"roblox://placeId={config['game_id']}&linkCode={code}"
            else:
                print_formatted("ERROR", "Invalid private server link format")
                return False
        else:
            url = f"roblox://placeId={config['game_id']}"
        
        # Build launch command
        launch_cmd = (
            f"am start --user 0 "
            f"-a android.intent.action.VIEW "
            f"-d '{url}' "
            f"-n {ROBLOX_PACKAGE}/com.roblox.client.ActivityLauncher "
            f"--activity-clear-task "
            f"--activity-no-history"
        )
        
        # Execute launch
        print_formatted("INFO", f"Launching: {url}")
        device.shell(launch_cmd)
        
        # Wait and verify
        print_formatted("INFO", "Waiting for game to load...")
        for i in range(15):
            time.sleep(1)
            if is_game_joined(device, config["game_id"], config["private_server"]):
                print_formatted("SUCCESS", "Successfully joined game")
                return True
            if i % 5 == 0:  # Bring to foreground periodically
                device.shell(f"am start -n {ROBLOX_PACKAGE}/com.roblox.client.ActivityLauncher")
        
        print_formatted("WARNING", "Game launch timed out")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Launch error: {e}")
        return False

# ======================
# GAME VALIDATION
# ======================
def validate_game_id(game_id, config):
    """Improved game ID validation with fallback option"""
    if not game_id.isdigit() or len(game_id) < 13 or len(game_id) > 15:
        print_formatted("ERROR", "Game ID must be 13-15 digits")
        return False
    
    if not config.get("game_validation", True):
        print_formatted("WARNING", "Skipping game validation as configured")
        return True
    
    try:
        url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data and data[0].get("placeId"):
                print_formatted("SUCCESS", f"Valid game: {data[0].get('name', 'Unknown')}")
                return True
            elif isinstance(data, dict) and data.get("data"):
                print_formatted("SUCCESS", f"Valid game: {data['data'][0].get('name', 'Unknown')}")
                return True
        
        print_formatted("WARNING", f"API returned {response.status_code}. Using fallback validation.")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Validation error: {e}")
        return True

def validate_private_server(link, config):
    """Improved private server validation"""
    try:
        if not link.startswith(("https://www.roblox.com/games/", "roblox://")):
            print_formatted("ERROR", "Invalid link format")
            return False, None
            
        if "privateServerLinkCode=" in link:
            parts = link.split("/games/")[1].split("/")
            place_id = parts[0]
            code = link.split("privateServerLinkCode=")[1].split("&")[0]
            return True, place_id
            
        elif "share?code=" in link:
            parts = link.split("/games/")[1].split("/")
            place_id = parts[0]
            code = link.split("share?code=")[1].split("&")[0]
            return True, place_id
            
        print_formatted("ERROR", "Link must contain privateServerLinkCode or share?code")
        return False, None
    except Exception as e:
        print_formatted("ERROR", f"Link validation error: {e}")
        return False, None

# ======================
# ACCOUNT MANAGEMENT
# ======================
def get_user_id(username):
    try:
        url = f"https://api.roblox.com/users/get-by-username?username={username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return str(data.get("Id"))
        print_formatted("ERROR", f"API error: {response.status_code}")
        return None
    except Exception as e:
        print_formatted("ERROR", f"User ID fetch error: {e}")
        return None

def add_account(config):
    print_formatted("INFO", "Enter Roblox username or ID:")
    account = input("> ").strip()
    
    if not account:
        print_formatted("ERROR", "Account cannot be empty")
        return
        
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        if user_id:
            account = user_id
        else:
            print_formatted("WARNING", "Couldn't verify username. Using as-is")
    
    if account not in config["accounts"]:
        config["accounts"].append(account)
        save_config(config)
        print_formatted("SUCCESS", f"Added account: {account}")
    else:
        print_formatted("WARNING", "Account already exists")

def delete_account(config):
    if not config["accounts"]:
        print_formatted("WARNING", "No accounts to delete")
        return
        
    print_formatted("INFO", "Select account to delete:")
    for i, acc in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}: {acc}{COLORS['RESET']}")
    
    try:
        choice = int(input("> ")) - 1
        if 0 <= choice < len(config["accounts"]):
            removed = config["accounts"].pop(choice)
            if config["active_account"] == removed:
                config["active_account"] = ""
            save_config(config)
            print_formatted("SUCCESS", f"Removed account: {removed}")
        else:
            print_formatted("ERROR", "Invalid selection")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def select_account(config):
    if not config["accounts"]:
        print_formatted("WARNING", "No accounts available")
        return
        
    print_formatted("INFO", "Select active account:")
    for i, acc in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}: {acc}{COLORS['RESET']}")
    
    try:
        choice = int(input("> ")) - 1
        if 0 <= choice < len(config["accounts"]):
            config["active_account"] = config["accounts"][choice]
            save_config(config)
            print_formatted("SUCCESS", f"Active account: {config['active_account']}")
        else:
            print_formatted("ERROR", "Invalid selection")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

# ======================
# GAME SETTINGS
# ======================
def set_game(config):
    print_formatted("INFO", "Enter Game ID or Private Server Link:")
    print("(Type 'delete' to clear current settings)")
    game_input = input("> ").strip()
    
    if game_input.lower() == "delete":
        delete_game_settings(config)
        return
        
    if "roblox.com" in game_input or game_input.startswith("roblox://"):
        is_valid, place_id = validate_private_server(game_input, config)
        if is_valid:
            config["private_server"] = game_input
            config["game_id"] = place_id
            save_config(config)
            print_formatted("SUCCESS", "Private server configured")
    else:
        if validate_game_id(game_input, config):
            config["game_id"] = game_input
            config["private_server"] = ""
            save_config(config)
            print_formatted("SUCCESS", "Game ID configured")

def delete_game_settings(config):
    config["game_id"] = ""
    config["private_server"] = ""
    save_config(config)
    print_formatted("SUCCESS", "Game ID and Server Link cleared")

def set_check_delay(config):
    try:
        print_formatted("INFO", "Enter check delay (seconds, min 10):")
        delay = int(input("> ").strip())
        if delay < 10:
            print_formatted("ERROR", "Minimum delay is 10 seconds")
            return
        config["check_delay"] = delay
        save_config(config)
        print_formatted("SUCCESS", f"Check delay set to {delay}s")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def set_check_method(config):
    print_formatted("INFO", "Select check method:")
    print(f"{COLORS['CYAN']}1:{COLORS['RESET']} Executor UI only")
    print(f"{COLORS['CYAN']}2:{COLORS['RESET']} Roblox running only")
    print(f"{COLORS['CYAN']}3:{COLORS['RESET']} Both (recommended)")
    
    choice = input("> ").strip()
    methods = {"1": "executor", "2": "roblox", "3": "both"}
    
    if choice in methods:
        config["check_method"] = methods[choice]
        save_config(config)
        print_formatted("SUCCESS", f"Method set to: {methods[choice]}")
    else:
        print_formatted("ERROR", "Invalid selection")

def toggle_auto_cache(config):
    config["auto_clear_cache"] = not config.get("auto_clear_cache", True)
    save_config(config)
    status = "ENABLED" if config["auto_clear_cache"] else "DISABLED"
    print_formatted("SUCCESS", f"Auto cache clearing {status}")

def toggle_game_validation(config):
    config["game_validation"] = not config.get("game_validation", True)
    save_config(config)
    status = "ENABLED" if config["game_validation"] else "DISABLED"
    print_formatted("SUCCESS", f"Game validation {status}")

# ======================
# STATUS CHECKS
# ======================
def check_status(config):
    device = check_adb()
    if not device:
        return
        
    print_formatted("INFO", "Running status checks...")
    
    if config["check_method"] in ["executor", "both"]:
        executor_running = is_executor_running(device)
        print_formatted("SUCCESS" if executor_running else "WARNING", 
                      f"Executor: {'Running' if executor_running else 'Not running'}")
    
    if config["check_method"] in ["roblox", "both"]:
        roblox_running = is_roblox_running(device)
        print_formatted("SUCCESS" if roblox_running else "WARNING", 
                      f"Roblox: {'Running' if roblox_running else 'Not running'}")
        
        if roblox_running:
            in_game = is_game_joined(device, config["game_id"], config["private_server"])
            print_formatted("SUCCESS" if in_game else "WARNING", 
                          f"Game status: {'In game' if in_game else 'Not in game'}")
            
            if is_roblox_in_main_menu(device):
                print_formatted("WARNING", "Roblox is in main menu")
    
    if config["active_account"]:
        logged_in = is_account_logged_in(device, config["active_account"])
        print_formatted("SUCCESS" if logged_in else "WARNING", 
                      f"Account: {'Logged in' if logged_in else 'Not logged in'}")
    
    print_formatted("INFO", "Status check complete")

def is_executor_running(device):
    try:
        packages = ["com.codex", "com.arceusx", "com.delta"]
        for pkg in packages:
            output = device.shell(f"ps -A | grep {pkg}")
            if output.strip():
                return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Executor check error: {e}")
        return False

def is_account_logged_in(device, user_id):
    try:
        output = device.shell(f"logcat -d -t 200 | grep -i 'user.*id.*{user_id}'")
        return user_id in output
    except Exception as e:
        print_formatted("ERROR", f"Account check error: {e}")
        return False

# ======================
# AUTO-REJOIN (FIXED)
# ======================
def auto_rejoin(config):
    if not is_root_available():
        print_formatted("ERROR", "Root access required for auto-rejoin")
        return
        
    if not config["active_account"]:
        print_formatted("ERROR", "No active account selected")
        return
        
    if not config["game_id"]:
        print_formatted("ERROR", "No game configured")
        return
        
    device = check_adb()
    if not device:
        return
        
    print_formatted("INFO", f"Starting auto-rejoin for {config['active_account']}")
    print_formatted("INFO", "Press Ctrl+C to stop")
    
    try:
        retry_count = 0
        max_retries = config.get("max_retries", 3)
        
        while True:
            try:
                # 1. Check current status
                if not is_roblox_running(device):
                    print_formatted("WARNING", "Roblox not running - launching...")
                    prepare_roblox(device, config)
                    if launch_game(config, device):
                        retry_count = 0
                    else:
                        retry_count += 1
                elif not is_game_joined(device, config["game_id"], config["private_server"]):
                    print_formatted("WARNING", "Not in game - rejoining...")
                    prepare_roblox(device, config)
                    if launch_game(config, device):
                        retry_count = 0
                    else:
                        retry_count += 1
                else:
                    retry_count = 0
                    print_formatted("SUCCESS", "Roblox is running and in game")
                
                # 2. Check retry limit
                if retry_count >= max_retries:
                    print_formatted("ERROR", f"Max retries ({max_retries}) reached. Waiting...")
                    time.sleep(30)
                    retry_count = 0
                    continue
                
                # 3. Wait for next check
                for i in range(config["check_delay"]):
                    time.sleep(1)
                    remaining = config["check_delay"] - i - 1
                    print(f"\r{COLORS['CYAN']}Monitoring... {remaining}s until next check{COLORS['RESET']}", end="")
                print("\r" + " " * 50 + "\r", end="")
                
            except Exception as e:
                print_formatted("ERROR", f"Rejoin error: {e}")
                time.sleep(5)
                retry_count += 1
                
    except KeyboardInterrupt:
        print_formatted("INFO", "Auto-rejoin stopped")
        close_roblox(device)

# ======================
# MAIN MENU
# ======================
def show_menu(config):
    while True:
        os.system("clear")
        print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v4.0
====================================={COLORS['RESET']}
{COLORS['BOLD']}Current Settings:{COLORS['RESET']}
{COLORS['CYAN']}• Account: {config['active_account'] or 'None'}
{COLORS['CYAN']}• Game ID: {config['game_id'] or 'None'}
{COLORS['CYAN']}• Private Server: {config['private_server'] or 'None'}
{COLORS['CYAN']}• Check Delay: {config['check_delay']}s
{COLORS['CYAN']}• Check Method: {config['check_method']}
{COLORS['CYAN']}• Auto Clear Cache: {'ON' if config.get('auto_clear_cache', True) else 'OFF'}
{COLORS['CYAN']}• Game Validation: {'ON' if config.get('game_validation', True) else 'OFF'}

{COLORS['BOLD']}Menu Options:{COLORS['RESET']}
{COLORS['CYAN']}1:{COLORS['RESET']} Add Account
{COLORS['CYAN']}2:{COLORS['RESET']} Delete Account
{COLORS['CYAN']}3:{COLORS['RESET']} Select Account
{COLORS['CYAN']}4:{COLORS['RESET']} Set Game/Server
{COLORS['CYAN']}5:{COLORS['RESET']} Set Check Delay
{COLORS['CYAN']}6:{COLORS['RESET']} Set Check Method
{COLORS['CYAN']}7:{COLORS['RESET']} Toggle Auto Cache
{COLORS['CYAN']}8:{COLORS['RESET']} Toggle Game Validation
{COLORS['CYAN']}9:{COLORS['RESET']} Check Status
{COLORS['CYAN']}10:{COLORS['RESET']} Start Auto-Rejoin
{COLORS['CYAN']}11:{COLORS['RESET']} Delete Game ID/Server
{COLORS['CYAN']}12:{COLORS['RESET']} Exit
""")

        choice = input(f"{COLORS['CYAN']}> {COLORS['RESET']}").strip()
        
        if choice == "1":
            add_account(config)
        elif choice == "2":
            delete_account(config)
        elif choice == "3":
            select_account(config)
        elif choice == "4":
            set_game(config)
        elif choice == "5":
            set_check_delay(config)
        elif choice == "6":
            set_check_method(config)
        elif choice == "7":
            toggle_auto_cache(config)
        elif choice == "8":
            toggle_game_validation(config)
        elif choice == "9":
            check_status(config)
        elif choice == "10":
            auto_rejoin(config)
        elif choice == "11":
            delete_game_settings(config)
        elif choice == "12":
            print_formatted("INFO", "Exiting...")
            break
        else:
            print_formatted("ERROR", "Invalid choice")
        
        input("Press Enter to continue...")

def main():
    config = load_config()
    
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v4.0
====================================={COLORS['RESET']}
{COLORS['BOLD']}Features:{COLORS['RESET']}
• Fixed Termux staying alive during auto-rejoin
• Improved game ID validation
• Better private server handling
• Auto-cache cleaning
• Configurable settings
• More reliable game joining
""")
    
    device = check_adb()
    if not device:
        print_formatted("ERROR", "ADB connection failed. Check:")
        print_formatted("INFO", "1. USB Debugging enabled")
        print_formatted("INFO", "2. Device connected")
        print_formatted("INFO", "3. ADB properly set up")
        return
    
    show_menu(config)

if __name__ == "__main__":
    main()