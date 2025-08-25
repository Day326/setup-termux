#!/usr/bin/env python3
"""
Enhanced Roblox Automation Tool (Rejoiner.py) - Improved Version
Supports: UGPHONE, VSPHONE, REDFINGER, Standard Android/Emulators
Enhanced with robust crash detection, continuous monitoring, and better logging
Author: Enhanced for multi-platform compatibility and reliability
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
import signal
from datetime import datetime
from pathlib import Path

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
    "HEADER": "\033[95m",
    "PURPLE": "\033[35m"
}

CONFIG_FILE = "/sdcard/roblox_config.json"
LOG_FILE = "/sdcard/roblox_automation.log"
ROBLOX_PACKAGE = "com.roblox.client"

# Global variables
automation_running = False
platform_info = None
last_game_join_time = None
monitoring_thread = None
heartbeat_thread = None
restart_count = 0
last_ui_response_time = None

# ======================
# LOGGING SYSTEM
# ======================
class Logger:
    def __init__(self, log_file=LOG_FILE, verbose=False):
        self.log_file = log_file
        self.verbose = verbose
        self.ensure_log_dir()
    
    def ensure_log_dir(self):
        """Ensure log directory exists"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        except:
            pass
    
    def log(self, level, message, console_only=False):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Console output with colors
        prefix = {
            "INFO": "INFO",
            "SUCCESS": "OK",
            "WARNING": "WARN",
            "ERROR": "ERROR",
            "HEADER": "====",
            "DEBUG": "DEBUG",
            "MONITOR": "MON"
        }.get(level, level)
        
        console_msg = f"{COLORS.get(level, '')}{timestamp} [{prefix}] {message}{COLORS['RESET']}"
        print(console_msg)
        
        # File output (if not console_only)
        if not console_only:
            try:
                file_msg = f"{timestamp} [{prefix}] {message}\n"
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(file_msg)
            except:
                pass
    
    def debug(self, message):
        if self.verbose:
            self.log("DEBUG", message)
    
    def info(self, message):
        self.log("INFO", message)
    
    def success(self, message):
        self.log("SUCCESS", message)
    
    def warning(self, message):
        self.log("WARNING", message)
    
    def error(self, message):
        self.log("ERROR", message)
    
    def monitor(self, message):
        self.log("MONITOR", message)
    
    def clear_screen(self):
        """Clear screen for better readability"""
        try:
            run_shell_command("clear", platform_info=platform_info)
        except:
            pass

logger = Logger()

