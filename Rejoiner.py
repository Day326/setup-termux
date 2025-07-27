import requests
import time
import os
import json
import subprocess
from ppadb.client import Client

# Configuration file to store account and game data
CONFIG_FILE = "/sdcard/Download/roblox_config.json"

# Load or initialize config
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        print("Config file not found. Creating new config.")
        return {"accounts": [], "game_id": "", "private_server": "", "check_delay": 30, "active_account": ""}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {"accounts": [], "game_id": "", "private_server": "", "check_delay": 30, "active_account": ""}

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Config saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving config: {e}")

# Get User ID from username using Roblox API
def get_user_id(username):
    try:
        url = f"https://api.roblox.com/users/get-by-username?username={username}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_id = str(data.get("Id"))
            if user_id:
                print(f"Resolved username {username} to User ID {user_id}")
                return user_id
            else:
                print(f"No User ID found for username {username}")
                return None
        else:
            print(f"Failed to get User ID for {username}. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching User ID: {e}")
        return None

# Add account (username or user ID)
def add_account(config):
    print("Enter Roblox Username or User ID:")
    account = input("> ").strip()
    if not account:
        print("Account cannot be empty.")
        return
    # If it looks like a username (contains letters), convert to User ID
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        if user_id:
            account = user_id
            print(f"Converted username to User ID {user_id}.")
        else:
            print(f"Could not validate username {account}. Using as is.")
    if account not in config["accounts"]:
        config["accounts"].append(account)
        save_config(config)
        print(f"Account {account} added.")
    else:
        print("Account already exists.")

# Delete account
def delete_account(config):
    if not config["accounts"]:
        print("No accounts to delete.")
        return
    print("Select account to delete:")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{i}: {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            removed_account = config["accounts"].pop(choice)
            if config["active_account"] == removed_account:
                config["active_account"] = ""
            save_config(config)
            print(f"Account {removed_account} deleted.")
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input. Please enter a number.")

# Select active account for auto-rejoin
def select_account(config):
    if not config["accounts"]:
        print("No accounts available. Please add an account first.")
        return
    print("Select account for auto-rejoin:")
    for i, account in enumerate(config["accounts"], 1):
        print(f"{i}: {account}")
    try:
        choice = int(input("> ").strip()) - 1
        if 0 <= choice < len(config["accounts"]):
            config["active_account"] = config["accounts"][choice]
            save_config(config)
            print(f"Active account set to {config['active_account']}.")
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input. Please enter a number.")

# Set game ID or private server link
def set_game(config):
    print("Enter Game ID (PlaceID) or Private Server Link:")
    game_input = input("> ").strip()
    if "privateServerLinkCode" in game_input:
        config["private_server"] = game_input
        try:
            config["game_id"] = game_input.split('/')[4]  # Extract PlaceID from link
            print("Note: Private server links may require additional authentication.")
        except IndexError:
            print("Invalid private server link format. Please enter a valid link.")
            return
    else:
        config["game_id"] = game_input
        config["private_server"] = ""
    save_config(config)
    print("Game settings updated.")

# Set check delay
def set_check_delay(config):
    try:
        print("Enter check delay (seconds, minimum 10):")
        delay = int(input("> ").strip())
        if delay < 10:
            print("Delay must be at least 10 seconds.")
            return
        config["check_delay"] = delay
        save_config(config)
        print(f"Check delay set to {delay} seconds.")
    except ValueError:
        print("Invalid input. Please enter a number.")

# Check if ADB is set up and device is connected
def check_adb():
    try:
        adb = Client(host="127.0.0.1", port=5037)
        devices = adb.devices()
        if not devices:
            print("No devices connected. Ensure ADB is enabled and device is connected.")
            return None
        print(f"Connected to device: {devices[0].serial}")
        return devices[0]
    except Exception as e:
        print(f"ADB connection error: {e}")
        return None

# Launch Roblox game via ADB
def launch_game(game_id, private_server):
    device = check_adb()
    if not device:
        return False
    try:
        url = f"roblox://placeID={game_id}" if not private_server else private_server
        cmd = f"am start -a android.intent.action.VIEW -d '{url}' com.roblox.client"
        print(f"Executing ADB command: {cmd}")
        device.shell(cmd)
        time.sleep(5)  # Wait for app to launch
        print(f"Launched Roblox game with PlaceID {game_id}.")
        return True
    except Exception as e:
        print(f"Error launching game: {e}")
        return False

# Check if Roblox is running
def is_roblox_running(device):
    if not device:
        return False
    try:
        output = device.shell("ps | grep com.roblox.client")
        return "com.roblox.client" in output
    except Exception as e:
        print(f"Error checking if Roblox is running: {e}")
        return False

# Check for errors in logs (e.g., kick, ban, disconnect)
def check_for_errors(device):
    if not device:
        return False
    try:
        cmd = "logcat -d | grep -iE 'kicked|disconnected|banned|error|freeze|crash|timeout'"
        output = device.shell(cmd)
        if output.strip():
            print(f"Detected error in logs: {output.strip()}")
            return True
        return False
    except Exception as e:
        print(f"Error checking logs: {e}")
        return False

# Close Roblox app
def close_roblox(device):
    if not device:
        return False
    try:
        device.shell("am force-stop com.roblox.client")
        print("Closed Roblox app.")
        time.sleep(5)  # Ensure app is fully closed
        return True
    except Exception as e:
        print(f"Error closing Roblox: {e}")
        return False

# Main auto-rejoin loop with error detection
def auto_rejoin(config):
    if not config["active_account"]:
        print("No active account selected. Please select an account.")
        return
    game_id = config["game_id"]
    check_delay = config["check_delay"]
    
    if not game_id:
        print("No game ID set. Please set a game ID or private server link.")
        return
    
    device = check_adb()
    if not device:
        print("Cannot start auto-rejoin due to ADB connection failure.")
        return
    
    print(f"Starting Koala Hub Auto-Rejoin for account {config['active_account']} and game ID {game_id}...")
    while True:
        if not is_roblox_running(device) or check_for_errors(device):
            print("Error detected or Roblox not running. Closing and rejoining...")
            close_roblox(device)
            time.sleep(5)  # Wait before rejoining
            launch_game(game_id, config["private_server"])
        else:
            print("Roblox is running normally.")
        time.sleep(check_delay)

# Main menu
def main():
    print("""
    Welcome to Koala Hub Auto-Rejoin!
    Created for the Koala Hub community.
    """)
    
    config = load_config()
    
    while True:
        print("\nKoala Hub Auto-Rejoin Menu:")
        print(f"Active Account: {config['active_account'] or 'None'}")
        print(f"Game ID: {config['game_id'] or 'None'}")
        print(f"Check Delay: {config['check_delay']} seconds")
        print("1: Add Account")
        print("2: Delete Account")
        print("3: Select Account")
        print("4: Set GameID/PsLink")
        print("5: Set Check Delay")
        print("6: Start Auto-Rejoin")
        print("7: Exit")
        
        choice = input("> ").strip()
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
            print("Exiting Koala Hub Auto-Rejoin...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()