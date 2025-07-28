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

CONFIG_FILE = "/sdcard/roblox_config.json"
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
        result = subprocess.run(["su", "-c", "echo test"], capture_output=True, text=True, timeout=5)
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
        "max_retries": 3,
        "game_validation": True,
        "launch_delay": 70,
        "retry_delay": 15,
        "force_kill_delay": 5,
        "minimize_crashes": True,
        "launch_attempts": 3
    }
    try:
        device = check_adb()
        if device:
            device.shell(f"touch {CONFIG_FILE}")
            output = device.shell(f"cat {CONFIG_FILE}")
            if output.strip():
                config = json.loads(output)
                return {**default_config, **config}
            print_formatted("INFO", "Creating new config file...")
            save_config(default_config, device)
            return default_config
        else:
            print_formatted("ERROR", "No device connected for config load")
            return default_config
    except Exception as e:
        print_formatted("ERROR", f"Config load error: {e}")
        return default_config

def save_config(config, device):
    try:
        temp_file = "/sdcard/temp_config.json"
        with open(temp_file, 'w') as f:
            json.dump(config, f, indent=4)
        device.push(temp_file, CONFIG_FILE)
        os.remove(temp_file)
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
def verify_roblox_installation(device):
    try:
        output = device.shell(f"pm list packages {ROBLOX_PACKAGE}")
        if ROBLOX_PACKAGE not in output:
            print_formatted("ERROR", "Roblox is not installed on the device")
            return False
        return True
    except Exception as e:
        print_formatted("ERROR", f"Installation check error: {e}")
        return False

def is_roblox_running(device):
    try:
        proc = device.shell(f"ps -A | grep {ROBLOX_PACKAGE}").strip()
        return bool(proc)
    except Exception as e:
        print_formatted("ERROR", f"Process check error: {e}")
        return False

def get_roblox_process_count(device):
    try:
        output = device.shell(f"ps -A | grep {ROBLOX_PACKAGE}").strip()
        return len(output.splitlines()) if output else 0
    except Exception as e:
        print_formatted("ERROR", f"Process count error: {e}")
        return 0

def get_current_activity(device):
    try:
        output = device.shell("dumpsys window windows | grep mCurrentFocus")
        return output.strip()
    except Exception as e:
        print_formatted("ERROR", f"Activity check error: {e}")
        return ""

def is_in_game_activity(activity):
    return "GameActivity" in activity or "ExperienceActivity" in activity

def is_in_main_menu(activity):
    return "MainActivity" in activity or "HomeActivity" in activity

def is_in_error_state(activity):
    return "ErrorActivity" in activity or "CrashActivity" in activity or "white" in activity.lower()

def detect_main_activity(device):
    activities = [
        "com.roblox.client.StartupActivity",
        "com.roblox.client.MainActivity",
        "com.roblox.client.HomeActivity",
        "com.roblox.client.LauncherActivity"
    ]
    for activity in activities:
        try:
            result = device.shell(f"am start -n {ROBLOX_PACKAGE}/{activity}")
            if "Error" not in result:
                time.sleep(3)
                if is_roblox_running(device) and not is_in_error_state(get_current_activity(device)):
                    return activity
        except:
            continue
    return activities[0]

def is_game_joined(device, game_id, private_server):
    try:
        device.shell("logcat -c")
        time.sleep(1)

        patterns = [
            f"place[._]?id.*{game_id}",
            f"game[._]?id.*{game_id}",
            f"joining.*{game_id}",
            f"placeId={game_id}"
        ]
        if private_server:
            if "privateServerLinkCode=" in private_server:
                code = private_server.split("privateServerLinkCode=")[1].split("&")[0]
            else:
                code = private_server.split("share?code=")[1].split("&")[0]
            patterns.append(f"linkCode={code}")

        log_cmd = f"logcat -d -t 200 | grep -iE '{'|'.join(patterns)}'"
        logs = device.shell(log_cmd)
        if logs.strip():
            print_formatted("INFO", "Game join confirmed via logs")
            return True

        activity = get_current_activity(device)
        if ROBLOX_PACKAGE in activity and is_in_game_activity(activity):
            print_formatted("INFO", "Game join confirmed via activity")
            return True

        return False
    except Exception as e:
        print_formatted("ERROR", f"Game detection error: {e}")
        return False

