@echo off
chcp 65001 >nul
python -m pip install --upgrade pip
pip install -r requirements.txt
pause
