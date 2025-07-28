import requests
import time
import os
import json
import subprocess
from datetime import datetime
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

def run_shell_command(command):
    try:
        if is_root_available():
            result = subprocess.run(f"su -c '{command}'", shell=True, 
                                 capture_output=True, text=True)
        else:
            result = subprocess.run(command, shell=True,
                                 capture_output=True, text=True)
        return result.stdout.strip()
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
        "launch_delay": 90,
        "retry_delay": 15,
        "force_kill_delay": 7,
        "minimize_crashes": True,
        "cooldown_period": 120
    }
    try:
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f)
            print_formatted("INFO", "Creating new config file...")
            return default_config
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return {**default_config, **config}
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
# ROBLOX CONTROL FUNCTIONS
# ======================
def verify_roblox_installation():
    try:
        output = run_shell_command(f"pm list packages {ROBLOX_PACKAGE}")
        return ROBLOX_PACKAGE in output
    except Exception as e:
        print_formatted("ERROR", f"Installation check error: {e}")
        return False

def is_roblox_running():
    try:
        output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE}")
        return bool(output.strip())
    except Exception as e:
        print_formatted("ERROR", f"Process check error: {e}")
        return False

def get_current_activity():
    try:
        output = run_shell_command("dumpsys window windows | grep mCurrentFocus")
        return output.strip()
    except Exception as e:
        print_formatted("ERROR", f"Activity check error: {e}")
        return ""

def is_in_game_activity(activity):
    return "GameActivity" in activity or "ExperienceActivity" in activity

def is_in_main_menu(activity):
    return "MainActivity" in activity or "HomeActivity" in activity

def is_in_error_state(activity):
    error_states = ["ErrorActivity", "CrashActivity", "NotResponding", "ANR"]
    return any(state in activity for state in error_states)

def detect_main_activity():
    activities = [
        "com.roblox.client.StartupActivity",
        "com.roblox.client.MainActivity",
        "com.roblox.client.HomeActivity"
    ]
    for activity in activities:
        try:
            result = run_shell_command(f"am start -n {ROBLOX_PACKAGE}/{activity}")
            if "Error" not in result:
                time.sleep(2)
                if is_roblox_running():
                    return activity
        except:
            continue
    return activities[0]

def close_roblox(config=None):
    try:
        is_rooted = is_root_available()
        print_formatted("INFO", "Closing Roblox...")
        
        run_shell_command("input keyevent HOME")
        time.sleep(1)
        run_shell_command(f"am force-stop {ROBLOX_PACKAGE}")
        time.sleep(config.get("force_kill_delay", 7) if config else 7)
        
        if is_roblox_running():
            print_formatted("WARNING", "Roblox still running, using advanced kill methods...")
            run_shell_command(f"am kill {ROBLOX_PACKAGE}")
            run_shell_command(f"pkill -f {ROBLOX_PACKAGE}")
            
            if is_rooted:
                run_shell_command("am force-stop com.roblox.client")
                run_shell_command("pkill -9 -f com.roblox.client")
            
            run_shell_command(f"pm clear {ROBLOX_PACKAGE}")
            time.sleep(5)
        
        if is_roblox_running():
            print_formatted("ERROR", "Failed to fully close Roblox")
            return False
            
        return True
    except Exception as e:
        print_formatted("ERROR", f"Failed to close Roblox: {e}")
        return False

def prepare_roblox(config):
    try:
        print_formatted("INFO", "Preparing Roblox for launch...")
        if not close_roblox(config):
            return False
            
        run_shell_command(f"pm clear {ROBLOX_PACKAGE}")
        time.sleep(3)
        return True
    except Exception as e:
        print_formatted("ERROR", f"Preparation error: {e}")
        return False

