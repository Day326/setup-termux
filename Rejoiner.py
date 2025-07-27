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
        print_status("INFO", "Config file not found. Creating new config.", "Init")
        return {"accounts": [], "game_id": "", "private_server": "", "check_delay": 30, "active_account": "", "check_method": 3}
    except Exception as e:
        print_status("ERROR", f"Error loading config: {e}", "Failed")
        return {"accounts": [], "game_id": "", "private_server": "", "check_delay": 30, "active_account": "", "check_method": 3}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print_status("SUCCESS", "Config saved.", "Saved")
    except Exception as e:
        print_status("ERROR", f"Error saving config: {e}", "Failed")

# Get User ID from username using Roblox API
def get_user_id(username):
    try:
        url = f"https://api.roblox.com/users/get-by-username?username={username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_id = str(data.get("Id"))
            if user_id:
                print_status("SUCCESS", f"Resolved username {username} to User ID {user_id}", "Resolved")
                return user_id
            print_status("ERROR", f"No User ID found for username {username}", "Failed")
            return None
        print_status("ERROR", f"Failed to get User ID for {username}. Status code: {response.status_code}", "Failed")
        return None
    except Exception as e:
        print_status("ERROR", f"Error fetching User ID: {e}", "Failed")
        return None

# Add account
def add_account(config):
    print_status("INFO", "Enter Roblox Username or User ID:", "Input")
    account = input("> ").strip()
    if not account:
        print_status("ERROR", "Account cannot be empty.", "Failed")
        return
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        if user_id:
            account = user_id
            print_status("SUCCESS", f"Converted username to User ID {user_id}", "Converted")
        else:
            print_status("WARNING", f"Could not validate username {account}. Using as is.", "Warning")
    if account not in config["accounts"]:
        config["accounts"].append(account)
        save_config(config)
        print_status("SUCCESS", f"Account {account} added.", "Added")
    else:
        print_status("WARNING", "Account already exists.", "Warning")

# Delete account
def delete_account(config):
    if not config["accounts"]:
        print_status("WARNING", "No accounts to delete.", "Warning")
        return
    print_status("INFO", "Select account to delete:", "Input")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            removed_account = config["accounts"].pop(choice)
            if config["active_account"] == removed_account:
                config["active_account"] = ""
            save_config(config)
            print_status("SUCCESS", f"Account {removed_account} deleted.", "Deleted")
        else:
            print_status("ERROR", "Invalid choice.", "Failed")
    except ValueError:
        print_status("ERROR", "Invalid input. Please enter a number.", "Failed")

