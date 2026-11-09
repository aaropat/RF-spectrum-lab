@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo The app has not been installed yet.
    echo Double-click setup_windows.bat first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo Streamlit closed with an error. See the messages above.
    pause
    exit /b 1
)
exit /b 0