# ======================
# PLATFORM DETECTION (Enhanced)
# ======================
class PlatformDetector:
    def __init__(self):
        self.detected_platform = None
    
    def detect_platform(self):
        """Enhanced platform detection with better logging"""
        try:
            logger.info("Detecting platform...")
            
            # Check for UGPHONE
            if self._is_ugphone():
                self.detected_platform = {
                    'type': 'ugphone',
                    'name': 'UGPHONE',
                    'has_root': self._check_root_ugphone(),
                    'use_adb': False,
                    'shell_prefix': '',
                    'special_commands': True,
                    'tap_method': 'ugphone_tap'
                }
                logger.success(f"Platform detected: {self.detected_platform['name']}")
                return self.detected_platform
            
            # Check for VSPHONE
            if self._is_vsphone():
                self.detected_platform = {
                    'type': 'vsphone',
                    'name': 'VSPHONE',
                    'has_root': self._check_root_vsphone(),
                    'use_adb': False,
                    'shell_prefix': '',
                    'special_commands': True,
                    'tap_method': 'vsphone_tap'
                }
                logger.success(f"Platform detected: {self.detected_platform['name']}")
                return self.detected_platform
            
            # Check for REDFINGER
            if self._is_redfinger():
                self.detected_platform = {
                    'type': 'redfinger',
                    'name': 'REDFINGER',
                    'has_root': self._check_root_standard(),
                    'use_adb': True,
                    'shell_prefix': 'su -c',
                    'special_commands': False,
                    'tap_method': 'standard_tap'
                }
                logger.success(f"Platform detected: {self.detected_platform['name']}")
                return self.detected_platform
            
            # Standard Android
            self.detected_platform = {
                'type': 'standard',
                'name': 'Standard Android',
                'has_root': self._check_root_standard(),
                'use_adb': True,
                'shell_prefix': 'su -c' if self._check_root_standard() else '',
                'special_commands': False,
                'tap_method': 'standard_tap'
            }
            logger.success(f"Platform detected: {self.detected_platform['name']}")
            return self.detected_platform
            
        except Exception as e:
            logger.error(f"Platform detection error: {str(e)}")
            self.detected_platform = {
                'type': 'unknown',
                'name': 'Unknown Platform',
                'has_root': False,
                'use_adb': False,
                'shell_prefix': '',
                'special_commands': False,
                'tap_method': 'standard_tap'
            }
            return self.detected_platform
    
    def _is_ugphone(self):
        """Enhanced UGPHONE detection"""
        try:
            indicators = [
                '/system/bin/ugphone',
                '/system/app/UGPhone',
                '/data/local/tmp/ugphone',
                '/system/lib/libugphone.so'
            ]
            
            for indicator in indicators:
                if os.path.exists(indicator):
                    logger.debug(f"UGPHONE indicator found: {indicator}")
                    return True
            
            build_info = self._get_build_prop()
            ugphone_patterns = ['ugphone', 'ug_phone', 'cloudphone', 'ug-phone']
            
            for pattern in ugphone_patterns:
                if pattern.lower() in build_info.lower():
                    logger.debug(f"UGPHONE pattern found in build.prop: {pattern}")
                    return True
            
            return False
        except Exception as e:
            logger.debug(f"UGPHONE detection error: {e}")
            return False
    
    def _is_vsphone(self):
        """Enhanced VSPHONE detection"""
        try:
            indicators = [
                '/system/bin/vsphone',
                '/system/app/VSPhone',
                '/data/local/tmp/vsphone',
                '/system/lib/libvsphone.so'
            ]
            
            for indicator in indicators:
                if os.path.exists(indicator):
                    logger.debug(f"VSPHONE indicator found: {indicator}")
                    return True
            
            build_info = self._get_build_prop()
            vsphone_patterns = ['vsphone', 'vs_phone', 'virtualphone', 'vs-phone']
            
            for pattern in vsphone_patterns:
                if pattern.lower() in build_info.lower():
                    logger.debug(f"VSPHONE pattern found in build.prop: {pattern}")
                    return True
            
            return False
        except Exception as e:
            logger.debug(f"VSPHONE detection error: {e}")
            return False
    
    def _is_redfinger(self):
        """Enhanced REDFINGER detection"""
        try:
            indicators = [
                '/system/bin/redfinger',
                '/system/app/RedFinger',
                '/data/local/tmp/redfinger',
                '/system/lib/libredfinger.so'
            ]
            
            for indicator in indicators:
                if os.path.exists(indicator):
                    logger.debug(f"REDFINGER indicator found: {indicator}")
                    return True
            
            build_info = self._get_build_prop()
            redfinger_patterns = ['redfinger', 'red_finger', 'redcloud', 'red-finger']
            
            for pattern in redfinger_patterns:
                if pattern.lower() in build_info.lower():
                    logger.debug(f"REDFINGER pattern found in build.prop: {pattern}")
                    return True
            
            return False
        except Exception as e:
            logger.debug(f"REDFINGER detection error: {e}")
            return False
    
    def _get_build_prop(self):
        """Get build.prop content with error handling"""
        try:
            result = subprocess.run(['cat', '/system/build.prop'], 
                                  capture_output=True, text=True, timeout=5)
            return result.stdout
        except Exception as e:
            logger.debug(f"Failed to read build.prop: {e}")
            return ""
    
    def _check_root_standard(self):
        """Enhanced root check for standard Android"""
        try:
            # Multiple methods to check root
            methods = [
                ['su', '-c', 'echo test'],
                ['which', 'su'],
                ['ls', '/system/xbin/su'],
                ['ls', '/system/bin/su']
            ]
            
            for method in methods:
                try:
                    result = subprocess.run(method, capture_output=True, text=True, timeout=3)
                    if result.returncode == 0 and ('test' in result.stdout or 'su' in result.stdout):
                        logger.debug("Root access confirmed")
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.debug(f"Root check error: {e}")
            return False
    
    def _check_root_ugphone(self):
        """Enhanced root check for UGPHONE"""
        try:
            if self._check_root_standard():
                return True
            
            # UGPHONE specific root methods
            ugphone_methods = [
                ['ugphone_su', '-c', 'echo test'],
                ['ug_su', '-c', 'echo test']
            ]
            
            for method in ugphone_methods:
                try:
                    result = subprocess.run(method, capture_output=True, text=True, timeout=3)
                    if 'test' in result.stdout:
                        return True
                except:
                    continue
            
            return False
        except:
            return False
    
    def _check_root_vsphone(self):
        """Enhanced root check for VSPHONE"""
        try:
            if self._check_root_standard():
                return True
            
            # VSPHONE specific root methods
            vsphone_methods = [
                ['vsphone_su', '-c', 'echo test'],
                ['vs_su', '-c', 'echo test']
            ]
            
            for method in vsphone_methods:
                try:
                    result = subprocess.run(method, capture_output=True, text=True, timeout=3)
                    if 'test' in result.stdout:
                        return True
                except:
                    continue
            
            return False
        except:
            return False

# ======================
# ENHANCED SHELL COMMAND EXECUTION
# ======================
def run_shell_command(command, timeout=10, platform_info=None, retry_count=2):
    """Enhanced shell command execution with retry logic"""
    for attempt in range(retry_count + 1):
        try:
            if platform_info and platform_info.get('shell_prefix') and platform_info.get('has_root'):
                if platform_info['shell_prefix']:
                    prefix_parts = platform_info['shell_prefix'].split()
                    full_command = prefix_parts + [command]
                else:
                    full_command = command.split()
            else:
                full_command = command.split()
            
            logger.debug(f"Executing command (attempt {attempt + 1}): {' '.join(full_command)}")
            
            result = subprocess.run(full_command, capture_output=True, text=True, timeout=timeout)
            
            if result.stderr and "permission denied" not in result.stderr.lower():
                if attempt == retry_count:  # Only log on final attempt
                    logger.warning(f"Command stderr: {result.stderr.strip()}")
            
            if result.returncode == 0 or attempt == retry_count:
                return result.stdout.strip()
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timeout (attempt {attempt + 1}): {command}")
            if attempt == retry_count:
                return ""
        except Exception as e:
            logger.debug(f"Command failed (attempt {attempt + 1}): {command} - {str(e)}")
            if attempt == retry_count:
                logger.error(f"Command ultimately failed: {command} - {str(e)}")
                return ""
        
        if attempt < retry_count:
            time.sleep(1)  # Brief delay between retries
    
    return ""

