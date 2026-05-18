@echo off
chcp 65001 >nul
setlocal

cd /d "%~dp0"
uv run python run_search_today_all_platforms.py %*
exit /b %ERRORLEVEL%
