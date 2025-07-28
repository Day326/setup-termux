#!/bin/bash
echo "Setting up Koala Hub Auto-Rejoin environment..."

MEMORY=$(free -m | awk '/Mem:/ {print $2}')
if [ "$MEMORY" -lt 512 ]; then
    echo "Warning: Less than 512MB memory available. This may cause crashes. Free up memory and retry."
    exit 1
fi

if [ -e "/data/data/com.termux/files/home/storage" ]; then
    rm -rf /data/data/com.termux/files/home/storage
fi
termux-setup-storage

yes | pkg update
. <(curl https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/termux-change-repo.sh)
yes | pkg upgrade

yes | pkg install android-tools
yes | pkg install python python-pip
pip install --upgrade pip
pip install requests psutil prettytable pure-python-adb

adb kill-server
sleep 2
adb start-server
if ! adb devices | grep -q device; then
    echo "Error: ADB not connected. Ensure USB debugging is enabled and device is connected."
    exit 1
fi

curl -Ls "https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/Rejoiner.py" -o /sdcard/Download/Rejoiner.py

echo "Setup complete. Run 'cd /sdcard/Download && python Rejoiner.py' to start."
echo "Ensure USB debugging is enabled on your device or cloud phone."
echo "Root is required for the auto-rejoin feature."