# ======================
# CONFIGURATION MANAGEMENT
# ======================
def load_config():
    """Enhanced configuration loading with validation"""
    default_config = {
        "accounts": [],
        "game_id": "",
        "private_server": "",
        "check_delay": 30,
        "active_account": "",
        "check_method": "both",
        "max_retries": 5,
        "game_validation": True,
        "launch_delay": 180,
        "retry_delay": 10,
        "force_kill_delay": 5,
        "minimize_crashes": True,
        "launch_attempts": 3,
        "cooldown_period": 60,
        "auto_rejoin": True,
        "ui_timeout": 20,
        "verbose_logging": False,
        "monitoring_interval": 15,
        "crash_detection_sensitivity": "medium",
        "max_consecutive_failures": 3,
        "heartbeat_interval": 60,
        "screen_check_enabled": True,
        "process_check_enabled": True,
        "ui_response_timeout": 10,
        "auto_restart_enabled": True
    }
    
    try:
        if not os.path.exists(CONFIG_FILE):
            logger.info("Creating new configuration file...")
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=4)
            run_shell_command(f"chmod 644 {CONFIG_FILE}", platform_info=platform_info)
            logger.success("Configuration file created")
            return default_config
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged_config = {**default_config, **config}
            
            # Validate critical settings
            if merged_config["monitoring_interval"] < 5:
                merged_config["monitoring_interval"] = 5
                logger.warning("Monitoring interval too low, set to minimum 5 seconds")
            
            if merged_config["max_consecutive_failures"] < 1:
                merged_config["max_consecutive_failures"] = 1
            
            logger.success("Configuration loaded successfully")
            return merged_config
            
    except Exception as e:
        logger.error(f"Configuration load error: {e}")
        logger.info("Using default configuration")
        return default_config

