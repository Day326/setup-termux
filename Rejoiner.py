import requests
import time
import os
import json
import subprocess
import urllib.parse
import re
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
roblox_process_count = 0
last_launch_time = 0
roblox_version = "Unknown"

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

def is_root_available():
    try:
        result = subprocess.run(["su", "-c", "echo test"], capture_output=True, text=True, timeout=5)
        return "test" in result.stdout
    except:
        return False

def run_shell_command(command, timeout=10):
    try:
        result = subprocess.run(["su", "-c", command], capture_output=True, text=True, timeout=timeout)
        if result.stderr:
            print_formatted("WARNING", f"Command stderr: {result.stderr.strip()}")
        return result.stdout.strip()
    except Exception as e:
        print_formatted("ERROR", f"Command failed: {command} - {str(e)}")
        return ""

def get_roblox_version():
    global roblox_version
    try:
        output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep versionName")
        if output:
            roblox_version = output.split("versionName=")[1].split()[0]
            print_formatted("INFO", f"Roblox version: {roblox_version}")
        return roblox_version
    except:
        print_formatted("WARNING", "Could not detect Roblox version")
        return "Unknown"

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
        "join_delay": 45
    }
    try:
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f)
            run_shell_command(f"chmod 644 {CONFIG_FILE}")
            print_formatted("INFO", "Created new config file")
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
        run_shell_command(f"chmod 644 {CONFIG_FILE}")
        print_formatted("SUCCESS", "Config saved")
    except Exception as e:
        print_formatted("ERROR", f"Config save error: {e}")

# ======================
# ROBLOX CONTROL FUNCTIONS
# ======================
def verify_roblox_installation():
    output = run_shell_command(f"pm list packages {ROBLOX_PACKAGE}")
    if ROBLOX_PACKAGE not in output:
        print_formatted("ERROR", "Roblox not installed.")
        return False
    get_roblox_version()
    return True

def is_roblox_running():
    global roblox_process_count
    try:
        output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE} | grep -v grep")
        process_running = bool(output.strip())
        activity_output = run_shell_command(f"dumpsys activity | grep {ROBLOX_PACKAGE}")
        activity_running = ROBLOX_PACKAGE in activity_output and "mResumedActivity" in activity_output
        if process_running and activity_running:
            roblox_process_count = max(1, roblox_process_count)
            return True
        roblox_process_count = 0
        return False
    except Exception as e:
        print_formatted("ERROR", f"Process check error: {e}")
        return False

def get_current_activity():
    return run_shell_command("dumpsys window windows | grep mCurrentFocus")

def is_in_game_activity(activity):
    return "GameActivity" in activity or "ExperienceActivity" in activity or "SurfaceView" in activity

def is_in_main_menu(activity):
    return "MainActivity" in activity or "HomeActivity" in activity or "ActivitySplash" in activity

def is_in_error_state(activity):
    error_states = ["ErrorActivity", "CrashActivity", "NotResponding", "ANR"]
    return any(state in activity for state in error_states)

def check_roblox_state(game_id, private_server):
    try:
        run_shell_command("logcat -c")
        time.sleep(1)
        log_cmd = "logcat -d -t 200 | grep -iE 'crash|fatal|disconnected|kicked|banned|notresponding|exception|error|anr|timeout|network|luaerror|processerror|placeid|gameid|joining'"
        logs = run_shell_command(log_cmd)
        if any(x in logs.lower() for x in ["crash", "fatal", "exception", "error", "anr", "luaerror", "processerror"]):
            print_formatted("ERROR", "Roblox crash detected")
            return "crashed"
        if any(x in logs.lower() for x in ["disconnected", "kicked", "banned"]):
            print_formatted("ERROR", "Roblox kick/ban detected")
            return "kicked"
        if any(x in logs.lower() for x in ["notresponding", "timeout"]):
            print_formatted("ERROR", "Roblox freeze detected")
            return "frozen"
        if "network" in logs.lower():
            print_formatted("ERROR", "Roblox network issue detected")
            return "network"
        activity = get_current_activity()
        if is_in_error_state(activity):
            print_formatted("ERROR", "Roblox in error state")
            return "error"
        if is_game_joined(game_id, private_server):
            return "running"
        return "unknown"
    except Exception as e:
        print_formatted("ERROR", f"State check error: {e}")
        return "unknown"

