@echo off
setlocal
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --name "广告ERP" app.py
if errorlevel 1 (
  echo Build failed. Install PyInstaller first: python -m pip install pyinstaller
  pause
  exit /b 1
)
echo Build complete: dist\广告ERP\广告ERP.exe
endlocal