def save_config(config):
    """Enhanced configuration saving with validation"""
    try:
        # Validate config before saving
        if not isinstance(config, dict):
            logger.error("Invalid configuration format")
            return False
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        run_shell_command(f"chmod 644 {CONFIG_FILE}", platform_info=platform_info)
        logger.success("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error(f"Configuration save error: {e}")
        return False

# ======================
# ENHANCED ROBLOX MONITORING
# ======================
class RobloxMonitor:
    def __init__(self, config, platform_info):
        self.config = config
        self.platform_info = platform_info
        self.consecutive_failures = 0
        self.last_successful_check = time.time()
        self.game_state = "unknown"
        self.monitoring_active = False
    
    def start_monitoring(self):
        """Enhanced monitoring system with continuous console presence"""
        self.monitoring_active = True
        logger.success("🎮 ROBLOX MONITORING SYSTEM STARTED")
        logger.info("👀 Watching Roblox for crashes, kicks, bans, freezes...")
        logger.info("🔄 Will automatically restart if issues detected")
        logger.info("⏹️  Press Ctrl+C to stop monitoring")
        print(f"{COLORS['HEADER']}{'='*60}{COLORS['RESET']}")
        
        check_count = 0
        while self.monitoring_active and automation_running:
            try:
                check_count += 1
                self.perform_health_check()
                
                # Show periodic summary every 10 checks
                if check_count % 10 == 0:
                    uptime = int(time.time() - self.last_successful_check)
                    logger.info(f"📊 SUMMARY: {check_count} checks completed | Uptime: {uptime}s | Restarts: {restart_count}")
                
                time.sleep(self.config["monitoring_interval"])
                
            except KeyboardInterrupt:
                logger.info("⏹️  Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring system error: {e}")
                time.sleep(5)
        
        logger.info("🛑 Monitoring system stopped")
        print(f"{COLORS['HEADER']}{'='*60}{COLORS['RESET']}")
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
    
    def perform_health_check(self):
        """Enhanced comprehensive health check of Roblox"""
        try:
            # Multi-layer detection with enhanced logging
            process_running = self.check_process_status()
            ui_responsive = self.check_ui_responsiveness()
            game_active = self.check_game_activity()
            screen_state = self.check_screen_state()  # New: Check for kick/ban screens
            network_active = self.check_network_activity()  # New: Check network connectivity
            
            current_state = self.determine_game_state(process_running, ui_responsive, game_active, screen_state, network_active)
            
            # Always show current status every check (more visibility)
            timestamp = datetime.now().strftime("%H:%M:%S")
            status_msg = f"[{timestamp}] Monitoring - State: {current_state.upper()}"
            
            if current_state == "running":
                uptime = int(time.time() - self.last_successful_check)
                logger.monitor(f"{status_msg} | Uptime: {uptime}s | ✓ Healthy")
            else:
                logger.warning(f"{status_msg} | Issue: {current_state.upper()}")
            
            if current_state != self.game_state:
                logger.info(f"Game state changed: {self.game_state} → {current_state}")
                self.game_state = current_state
            
            if current_state in ["crashed", "kicked", "banned", "frozen", "disconnected", "error_screen"]:
                self.consecutive_failures += 1
                logger.error(f"❌ ISSUE DETECTED: {current_state.upper()} (failure #{self.consecutive_failures})")
                
                if self.consecutive_failures >= self.config["max_consecutive_failures"]:
                    logger.error(f"🔄 MAX FAILURES REACHED ({self.consecutive_failures}) - RESTARTING ROBLOX")
                    self.trigger_restart()
                    self.consecutive_failures = 0
            else:
                if self.consecutive_failures > 0:
                    logger.success(f"✅ RECOVERED from issues (was {self.consecutive_failures} failures)")
                self.consecutive_failures = 0
                self.last_successful_check = time.time()
        
        except Exception as e:
            logger.error(f"Health check error: {e}")
            self.consecutive_failures += 1
    
    def check_process_status(self):
        """Enhanced process status checking"""
        try:
            if not self.config["process_check_enabled"]:
                return True
            
            # Check if Roblox process exists
            process_output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE} | grep -v grep", 
                                             platform_info=self.platform_info)
            
            if not process_output.strip():
                logger.debug("Roblox process not found")
                return False
            
            # Check process health
            pid_match = re.search(r'\s+(\d+)\s+', process_output)
            if pid_match:
                pid = pid_match.group(1)
                # Check if process is responsive
                status_output = run_shell_command(f"cat /proc/{pid}/status 2>/dev/null | grep State", 
                                                platform_info=self.platform_info)
                if "zombie" in status_output.lower() or "dead" in status_output.lower():
                    logger.debug(f"Roblox process {pid} is in bad state: {status_output}")
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Process check error: {e}")
            return False
    
    def check_ui_responsiveness(self):
        """Check if Roblox UI is responsive"""
        try:
            if not self.config["screen_check_enabled"]:
                return True
            
            global last_ui_response_time
            
            # Check if Roblox activity is in foreground
            activity_output = run_shell_command(f"dumpsys activity | grep mResumedActivity", 
                                              platform_info=self.platform_info)
            
            if ROBLOX_PACKAGE not in activity_output:
                logger.debug("Roblox not in foreground")
                return False
            
            # Test UI responsiveness with a light touch
            self.test_ui_response()
            
            current_time = time.time()
            if last_ui_response_time is None:
                last_ui_response_time = current_time
            
            # If UI hasn't responded for too long, consider it frozen
            if current_time - last_ui_response_time > self.config["ui_response_timeout"]:
                logger.debug("UI response timeout detected")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"UI responsiveness check error: {e}")
            return False
    
    def test_ui_response(self):
        """Test UI responsiveness with minimal interaction"""
        try:
            # Send a harmless key event to test responsiveness
            result = run_shell_command("input keyevent KEYCODE_MENU", 
                                     platform_info=self.platform_info, timeout=3)
            time.sleep(0.5)
            run_shell_command("input keyevent KEYCODE_BACK", 
                            platform_info=self.platform_info, timeout=3)
            
            global last_ui_response_time
            last_ui_response_time = time.time()
            
        except Exception as e:
            logger.debug(f"UI response test error: {e}")
    
    def check_game_activity(self):
        """Check if actually in a game"""
        try:
            # Check network activity
            network_output = run_shell_command(f"netstat -an | grep {ROBLOX_PACKAGE}", 
                                             platform_info=self.platform_info, timeout=5)
            
            if not network_output.strip():
                logger.debug("No network activity detected")
                return False
            
            # Look for established connections
            if "ESTABLISHED" not in network_output:
                logger.debug("No established connections")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Game activity check error: {e}")
            return True  # Default to true if check fails
    
    def check_screen_state(self):
        """Enhanced screen state detection for kick/ban screens"""
        try:
            # Get current activity and window info
            activity_output = run_shell_command(f"dumpsys activity activities | grep {ROBLOX_PACKAGE}", 
                                              platform_info=self.platform_info)
            
            # Check for common kick/ban indicators in activity names or states
            kick_indicators = [
                "kick", "ban", "error", "disconnect", "timeout", 
                "maintenance", "suspended", "violation", "warning"
            ]
            
            for indicator in kick_indicators:
                if indicator.lower() in activity_output.lower():
                    logger.warning(f"Screen state indicator found: {indicator}")
                    return "error_screen"
            
            # Check window focus and state
            window_output = run_shell_command("dumpsys window windows | grep -A 5 -B 5 roblox", 
                                            platform_info=self.platform_info)
            
            if "mHasSurface=false" in window_output or "mWindowRemovalAllowed=true" in window_output:
                return "error_screen"
            
            return "normal_screen"
            
        except Exception as e:
            logger.debug(f"Screen state check error: {e}")
            return "unknown_screen"
    
    def check_network_activity(self):
        """Check if Roblox has active network connections"""
        try:
            # Get Roblox process ID
            ps_output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE} | head -1", 
                                        platform_info=self.platform_info)
            
            if not ps_output:
                return False
            
            pid_match = re.search(r'\s+(\d+)\s+', ps_output)
            if not pid_match:
                return False
            
            pid = pid_match.group(1)
            
            # Check for network connections
            netstat_output = run_shell_command(f"netstat -tulpn 2>/dev/null | grep {pid}", 
                                             platform_info=self.platform_info, timeout=5)
            
            if netstat_output:
                connection_count = len([line for line in netstat_output.split('\n') if line.strip()])
                logger.debug(f"Active network connections: {connection_count}")
                return connection_count > 0
            
            return True  # Default to true if can't check
            
        except Exception as e:
            logger.debug(f"Network activity check error: {e}")
            return True  # Default to true on error
    
    def determine_game_state(self, process_running, ui_responsive, game_active, screen_state=None, network_active=None):
        """Enhanced game state determination with more indicators"""
        try:
            # Process not running = crashed
            if not process_running:
                return "crashed"
            
            # Error screen detected = kicked/banned
            if screen_state == "error_screen":
                return "kicked"
            
            # UI not responsive = frozen
            if not ui_responsive:
                return "frozen"
            
            # No network activity = disconnected
            if network_active is False:
                return "disconnected"
            
            # Game not active = various issues
            if not game_active:
                return "disconnected"
            
            return "running"
            
        except Exception as e:
            logger.debug(f"State determination error: {e}")
            return "unknown"
    
    def check_for_kick_indicators(self):
        """Check for visual indicators of being kicked"""
        try:
            # This would ideally use screen capture and OCR
            # For now, use indirect methods
            
            # Check if we're back at main menu unexpectedly
            current_activity = run_shell_command("dumpsys activity | grep mFocusedActivity", 
                                                platform_info=self.platform_info)
            
            # Look for specific Roblox activities that indicate main menu
            kick_indicators = ["MainActivity", "LoginActivity", "HomeActivity"]
            
            for indicator in kick_indicators:
                if indicator in current_activity:
                    logger.debug(f"Possible kick indicator found: {indicator}")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Kick indicator check error: {e}")
            return False
    
    def trigger_restart(self):
        """Enhanced Roblox restart with better recovery"""
        try:
            global restart_count
            restart_count += 1
            
            logger.info(f"🔄 TRIGGERING RESTART #{restart_count}")
            logger.info("Step 1: Closing Roblox completely...")
            
            # Enhanced closure process
            close_roblox_enhanced(self.config)
            
            logger.info("Step 2: Waiting for cleanup...")
            time.sleep(self.config["force_kill_delay"] + 2)  # Extra time for cleanup
            
            # Verify closure
            attempts = 0
            while is_roblox_running() and attempts < 5:
                logger.warning(f"Roblox still running, force killing (attempt {attempts + 1})...")
                run_shell_command(f"pkill -9 -f {ROBLOX_PACKAGE}", platform_info=self.platform_info)
                run_shell_command(f"killall -9 {ROBLOX_PACKAGE}", platform_info=self.platform_info)
                time.sleep(2)
                attempts += 1
            
            logger.info("Step 3: Launching Roblox...")
            
            # Clear any UI interference before launch
            run_shell_command("input keyevent KEYCODE_HOME", platform_info=self.platform_info)
            time.sleep(1)
            
            if launch_roblox_game(self.config):
                logger.success(f"✅ RESTART #{restart_count} SUCCESSFUL")
                self.last_successful_check = time.time()
                self.consecutive_failures = 0
                
                # Wait a bit longer after successful restart
                logger.info("Giving game time to fully load...")
                time.sleep(10)
            else:
                logger.error(f"❌ RESTART #{restart_count} FAILED")
            
        except Exception as e:
            logger.error(f"Restart trigger error: {e}")

