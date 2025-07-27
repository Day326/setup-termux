import requests
import time
import os
import json
from datetime import datetime
from ppadb.client import Client
from prettytable import PrettyTable

# ANSI color codes for console UI
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

# Check if root is available
def is_root_available():
    try:
        import subprocess
        subprocess.run(["su", "-c", "echo test"], capture_output=True, text=True)
        return True
    except:
        return False

# Print formatted console message with table-like structure
def print_formatted(level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = {
        "INFO": COLORS["INFO"],
        "SUCCESS": COLORS["SUCCESS"],
        "WARNING": COLORS["WARNING"],
        "ERROR": COLORS["ERROR"]
    }.get(level, COLORS["RESET"])
    table = PrettyTable()
    table.field_names = ["Timestamp", "Level", "Message"]
    table.align = "l"
    table.add_row([timestamp, level, message])
    print(f"{color}{table}{COLORS['RESET']}")

# Load or initialize config
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        print_formatted("INFO", "Config file not found. Running setup wizard...")
        config = {
            "accounts": [],
            "game_id": "",
            "private_server": "",
            "check_delay": 30,
            "active_account": "",
            "check_method": "both"
        }
        setup_wizard(config)
        return config
    except Exception as e:
        print_formatted("ERROR", f"Error loading config: {e}")
        return {
            "accounts": [],
            "game_id": "",
            "private_server": "",
            "check_delay": 30,
            "active_account": "",
            "check_method": "both"
        }

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print_formatted("SUCCESS", f"Config saved to {CONFIG_FILE}")
    except Exception as e:
        print_formatted("ERROR", f"Error saving config: {e}")

# Setup wizard for first-time use
def setup_wizard(config):
    print_formatted("INFO", "Welcome to Koala Hub Auto-Rejoin Setup Wizard")
    print_formatted("INFO", "Enter Roblox Username or User ID:")
    account = input("> ").strip()
    if account:
        add_account(config, account)
        select_account(config, len(config["accounts"]) - 1)
    set_game(config)
    set_check_delay(config)
    print_formatted("INFO", "Setup complete. You can modify settings from the main menu.")

# Validate game ID via Roblox API
def validate_game_id_api(game_id):
    try:
        url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}"
        response = requests.get(url, timeout=10)
        print_formatted("INFO", f"API Response Status: {response.status_code} for Game ID {game_id}")
        if response.status_code == 200 and response.json().get("data"):
            print_formatted("SUCCESS", f"Game ID {game_id} is valid.")
            return True
        print_formatted("ERROR", f"Game ID {game_id} is invalid or not found. Response: {response.text[:100]}...")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error validating Game ID via API: {e}")
        return False

# Get User ID from username
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
            print_formatted("ERROR", f"No User ID found for username {username}")
            return None
        print_formatted("ERROR", f"Failed to get User ID. Status code: {response.status_code}")
        return None
    except Exception as e:
        print_formatted("ERROR", f"Error fetching User ID: {e}")
        return None

# Add account
def add_account(config, account=None):
    if not account:
        print_formatted("INFO", "Enter Roblox Username or User ID:")
        account = input("> ").strip()
    if not account:
        print_formatted("ERROR", "Account cannot be empty.")
        return
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        if user_id:
            account = user_id
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
def select_account(config, choice=None):
    if not config["accounts"]:
        print_formatted("WARNING", "No accounts available. Please add an account first.")
        return
    if choice is None:
        print_formatted("INFO", "Select account for auto-rejoin:")
        for i, account in enumerate(config["accounts"], 1):
            print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
        try:
            choice = int(input("> ").strip()) - 1
        except ValueError:
            print_formatted("ERROR", "Invalid input. Please enter a number.")
            return
    if 0 <= choice < len(config["accounts"]):
        config["active_account"] = config["accounts"][choice]
        save_config(config)
        print_formatted("SUCCESS", f"Active account set to {config['active_account']}.")
    else:
        print_formatted("ERROR", "Invalid choice.")

# Validate game ID
def validate_game_id(game_id):
    if not game_id.isdigit() or len(game_id) < 7 or len(game_id) > 18:
        print_formatted("ERROR", f"Invalid Game ID {game_id}. It should be a 7-18 digit number.")
        return False
    return validate_game_id_api(game_id)

