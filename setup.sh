#!/bin/bash
if [ -e "/data/data/com.termux/files/home/storage" ]; then
    rm -rf /data/data/com.termux/files/home/storage
fi
termux-setup-storage
yes | pkg update
. <(curl https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/termux-change-repo.sh)
yes | pkg upgrade
yes | pkg install python android-tools python-pip
pip install requests psutil prettytable pure-python-adb
curl -Ls "https://raw.githubusercontent.com/Day326/setup-termux/refs/heads/main/Rejoiner.py" -o /sdcard/Download/Rejoiner.py