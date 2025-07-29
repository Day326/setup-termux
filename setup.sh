#!/bin/bash
echo "Setting up Koala Hub Auto-Rejoin environment..."

MEMORY=$(free -m | awk '/Mem:/ {print $2}')
if [ "$MEMORY" -lt 512 ]; then
    echo "Error: Less than 512MB memory available. Free up memory and retry."
    exit 1
fi

if ! su -c "echo test" | grep -q "test"; then
    echo "Error: Root access required. Install Magisk or equivalent and retry."
    exit 1
fi

if [ -e "/data/data/com.termux/files/home/storage" ]; then
    rm -rf /data/data/com.termux/files/home/storage
fi
termux-setup-storage
sleep 2

pkg update -y
pkg install python3 python3-pip curl -y
pip3 install --upgrade pip

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
if [[ ! "$PYTHON_VERSION" =~ ^3\.[6-9] ]]; then
    echo "Error: Python 3.6 or higher required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "Python version: $PYTHON_VERSION"

pip3 install requests psutil prettytable

python3 -c "import urllib.parse" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: urllib.parse module not found. Reinstall Python3."
    pkg uninstall python3 -y
    pkg install python3 -y
    exit 1
fi
echo "urllib.parse module verified"

curl -Ls "https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/Rejoiner.py" -o /sdcard/Download/Rejoiner.py
su -c "chmod 644 /sdcard/Download/Rejoiner.py"

if ! su -c "pm list packages com.roblox.client" | grep -q "com.roblox.client"; then
    echo "Warning: Roblox is not installed."
fi

echo "Setup complete. Run 'cd /sdcard/Download && python3 Rejoiner.py' to start."
echo "Ensure Roblox is installed and device is rooted."
echo "To update Rejoiner.py, edit in VSCode and replace /sdcard/Download/Rejoiner.py."