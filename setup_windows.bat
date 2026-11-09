@echo off
setlocal
cd /d "%~dp0"
echo ==================================================
echo RF Spectrum Lab - Windows setup
echo ==================================================
where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" was not found.
    echo Please install Python 3.11 or newer from https://www.python.org/downloads/
    echo and enable the Python launcher during installation.
    pause
    exit /b 1
)
py -m venv .venv
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Installation finished. Next, double-click run_windows.bat
pause
exit /b 0
:error
echo.
echo Installation failed. Check the messages above and your internet connection.
pause
exit /b 1