def close_roblox(device, is_rooted, config=None):
    try:
        if config and config.get("minimize_crashes", True):
            print_formatted("INFO", "Using safe close method...")
            device.shell("input keyevent HOME")
            time.sleep(2)
            device.shell(f"am force-stop {ROBLOX_PACKAGE}")
            time.sleep(config.get("force_kill_delay", 5))
        else:
            if is_rooted:
                device.shell(f"su -c 'am force-stop {ROBLOX_PACKAGE}'")
                time.sleep(2)
                device.shell(f"su -c 'pkill -9 -f {ROBLOX_PACKAGE}'")
                time.sleep(3)

        for _ in range(3):
            if get_roblox_process_count(device) > 0:
                print_formatted("WARNING", "Residual Roblox processes detected, forcing kill...")
                device.shell(f"am kill {ROBLOX_PACKAGE}")
                time.sleep(2)
            else:
                break

        return get_roblox_process_count(device) == 0
    except Exception as e:
        print_formatted("ERROR", f"Failed to close Roblox: {e}")
        return False

# ======================
# GAME LAUNCH FUNCTIONS
# ======================
def prepare_roblox(device, config):
    try:
        print_formatted("INFO", "Preparing Roblox for launch...")
        is_rooted = is_root_available()
        
        if is_roblox_running(device):
            close_roblox(device, is_rooted, config)
        time.sleep(5)
        return True
    except Exception as e:
        print_formatted("ERROR", f"Preparation error: {e}")
        return False

def launch_game(config, device):
    try:
        is_rooted = is_root_available()
        main_activity = detect_main_activity(device)
        
        for attempt in range(config.get("launch_attempts", 3)):
            print_formatted("INFO", f"Launch attempt {attempt + 1} of {config.get('launch_attempts', 3)}")
            
            try:
                if get_roblox_process_count(device) > 0:
                    print_formatted("WARNING", "Existing Roblox instances detected, closing all...")
                    close_roblox(device, is_rooted, config)
                    time.sleep(5)

                device.shell(f"am start -n {ROBLOX_PACKAGE}/{main_activity}")
                time.sleep(15)
                
                device.shell("input keyevent BACK")
                time.sleep(2)
                
                if config["private_server"]:
                    launch_url = config["private_server"]
                else:
                    launch_url = f"roblox://placeID={config['game_id']}"
                
                device.shell(f"am start -a android.intent.action.VIEW -d '{launch_url}'")
                time.sleep(5)
                
                device.shell(f"am start -n {ROBLOX_PACKAGE}/{main_activity}")
                time.sleep(5)

                for i in range(config['launch_delay'] // 5):
                    time.sleep(5)
                    activity = get_current_activity(device)
                    if is_game_joined(device, config["game_id"], config["private_server"]):
                        print_formatted("SUCCESS", "Successfully joined game")
                        return True
                    elif is_in_error_state(activity):
                        print_formatted("WARNING", "Detected white screen or error state, retrying...")
                        break
                    
                    if i % 2 == 0 and is_rooted and get_roblox_process_count(device) > 1:
                        print_formatted("WARNING", "Multiple instances detected, forcing close...")
                        close_roblox(device, is_rooted, config)
                        break

                print_formatted("WARNING", f"Attempt {attempt + 1} failed, retrying...")
                prepare_roblox(device, config)
                
            except Exception as e:
                print_formatted("ERROR", f"Launch attempt {attempt + 1} error: {e}")
                prepare_roblox(device, config)

        print_formatted("ERROR", "All launch attempts failed")
        return False
        
    except Exception as e:
        print_formatted("ERROR", f"Launch error: {e}")
        return False

# ======================
# GAME VALIDATION
# ======================
def validate_game_id(game_id, config):
    if not game_id.isdigit() or len(game_id) < 13 or len(game_id) > 15:
        print_formatted("ERROR", "Game ID must be 13-15 digits")
        return False
    if not config.get("game_validation", True):
        print_formatted("WARNING", "Skipping game validation as configured")
        return True
    try:
        url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}"
        headers = {"User-Agent": "Mozilla/5.0"}
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
    try:
        if not link.startswith(("https://www.roblox.com/games/", "roblox://")):
            print_formatted("ERROR", "Invalid link format")
            return False, None
        if "privateServerLinkCode=" in link or "share?code=" in link:
            parts = link.split("/games/")[1].split("/")
            place_id = parts[0]
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

