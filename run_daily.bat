@echo off
REM Runs the job finder; schedule this with Windows Task Scheduler for a daily refresh.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python run.py %* >> output\run.log 2>&1
