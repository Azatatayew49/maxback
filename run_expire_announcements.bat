@echo off
REM This script runs the expire_announcements management command
REM Run this daily (e.g., using Windows Task Scheduler) to automatically mark expired announcements

cd /d "%~dp0"
python manage.py expire_announcements

REM Optional: Add timestamp to log
echo Expire announcements run at %date% %time% >> expire_log.txt
