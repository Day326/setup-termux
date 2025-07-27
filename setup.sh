#!/bin/bash
if [ -e "/data/data/com.termux/files/home/storage" ]; then
    rm -rf /data/data/com.termux/files/home/storage
fi
termux-setup-storage

yes | pkg update && pkg upgrade

yes | pkg install android-tools

yes | pkg install python python-pip
pip install --upgrade pip
pip install requests psutil prettytable pure-python-adb

adb kill-server
adb start-server

curl -Ls "https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/Rejoiner.py" -o /sdcard/Download/Rejoiner.py

echo "Setup complete. Run 'cd /sdcard/Download && python Rejoiner.py' to start."