# Validate private server link
def validate_private_server(private_server):
    try:
        if "privateServerLinkCode" in private_server and "roblox.com" in private_server:
            place_id = private_server.split("games/")[1].split("/")[0] if "games/" in private_server else ""
            if place_id and validate_game_id_api(place_id):
                return True, place_id
        elif "share?code=" in private_server and "roblox.com" in private_server:
            place_id = private_server.split("games/")[1].split("/")[0] if "games/" in private_server else ""
            if place_id and validate_game_id_api(place_id):
                print_formatted("WARNING", "Using share link as private server. Ensure it’s a valid server link.")
                return True, place_id
        print_formatted("ERROR", f"Invalid private server link: {private_server}. Must contain 'privateServerLinkCode' or be a valid share link with PlaceID.")
        return False, None
    except Exception as e:
        print_formatted("ERROR", f"Error validating private server link: {e}")
        return False, None

# Set game ID or private server link
def set_game(config):
    print_formatted("INFO", "Enter Game ID (PlaceID) or Private Server Link (e.g., https://www.roblox.com/games/...?privateServerLinkCode=...):")
    game_input = input("> ").strip()
    if "roblox.com" in game_input:
        is_valid, place_id = validate_private_server(game_input)
        if is_valid:
            config["private_server"] = game_input
            config["game_id"] = place_id
            print_formatted("INFO", f"Private server link set with PlaceID {place_id}.")
        else:
            return
    else:
        if validate_game_id(game_input):
            config["game_id"] = game_input
            config["private_server"] = ""
        else:
            return
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

# Set check method
def set_check_method(config):
    print_formatted("INFO", "Select check method for status checks:")
    print(f"{COLORS['CYAN']}1:{COLORS['RESET']} Executor UI only")
    print(f"{COLORS['CYAN']}2:{COLORS['RESET']} Roblox running only")
    print(f"{COLORS['CYAN']}3:{COLORS['RESET']} Both Executor UI and Roblox running")
    try:
        choice = input("> ").strip()
        methods = {"1": "executor", "2": "roblox", "3": "both"}
        if choice in methods:
            config["check_method"] = methods[choice]
            save_config(config)
            print_formatted("SUCCESS", f"Check method set to {config['check_method']}.")
        else:
            print_formatted("ERROR", "Invalid choice.")
    except Exception as e:
        print_formatted("ERROR", f"Error setting check method: {e}")

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

# Check if executor GUI is running
def is_executor_running(device):
    if not device:
        return False
    try:
        executor_packages = ["com.codex", "com.arceusx", "com.delta"]
        for pkg in executor_packages:
            output = device.shell(f"ps | grep {pkg}")
            if output.strip():
                activity_output = device.shell(f"dumpsys activity | grep {pkg}")
                if "mResumed=true" in activity_output:
                    print_formatted("SUCCESS", f"Executor UI active: {pkg}")
                    return True
                print_formatted("INFO", f"Executor process detected but UI not active: {pkg}")
                return False
        print_formatted("WARNING", "No executor detected.")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking for executor: {e}")
        return False

# Check if account is logged in
def is_account_logged_in(device, user_id):
    if not device:
        return False
    try:
        cmd = f"logcat -d | grep -i 'UserId.*{user_id}'"
        output = device.shell(cmd)
        if user_id in output:
            print_formatted("SUCCESS", f"Account {user_id} is logged in.")
            return True
        print_formatted("WARNING", f"Account {user_id} not detected as logged in.")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking account login: {e}")
        return False

# Check if Roblox is running
def is_roblox_running(device):
    if not device:
        return False
    try:
        output = device.shell("ps | grep com.roblox.client")
        if "com.roblox.client" in output:
            return True
        activity_output = device.shell("dumpsys activity | grep com.roblox.client")
        if "com.roblox.client" in activity_output and "mResumed=true" in activity_output:
            return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking if Roblox is running: {e}")
        return False

# Check if Roblox is in main menu
def is_roblox_in_main_menu(device):
    if not device:
        return False
    try:
        output = device.shell("dumpsys activity | grep com.roblox.client")
        if "HomeActivity" in output or "MainActivity" in output:
            print_formatted("WARNING", "Roblox is in the main menu.")
            return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking main menu status: {e}")
        return False

# Check if game is joined
def is_game_joined(device, game_id, private_server):
    if not device:
        return False
    try:
        if private_server:
            link_code = private_server.split("privateServerLinkCode=")[-1].split("&")[0] if "privateServerLinkCode=" in private_server else private_server.split("share?code=")[1].split("&")[0]
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
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking if game is joined: {e}")
        return False