# ======================
# ENHANCED ROBLOX CONTROL
# ======================
def verify_roblox_installation():
    """Enhanced Roblox installation verification"""
    try:
        logger.info("Verifying Roblox installation...")
        
        # Check if package is installed
        output = run_shell_command(f"pm list packages {ROBLOX_PACKAGE}", platform_info=platform_info)
        if ROBLOX_PACKAGE not in output:
            logger.error("Roblox not installed - please install from Play Store")
            return False
        
        # Get detailed package info
        version_output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep versionName", 
                                         platform_info=platform_info)
        if version_output:
            try:
                version = version_output.split("versionName=")[1].split()[0] if "versionName=" in version_output else "Unknown"
                logger.success(f"Roblox version: {version}")
            except:
                logger.info("Roblox version: Unknown")
        
        # Check package permissions
        perms_output = run_shell_command(f"pm dump {ROBLOX_PACKAGE} | grep permission", 
                                       platform_info=platform_info)
        logger.debug(f"Roblox has {len(perms_output.splitlines())} permissions")
        
        # Check if package is enabled
        enabled_output = run_shell_command(f"pm list packages -e {ROBLOX_PACKAGE}", 
                                         platform_info=platform_info)
        if ROBLOX_PACKAGE not in enabled_output:
            logger.warning("Roblox package appears to be disabled")
            return False
        
        logger.success("Roblox installation verified")
        return True
        
    except Exception as e:
        logger.error(f"Roblox verification error: {e}")
        return False