def add_account(config, device):
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
        save_config(config, device)
        print_formatted("SUCCESS", f"Added account: {account}")
    else:
        print_formatted("WARNING", "Account already exists")

def delete_account(config, device):
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
            save_config(config, device)
            print_formatted("SUCCESS", f"Removed account: {removed}")
        else:
            print_formatted("ERROR", "Invalid selection")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def select_account(config, device):
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
            save_config(config, device)
            print_formatted("SUCCESS", f"Active account: {config['active_account']}")
        else:
            print_formatted("ERROR", "Invalid selection")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

# ======================
# GAME SETTINGS
# ======================
def set_game(config, device):
    print_formatted("INFO", "Enter Game ID or Private Server Link:")
    print("(Type 'delete' to clear current settings)")
    game_input = input("> ").strip()
    if game_input.lower() == "delete":
        delete_game_settings(config, device)
        return
    if "roblox.com" in game_input or game_input.startswith("roblox://"):
        is_valid, place_id = validate_private_server(game_input, config)
        if is_valid:
            config["private_server"] = game_input
            config["game_id"] = place_id
            save_config(config, device)
            print_formatted("SUCCESS", "Private server configured")
    else:
        if validate_game_id(game_input, config):
            config["game_id"] = game_input
            config["private_server"] = ""
            save_config(config, device)
            print_formatted("SUCCESS", "Game ID configured")

def delete_game_settings(config, device):
    config["game_id"] = ""
    config["private_server"] = ""
    save_config(config, device)
    print_formatted("SUCCESS", "Game ID and Server Link cleared")

def set_check_delay(config, device):
    try:
        print_formatted("INFO", "Enter check delay (seconds, min 10):")
        delay = int(input("> ").strip())
        if delay < 10:
            print_formatted("ERROR", "Minimum delay is 10 seconds")
            return
        config["check_delay"] = delay
        save_config(config, device)
        print_formatted("SUCCESS", f"Check delay set to {delay}s")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def set_check_method(config, device):
    print_formatted("INFO", "Select check method:")
    print(f"{COLORS['CYAN']}1:{COLORS['RESET']} Executor UI only")
    print(f"{COLORS['CYAN']}2:{COLORS['RESET']} Roblox running only")
    print(f"{COLORS['CYAN']}3:{COLORS['RESET']} Both (recommended)")
    choice = input("> ").strip()
    methods = {"1": "executor", "2": "roblox", "3": "both"}
    if choice in methods:
        config["check_method"] = methods[choice]
        save_config(config, device)
        print_formatted("SUCCESS", f"Method set to: {methods[choice]}")
    else:
        print_formatted("ERROR", "Invalid selection")

def set_launch_delay(config, device):
    try:
        print_formatted("INFO", "Enter launch delay (seconds, min 10, default 70):")
        delay = int(input("> ").strip())
        if delay < 10:
            print_formatted("ERROR", "Minimum delay is 10 seconds")
            return
        config["launch_delay"] = delay
        save_config(config, device)
        print_formatted("SUCCESS", f"Launch delay set to {delay}s")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def set_retry_delay(config, device):
    try:
        print_formatted("INFO", "Enter retry delay (seconds, min 5, default 15):")
        delay = int(input("> ").strip())
        if delay < 5:
            print_formatted("ERROR", "Minimum delay is 5 seconds")
            return
        config["retry_delay"] = delay
        save_config(config, device)
        print_formatted("SUCCESS", f"Retry delay set to {delay}s")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def toggle_game_validation(config, device):
    config["game_validation"] = not config.get("game_validation", True)
    save_config(config, device)
    status = "ENABLED" if config["game_validation"] else "DISABLED"
    print_formatted("SUCCESS", f"Game validation {status}")