# Check for freezes or errors
def check_for_freezes_or_errors(device):
    if not device:
        return False
    try:
        cmd = "logcat -d | grep -iE 'kicked|disconnected|banned|error|freeze|crash|timeout|ANR|server shutdown'"
        output = device.shell(cmd)
        if output.strip():
            print_formatted("ERROR", f"Detected issue in logs: {output.strip()}")
            return True
        cmd = "logcat -d | grep com.roblox.client | tail -n 10"
        output = device.shell(cmd)
        if not output.strip():
            print_formatted("ERROR", "No recent Roblox activity detected. Possible freeze.")
            return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Error checking logs: {e}")
        return False

# Launch Roblox game
def launch_game(config, game_id, private_server, retries=3):
    device = check_adb()
    if not device:
        return False
    if private_server:
        is_valid, place_id = validate_private_server(private_server)
        if not is_valid:
            return False
        url = private_server.replace("https://www.roblox.com", "roblox://") if "privateServerLinkCode" in private_server else f"roblox://placeID={place_id}&linkCode={private_server.split('share?code=')[1].split('&')[0]}"
        game_id = place_id
    else:
        if not validate_game_id(game_id):
            print_formatted("ERROR", f"Invalid Game ID {game_id}. Enter a new Game ID:")
            new_id = input("> ").strip()
            if new_id and validate_game_id(new_id):
                config["game_id"] = new_id
                config["private_server"] = ""
                save_config(config)
                game_id = new_id
            else:
                print_formatted("ERROR", "No valid Game ID provided. Launch aborted.")
                return False
        url = f"roblox://placeID={game_id}"
    for attempt in range(retries):
        try:
            if is_root_available():
                device.shell("su -c 'settings put system accelerometer_rotation 0'")
                device.shell("su -c 'input keyevent 19'")  # Rotate to landscape with root
            else:
                device.shell("settings put system accelerometer_rotation 0")
                device.shell("input keyevent 19")  # Non-root fallback
            cmd = f"am start -a android.intent.action.VIEW -d '{url}' -n com.roblox.client/.ActivityLauncher"
            print_formatted("INFO", f"Attempt {attempt + 1}/{retries} - Launching: {cmd}")
            device.shell(cmd)
            time.sleep(15)
            if is_roblox_running(device) and is_game_joined(device, game_id, private_server):
                print_formatted("SUCCESS", f"Launched Roblox with {'private server' if private_server else f'PlaceID {game_id}'}.")
                return True
        except Exception as e:
            print_formatted("ERROR", f"Error launching game on attempt {attempt + 1}: {e}")
        time.sleep(5)
    print_formatted("ERROR", "Failed to launch Roblox after retries.")
    return False

# Close Roblox app
def close_roblox(device, user_id):
    if not device:
        return False
    try:
        if is_executor_running(device) and not check_for_freezes_or_errors(device):
            print_formatted("INFO", "Executor is active and no issues detected. Skipping closure.")
            return False
        if is_root_available():
            if is_account_logged_in(device, user_id):
                print_formatted("INFO", "Minimizing Roblox to preserve login.")
                device.shell("su -c 'input keyevent 4'")  # Back key with root
                time.sleep(5)
            else:
                print_formatted("WARNING", "Account not logged in. Force-stopping Roblox.")
                device.shell("su -c 'am force-stop com.roblox.client'")
                time.sleep(5)
        else:
            if is_account_logged_in(device, user_id):
                print_formatted("INFO", "Minimizing Roblox to preserve login.")
                device.shell("input keyevent 4")  # Back key without root
                time.sleep(5)
            else:
                print_formatted("WARNING", "Account not logged in. Force-stopping Roblox.")
                device.shell("am force-stop com.roblox.client")
                time.sleep(5)
        print_formatted("SUCCESS", "Closed Roblox app.")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Error closing Roblox: {e}")
        return False

