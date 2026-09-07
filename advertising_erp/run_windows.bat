@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul && (py -3 app.py & goto :end)
where python >nul 2>nul && (python app.py & goto :end)
echo Python 3 was not found. Please install Python 3.10+ and select Add Python to PATH.
pause
:end
endlocal