def toggle_crash_protection(config, device):
    config["minimize_crashes"] = not config.get("minimize_crashes", True)
    save_config(config, device)
    status = "ENABLED" if config["minimize_crashes"] else "DISABLED"
    print_formatted("SUCCESS", f"Crash protection {status}")

# ======================
# STATUS CHECKS
# ======================
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
        device.shell("logcat -c")
        time.sleep(1)
        output = device.shell(f"logcat -d -t 200 | grep -i 'user.*id.*{user_id}'")
        return user_id in output
    except Exception as e:
        print_formatted("ERROR", f"Account check error: {e}")
        return False

def check_status(config, device):
    if not device:
        return
        
    if not verify_roblox_installation(device):
        return
        
    print_formatted("INFO", "Running status checks...")
    
    if config["check_method"] in ["executor", "both"]:
        executor_running = is_executor_running(device)
        print_formatted("SUCCESS" if executor_running else "WARNING", f"Executor: {'Running' if executor_running else 'Not running'}")
    
    if config["check_method"] in ["roblox", "both"]:
        roblox_running = is_roblox_running(device)
        print_formatted("SUCCESS" if roblox_running else "WARNING", f"Roblox: {'Running' if roblox_running else 'Not running'}")
        
        if roblox_running:
            activity = get_current_activity(device)
            in_game = is_game_joined(device, config["game_id"], config["private_server"])
            print_formatted("SUCCESS" if in_game else "WARNING", f"Game status: {'In game' if in_game else 'Not in game'}")
            
            if is_in_main_menu(activity):
                print_formatted("WARNING", "Roblox is in main menu")
            if is_in_error_state(activity):
                print_formatted("ERROR", "Roblox is in error state")
    
    if config["active_account"]:
        logged_in = is_account_logged_in(device, config["active_account"])
        print_formatted("SUCCESS" if logged_in else "WARNING", f"Account: {'Logged in' if logged_in else 'Not logged in'}")
    
    print_formatted("INFO", "Status check complete")

# ======================
# AUTO-REJOIN
# ======================
def should_rejoin(device, config):
    if not is_roblox_running(device):
        return True
        
    activity = get_current_activity(device)
    
    if is_game_joined(device, config["game_id"], config["private_server"]):
        return False
        
    if (is_in_main_menu(activity) or 
        is_in_error_state(activity) or
        "NotResponding" in activity):
        return True
        
    return False

def auto_rejoin(config, device):
    if not is_root_available():
        print_formatted("ERROR", "Root access required for auto-rejoin.")
        return
    
    if not config["active_account"]:
        print_formatted("ERROR", "No active account selected")
        return
        
    if not config["game_id"]:
        print_formatted("ERROR", "No game configured")
        return
        
    if not device:
        return
        
    if not verify_roblox_installation(device):
        return
    
    print_formatted("INFO", f"Starting auto-rejoin for {config['active_account']}")
    print_formatted("INFO", "Press Ctrl+C to stop. Note: Join game manually if auto-join fails.")
    
    try:
        retry_count = 0
        max_retries = config.get("max_retries", 3)
        
        while True:
            try:
                if should_rejoin(device, config):
                    print_formatted("WARNING", "Rejoin conditions met - attempting to rejoin...")
                    prepare_roblox(device, config)
                    if launch_game(config, device):
                        retry_count = 0
                    else:
                        retry_count += 1
                else:
                    retry_count = 0
                    print_formatted("SUCCESS", "Roblox is running and in correct game")
                
                if retry_count >= max_retries:
                    print_formatted("ERROR", f"Max retries ({max_retries}) reached. Waiting {config['retry_delay']}s...")
                    time.sleep(config["retry_delay"])
                    retry_count = 0
                    continue
                
                for i in range(config["check_delay"]):
                    time.sleep(1)
                    remaining = config["check_delay"] - i - 1
                    print(f"\r{COLORS['CYAN']}Monitoring... {remaining}s until next check{COLORS['RESET']}", end="")
                print("\r" + " " * 50 + "\r", end="")
                
            except Exception as e:
                print_formatted("ERROR", f"Rejoin error: {e}")
                time.sleep(config["retry_delay"])
                retry_count += 1
                
    except KeyboardInterrupt:
        print_formatted("INFO", "Auto-rejoin stopped")
        close_roblox(device, True, config)