def close_roblox(config=None):
    global roblox_process_count
    try:
        print_formatted("INFO", "Closing Roblox...")
        run_shell_command("input keyevent HOME")
        time.sleep(2)
        run_shell_command(f"am force-stop {ROBLOX_PACKAGE}")
        run_shell_command(f"killall -9 {ROBLOX_PACKAGE}")
        run_shell_command(f"pkill -9 -f {ROBLOX_PACKAGE}")
        time.sleep(config.get("force_kill_delay", 10) if config else 10)
        if is_roblox_running():
            print_formatted("WARNING", "Roblox still running, clearing cache...")
            run_shell_command(f"rm -rf /data/data/{ROBLOX_PACKAGE}/cache/*")
            time.sleep(5)
        if is_roblox_running():
            print_formatted("ERROR", "Failed to close Roblox")
            return False
        roblox_process_count = 0
        print_formatted("SUCCESS", "Roblox closed successfully")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Failed to close Roblox: {e}")
        return False

def prepare_roblox(config):
    global roblox_process_count
    try:
        print_formatted("INFO", "Preparing Roblox for launch...")
        for _ in range(3):
            if is_roblox_running():
                if not close_roblox(config):
                    print_formatted("ERROR", "Failed to prepare Roblox")
                    return False
            time.sleep(2)
        roblox_process_count = 0
        return True
    except Exception as e:
        print_formatted("ERROR", f"Preparation error: {e}")
        return False

# ======================
# GAME LAUNCH FUNCTIONS
# ======================
def get_main_activity():
    try:
        output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep -A 5 'android.intent.action.MAIN'")
        match = re.search(r'com\.roblox\.client/(\.[A-Za-z0-9.]+)', output)
        if match:
            activity = match.group(1)
            print_formatted("INFO", f"Detected main activity: {activity}")
            return activity
        print_formatted("WARNING", "Could not parse main activity, trying .ActivitySplash")
        output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep ActivitySplash")
        if "ActivitySplash" in output:
            return ".startup.ActivitySplash"
        print_formatted("WARNING", "Could not find ActivitySplash, falling back to .MainActivity")
        return ".MainActivity"
    except Exception as e:
        print_formatted("WARNING", f"Main activity detection error: {e}, using .MainActivity")
        return ".MainActivity"

def is_game_joined(game_id, private_server):
    try:
        run_shell_command("logcat -c")
        time.sleep(1)
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
                patterns.append(f"linkCode={code}")
                patterns.append(f"privateServer.*{code}")
        log_cmd = f"logcat -d -t 200 | grep -iE '{'|'.join(patterns)}'"
        logs = run_shell_command(log_cmd)
        if logs.strip():
            activity = get_current_activity()
            if ROBLOX_PACKAGE in activity and is_in_game_activity(activity):
                process_check = run_shell_command(f"dumpsys activity | grep {ROBLOX_PACKAGE}")
                if "mResumedActivity" in process_check:
                    print_formatted("INFO", "Game join confirmed via logs and activity")
                    return True
        return False
    except Exception as e:
        print_formatted("ERROR", f"Game detection error: {e}")
        return False

def extract_private_server_code(link):
    try:
        for sep in ["privateServerLinkCode=", "share?code=", "&linkCode=", "="]:
            if sep in link:
                code = link.split(sep)[1].split("&")[0].strip()
                if code:
                    return code
        return None
    except:
        return None

def build_launch_url(game_id, private_server):
    try:
        if private_server:
            code = extract_private_server_code(private_server)
            if code:
                return f"roblox://placeID={game_id}&privateServerLinkCode={code}"
            print_formatted("WARNING", "No private server code found, using game ID")
        return f"roblox://placeID={game_id}"
    except Exception as e:
        print_formatted("ERROR", f"URL build error: {e}")
        return f"roblox://placeID={game_id}"

def is_account_logged_in(user_id):
    try:
        run_shell_command("logcat -c")
        time.sleep(1)
        output = run_shell_command(f"logcat -d -t 100 | grep -i 'user.*id.*{user_id}'")
        if user_id in output:
            print_formatted("SUCCESS", f"Account {user_id} is logged in")
            return True
        print_formatted("WARNING", f"Account {user_id} not logged in")
        return False
    except Exception as e:
        print_formatted("ERROR", f"Login check error: {e}")
        return False

