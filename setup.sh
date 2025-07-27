#!/bin/bash
if [ -e "/data/data/com.termux/files/home/storage" ]; then
    rm -rf /data/data/com.termux/files/home/storage
fi
termux-setup-storage
yes | pkg update
. <(curl https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/termux-change-repo.sh)
yes | pkg upgrade && yes | pkg i python && yes | pkg i android-tools && yes | pkg i python-pip && pip install requests psutil pure-python-adb
curl -Ls "https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/Rejoiner.py" -o /sdcard/Download/Rejoiner.py
echo "Setup complete. Run 'cd /sdcard/Download && python Rejoiner.py' to start Koala Hub Auto-Rejoin."