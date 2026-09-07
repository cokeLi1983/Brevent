@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || where python >nul 2>nul || (
  echo Python 3.10 or later is required. Install it from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
echo Installation check completed.
echo Start the application by double-clicking run_windows.bat.
pause
endlocal