def is_roblox_running():
    """Enhanced Roblox running check"""
    try:
        # Check processes
        process_output = run_shell_command(f"ps -A | grep {ROBLOX_PACKAGE} | grep -v grep", 
                                         platform_info=platform_info)
        process_running = bool(process_output.strip())
        
        if not process_running:
            logger.debug("Roblox process not found")
            return False
        
        # Check activities
        activity_output = run_shell_command(f"dumpsys activity | grep {ROBLOX_PACKAGE}", 
                                          platform_info=platform_info)
        activity_running = ROBLOX_PACKAGE in activity_output
        
        # Check if in foreground
        foreground_output = run_shell_command("dumpsys activity | grep mResumedActivity", 
                                            platform_info=platform_info)
        in_foreground = ROBLOX_PACKAGE in foreground_output
        
        logger.debug(f"Process: {process_running}, Activity: {activity_running}, Foreground: {in_foreground}")
        
        return process_running and activity_running
        
    except Exception as e:
        logger.error(f"Process check error: {str(e)}")
        return False

def close_roblox_enhanced(config=None):
    """Enhanced Roblox closing with multiple methods"""
    try:
        logger.info("Initiating enhanced Roblox shutdown...")
        
        # Method 1: Graceful close
        logger.debug("Attempting graceful close...")
        run_shell_command("input keyevent KEYCODE_HOME", platform_info=platform_info)
        time.sleep(2)
        
        # Method 2: Force stop
        logger.debug("Force stopping application...")
        run_shell_command(f"am force-stop {ROBLOX_PACKAGE}", platform_info=platform_info)
        time.sleep(2)
        
        # Method 3: Kill processes
        logger.debug("Killing processes...")
        kill_commands = [
            f"killall -9 {ROBLOX_PACKAGE}",
            f"pkill -9 -f {ROBLOX_PACKAGE}",
            f"pkill -9 roblox",
            f"pkill -9 RobloxPlayer"
        ]
        
        for cmd in kill_commands:
            run_shell_command(cmd, platform_info=platform_info)
            time.sleep(1)
        
        # Method 4: Platform-specific killing
        if platform_info and platform_info.get('special_commands'):
            logger.debug("Using platform-specific kill methods...")
            if platform_info['type'] == 'ugphone':
                run_shell_command("ugphone_kill_app com.roblox.client", platform_info=platform_info)
            elif platform_info['type'] == 'vsphone':
                run_shell_command("vsphone_kill_app com.roblox.client", platform_info=platform_info)
        
        # Verify closure
        time.sleep(3)
        if not is_roblox_running():
            logger.success("Roblox successfully closed")
            return True
        else:
            logger.warning("Roblox may still be running after close attempt")
            return False
        
    except Exception as e:
        logger.error(f"Enhanced close error: {e}")
        return False

def enhanced_tap(x, y, duration=100, safe_mode=True):
    """Enhanced tap function with safety features to prevent accidental clicks"""
    try:
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            logger.error(f"Invalid tap coordinates: x={x}, y={y}")
            return False
        
        # Safety check: prevent dangerous coordinates (like system UI areas)
        if safe_mode:
            # Avoid top status bar (y < 100) and bottom navigation (y > screen_height - 200)
            # This prevents accidental system interactions
            if y < 100:
                logger.warning(f"Blocking tap in status bar area: y={y}")
                return False
            if y > 2000:  # Typical screen height threshold
                logger.warning(f"Blocking tap in navigation area: y={y}")
                return False
            if x < 50 or x > 1030:  # Side edges
                logger.warning(f"Blocking tap near screen edges: x={x}")
                return False
        
        # Validate coordinates are reasonable
        if x < 0 or y < 0 or x > 2000 or y > 4000:
            logger.warning(f"Tap coordinates out of bounds: ({x}, {y})")
            return False
        
        logger.debug(f"Safe tap at ({x}, {y}) for {duration}ms")
        
        # Wait a moment to avoid rapid taps
        time.sleep(0.1)
        
        # Platform-specific tap methods
        if platform_info and platform_info.get('tap_method'):
            method = platform_info['tap_method']
            
            if method == 'ugphone_tap':
                result = run_shell_command(f"ugphone_tap {x} {y} {duration}", platform_info=platform_info)
            elif method == 'vsphone_tap':
                result = run_shell_command(f"vsphone_tap {x} {y} {duration}", platform_info=platform_info)
            else:
                result = run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
        else:
            result = run_shell_command(f"input tap {x} {y}", platform_info=platform_info)
        
        time.sleep(duration / 1000.0)  # Convert ms to seconds
        
        global last_ui_response_time
        last_ui_response_time = time.time()
        
        return True
        
    except Exception as e:
        logger.error(f"Enhanced tap error at ({x}, {y}): {e}")
        return False

