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
pkg install python python-pip curl -y
pip install --upgrade pip

pip install requests psutil prettytable

curl -Ls "https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/Rejoiner.py" -o /sdcard/Download/Rejoiner.py
su -c "chmod 644 /sdcard/Download/Rejoiner.py"

if ! su -c "pm list packages com.roblox.client" | grep -q "com.roblox.client"; then
    echo "Warning: Roblox is not installed. Install from Google Play or a trusted APK (e.g., v2.681.805 from APKMirror)."
fi

echo "Setup complete. Run 'cd /sdcard/Download && python Rejoiner.py' to start."
echo "Ensure Roblox is installed and device is rooted."