def launch_game(config):
    global roblox_process_count, last_launch_time
    current_time = time.time()
    if current_time - last_launch_time < 20:
        print_formatted("INFO", "Waiting before next launch...")
        time.sleep(20 - (current_time - last_launch_time))
    last_launch_time = current_time
    
    try:
        print_formatted("HEADER", "Launch Sequence Started")
        
        # Step 1: Close existing Roblox instances
        if not close_roblox(config):
            print_formatted("ERROR", "Failed to close Roblox before launch")
            return False
        
        # Step 2: Prepare for launch
        if not prepare_roblox(config):
            print_formatted("ERROR", "Failed to prepare Roblox")
            return False
        
        # Step 3: Get main activity
        main_activity = get_main_activity()
        print_formatted("INFO", f"Using main activity: {main_activity}")
        
        # Step 4: Build launch URL
        launch_url = build_launch_url(config["game_id"], config["private_server"])
        print_formatted("INFO", f"Launch URL: {launch_url}")
        
        # Step 5: Launch Roblox with deep link
        print_formatted("INFO", "Launching Roblox with deep link...")
        result = run_shell_command(f"am start --user 0 -a android.intent.action.VIEW -d '{launch_url}' -n {ROBLOX_PACKAGE}/{main_activity}")
        print_formatted("INFO", f"Launch result: {result}")
        
        if "Error" in result:
            print_formatted("WARNING", "Deep link launch failed, trying fallback method")
            result = run_shell_command(f"am start --user 0 -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n {ROBLOX_PACKAGE}/{main_activity}")
            print_formatted("INFO", f"Fallback result: {result}")
            if "Error" in result:
                print_formatted("ERROR", "Failed to launch Roblox")
                return False
        
        roblox_process_count = 1
        
        # Step 6: Wait for Roblox to initialize
        print_formatted("INFO", "Waiting for Roblox to initialize...")
        time.sleep(15)  # Initial loading time
        
        # Step 7: Check if Roblox is running
        if not is_roblox_running():
            print_formatted("ERROR", "Roblox failed to start")
            close_roblox(config)
            return False
        
        # Step 8: Check account login status
        print_formatted("INFO", "Checking login status...")
        if not is_account_logged_in(config["active_account"]):
            print_formatted("WARNING", "Manual login may be required")
        
        # Step 9: Wait for game to join
        print_formatted("INFO", "Waiting for game to join...")
        loaded = False
        for i in range(config.get("join_delay", 45) // 5):
            time.sleep(5)
            state = check_roblox_state(config["game_id"], config["private_server"])
            
            if state in ["crashed", "kicked", "frozen", "error", "network"]:
                print_formatted("ERROR", f"Roblox state: {state}")
                close_roblox(config)
                return False
            
            if is_game_joined(config["game_id"], config["private_server"]):
                print_formatted("SUCCESS", "Successfully joined game")
                loaded = True
                break
            
            print(f"\r{COLORS['CYAN']}Waiting for game to load... {i * 5}s/{config.get('join_delay', 45)}s{COLORS['RESET']}", end="")
        
        print("\r" + " " * 50 + "\r", end="")
        
        if not loaded:
            print_formatted("WARNING", "Failed to join game")
            close_roblox(config)
            return False
        
        print_formatted("HEADER", "Launch Sequence Completed")
        return True
        
    except Exception as e:
        print_formatted("ERROR", f"Launch error: {e}")
        close_roblox(config)
        return False

# ======================
# GAME VALIDATION
# ======================
def validate_game_id(game_id, config):
    if not game_id.isdigit() or len(game_id) < 6 or len(game_id) > 15:
        print_formatted("ERROR", "Game ID must be 6-15 digits")
        return False
    if not config.get("game_validation", True):
        print_formatted("WARNING", "Skipping game validation")
        return True
    try:
        url = f"https://games.roblox.com/v1/games/multiget-place-details?placeIds={game_id}"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("data"):
                data = data["data"]
            if isinstance(data, list) and data and data[0].get("placeId"):
                print_formatted("SUCCESS", f"Valid game: {data[0].get('name', 'Unknown')}")
                return True
        print_formatted("WARNING", "Game validation failed, proceeding anyway")
        return True
    except Exception as e:
        print_formatted("ERROR", f"Validation error: {e}")
        return True

def validate_private_server(link, game_id):
    try:
        if not link.startswith(("https://www.roblox.com/games/", "roblox://")):
            print_formatted("ERROR", "Invalid link format")
            return False
        code = extract_private_server_code(link)
        if not code:
            print_formatted("ERROR", "Link must contain private server code")
            return False
        if link.startswith("https://"):
            parts = link.split("/games/")[1].split("/")
            place_id = parts[0]
        else:
            place_id = link.split("placeID=")[1].split("&")[0] if "placeID=" in link else game_id
        if place_id != str(game_id):
            print_formatted("ERROR", "Private server Game ID does not match provided Game ID")
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
            print_formatted("WARNING", "Couldn't verify username, using as-is")
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
    if game_id.lower() == "delete":
        delete_game_settings(config)
        return
    if not validate_game_id(game_id, config):
        return
    config["game_id"] = game_id
    print_formatted("INFO", "Enter Private Server Link (leave empty if none):")
    ps_link = input("> ").strip()
    if ps_link:
        if ps_link.startswith(("http://", "https://", "roblox://")) and validate_private_server(ps_link, game_id):
            config["private_server"] = ps_link
            print_formatted("SUCCESS", f"Private server link saved: {ps_link}")
        else:
            config["private_server"] = ""
            print_formatted("WARNING", "Invalid private server link, using game ID only")
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
    print(f"{COLORS['CYAN']}1: Executor UI only{COLORS['RESET']}")
    print(f"{COLORS['CYAN']}2: Roblox running only{COLORS['RESET']}")
    print(f"{COLORS['CYAN']}3: Both (recommended){COLORS['RESET']}")
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
        print_formatted("INFO", "Enter launch delay (seconds, min 10, default 300):")
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
    packages = ["com.codex", "com.arceusx", "com.delta"]
    for pkg in packages:
        output = run_shell_command(f"ps -A | grep {pkg} | grep -v grep")
        if output.strip():
            return True
    return False

def check_status(config):
    if not verify_roblox_installation():
        return
    print_formatted("HEADER", "Status Check")
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
            state = check_roblox_state(config["game_id"], config["private_server"])
            print_formatted("SUCCESS" if in_game and state == "running" else "WARNING",
                            f"Game status: {'In game' if in_game and state == 'running' else f'Not in game or {state}'}")
            if is_in_main_menu(activity):
                print_formatted("WARNING", "Roblox is in main menu")
            if is_in_error_state(activity):
                print_formatted("ERROR", "Roblox in error state")
    if config["active_account"]:
        logged_in = is_account_logged_in(config["active_account"])
        print_formatted("SUCCESS" if logged_in else "WARNING",
                        f"Account: {'Logged in' if logged_in else 'Not logged in'}")
    print_formatted("HEADER", "Status Check Complete")

# ======================
# AUTO-REJOIN
# ======================
def should_rejoin(config):
    if not is_roblox_running():
        return True, "not_running"
    state = check_roblox_state(config["game_id"], config["private_server"])
    if state == "running":
        return False, "running"
    return True, state or "unknown"

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
    if not verify_roblox_installation():
        return
    print_formatted("HEADER", f"Auto-Rejoin Started for {config['active_account']}")
    print_formatted("INFO", "Press Ctrl+C to stop")
    try:
        retry_count = 0
        max_retries = config.get("max_retries", 3)
        cooldown = False
        while True:
            if cooldown:
                print_formatted("WARNING", f"In cooldown: waiting {config.get('cooldown_period', 120)}s")
                time.sleep(config.get("cooldown_period", 120))
                cooldown = False
                roblox_process_count = 0
            should, reason = should_rejoin(config)
            if should:
                print_formatted("WARNING", f"Rejoin triggered: {reason}")
                if not close_roblox(config):
                    retry_count += 1
                    time.sleep(config.get("retry_delay", 15))
                    continue
                if not prepare_roblox(config):
                    retry_count += 1
                    time.sleep(config.get("retry_delay", 15))
                    continue
                if launch_game(config):
                    retry_count = 0
                else:
                    retry_count += 1
                    print_formatted("WARNING", f"Rejoin failed (attempt {retry_count}/{max_retries})")
            else:
                retry_count = 0
                print_formatted("SUCCESS", "Roblox is running and in game")
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
    except KeyboardInterrupt:
        print_formatted("INFO", "Auto-rejoin stopped")
        close_roblox(config)
    except Exception as e:
        print_formatted("ERROR", f"Rejoin error: {e}")
        close_roblox(config)

# ======================
# MAIN MENU
# ======================
def show_menu(config):
    while True:
        os.system("clear")
        print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=== Koala Hub Auto-Rejoin v6.0 ===
{COLORS['RESET']}
{COLORS['BOLD']}Settings:{COLORS['RESET']}
  Roblox Version: {roblox_version}
  Account: {config['active_account'] or 'None'}
  Game ID: {config['game_id'] or 'None'}
  Private Server: {config['private_server'] or 'None'}
  Check Delay: {config['check_delay']}s
  Check Method: {config['check_method']}
  Launch Delay: {config['launch_delay']}s
  Retry Delay: {config.get('retry_delay', 15)}s
  Cooldown Period: {config.get('cooldown_period', 120)}s
  Join Delay: {config.get('join_delay', 45)}s
  Game Validation: {'ON' if config.get('game_validation', True) else 'OFF'}
  Crash Protection: {'ON' if config.get('minimize_crashes', True) else 'OFF'}

{COLORS['BOLD']}Options:{COLORS['RESET']}
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
    if not is_root_available():
        print_formatted("ERROR", "Root access required. Ensure device is rooted.")
        return
    config = load_config()
    print(f"""
{COLORS['BOLD']}{COLORS['CYAN']}=== Koala Hub Auto-Rejoin v6.0 ===
{COLORS['RESET']}
{COLORS['BOLD']}Features:{COLORS['RESET']}
  - Preserves login sessions
  - Direct deep link to join game
  - Clean console interface
  - Robust error logging
""")
    if not verify_roblox_installation():
        return
    show_menu(config)

if __name__ == "__main__":
    main()