def launch_roblox_game(config):
    """Enhanced game launching with better error handling"""
    try:
        if not config.get("game_id"):
            logger.error("No game ID configured")
            return False
        
        logger.info(f"Launching Roblox game: {config['game_id']}")
        
        # Close any existing Roblox instances
        close_roblox_enhanced(config)
        time.sleep(2)
        
        # Construct game URL
        if config.get("private_server"):
            game_url = f"https://www.roblox.com/games/{config['game_id']}?privateServerLinkCode={config['private_server']}"
        else:
            game_url = f"https://www.roblox.com/games/{config['game_id']}"
        
        encoded_url = urllib.parse.quote(game_url, safe=':/?&=')
        
        logger.debug(f"Game URL: {game_url}")
        
        # Launch attempts with retry logic
        max_attempts = config.get("launch_attempts", 3)
        
        for attempt in range(max_attempts):
            logger.info(f"Launch attempt {attempt + 1}/{max_attempts}")
            
            # Method 1: Direct intent
            intent_cmd = f"am start -a android.intent.action.VIEW -d '{encoded_url}'"
            result = run_shell_command(intent_cmd, platform_info=platform_info)
            
            # Wait for launch
            launch_wait = config.get("launch_delay", 180)
            logger.info(f"Waiting {launch_wait}s for game to load...")
            
            # Monitor launch progress
            for i in range(0, launch_wait, 10):
                time.sleep(10)
                if is_roblox_running():
                    logger.success(f"Roblox launched successfully (took {i + 10}s)")
                    # Additional time to load into game
                    time.sleep(30)
                    return True
                logger.debug(f"Launch progress: {i + 10}/{launch_wait}s")
            
            logger.warning(f"Launch attempt {attempt + 1} timed out")
            
            if attempt < max_attempts - 1:
                logger.info(f"Retrying in {config.get('retry_delay', 10)}s...")
                time.sleep(config.get('retry_delay', 10))
        
        logger.error(f"Failed to launch after {max_attempts} attempts")
        return False
        
    except Exception as e:
        logger.error(f"Game launch error: {e}")
        return False

# ======================
# HEARTBEAT SYSTEM
# ======================
def start_heartbeat():
    """Start heartbeat monitoring to ensure automation stays alive"""
    global heartbeat_thread
    
    def heartbeat_worker():
        while automation_running:
            try:
                timestamp = datetime.now().strftime("%H:%M:%S")
                logger.monitor(f"Heartbeat [{timestamp}] - Automation running (restarts: {restart_count})")
                
                # Check if monitoring thread is alive
                if monitoring_thread and not monitoring_thread.is_alive():
                    logger.warning("Monitoring thread died - automation may need restart")
                
                time.sleep(60)  # Heartbeat every minute
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                time.sleep(60)
    
    heartbeat_thread = threading.Thread(target=heartbeat_worker, daemon=True)
    heartbeat_thread.start()
    logger.info("Heartbeat system started")

# ======================
# MAIN AUTOMATION CONTROL
# ======================
def start_automation():
    """Enhanced automation startup"""
    global automation_running, monitoring_thread, platform_info
    
    try:
        # Initialize
        automation_running = True
        logger.success("=== Enhanced Roblox Automation Tool Started ===")
        
        # Detect platform
        detector = PlatformDetector()
        platform_info = detector.detect_platform()
        
        # Load configuration
        config = load_config()
        logger.verbose = config.get("verbose_logging", False)
        
        # Verify Roblox
        if not verify_roblox_installation():
            return False
        
        # Validate configuration
        if not config.get("game_id"):
            logger.error("No game ID configured - please set up configuration first")
            return False
        
        # Start heartbeat
        start_heartbeat()
        
        # Initial game launch
        logger.info("Starting initial game launch...")
        if not launch_roblox_game(config):
            logger.error("Failed initial game launch")
            return False
        
        # Start monitoring
        monitor = RobloxMonitor(config, platform_info)
        monitoring_thread = threading.Thread(target=monitor.start_monitoring, daemon=True)
        monitoring_thread.start()
        
        logger.success("Automation system fully initialized")
        logger.info("Monitoring Roblox - press Ctrl+C to stop")
        
        # Enhanced main loop with better status display
        try:
            while automation_running:
                time.sleep(5)  # Check every 5 seconds for better responsiveness
                
        except KeyboardInterrupt:
            logger.info("Automation stopped by user")
            
        finally:
            automation_running = False
            monitor.stop_monitoring()
            logger.success("🏁 Automation shutdown complete")
        
        return True
        
    except Exception as e:
        logger.error(f"Automation startup error: {e}")
        automation_running = False
        return False

# ======================
# SIGNAL HANDLING
# ======================
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global automation_running
    logger.info(f"Received signal {signum} - shutting down...")
    automation_running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ======================
# CLI INTERFACE
# ======================
def show_menu():
    """Display main menu"""
    print(f"\n{COLORS['HEADER']}{'='*50}")
    print("Enhanced Roblox Automation Tool")
    print(f"{'='*50}{COLORS['RESET']}")
    print(f"{COLORS['CYAN']}1.{COLORS['RESET']} Start Automation")
    print(f"{COLORS['CYAN']}2.{COLORS['RESET']} Configure Settings")
    print(f"{COLORS['CYAN']}3.{COLORS['RESET']} View Status")
    print(f"{COLORS['CYAN']}4.{COLORS['RESET']} View Logs")
    print(f"{COLORS['CYAN']}5.{COLORS['RESET']} Test Platform")
    print(f"{COLORS['CYAN']}6.{COLORS['RESET']} Exit")
    print(f"{COLORS['HEADER']}{'='*50}{COLORS['RESET']}")