# Select active account
def select_account(config):
    if not config["accounts"]:
        print_status("WARNING", "No accounts available. Please add an account first.", "Warning")
        return
    print_status("INFO", "Select account for auto-rejoin:", "Input")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{COLORS['CYAN']}{i}:{COLORS['RESET']} {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            config["active_account"] = config["accounts"][choice]
            save_config(config)
            print_status("SUCCESS", f"Active account set to {config['active_account']}", "Set")
        else:
            print_status("ERROR", "Invalid choice.", "Failed")
    except ValueError:
        print_status("ERROR", "Invalid input. Please enter a number.", "Failed")

# Validate game ID
def validate_game_id(game_id):
    try:
        if not game_id.isdigit() or len(game_id) < 9 or len(game_id) > 15:
            print_status("ERROR", f"Invalid Game ID {game_id}. It should be a 9-15 digit number.", "Failed")
            return False
        if len(game_id) > 12:
            print_status("WARNING", f"Game ID {game_id} is longer than typical (9-12 digits). It may be invalid.", "Warning")
        return True
    except Exception as e:
        print_status("ERROR", f"Error validating Game ID: {e}", "Failed")
        return False

# Validate private server link
def validate_private_server(private_server):
    try:
        if "privateServerLinkCode" not in private_server or "roblox.com" not in private_server:
            print_status("ERROR", "Invalid private server link. Must contain 'privateServerLinkCode' and 'roblox.com'.", "Failed")
            return False
        return True
    except Exception as e:
        print_status("ERROR", f"Error validating private server link: {e}", "Failed")
        return False

# Set game ID or private server link
def set_game(config):
    print_status("INFO", "Enter Game ID (PlaceID) or Private Server Link (e.g., https://www.roblox.com/games/...?privateServerLinkCode=...):", "Input")
    game_input = input("> ").strip()
    if "privateServerLinkCode" in game_input:
        if validate_private_server(game_input):
            config["private_server"] = game_input
            config["game_id"] = ""
            print_status("INFO", "Private server link set. Note: May require authentication.", "Set")
        else:
            return
    else:
        if not validate_game_id(game_input):
            return
        config["game_id"] = game_input
        config["private_server"] = ""
    save_config(config)
    print_status("SUCCESS", "Game settings updated.", "Updated")

# Set check delay
def set_check_delay(config):
    try:
        print_status("INFO", "Enter check delay (seconds, minimum 10):", "Input")
        delay = int(input("> ").strip())
        if delay < 10:
            print_status("ERROR", "Delay must be at least 10 seconds.", "Failed")
            return
        config["check_delay"] = delay
        save_config(config)
        print_status("SUCCESS", f"Check delay set to {delay} seconds.", "Set")
    except ValueError:
        print_status("ERROR", "Invalid input. Please enter a number.", "Failed")

# Check if ADB is connected
def check_adb():
    try:
        adb = Client(host="127.0.0.1", port=5037)
        devices = adb.devices()
        if not devices:
            print_status("ERROR", "No devices connected. Ensure ADB is enabled and device is connected.", "Failed")
            return None
        print_status("SUCCESS", f"Connected to device: {devices[0].serial}", "Connected")
        return devices[0]
    except Exception as e:
        print_status("ERROR", f"ADB connection error: {e}", "Failed")
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
                print_status("INFO", f"Executor detected: {pkg}", "Detected")
                return True
            activity_output = device.shell(f"dumpsys activity | grep {pkg}")
            if activity_output.strip():
                print_status("INFO", f"Executor UI detected for {pkg}", "Detected")
                return True
        print_status("WARNING", "No executor detected.", "Warning")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking for executor: {e}", "Failed")
        return False

# Check if the correct account is logged in
def is_account_logged_in(device, user_id):
    if not device:
        return False
    try:
        cmd = f"logcat -d | grep -i 'UserId.*{user_id}'"
        output = device.shell(cmd)
        if user_id in output:
            print_status("SUCCESS", f"Account {user_id} is logged in (detected in logs).", "LoggedIn")
            return True
        cmd = f"dumpsys activity | grep -i 'com.roblox.client.*{user_id}'"
        output = device.shell(cmd)
        if user_id in output:
            print_status("SUCCESS", f"Account {user_id} is logged in (detected in activity).", "LoggedIn")
            return True
        print_status("WARNING", f"Account {user_id} not detected as logged in.", "Warning")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking account login: {e}", "Failed")
        return False

# Improved check if Roblox is running
def is_roblox_running(device):
    if not device:
        return False
    try:
        ps_output = device.shell("ps | grep com.roblox.client")
        if "com.roblox.client" in ps_output:
            print_status("SUCCESS", "Roblox is running.", "Running")
            return True
        activity_output = device.shell("dumpsys activity | grep com.roblox.client")
        if "com.roblox.client" in activity_output:
            print_status("SUCCESS", "Roblox is running.", "Running")
            return True
        print_status("WARNING", "Roblox not running.", "Warning")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking if Roblox is running: {e}", "Failed")
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
                    print_status("SUCCESS", "Roblox has joined the private server.", "Joined")
                    return True
        else:
            cmd = f"logcat -d | grep -i 'PlaceId.*{game_id}'"
            output = device.shell(cmd)
            if game_id in output:
                print_status("SUCCESS", f"Roblox has joined game with PlaceID {game_id}.", "Joined")
                return True
            cmd = f"dumpsys activity | grep -i 'com.roblox.client.*{game_id}'"
            output = device.shell(cmd)
            if game_id in output:
                print_status("SUCCESS", f"Roblox has joined game with PlaceID {game_id} (detected in activity).", "Joined")
                return True
        print_status("WARNING", "Roblox has not joined the specified game.", "Warning")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking if game is joined: {e}", "Failed")
        return False

# Check for errors in logs
def check_for_errors(device):
    if not device:
        return False
    try:
        cmd = "logcat -d | grep -iE 'kicked|disconnected|banned|error|freeze|crash|timeout|ANR'"
        output = device.shell(cmd)
        if output.strip():
            print_status("ERROR", f"Detected error in logs: {output.strip()}", "Error")
            return True
        print_status("INFO", "No errors detected in logs.", "Checked")
        return False
    except Exception as e:
        print_status("ERROR", f"Error checking logs: {e}", "Failed")
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
            print_status("ERROR", f"Invalid Game ID {game_id}. Please enter a valid 9-15 digit Game ID:", "Failed")
            new_id = input("> ").strip()
            if new_id and validate_game_id(new_id):
                config["game_id"] = new_id
                config["private_server"] = ""
                save_config(config)
                game_id = new_id
            else:
                print_status("ERROR", "No valid Game ID provided. Launch aborted.", "Failed")
                return False
        url = f"roblox://placeID={game_id}"
    for attempt in range(retries):
        try:
            # Force landscape orientation
            device.shell("settings put system accelerometer_rotation 0")
            device.shell("input keyevent 19")  # Rotate to landscape
            device.shell("am start --activity-force-rotate -a android.intent.action.RUN -n com.roblox.client/.ActivityLauncher")
            time.sleep(2)
            device.shell("input keyevent 19")  # Double-check rotation
            
            # Try deep link with specific action
            cmd = f"am start -a android.intent.action.RUN -d '{url}' -n com.roblox.client/.ActivityLauncher"
            print_status("INFO", f"Attempt {attempt + 1}/{retries} - Executing ADB command: {cmd}", "Launching")
            device.shell(cmd)
            time.sleep(15)
            if is_roblox_running(device):
                print_status("SUCCESS", f"Launched Roblox in landscape with {'private server' if private_server else f'PlaceID {game_id}'}", "Running")
                return True
            
            # Fallback to app launch without URL if deep link fails
            print_status("WARNING", f"Deep link failed. Launching Roblox app directly...", "Warning")
            cmd = "am start -a android.intent.action.RUN -n com.roblox.client/.ActivityLauncher"
            print_status("INFO", f"Attempt {attempt + 1}/{retries} - Executing ADB command: {cmd}", "Launching")
            device.shell(cmd)
            time.sleep(15)
            if is_roblox_running(device):
                print_status("SUCCESS", f"Launched Roblox in landscape (no URL).", "Running")
                return True
        except Exception as e:
            print_status("ERROR", f"Error launching game on attempt {attempt + 1}: {e}", "Failed")
        print_status("WARNING", f"Attempt {attempt + 1} failed. Retrying after delay...", "Retrying")
        time.sleep(5)
    print_status("ERROR", "Failed to launch Roblox with all methods after retries.", "Failed")
    return False

# Close Roblox app (avoid logout)
def close_roblox(device, user_id):
    if not device:
        return False
    try:
        if is_executor_running(device) and not check_for_errors(device):
            print_status("INFO", "Executor GUI is active and no errors detected. Skipping Roblox closure.", "Skipped")
            return False
        if is_account_logged_in(device, user_id):
            print_status("INFO", "Correct account is logged in. Minimizing Roblox to preserve login.", "Minimizing")
            device.shell("am start -n com.roblox.client/.ActivityLauncher")
            time.sleep(2)
            device.shell("input keyevent 4")  # Back key
            time.sleep(15)
        else:
            print_status("WARNING", "Account not logged in or incorrect. Force-stopping Roblox.", "Warning")
            device.shell("am force-stop com.roblox.client")
            time.sleep(15)
        print_status("SUCCESS", "Closed Roblox app.", "Closed")
        return True
    except Exception as e:
        print_status("ERROR", f"Error closing Roblox: {e}", "Failed")
        return False

# Check executor and Roblox status (Option 7) - Manual check with method selection
def check_executor_and_roblox(config):
    device = check_adb()
    if not device:
        return
    print_status("INFO", "Performing manual check of Executor and Roblox status. Select method:", "Choosing")
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
            print_status("SUCCESS", f"Saved check method {choice}", "Saved")
        else:
            print_status("ERROR", "Invalid choice.", "Failed")
            return
        if choice == 1:
            print_status("INFO", "Checking Executor UI...", "Checking")
            if is_executor_running(device):
                print_status("SUCCESS", "Executor is running.", "Running")
            else:
                print_status("WARNING", "No executor detected.", "Warning")
        elif choice == 2:
            print_status("INFO", "Checking Roblox Running...", "Checking")
            if is_roblox_running(device):
                print_status("SUCCESS", "Roblox is running.", "Running")
            else:
                print_status("WARNING", "Roblox not running.", "Warning")
        elif choice == 3:
            print_status("INFO", "Checking Both...", "Checking")
            if is_roblox_running(device):
                print_status("SUCCESS", "Roblox is running.", "Running")
            else:
                print_status("WARNING", "Roblox not running.", "Warning")
            if is_executor_running(device):
                print_status("SUCCESS", "Executor is running.", "Running")
            else:
                print_status("WARNING", "No executor detected.", "Warning")
        print_status("INFO", "Check completed.", "Done")
    except ValueError:
        print_status("ERROR", "Invalid input. Please enter a number.", "Failed")

# Enhanced auto-rejoin loop with check method
def auto_rejoin(config):
    if not config["active_account"]:
        print_status("ERROR", "No active account selected. Please select an account.", "Stopped")
        return
    if not config["game_id"] and not config["private_server"]:
        print_status("ERROR", "No game ID or private server set. Please set one.", "Stopped")
        return
    
    device = check_adb()
    if not device:
        print_status("ERROR", "Cannot start auto-rejoin due to ADB connection failure.", "Stopped")
        return
    
    print_status("INFO", f"Starting Koala Hub Auto-Rejoin for account {config['active_account']}...", "Starting")
    while True:
        try:
            print_status("INFO", "Checking Roblox status...", "Checking")
            if not is_roblox_running(device):
                print_status("WARNING", "Roblox not running. Attempting to rejoin...", "Rejoining")
                close_roblox(device, config["active_account"])
                time.sleep(5)
                if not launch_game(config, config["game_id"], config["private_server"]):
                    print_status("WARNING", "Join attempt failed. Checking game ID validity...", "Warning")
                    if config["game_id"] and not validate_game_id(config["game_id"]):
                        print_status("ERROR", f"Game ID {config['game_id']} is invalid. Enter a new Game ID:", "Failed")
                        new_id = input("> ").strip()
                        if new_id and validate_game_id(new_id):
                            config["game_id"] = new_id
                            config["private_server"] = ""
                            save_config(config)
                        else:
                            print_status("ERROR", "No valid Game ID provided. Auto-rejoin paused.", "Stopped")
                            break
                        print_status("INFO", f"Updated Game ID to {config['game_id']}.", "Updated")
                        launch_game(config, config["game_id"], config["private_server"])
            elif not is_game_joined(device, config["game_id"], config["private_server"]):
                print_status("WARNING", "Roblox not joined to specified game. Attempting to rejoin...", "Rejoining")
                close_roblox(device, config["active_account"])
                time.sleep(5)
                if not launch_game(config, config["game_id"], config["private_server"]):
                    print_status("WARNING", "Rejoin failed. Checking game ID validity...", "Warning")
                    if config["game_id"] and not validate_game_id(config["game_id"]):
                        print_status("ERROR", f"Game ID {config['game_id']} is invalid. Enter a new Game ID:", "Failed")
                        new_id = input("> ").strip()
                        if new_id and validate_game_id(new_id):
                            config["game_id"] = new_id
                            config["private_server"] = ""
                            save_config(config)
                        else:
                            print_status("ERROR", "No valid Game ID provided. Auto-rejoin paused.", "Stopped")
                            break
                        print_status("INFO", f"Updated Game ID to {config['game_id']}.", "Updated")
                        launch_game(config, config["game_id"], config["private_server"])
            elif check_for_errors(device):
                print_status("ERROR", "Errors detected in logs. Attempting to rejoin...", "Rejoining")
                close_roblox(device, config["active_account"])
                time.sleep(5)
                launch_game(config, config["game_id"], config["private_server"])
            # Apply saved check method
            elif config["check_method"] == 1:
                if is_executor_running(device):
                    print_status("SUCCESS", "Executor is running. Roblox remains active.", "Running")
                else:
                    print_status("WARNING", "No executor detected. Checking again...", "Warning")
            elif config["check_method"] == 2:
                if is_roblox_running(device) and is_game_joined(device, config["game_id"], config["private_server"]):
                    print_status("SUCCESS", "Roblox is running and joined to the game.", "Running")
                else:
                    print_status("WARNING", "Roblox not running or not joined. Rejoining...", "Rejoining")
                    close_roblox(device, config["active_account"])
                    time.sleep(5)
                    launch_game(config, config["game_id"], config["private_server"])
            elif config["check_method"] == 3:
                if is_roblox_running(device) and is_game_joined(device, config["game_id"], config["private_server"]) and is_executor_running(device):
                    print_status("SUCCESS", "Roblox and executor active.", "Running")
                else:
                    print_status("WARNING", "Issue detected. Rejoining...", "Rejoining")
                    close_roblox(device, config["active_account"])
                    time.sleep(5)
                    launch_game(config, config["game_id"], config["private_server"])
            print_status("INFO", f"Next check in {config['check_delay']} seconds...", "Waiting")
            for _ in range(config["check_delay"]):
                time.sleep(1)
                print(f"\r{COLORS['CYAN']}Waiting... {config['check_delay'] - _ - 1} seconds remaining{COLORS['RESET']}", end="")
            print("\r" + " " * 40 + "\r", end="")
        except KeyboardInterrupt:
            print_status("INFO", "Auto-rejoin stopped by user.", "Stopped")
            close_roblox(device, config["active_account"])
            break
        except Exception as e:
            print_status("ERROR", f"Unexpected error in auto-rejoin loop: {e}", "Error")
            time.sleep(10)

# Main menu
def main():
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v3.3
====================================={COLORS['RESET']}
Created for the Koala Hub community.
Note: For cloud phones (e.g., UGPhone), enable floating windows manually if supported.
""")
    
    config = load_config()
    
    while True:
        print(f"""
{COLORS['BOLD']}Koala Hub Auto-Rejoin Menu:{COLORS['RESET']}
{COLORS['CYAN']}Active Account:{COLORS['RESET']} {config['active_account'] or 'None'}
{COLORS['CYAN']}Game ID:{COLORS['RESET']} {config['game_id'] or 'None'}
{COLORS['CYAN']}Private Server:{COLORS['RESET']} {config['private_server'] or 'None'}
{COLORS['CYAN']}Check Delay:{COLORS['RESET']} {config['check_delay']} seconds
{COLORS['CYAN']}Check Method:{COLORS['RESET']} {config['check_method'] or '3 (Both)'}
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
            print_status("INFO", "Exiting Koala Hub Auto-Rejoin...", "Exiting")
            break
        else:
            print_status("ERROR", "Invalid choice. Please try again.", "Failed")

if __name__ == "__main__":
    main()