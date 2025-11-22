@echo off
title Steamtrades bumper

rem Перейти в папку с батником и скриптом
cd /d "%~dp0"

python main.py

echo.
echo Нажмите любую клавишу для выхода...
pause >nul