def configure_settings():
    """Interactive configuration setup"""
    try:
        config = load_config()
        
        print(f"\n{COLORS['HEADER']}Configuration Setup{COLORS['RESET']}")
        
        # Game ID
        current_game = config.get("game_id", "Not set")
        print(f"Current Game ID: {COLORS['CYAN']}{current_game}{COLORS['RESET']}")
        game_id = input("Enter Game ID (or press Enter to keep current): ").strip()
        if game_id:
            config["game_id"] = game_id
        
        # Private Server
        current_private = config.get("private_server", "Not set")
        print(f"Current Private Server: {COLORS['CYAN']}{current_private}{COLORS['RESET']}")
        private_server = input("Enter Private Server Code (optional, press Enter to skip): ").strip()
        config["private_server"] = private_server
        
        # Monitoring settings
        print(f"\n{COLORS['INFO']}Monitoring Settings:{COLORS['RESET']}")
        
        monitoring_interval = input(f"Monitoring interval in seconds (current: {config['monitoring_interval']}): ").strip()
        if monitoring_interval.isdigit():
            config["monitoring_interval"] = max(5, int(monitoring_interval))
        
        max_failures = input(f"Max consecutive failures before restart (current: {config['max_consecutive_failures']}): ").strip()
        if max_failures.isdigit():
            config["max_consecutive_failures"] = max(1, int(max_failures))
        
        # Verbose logging
        verbose = input(f"Enable verbose logging? (current: {config['verbose_logging']}) [y/N]: ").strip().lower()
        config["verbose_logging"] = verbose.startswith('y')
        
        # Save configuration
        if save_config(config):
            logger.success("Configuration updated successfully")
        else:
            logger.error("Failed to save configuration")
            
    except Exception as e:
        logger.error(f"Configuration error: {e}")

def view_status():
    """View current system status"""
    print(f"\n{COLORS['HEADER']}System Status{COLORS['RESET']}")
    
    # Platform info
    if platform_info:
        print(f"Platform: {COLORS['SUCCESS']}{platform_info['name']}{COLORS['RESET']}")
        print(f"Root Access: {COLORS['SUCCESS' if platform_info['has_root'] else 'WARNING']}{platform_info['has_root']}{COLORS['RESET']}")
    
    # Roblox status
    roblox_running = is_roblox_running()
    print(f"Roblox Status: {COLORS['SUCCESS' if roblox_running else 'ERROR']}{'Running' if roblox_running else 'Not Running'}{COLORS['RESET']}")
    
    # Automation status
    print(f"Automation: {COLORS['SUCCESS' if automation_running else 'WARNING']}{'Active' if automation_running else 'Inactive'}{COLORS['RESET']}")
    
    # Restart count
    print(f"Restart Count: {COLORS['CYAN']}{restart_count}{COLORS['RESET']}")
    
    # Config summary
    config = load_config()
    print(f"Game ID: {COLORS['CYAN']}{config.get('game_id', 'Not set')}{COLORS['RESET']}")
    print(f"Monitoring Interval: {COLORS['CYAN']}{config.get('monitoring_interval', 'Unknown')}s{COLORS['RESET']}")

def view_logs():
    """View recent log entries"""
    try:
        print(f"\n{COLORS['HEADER']}Recent Logs (last 20 lines){COLORS['RESET']}")
        
        if os.path.exists(LOG_FILE):
            result = run_shell_command(f"tail -20 {LOG_FILE}", platform_info=platform_info)
            if result:
                print(result)
            else:
                print("No recent logs found")
        else:
            print("Log file not found")
            
    except Exception as e:
        logger.error(f"Error viewing logs: {e}")

def test_platform():
    """Test platform capabilities"""
    print(f"\n{COLORS['HEADER']}Platform Testing{COLORS['RESET']}")
    
    # Test platform detection
    detector = PlatformDetector()
    test_platform_info = detector.detect_platform()
    
    # Test shell commands
    print(f"\n{COLORS['INFO']}Testing shell commands...{COLORS['RESET']}")
    test_commands = [
        "echo 'Hello World'",
        "ps | head -5",
        "which su",
        f"pm list packages | grep {ROBLOX_PACKAGE}"
    ]
    
    for cmd in test_commands:
        print(f"Testing: {cmd}")
        result = run_shell_command(cmd, platform_info=test_platform_info)
        if result:
            print(f"  ✓ Success: {result[:50]}...")
        else:
            print(f"  ✗ Failed")
    
    # Test tap functionality
    print(f"\n{COLORS['INFO']}Testing tap functionality...{COLORS['RESET']}")
    if enhanced_tap(100, 100):
        print("  ✓ Tap test successful")
    else:
        print("  ✗ Tap test failed")

def main():
    """Main application entry point"""
    global platform_info
    
    try:
        # Initialize platform detection
        detector = PlatformDetector()
        platform_info = detector.detect_platform()
        
        # Initialize logger
        global logger
        logger = Logger(verbose=False)
        
        while True:
            show_menu()
            
            try:
                choice = input(f"\n{COLORS['CYAN']}Enter your choice (1-6): {COLORS['RESET']}").strip()
                
                if choice == '1':
                    start_automation()
                elif choice == '2':
                    configure_settings()
                elif choice == '3':
                    view_status()
                elif choice == '4':
                    view_logs()
                elif choice == '5':
                    test_platform()
                elif choice == '6':
                    logger.info("Exiting Enhanced Roblox Automation Tool")
                    break
                else:
                    print(f"{COLORS['WARNING']}Invalid choice. Please select 1-6.{COLORS['RESET']}")
                    
            except KeyboardInterrupt:
                print(f"\n{COLORS['WARNING']}Operation cancelled{COLORS['RESET']}")
                continue
                
    except Exception as e:
        logger.error(f"Main application error: {e}")
    finally:
        global automation_running
        automation_running = False

if __name__ == "__main__":
    main()