# ======================
# GAME LAUNCH FUNCTIONS
# ======================
def is_game_joined(game_id, private_server):
    try:
        activity = get_current_activity()
        if ROBLOX_PACKAGE in activity and is_in_game_activity(activity):
            print_formatted("INFO", "Game join confirmed via activity")
            return True
            
        run_shell_command("logcat -c")
        time.sleep(1)
        
        patterns = [f"place[._]?id.*{game_id}", f"game[._]?id.*{game_id}"]
        if private_server:
            code = private_server.split("privateServerLinkCode=")[-1].split("&")[0] if "privateServerLinkCode=" in private_server else private_server.split("share?code=")[-1].split("&")[0]
            patterns.append(f"linkCode={code}")
        
        logs = run_shell_command(f"logcat -d -t 200 | grep -iE '{'|'.join(patterns)}'")
        if logs.strip():
            print_formatted("INFO", "Game join confirmed via logs")
            return True

        if is_in_error_state(activity):
            print_formatted("ERROR", "Roblox crashed/frozen")
            return False
            
        return False
    except Exception as e:
        print_formatted("ERROR", f"Game detection error: {e}")
        return False

def launch_game(config):
    try:
        if not prepare_roblox(config):
            return False
            
        main_activity = detect_main_activity()
        
        print_formatted("INFO", "Launching Roblox...")
        run_shell_command(f"am start -n {ROBLOX_PACKAGE}/{main_activity}")
        time.sleep(10)
        
        run_shell_command("input keyevent BACK")
        time.sleep(2)
        
        if config["private_server"]:
            launch_url = config["private_server"]
            print_formatted("INFO", f"Joining private server: {launch_url}")
        else:
            launch_url = f"roblox://placeID={config['game_id']}"
            print_formatted("INFO", f"Joining game ID: {config['game_id']}")
        
        run_shell_command(f"am start -a android.intent.action.VIEW -d '{launch_url}'")
        
        loaded = False
        for i in range(config['launch_delay'] // 5):
            time.sleep(5)
            
            activity = get_current_activity()
            if is_in_error_state(activity):
                print_formatted("ERROR", "Detected crash/error activity")
                return False
                
            if is_game_joined(config["game_id"], config["private_server"]):
                print_formatted("SUCCESS", "Successfully joined game")
                loaded = True
                break
                
            if not is_roblox_running():
                print_formatted("ERROR", "Roblox process stopped")
                return False
                
        return loaded
        
    except Exception as e:
        print_formatted("ERROR", f"Launch error: {e}")
        return False

# ======================
# GAME VALIDATION
# ======================
def validate_game_id(game_id, config):
    if not game_id.isdigit() or len(game_id) < 6:
        print_formatted("ERROR", "Invalid Game ID format")
        return False
        
    if not config.get("game_validation", True):
        return True
        
    try:
        url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data and data[0].get("placeId"):
                print_formatted("SUCCESS", f"Valid game: {data[0].get('name', 'Unknown')}")
                return True
        return True
    except:
        return True

def validate_private_server(link):
    try:
        if not any(x in link for x in ["privateServerLinkCode=", "share?code="]):
            print_formatted("ERROR", "Link must contain private server code")
            return False
            
        if "games/" in link:
            place_id = link.split("/games/")[1].split("/")[0]
        elif "placeId=" in link:
            place_id = link.split("placeId=")[1].split("&")[0]
        else:
            print_formatted("ERROR", "Couldn't extract game ID from link")
            return False
            
        if not place_id.isdigit():
            print_formatted("ERROR", "Invalid game ID in link")
            return False
            
        return True
    except Exception as e:
        print_formatted("ERROR", f"Link validation error: {e}")
        return False

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
        return None
    except:
        return None

def add_account(config):
    print_formatted("INFO", "Enter Roblox username or ID:")
    account = input("> ").strip()
    if not account:
        print_formatted("ERROR", "Account cannot be empty")
        return
        
    if any(c.isalpha() for c in account):
        user_id = get_user_id(account)
        account = user_id if user_id else account
        
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
    print_formatted("INFO", "Enter Game ID:")
    game_id = input("> ").strip()
    
    if game_id.lower() == 'delete':
        delete_game_settings(config)
        return
        
    if not validate_game_id(game_id, config):
        return
        
    config["game_id"] = game_id
    
    print_formatted("INFO", "Enter Private Server Link (leave empty if none):")
    ps_link = input("> ").strip()
    
    if ps_link:
        if validate_private_server(ps_link):
            config["private_server"] = ps_link
        else:
            config["private_server"] = ""
            print_formatted("ERROR", "Invalid private server link - using game ID only")
    else:
        config["private_server"] = ""
    
    save_config(config)
    print_formatted("SUCCESS", "Game settings updated")

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

def set_launch_delay(config):
    try:
        print_formatted("INFO", "Enter launch delay (seconds, min 10, default 90):")
        delay = int(input("> ").strip())
        if delay < 10:
            print_formatted("ERROR", "Minimum delay is 10 seconds")
            return
        config["launch_delay"] = delay
        save_config(config)
        print_formatted("SUCCESS", f"Launch delay set to {delay}s")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def set_retry_delay(config):
    try:
        print_formatted("INFO", "Enter retry delay (seconds, min 5, default 15):")
        delay = int(input("> ").strip())
        if delay < 5:
            print_formatted("ERROR", "Minimum delay is 5 seconds")
            return
        config["retry_delay"] = delay
        save_config(config)
        print_formatted("SUCCESS", f"Retry delay set to {delay}s")
    except ValueError:
        print_formatted("ERROR", "Please enter a number")

def toggle_game_validation(config):
    config["game_validation"] = not config.get("game_validation", True)
    save_config(config)
    status = "ENABLED" if config["game_validation"] else "DISABLED"
    print_formatted("SUCCESS", f"Game validation {status}")

def toggle_crash_protection(config):
    config["minimize_crashes"] = not config.get("minimize_crashes", True)
    save_config(config)
    status = "ENABLED" if config["minimize_crashes"] else "DISABLED"
    print_formatted("SUCCESS", f"Crash protection {status}")

# ======================
# STATUS CHECKS
# ======================
def is_executor_running():
    try:
        packages = ["com.codex", "com.arceusx", "com.delta"]
        for pkg in packages:
            output = run_shell_command(f"ps -A | grep {pkg}")
            if output.strip():
                return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Executor check error: {e}")
        return False

def is_account_logged_in(user_id):
    try:
        run_shell_command("logcat -c")
        time.sleep(1)
        output = run_shell_command(f"logcat -d -t 200 | grep -i 'user.*id.*{user_id}'")
        return user_id in output
    except Exception as e:
        print_formatted("ERROR", f"Account check error: {e}")
        return False

def check_status(config):
    if not verify_roblox_installation():
        return
        
    print_formatted("INFO", "Running status checks...")
    
    if config["check_method"] in ["executor", "both"]:
        executor_running = is_executor_running()
        print_formatted("SUCCESS" if executor_running else "WARNING", 
                      f"Executor: {'Running' if executor_running else 'Not running'}")
    
    if config["check_method"] in ["roblox", "both"]:
        roblox_running = is_roblox_running()
        print_formatted("SUCCESS" if roblox_running else "WARNING", 
                      f"Roblox: {'Running' if roblox_running else 'Not running'}")
        
        if roblox_running:
            activity = get_current_activity()
            in_game = is_game_joined(config["game_id"], config["private_server"])
            print_formatted("SUCCESS" if in_game else "WARNING", 
                          f"Game status: {'In game' if in_game else 'Not in game'}")
            
            if is_in_main_menu(activity):
                print_formatted("WARNING", "Roblox is in main menu")
            if is_in_error_state(activity):
                print_formatted("ERROR", "Roblox is in error state")
    
    if config["active_account"]:
        logged_in = is_account_logged_in(config["active_account"])
        print_formatted("SUCCESS" if logged_in else "WARNING", 
                      f"Account: {'Logged in' if logged_in else 'Not logged in'}")
    
    print_formatted("INFO", "Status check complete")

# ======================
# AUTO-REJOIN
# ======================
def should_rejoin(config):
    if not is_roblox_running():
        return True
        
    activity = get_current_activity()
    
    if is_game_joined(config["game_id"], config["private_server"]):
        return False
        
    if (is_in_main_menu(activity) or is_in_error_state(activity)):
        return True
        
    return False

def auto_rejoin(config):
    if not is_root_available():
        print_formatted("ERROR", "Root access required for auto-rejoin.")
        return
    
    if not config["active_account"]:
        print_formatted("ERROR", "No active account selected")
        return
        
    if not config["game_id"]:
        print_formatted("ERROR", "No game configured")
        return
        
    if not verify_roblox_installation():
        return
    
    print_formatted("INFO", f"Starting auto-rejoin for {config['active_account']}")
    print_formatted("INFO", "Press Ctrl+C to stop")
    
    try:
        retry_count = 0
        max_retries = config.get("max_retries", 3)
        cooldown = False
        
        while True:
            try:
                if cooldown:
                    print_formatted("WARNING", f"In cooldown period - waiting {config.get('cooldown_period', 120)} seconds")
                    time.sleep(config.get("cooldown_period", 120))
                    cooldown = False
                    
                if should_rejoin(config):
                    print_formatted("WARNING", "Rejoin conditions met - attempting to rejoin...")
                    if launch_game(config):
                        retry_count = 0
                        print_formatted("SUCCESS", "Successfully rejoined game")
                    else:
                        retry_count += 1
                        print_formatted("WARNING", f"Rejoin failed (attempt {retry_count}/{max_retries})")
                else:
                    retry_count = 0
                    print_formatted("SUCCESS", "Roblox is running and in correct game")
                
                if retry_count >= max_retries:
                    print_formatted("ERROR", f"Max retries ({max_retries}) reached. Entering cooldown...")
                    cooldown = True
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
        close_roblox(config)

# ======================
# MAIN MENU
# ======================
def show_menu(config):
    while True:
        os.system("clear")
        print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=====================================
       Koala Hub Auto-Rejoin v4.8
====================================={COLORS['RESET']}
{COLORS['BOLD']}Current Settings:{COLORS['RESET']}
{COLORS['CYAN']}• Account: {config['active_account'] or 'None'}
{COLORS['CYAN']}• Game ID: {config['game_id'] or 'None'}
{COLORS['CYAN']}• Private Server: {'Yes' if config['private_server'] else 'No'}
{COLORS['CYAN']}• Check Delay: {config['check_delay']}s
{COLORS['CYAN']}• Check Method: {config['check_method']}
{COLORS['CYAN']}• Launch Delay: {config['launch_delay']}s
{COLORS['CYAN']}• Retry Delay: {config.get('retry_delay', 15)}s
{COLORS['CYAN']}• Cooldown Period: {config.get('cooldown_period', 120)}s
{COLORS['CYAN']}• Game Validation: {'ON' if config.get('game_validation', True) else 'OFF'}
{COLORS['CYAN']}• Crash Protection: {'ON' if config.get('minimize_crashes', True) else 'OFF'}

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
            set_launch_delay(config)
        elif choice == "8":
            set_retry_delay(config)
        elif choice == "9":
            toggle_game_validation(config)
        elif choice == "10":
            toggle_crash_protection(config)
        elif choice == "11":
            check_status(config)
        elif choice == "12":
            auto_rejoin(config)
        elif choice == "13":
            delete_game_settings(config)
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
• Single-attempt launch (more reliable)
• Improved private server handling
• Better crash/freeze detection
• Cloud phone compatible
• Root-optimized performance
""")
    show_menu(config)

if __name__ == "__main__":
    main()