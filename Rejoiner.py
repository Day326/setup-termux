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

# Print formatted console message
def print_formatted(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = {
        "INFO": COLORS["INFO"],
        "SUCCESS": COLORS["SUCCESS"],
        "WARNING": COLORS["WARNING"],
        "ERROR": COLORS["ERROR"]
    }.get(level, COLORS["RESET"])
    print(f"{COLORS['CYAN']}[{timestamp}]{COLORS['RESET']} {color}{level}:{COLORS['RESET']} {message}")

# Load or initialize config
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        print_formatted("INFO", "Config file not found. Creating new config.")
        return {"accounts": [], "game_id": "15943173912", "private_server": "", "check_delay": 30, "active_account": ""}
    except Exception as e:
        print_formatted("ERROR", f"Error loading config: {e}")
        return {"accounts": [], "game_id": "15943173912", "private_server": "", "check_delay": 30, "active_account": ""}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print_formatted("SUCCESS", f"Config saved to {CONFIG_FILE}")
    except Exception as e:
        print_formatted("ERROR", f"Error saving config: {e}")

# Get User ID from username using Roblox API
def get_user_id(username):
    try:
        url = f"https://api.roblox.com/users/get-by-username?username={username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_id = str(data.get("Id"))
            if user_id:
                print_formatted("SUCCESS", f"Resolved username {username} to User ID {user_id}")
                return user_id
            else:
                print_formatted("ERROR", f"No User ID found for username {username}")
                return None
        else:
            print_formatted("ERROR", f"Failed to get User ID for {username}. Status code: {response.status_code}")
            return None
    except Exception as e:
        print_formatted("ERROR", f"Error fetching User ID: {e}")
        return None

# Add account
def add_account(config):
    print_formatted("INFO", "Enter Roblox Username or User ID:")
    account = input("> ").strip()
    if not account:
        print_formatted("ERROR", "Account cannot be empty.")
        return
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        if user_id:
            account = user_id
            print_formatted("SUCCESS", f"Converted username to User ID {user_id}.")
        else:
            print_formatted("WARNING", f"Could not validate username {account}. Using as is.")
    if account not in config["accounts"]:
        config["accounts"].append(account)
        save_config(config)
        print_formatted("SUCCESS", f"Account {account} added.")
    else:
        print_formatted("WARNING", "Account already exists.")

# Delete account
def delete_account(config):
    if not config["accounts"]:
        print_formatted("WARNING", "No accounts to delete.")
        return
    print_formatted("INFO", "Select account to delete:")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            removed_account = config["accounts"].pop(choice)
            if config["active_account"] == removed_account:
                config["active_account"] = ""
            save_config(config)
            print_formatted("SUCCESS", f"Account {removed_account} deleted.")
        else:
            print_formatted("ERROR", "Invalid choice.")
    except ValueError:
        print_formatted("ERROR", "Invalid input. Please enter a number.")

# Select active account
def select_account(config):
    if not config["accounts"]:
        print_formatted("WARNING", "No accounts available. Please add an account first.")
        return
    print_formatted("INFO", "Select account for auto-rejoin:")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            config["active_account"] = config["accounts"][choice]
            save_config(config)
            print_formatted("SUCCESS", f"Active account set to {config['active_account']}.")
        else:
            print_formatted("ERROR", "Invalid choice.")
    except ValueError:
        print_formatted("ERROR", "Invalid input. Please enter a number.")

# Validate game ID
def validate_game_id(game_id):
    try:
        if not game_id.isdigit() or len(game_id) < 9 or len(game_id) > 15:
            print_formatted("ERROR", f"Invalid Game ID {game_id}. It should be a 9-15 digit number.")
            return False
        if len(game_id) > 12:
            print_formatted("WARNING", f"Game ID {game_id} is longer than typical (9-12 digits). It may be invalid.")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Error validating Game ID: {e}")
        return False

# Validate private server link
def validate_private_server(private_server):
    try:
        if "privateServerLinkCode" not in private_server or "roblox.com" not in private_server:
            print_formatted("ERROR", "Invalid private server link. Must contain 'privateServerLinkCode' and 'roblox.com'.")
            return False
        return True
    except Exception as e:
        print_formatted("ERROR", f"Error validating private server link: {e}")
        return False

# Set game ID or private server link
def set_game(config):
    print_formatted("INFO", "Enter Game ID (PlaceID) or Private Server Link (e.g., https://www.roblox.com/games/...?privateServerLinkCode=...):")
    game_input = input("> ").strip()
    if "privateServerLinkCode" in game_input:
        if validate_private_server(game_input):
            config["private_server"] = game_input
            config["game_id"] = ""
            print_formatted("INFO", "Private server link set. Note: May require authentication.")
        else:
            return
    else:
        if not validate_game_id(game_input):
            return
        config["game_id"] = game_input
        config["private_server"] = ""
    save_config(config)
    print_formatted("SUCCESS", "Game settings updated.")

# Set check delay
def set_check_delay(config):
    try:
        print_formatted("INFO", "Enter check delay (seconds, minimum 10):")
        delay = int(input("> ").strip())
        if delay < 10:
            print_formatted("ERROR", "Delay must be at least 10 seconds.")
            return
        config["check_delay"] = delay
        save_config(config)
        print_formatted("SUCCESS", f"Check delay set to {delay} seconds.")
    except ValueError:
        print_formatted("ERROR", "Invalid input. Please enter a number.")

# Check if ADB is connected
def check_adb():
    try:
        adb = Client(host="127.0.0.1", port=5037)
        devices = adb.devices()
        if not devices:
            print_formatted("ERROR", "No devices connected. Ensure ADB is enabled and device is connected.")
            return None
        print_formatted("SUCCESS", f"Connected to device: {devices[0].serial}")
        return devices[0]
    except Exception as e:
        print_formatted("ERROR", f"ADB connection error: {e}")
        return None

# Check if an executor GUI is running
def is_executor_running(device):
    if not device:
        return False
    try:
        executor_packages = ["com.codex", "com.arceusx", "com.delta"]
        for pkg in executor_packages:
            output = device.shell(f"ps | grep {pkg}")
            if output.strip():
                print_formatted("INFO", f"Executor detected: {pkg}")
                return True
            activity_output = device.shell(f"dumpsys activity | grep {pkg}")
            if activity_output.strip():
                print_formatted("INFO", f"Executor UI detected for {pkg}")
                return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking for executor: {e}")
        return False

# Check if the correct account is logged in
def is_account_logged_in(device, user_id):
    if not device:
        return False
    try:
        cmd = f"logcat -d | grep -i 'UserId.*{user_id}'"
        output = device.shell(cmd)
        if user_id in output:
            print_formatted("SUCCESS", f"Account {user_id} is logged in (detected in logs).")
            return True
        cmd = f"dumpsys activity | grep -i 'com.roblox.client.*{user_id}'"
        output = device.shell(cmd)
        if user_id in output:
            print_formatted("SUCCESS", f"Account {user_id} is logged in (detected in activity).")
            return True
        print_formatted("WARNING", f"Account {user_id} not detected as logged in.")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking account login: {e}")
        return False

# Improved check if Roblox is running
def is_roblox_running(device):
    if not device:
        return False
    try:
        ps_output = device.shell("ps | grep com.roblox.client")
        if "com.roblox.client" in ps_output:
            return True
        activity_output = device.shell("dumpsys activity | grep com.roblox.client")
        if "com.roblox.client" in activity_output:
            return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking if Roblox is running: {e}")
        return False

# Check if Roblox has joined the specified game
def is_game_joined(device, game_id, private_server):
    if not device:
        return False
    try:
        if private_server:
            link_code = private_server.split("privateServerLinkCode=")[-1].split("&")[0] if "privateServerLinkCode" in private_server else ""
            if link_code:
                cmd = f"logcat -d | grep -i '{link_code}'"
                output = device.shell(cmd)
                if output.strip():
                    print_formatted("SUCCESS", "Roblox has joined the private server.")
                    return True
        else:
            cmd = f"logcat -d | grep -i 'PlaceId.*{game_id}'"
            output = device.shell(cmd)
            if game_id in output:
                print_formatted("SUCCESS", f"Roblox has joined game with PlaceID {game_id}.")
                return True
            cmd = f"dumpsys activity | grep -i 'com.roblox.client.*{game_id}'"
            output = device.shell(cmd)
            if game_id in output:
                print_formatted("SUCCESS", f"Roblox has joined game with PlaceID {game_id} (detected in activity).")
                return True
        print_formatted("WARNING", "Roblox has not joined the specified game.")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking if game is joined: {e}")
        return False

# Check for errors in logs
def check_for_errors(device):
    if not device:
        return False
    try:
        cmd = "logcat -d | grep -iE 'kicked|disconnected|banned|error|freeze|crash|timeout|ANR'"
        output = device.shell(cmd)
        if output.strip():
            print_formatted("ERROR", f"Detected error in logs: {output.strip()}")
            return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking logs: {e}")
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
            print_formatted("WARNING", f"Invalid Game ID {game_id}. Defaulting to 15943173912.")
            config["game_id"] = "15943173912"
            config["private_server"] = ""
            save_config(config)
            game_id = "15943173912"
        url = f"roblox://placeID={game_id}"
    for attempt in range(retries):
        try:
            # Set landscape orientation
            device.shell("settings put system accelerometer_rotation 0")
            device.shell("input keyevent 19")  # Rotate to landscape
            time.sleep(2)
            # Try primary URL
            cmd = f"am start -a android.intent.action.VIEW -d '{url}' com.roblox.client"
            print_formatted("INFO", f"Attempt {attempt + 1}/{retries} - Executing ADB command: {cmd}")
            device.shell(cmd)
            time.sleep(15)
            if is_roblox_running(device):
                print_formatted("SUCCESS", f"Launched Roblox in landscape with {'private server' if private_server else f'PlaceID {game_id}'}.")
                return True
            # Fallback to robloxmobile://
            print_formatted("WARNING", f"Failed to launch with {url}. Trying robloxmobile://...")
            mobile_url = url.replace("roblox://", "robloxmobile://")
            cmd = f"am start -a android.intent.action.VIEW -d '{mobile_url}' com.roblox.client"
            print_formatted("INFO", f"Attempt {attempt + 1}/{retries} - Executing ADB command: {cmd}")
            device.shell(cmd)
            time.sleep(15)
            if is_roblox_running(device):
                print_formatted("SUCCESS", f"Launched Roblox in landscape with {'private server' if private_server else f'PlaceID {game_id}'} using robloxmobile://.")
                return True
            # Fallback to launching without URL
            print_formatted("WARNING", "Both URL schemes failed. Trying to launch Roblox app without URL...")
            cmd = "am start -n com.roblox.client/.ActivityLauncher"
            print_formatted("INFO", f"Attempt {attempt + 1}/{retries} - Executing ADB command: {cmd}")
            device.shell(cmd)
            time.sleep(15)
            if is_roblox_running(device):
                print_formatted("SUCCESS", "Launched Roblox app in landscape (no URL).")
                return True
        except Exception as e:
            print_formatted("ERROR", f"Error launching game on attempt {attempt + 1}: {e}")
        print_formatted("WARNING", f"Attempt {attempt + 1} failed. Retrying after delay...")
        time.sleep(5)
    print_formatted("ERROR", "Failed to launch Roblox with all methods after retries.")
    return False

# Close Roblox app (avoid logout)
def close_roblox(device, user_id):
    if not device:
        return False
    try:
        if is_executor_running(device) and not check_for_errors(device):
            print_formatted("INFO", "Executor GUI is active and no errors detected. Skipping Roblox closure.")
            return False
        if is_account_logged_in(device, user_id):
            print_formatted("INFO", "Correct account is logged in. Minimizing Roblox to preserve login.")
            device.shell("am start -n com.roblox.client/.ActivityLauncher")
            time.sleep(2)
            device.shell("input keyevent 4")  # Back key
            time.sleep(15)
        else:
            print_formatted("WARNING", "Account not logged in or incorrect. Force-stopping Roblox.")
            device.shell("am force-stop com.roblox.client")
            time.sleep(15)
        print_formatted("SUCCESS", "Closed Roblox app.")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Error closing Roblox: {e}")
        return False

# Check executor and Roblox status (Option 7)
def check_executor_and_roblox(config):
    device = check_adb()
    if not device:
        return
    print_formatted("INFO", "Checking executor and Roblox status...")
    if not is_roblox_running(device):
        print_formatted("ERROR", "Roblox is not running. Please start Roblox and join the game first.")
        return
    if not is_game_joined(device, config["game_id"], config["private_server"]):
        print_formatted("ERROR", "Roblox has not joined the specified game. Please join the game first.")
        return
    print_formatted("SUCCESS", "Roblox is running and has joined the specified game.")
    if is_executor_running(device):
        print_formatted("SUCCESS", "Executor is running.")
        if check_for_errors(device):
            print_formatted("ERROR", "Errors detected in logs. Restarting Roblox...")
            if config["active_account"]:
                close_roblox(device, config["active_account"])
                launch_game(config, config["game_id"], config["private_server"])
            else:
                print_formatted("ERROR", "No active account set. Cannot auto-rejoin.")
        else:
            print_formatted("INFO", "No errors detected. Roblox and executor are stable.")
    else:
        print_formatted("WARNING", "No executor detected.")
        if check_for_errors(device):
            print_formatted("ERROR", "Errors detected in logs. Restarting Roblox...")
            if config["active_account"]:
                close_roblox(device, config["active_account"])
                launch_game(config, config["game_id"], config["private_server"])
            else:
                print_formatted("ERROR", "No active account set. Cannot auto-rejoin.")
        else:
            print_formatted("INFO", "No errors detected. Roblox is stable.")

# Enhanced auto-rejoin loop
def auto_rejoin(config):
    if not config["active_account"]:
        print_formatted("ERROR", "No active account selected. Please select an account.")
        return
    if not config["game_id"] and not config["private_server"]:
        print_formatted("ERROR", "No game ID or private server set. Please set one.")
        return
    
    device = check_adb()
    if not device:
        print_formatted("ERROR", "Cannot start auto-rejoin due to ADB connection failure.")
        return
    
    print_formatted("INFO", f"Starting Koala Hub Auto-Rejoin for account {config['active_account']}...")
    while True:
        try:
            print_formatted("INFO", "Checking Roblox status...")
            if not is_roblox_running(device):
                print_formatted("WARNING", "Roblox not running. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                time.sleep(5)
                if not launch_game(config, config["game_id"], config["private_server"]):
                    print_formatted("WARNING", "Join attempt failed. Checking game ID validity...")
                    if config["game_id"] and not validate_game_id(config["game_id"]):
                        print_formatted("ERROR", f"Game ID {config['game_id']} is invalid. Enter a new Game ID (or press Enter for default 15943173912):")
                        new_id = input("> ").strip()
                        if new_id and validate_game_id(new_id):
                            config["game_id"] = new_id
                            config["private_server"] = ""
                            save_config(config)
                        else:
                            config["game_id"] = "15943173912"
                            save_config(config)
                        print_formatted("INFO", f"Updated Game ID to {config['game_id']}.")
                        launch_game(config, config["game_id"], config["private_server"])
            elif not is_game_joined(device, config["game_id"], config["private_server"]):
                print_formatted("WARNING", "Roblox not joined to specified game. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                time.sleep(5)
                if not launch_game(config, config["game_id"], config["private_server"]):
                    print_formatted("WARNING", "Rejoin failed. Checking game ID validity...")
                    if config["game_id"] and not validate_game_id(config["game_id"]):
                        print_formatted("ERROR", f"Game ID {config['game_id']} is invalid. Enter a new Game ID (or press Enter for default 15943173912):")
                        new_id = input("> ").strip()
                        if new_id and validate_game_id(new_id):
                            config["game_id"] = new_id
                            config["private_server"] = ""
                            save_config(config)
                        else:
                            config["game_id"] = "15943173912"
                            save_config(config)
                        print_formatted("INFO", f"Updated Game ID to {config['game_id']}.")
                        launch_game(config, config["game_id"], config["private_server"])
            elif check_for_errors(device):
                print_formatted("ERROR", "Errors detected in logs. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                time.sleep(5)
                launch_game(config, config["game_id"], config["private_server"])
            elif is_executor_running(device):
                print_formatted("SUCCESS", "Executor is running. Roblox remains active.")
            else:
                print_formatted("SUCCESS", "Roblox is running and joined to the game.")
            print_formatted("INFO", f"Next check in {config['check_delay']} seconds...")
            for _ in range(config["check_delay"]):
                time.sleep(1)
                print(f"\r{COLORS['CYAN']}Waiting... {config['check_delay'] - _ - 1} seconds remaining{COLORS['RESET']}", end="")
            print("\r" + " " * 40 + "\r", end="")
        except KeyboardInterrupt:
            print_formatted("INFO", "Auto-rejoin stopped by user.")
            close_roblox(device, config["active_account"])
            break
        except Exception as e:
            print_formatted("ERROR", f"Unexpected error in auto-rejoin loop: {e}")
            time.sleep(10)

# Main menu
def main():
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v2.3
====================================={COLORS['RESET']}
Created for the Koala Hub community.
""")
    
    config = load_config()
    
    while True:
        print(f"""
{COLORS['BOLD']}Koala Hub Auto-Rejoin Menu:{COLORS['RESET']}
{COLORS['CYAN']}Active Account:{COLORS['RESET']} {config['active_account'] or 'None'}
{COLORS['CYAN']}Game ID:{COLORS['RESET']} {config['game_id'] or 'None'}
{COLORS['CYAN']}Private Server:{COLORS['RESET']} {config['private_server'] or 'None'}
{COLORS['CYAN']}Check Delay:{COLORS['RESET']} {config['check_delay']} seconds
{COLORS['BOLD']}Options:{COLORS['RESET']}
  {COLORS['CYAN']}1:{COLORS['RESET']} Add Account
  {COLORS['CYAN']}2:{COLORS['RESET']} Delete Account
  {COLORS['CYAN']}3:{COLORS['RESET']} Select Account
  {COLORS['CYAN']}4:{COLORS['RESET']} Set GameID/PsLink
  {COLORS['CYAN']}5:{COLORS['RESET']} Set Check Delay
  {COLORS['CYAN']}6:{COLORS['RESET']} Start Auto-Rejoin
  {COLORS['CYAN']}7:{COLORS['RESET']} Check Executor & Roblox Status
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
            print_formatted("INFO", "Exiting Koala Hub Auto-Rejoin...")
            break
        else:
            print_formatted("ERROR", "Invalid choice. Please try again.")

if __name__ == "__main__":
    main()