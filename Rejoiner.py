import requests
import time
import os
import json
from ppadb.client import Client
from datetime import datetime

# ANSI color codes for enhanced console UI
COLORS = {
    "RESET": "\033[0m",
    "INFO": "\033[94m",
    "SUCCESS": "\033[92m",
    "WARNING": "\033[93m",
    "ERROR": "\033[91m",
    "BOLD": "\033[1m",
    "CYAN": "\033[96m"
}

# Configuration file
CONFIG_FILE = "/sdcard/Download/roblox_config.json"

# Print formatted console message with status
def print_status(level, message, status=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = {
        "INFO": COLORS["INFO"],
        "SUCCESS": COLORS["SUCCESS"],
        "WARNING": COLORS["WARNING"],
        "ERROR": COLORS["ERROR"]
    }.get(level, COLORS["RESET"])
    status_str = f" [{status}]" if status else ""
    print(f"{COLORS['CYAN']}[{timestamp}]{COLORS['RESET']} {color}{level}:{COLORS['RESET']} {message}{status_str}")

# Load or initialize config
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                if "check_method" not in config:
                    config["check_method"] = 3  # Default to both if not set
                return config
        print_status("INFO", "Config file not found. Creating new config.")
        return {"accounts": [], "game_id": "", "private_server": "", "check_delay": 30, "active_account": "", "check_method": 3}
    except Exception as e:
        print_status("ERROR", f"Error loading config: {e}")
        return {"accounts": [], "game_id": "", "private_server": "", "check_delay": 30, "active_account": "", "check_method": 3}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print_status("SUCCESS", "Config saved.")
    except Exception as e:
        print_status("ERROR", f"Error saving config: {e}")

# Get User ID from username using Roblox API
def get_user_id(username):
    try:
        url = f"https://api.roblox.com/users/get-by-username?username={username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_id = str(data.get("Id"))
            if user_id:
                print_status("SUCCESS", f"Resolved {username} to User ID {user_id}")
                return user_id
            print_status("ERROR", f"No User ID for {username}")
            return None
        print_status("ERROR", f"Failed to get User ID for {username}. Status: {response.status_code}")
        return None
    except Exception as e:
        print_status("ERROR", f"Error fetching User ID: {e}")
        return None

# Add account
def add_account(config):
    print_status("INFO", "Enter Roblox Username or User ID:")
    account = input("> ").strip()
    if not account:
        print_status("ERROR", "Account cannot be empty")
        return
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        if user_id:
            account = user_id
            print_status("SUCCESS", f"Converted to User ID {user_id}")
        else:
            print_status("WARNING", f"Could not validate {account}. Using as is")
    if account not in config["accounts"]:
        config["accounts"].append(account)
        save_config(config)
        print_status("SUCCESS", f"Added account {account}")
    else:
        print_status("WARNING", "Account already exists")

# Delete account
def delete_account(config):
    if not config["accounts"]:
        print_status("WARNING", "No accounts to delete")
        return
    print_status("INFO", "Select account to delete:")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            removed = config["accounts"].pop(choice)
            if config["active_account"] == removed:
                config["active_account"] = ""
            save_config(config)
            print_status("SUCCESS", f"Deleted account {removed}")
        else:
            print_status("ERROR", "Invalid choice")
    except ValueError:
        print_status("ERROR", "Enter a number")

# Select active account
def select_account(config):
    if not config["accounts"]:
        print_status("WARNING", "No accounts available")
        return
    print_status("INFO", "Select account for auto-rejoin:")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            config["active_account"] = config["accounts"][choice]
            save_config(config)
            print_status("SUCCESS", f"Set active account to {config['active_account']}")
        else:
            print_status("ERROR", "Invalid choice")
    except ValueError:
        print_status("ERROR", "Enter a number")

# Validate game ID
def validate_game_id(game_id):
    try:
        if not game_id.isdigit() or len(game_id) < 9 or len(game_id) > 15:
            print_status("ERROR", f"Invalid Game ID {game_id}. Must be 9-15 digits")
            return False
        return True
    except Exception as e:
        print_status("ERROR", f"Error validating Game ID: {e}")
        return False

# Validate private server link
def validate_private_server(private_server):
    try:
        if "privateServerLinkCode" not in private_server or "roblox.com" not in private_server:
            print_status("ERROR", "Invalid private server link. Must include 'privateServerLinkCode' and 'roblox.com'")
            return False
        return True
    except Exception as e:
        print_status("ERROR", f"Error validating private server: {e}")
        return False

# Set game ID or private server link
def set_game(config):
    print_status("INFO", "Enter Game ID (PlaceID) or Private Server Link:")
    game_input = input("> ").strip()
    if "privateServerLinkCode" in game_input:
        if validate_private_server(game_input):
            config["private_server"] = game_input
            config["game_id"] = ""
            print_status("INFO", "Private server set. May require authentication")
        else:
            return
    else:
        if not validate_game_id(game_input):
            return
        config["game_id"] = game_input
        config["private_server"] = ""
    save_config(config)
    print_status("SUCCESS", "Game settings updated")

# Set check delay
def set_check_delay(config):
    try:
        print_status("INFO", "Enter check delay (seconds, min 10):")
        delay = int(input("> ").strip())
        if delay < 10:
            print_status("ERROR", "Delay must be at least 10 seconds")
            return
        config["check_delay"] = delay
        save_config(config)
        print_status("SUCCESS", f"Check delay set to {delay} seconds")
    except ValueError:
        print_status("ERROR", "Enter a number")

# Check if ADB is connected
def check_adb():
    try:
        adb = Client(host="127.0.0.1", port=5037)
        devices = adb.devices()
        if not devices:
            print_status("ERROR", "No devices connected. Enable ADB and connect")
            return None
        print_status("SUCCESS", f"Connected to {devices[0].serial}")
        return devices[0]
    except Exception as e:
        print_status("ERROR", f"ADB error: {e}")
        return None

# Check if Roblox is running and in-game
def is_roblox_running(device, game_id=None):
    if not device:
        return False
    try:
        ps_output = device.shell("ps | grep com.roblox.client")
        if "com.roblox.client" in ps_output:
            cmd = "dumpsys activity | grep com.roblox.client"
            activity_output = device.shell(cmd)
            if "com.roblox.client" in activity_output:
                if game_id:
                    cmd = f"logcat -d | grep -i 'PlaceId.*{game_id}'"
                    output = device.shell(cmd)
                    if game_id in output:
                        print_status("SUCCESS", f"Roblox running with Game ID {game_id}")
                        return True
                    print_status("WARNING", "Roblox running but not in specified game")
                    return "menu"
                print_status("SUCCESS", "Roblox running")
                return True
        print_status("WARNING", "Roblox not running")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking Roblox: {e}")
        return False

# Check if game is joined
def is_game_joined(device, game_id, private_server):
    if not device:
        return False
    try:
        if private_server:
            link_code = private_server.split("privateServerLinkCode=")[-1].split("&")[0]
            cmd = f"logcat -d | grep -i '{link_code}'"
            output = device.shell(cmd)
            if output.strip():
                print_status("SUCCESS", "Joined private server")
                return True
        else:
            cmd = f"logcat -d | grep -i 'PlaceId.*{game_id}'"
            output = device.shell(cmd)
            if game_id in output:
                print_status("SUCCESS", f"Joined game with ID {game_id}")
                return True
            # Additional check for activity state
            cmd = f"dumpsys activity | grep -i {game_id}"
            activity_output = device.shell(cmd)
            if game_id in activity_output:
                print_status("SUCCESS", f"Detected game with ID {game_id} in activity")
                return True
        print_status("WARNING", "Not joined to specified game")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking game join: {e}")
        return False

# Check executor UI and Roblox status
def is_executor_running(device):
    if not device:
        return False
    try:
        executor_packages = ["com.codex", "com.arceusx", "com.delta"]
        for pkg in executor_packages:
            output = device.shell(f"ps | grep {pkg}")
            if output.strip():
                print_status("INFO", f"Executor {pkg} detected")
                # Check Roblox UI for kick/ban/freeze
                cmd = "logcat -d | grep -iE 'kicked|disconnected|banned|freeze|crash|ANR'"
                log_output = device.shell(cmd)
                if any(keyword in log_output.lower() for keyword in ["kicked", "disconnected", "banned", "crash", "anr"]):
                    print_status("ERROR", "Roblox kicked/banned/crashed")
                    return "rejoin"
                cmd = "dumpsys window | grep mCurrentFocus"
                focus_output = device.shell(cmd)
                if "com.roblox.client" not in focus_output:
                    print_status("WARNING", "Roblox not in focus. Possible freeze or UI issue")
                    return "check"
                print_status("SUCCESS", "Executor and Roblox UI active")
                return True
        print_status("WARNING", "No executor detected")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking executor: {e}")
        return False

# Check for freeze (simplified via log activity)
def is_frozen(device):
    if not device:
        return False
    try:
        cmd = "logcat -d | grep -iE 'freeze|stuck|timeout'"
        output = device.shell(cmd)
        if any(keyword in output.lower() for keyword in ["freeze", "stuck", "timeout"]):
            print_status("ERROR", "Roblox appears frozen")
            return True
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking freeze: {e}")
        return False

# Launch Roblox game with orientation
def launch_game(config, game_id, private_server, retries=3):
    device = check_adb()
    if not device:
        return False
    if private_server:
        if not validate_private_server(private_server):
            return False
        url = private_server.replace("https://www.roblox.com", "roblox://")
    else:
        if not validate_game_id(game_id):
            print_status("ERROR", f"Invalid Game ID {game_id}. Enter a valid 9-15 digit ID:")
            new_id = input("> ").strip()
            if new_id and validate_game_id(new_id):
                config["game_id"] = new_id
                config["private_server"] = ""
                save_config(config)
                game_id = new_id
            else:
                print_status("ERROR", "No valid ID. Launch aborted")
                return False
        url = f"roblox://placeID={game_id}"
    deep_link_failed = 0
    for attempt in range(retries):
        try:
            device.shell("settings put system accelerometer_rotation 0")
            device.shell("input keyevent 19")
            device.shell("am start --activity-force-rotate -a android.intent.action.RUN -n com.roblox.client/.ActivityLauncher")
            time.sleep(2)
            device.shell("input keyevent 19")
            cmd = f"am start -a android.intent.action.RUN -d '{url}' -n com.roblox.client/.ActivityLauncher"
            print_status("INFO", f"Attempt {attempt + 1}/{retries}: {cmd}", "Launching")
            device.shell(cmd)
            time.sleep(20)  # Extended wait for app to start
            if is_roblox_running(device, game_id):
                print_status("SUCCESS", f"Launched with {'private server' if private_server else f'Game ID {game_id}'}", "Running")
                return True
            deep_link_failed += 1
            print_status("INFO", f"Deep link attempt {attempt + 1} failed. Checking activity...", "Debug")
            cmd = "dumpsys activity | grep com.roblox.client"
            activity_output = device.shell(cmd)
            if "com.roblox.client" in activity_output:
                print_status("WARNING", "Deep link failed but Roblox app started. Joining manually recommended...")
                cmd = "am start -a android.intent.action.RUN -n com.roblox.client/.ActivityLauncher"
                device.shell(cmd)
                time.sleep(20)
                if is_roblox_running(device):
                    print_status("SUCCESS", "Launched. Join game manually if needed", "Running")
                    if deep_link_failed == retries:
                        print_status("WARNING", "Deep links failed repeatedly. Manual join required.")
                    return True
            print_status("WARNING", "Deep link and direct launch failed. Retrying...")
        except Exception as e:
            print_status("ERROR", f"Launch error: {e}", "Failed")
        print_status("WARNING", f"Attempt {attempt + 1} failed. Retrying...", "Retrying")
        time.sleep(5)
    print_status("ERROR", "Launch failed after retries. Open Roblox manually and use option 7 to verify.", "Failed")
    return False

# Close Roblox app
def close_roblox(device):
    if not device:
        return False
    try:
        device.shell("am force-stop com.roblox.client")
        time.sleep(5)
        print_status("SUCCESS", "Closed Roblox")
        return True
    except Exception as e:
        print_status("ERROR", f"Error closing Roblox: {e}")
        return False

# Check status with selectable method and save preference
def check_executor_and_roblox(config):
    device = check_adb()
    if not device:
        return
    print_status("INFO", "Select check method:", "Choosing")
    print(f"""
{COLORS['BOLD']}Check Options:{COLORS['RESET']}
  {COLORS['CYAN']}1:{COLORS['RESET']} Check Executor UI
  {COLORS['CYAN']}2:{COLORS['RESET']} Check Roblox Running
  {COLORS['CYAN']}3:{COLORS['RESET']} Check Both
""")
    try:
        choice = int(input(f"{COLORS['CYAN']}> {COLORS['RESET']}").strip())
        if choice in [1, 2, 3]:
            config["check_method"] = choice
            save_config(config)
            print_status("SUCCESS", f"Saved check method {choice}")
        else:
            print_status("ERROR", "Invalid choice")
            return
        if choice == 1:
            print_status("INFO", "Checking Executor UI...", "Checking")
            executor_status = is_executor_running(device)
            if executor_status == "rejoin":
                print_status("ERROR", "Roblox issue detected. Rejoin recommended")
            elif executor_status == "check":
                print_status("WARNING", "Roblox may be frozen or not in focus")
            elif executor_status:
                print_status("SUCCESS", "Executor UI active")
            else:
                print_status("WARNING", "No executor detected")
        elif choice == 2:
            print_status("INFO", "Checking Roblox Running...", "Checking")
            status = is_roblox_running(device, config["game_id"])
            if status == True:
                print_status("SUCCESS", "Roblox running in game")
            elif status == "menu":
                print_status("WARNING", "Roblox running but not in game")
            else:
                print_status("WARNING", "Roblox not running")
        elif choice == 3:
            print_status("INFO", "Checking Both...", "Checking")
            status = is_roblox_running(device, config["game_id"])
            if status == True:
                print_status("SUCCESS", "Roblox running in game")
            elif status == "menu":
                print_status("WARNING", "Roblox running but not in game")
            else:
                print_status("WARNING", "Roblox not running")
            executor_status = is_executor_running(device)
            if executor_status == "rejoin":
                print_status("ERROR", "Roblox issue detected. Rejoin recommended")
            elif executor_status == "check":
                print_status("WARNING", "Roblox may be frozen or not in focus")
            elif executor_status:
                print_status("SUCCESS", "Executor UI active")
            else:
                print_status("WARNING", "No executor detected")
        print_status("INFO", "Check complete. Method saved for auto-rejoin.", "Done")
    except ValueError:
        print_status("ERROR", "Enter a number")

# Auto-rejoin loop with saved check method
def auto_rejoin(config):
    if not config["active_account"]:
        print_status("ERROR", "No active account selected", "Stopped")
        return
    if not config["game_id"] and not config["private_server"]:
        print_status("ERROR", "No game ID or private server set", "Stopped")
        return
    device = check_adb()
    if not device:
        print_status("ERROR", "ADB connection failed", "Stopped")
        return
    print_status("INFO", f"Starting auto-rejoin for {config['active_account']}...", "Starting")
    while True:
        try:
            print_status("INFO", "Checking status...", "Checking")
            status = is_roblox_running(device, config["game_id"])
            if not status:
                print_status("WARNING", "Roblox not running. Rejoining...", "Rejoining")
                close_roblox(device)
                if not launch_game(config, config["game_id"], config["private_server"]):
                    print_status("ERROR", "Rejoin failed. Check Game ID or open Roblox manually.", "Failed")
                    if config["game_id"] and not validate_game_id(config["game_id"]):
                        print_status("ERROR", "Invalid Game ID. Enter new ID:")
                        new_id = input("> ").strip()
                        if new_id and validate_game_id(new_id):
                            config["game_id"] = new_id
                            save_config(config)
                            print_status("INFO", f"Updated to {new_id}", "Updated")
                            launch_game(config, config["game_id"], config["private_server"])
            elif status == "menu":
                print_status("WARNING", "Not in game. Rejoining...", "Rejoining")
                close_roblox(device)
                launch_game(config, config["game_id"], config["private_server"])
            # Apply saved check method
            if config["check_method"] == 1:
                executor_status = is_executor_running(device)
                if executor_status == "rejoin":
                    close_roblox(device)
                    launch_game(config, config["game_id"], config["private_server"])
                elif is_frozen(device):
                    print_status("ERROR", "Roblox frozen. Rejoining...", "Rejoining")
                    close_roblox(device)
                    launch_game(config, config["game_id"], config["private_server"])
                elif executor_status:
                    print_status("SUCCESS", "Executor UI active", "Running")
            elif config["check_method"] == 2:
                if is_frozen(device):
                    print_status("ERROR", "Roblox frozen. Rejoining...", "Rejoining")
                    close_roblox(device)
                    launch_game(config, config["game_id"], config["private_server"])
                elif status:
                    print_status("SUCCESS", "Roblox running in game", "Running")
            elif config["check_method"] == 3:
                executor_status = is_executor_running(device)
                if executor_status == "rejoin":
                    close_roblox(device)
                    launch_game(config, config["game_id"], config["private_server"])
                elif is_frozen(device):
                    print_status("ERROR", "Roblox frozen. Rejoining...", "Rejoining")
                    close_roblox(device)
                    launch_game(config, config["game_id"], config["private_server"])
                elif status and executor_status:
                    print_status("SUCCESS", "Roblox and executor active", "Running")
            print_status("INFO", f"Next check in {config['check_delay']}s...", "Waiting")
            for i in range(config["check_delay"]):
                time.sleep(1)
                print(f"\r{COLORS['CYAN']}Waiting: {config['check_delay'] - i}s{COLORS['RESET']}", end="")
            print("\r" + " " * 20 + "\r", end="")
        except KeyboardInterrupt:
            print_status("INFO", "Stopped by user", "Stopped")
            close_roblox(device)
            break
        except Exception as e:
            print_status("ERROR", f"Unexpected error: {e}", "Error")
            time.sleep(10)

# Main menu
def main():
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=================================
       Koala Hub Auto-Rejoin v3.1
================================={COLORS['RESET']}
Note: For cloud phones (e.g., UGPhone), enable floating windows manually if supported.
""")
    config = load_config()
    while True:
        print(f"""
{COLORS['BOLD']}Menu:{COLORS['RESET']}
{COLORS['CYAN']}Active Account:{COLORS['RESET']} {config['active_account'] or 'None'}
{COLORS['CYAN']}Game ID:{COLORS['RESET']} {config['game_id'] or 'None'}
{COLORS['CYAN']}Private Server:{COLORS['RESET']} {config['private_server'] or 'None'}
{COLORS['CYAN']}Check Delay:{COLORS['RESET']} {config['check_delay']}s
{COLORS['CYAN']}Check Method:{COLORS['RESET']} {config['check_method'] or '3 (Both)'}
{COLORS['BOLD']}Options:{COLORS['RESET']}
  {COLORS['CYAN']}1:{COLORS['RESET']} Add Account
  {COLORS['CYAN']}2:{COLORS['RESET']} Delete Account
  {COLORS['CYAN']}3:{COLORS['RESET']} Select Account
  {COLORS['CYAN']}4:{COLORS['RESET']} Set GameID/PsLink
  {COLORS['CYAN']}5:{COLORS['RESET']} Set Check Delay
  {COLORS['CYAN']}6:{COLORS['RESET']} Start Auto-Rejoin
  {COLORS['CYAN']}7:{COLORS['RESET']} Check Status
  {COLORS['CYAN']}8:{COLORS['RESET']} Exit
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
            auto_rejoin(config)
        elif choice == "7":
            check_executor_and_roblox(config)
        elif choice == "8":
            print_status("INFO", "Exiting...")
            break
        else:
            print_status("ERROR", "Invalid choice")

if __name__ == "__main__":
    main()