# Check executor and Roblox status
def check_executor_and_roblox(config):
    device = check_adb()
    if not device:
        return
    print_formatted("INFO", f"Checking status with method: {config['check_method']}...")
    if config["check_method"] in ["executor", "both"]:
        if is_executor_running(device):
            print_formatted("SUCCESS", "Executor UI is active.")
        else:
            print_formatted("WARNING", "No executor UI detected.")
    if config["check_method"] in ["roblox", "both"]:
        if not is_roblox_running(device):
            print_formatted("WARNING", "Roblox is not running.")
        elif is_roblox_in_main_menu(device):
            print_formatted("WARNING", "Roblox is in the main menu.")
        elif is_game_joined(device, config["game_id"], config["private_server"]):
            print_formatted("SUCCESS", "Roblox is in the specified game.")
        else:
            print_formatted("WARNING", "Roblox is running but not in the specified game.")
        if config["active_account"] and not is_account_logged_in(device, config["active_account"]):
            print_formatted("WARNING", f"Active account {config['active_account']} is not logged in.")
    if check_for_freezes_or_errors(device):
        print_formatted("ERROR", "Issues detected in logs or possible freeze.")
    else:
        print_formatted("INFO", "No issues detected.")
    print_formatted("INFO", "Check completed.")

# Auto-rejoin loop
def auto_rejoin(config):
    if not is_root_available():
        print_formatted("ERROR", "Auto-rejoin is only supported on rooted devices. Please root your device or emulator and try again.")
        return
    if not config["active_account"]:
        print_formatted("ERROR", "No active account selected. Please select an account.")
        return
    if not config["game_id"] and not config["private_server"]:
        print_formatted("ERROR", "No game ID or private server set. Please set one.")
        return
    device = check_adb()
    if not device:
        return
    print_formatted("INFO", f"Starting auto-rejoin for account {config['active_account']}...")
    while True:
        try:
            if not is_roblox_running(device):
                print_formatted("WARNING", "Roblox not running. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                launch_game(config, config["game_id"], config["private_server"])
            elif is_roblox_in_main_menu(device):
                print_formatted("WARNING", "Roblox in main menu. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                launch_game(config, config["game_id"], config["private_server"])
            elif not is_game_joined(device, config["game_id"], config["private_server"]):
                print_formatted("WARNING", "Roblox not in specified game. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                launch_game(config, config["game_id"], config["private_server"])
            elif check_for_freezes_or_errors(device):
                print_formatted("WARNING", "Issues detected. Attempting to rejoin...")
                close_roblox(device, config["active_account"])
                launch_game(config, config["game_id"], config["private_server"])
            else:
                print_formatted("SUCCESS", "Roblox is running and in the specified game.")
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
            print_formatted("ERROR", f"Unexpected error in auto-rejoin: {e}")
            time.sleep(10)

# Main menu
def main():
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v3.0
====================================={COLORS['RESET']}
Created for the Koala Hub community.
Supports cloud phones (e.g., UGPhone) and emulators with ADB.
Root required for auto-rejoin feature.
[SAFETY NOTE] This script is safe for emulators/cloud phones when used as intended. Avoid entering personal data and respect Roblox/UGPhone terms to avoid bans.
""")
    config = load_config()
    while True:
        table = PrettyTable()
        table.field_names = ["Setting", "Value"]
        table.align = "l"
        table.add_row(["Active Account", config["active_account"] or "None"])
        table.add_row(["Game ID", config["game_id"] or "None"])
        table.add_row(["Private Server", config["private_server"] or "None"])
        table.add_row(["Check Delay", f"{config['check_delay']} seconds"])
        table.add_row(["Check Method", config["check_method"]])
        print(f"\n{COLORS['BOLD']}Settings:{COLORS['RESET']}\n{table}")
        print(f"""
{COLORS['BOLD']}Menu:{COLORS['RESET']}
{COLORS['CYAN']}1:{COLORS['RESET']} Add Account
{COLORS['CYAN']}2:{COLORS['RESET']} Delete Account
{COLORS['CYAN']}3:{COLORS['RESET']} Select Account
{COLORS['CYAN']}4:{COLORS['RESET']} Set GameID/PsLink
{COLORS['CYAN']}5:{COLORS['RESET']} Set Check Delay
{COLORS['CYAN']}6:{COLORS['RESET']} Set Check Method
{COLORS['CYAN']}7:{COLORS['RESET']} Check Executor & Roblox Status
{COLORS['CYAN']}8:{COLORS['RESET']} Start Auto-Rejoin
{COLORS['CYAN']}9:{COLORS['RESET']} Exit
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
            check_executor_and_roblox(config)
        elif choice == "8":
            auto_rejoin(config)
        elif choice == "9":
            print_formatted("INFO", "Exiting Koala Hub Auto-Rejoin...")
            break
        else:
            print_formatted("ERROR", "Invalid choice. Please try again.")

if __name__ == "__main__":
    main()