# ======================
# MAIN MENU
# ======================
def show_menu(config, device):
    while True:
        os.system("clear")
        print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v4.8
====================================={COLORS['RESET']}
{COLORS['BOLD']}Current Settings:{COLORS['RESET']}
{COLORS['CYAN']}• Account: {config['active_account'] or 'None'}
{COLORS['CYAN']}• Game ID: {config['game_id'] or 'None'}
{COLORS['CYAN']}• Private Server: {config['private_server'] or 'None'}
{COLORS['CYAN']}• Check Delay: {config['check_delay']}s
{COLORS['CYAN']}• Check Method: {config['check_method']}
{COLORS['CYAN']}• Launch Delay: {config['launch_delay']}s
{COLORS['CYAN']}• Retry Delay: {config.get('retry_delay', 15)}s
{COLORS['CYAN']}• Game Validation: {'ON' if config.get('game_validation', True) else 'OFF'}
{COLORS['CYAN']}• Crash Protection: {'ON' if config.get('minimize_crashes', True) else 'OFF'}
{COLORS['CYAN']}• Launch Attempts: {config.get('launch_attempts', 3)}

{COLORS['BOLD']}Menu Options:{COLORS['RESET']}
{COLORS['CYAN']}1:{COLORS['RESET']} Add Account
{COLORS['CYAN']}2:{COLORS['RESET']} Delete Account
{COLORS['CYAN']}3:{COLORS['RESET']} Select Account
{COLORS['CYAN']}4:{COLORS['RESET']} Set Game/Server
{COLORS['CYAN']}5:{COLORS['RESET']} Set Check Delay
{COLORS['CYAN']}6:{COLORS['RESET']} Set Check Method
{COLORS['CYAN']}7:{COLORS['RESET']} Set Launch Delay
{COLORS['CYAN']}8:{COLORS['RESET']} Set Retry Delay
{COLORS['CYAN']}9:{COLORS['RESET']} Toggle Game Validation
{COLORS['CYAN']}10:{COLORS['RESET']} Toggle Crash Protection
{COLORS['CYAN']}11:{COLORS['RESET']} Check Status
{COLORS['CYAN']}12:{COLORS['RESET']} Start Auto-Rejoin
{COLORS['CYAN']}13:{COLORS['RESET']} Delete Game ID/Server
{COLORS['CYAN']}14:{COLORS['RESET']} Exit
""")
        choice = input(f"{COLORS['CYAN']}> {COLORS['RESET']}").strip()
        if choice == "1":
            add_account(config, device)
        elif choice == "2":
            delete_account(config, device)
        elif choice == "3":
            select_account(config, device)
        elif choice == "4":
            set_game(config, device)
        elif choice == "5":
            set_check_delay(config, device)
        elif choice == "6":
            set_check_method(config, device)
        elif choice == "7":
            set_launch_delay(config, device)
        elif choice == "8":
            set_retry_delay(config, device)
        elif choice == "9":
            toggle_game_validation(config, device)
        elif choice == "10":
            toggle_crash_protection(config, device)
        elif choice == "11":
            check_status(config, device)
        elif choice == "12":
            auto_rejoin(config, device)
        elif choice == "13":
            delete_game_settings(config, device)
        elif choice == "14":
            print_formatted("INFO", "Exiting...")
            break
        else:
            print_formatted("ERROR", "Invalid choice")
        input("Press Enter to continue...")

def main():
    config = load_config()
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v4.8
====================================={COLORS['RESET']}
{COLORS['BOLD']}Features:{COLORS['RESET']}
• Reliable single-instance Roblox launching
• Advanced crash protection system
• Smart game detection and rejoin logic
• Root-optimized for best performance
• Emulator compatibility improvements
""")
    device = check_adb()
    if not device:
        print_formatted("ERROR", "ADB connection failed. Check:")
        print_formatted("INFO", "1. USB Debugging enabled")
        print_formatted("INFO", "2. Device connected")
        print_formatted("INFO", "3. ADB properly set up")
        return
    show_menu(config, device)

if __name__ == "__main__":
    main()