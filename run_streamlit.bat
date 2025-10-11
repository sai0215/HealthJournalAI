@echo off
REM Quick launcher for Streamlit Health Assistant (Windows)

echo.
echo ============================================
echo    🏥 Health Assistant Launcher
echo ============================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if exist "venv_mac\Scripts\activate.bat" (
    echo ✓ Activating virtual environment...
    call venv_mac\Scripts\activate.bat
) else (
    echo ❌ Virtual environment not found!
    echo Please run: python -m venv venv_mac
    echo Then: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Check if streamlit is installed
streamlit --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Streamlit not found!
    echo Installing required packages...
    pip install -r requirements.txt
)

echo ✓ Starting Streamlit app...
echo.
echo 📱 The app will open in your browser at: http://localhost:8501
echo 🛑 To stop the app, press Ctrl+C
echo.
echo ============================================
echo.

REM Run streamlit
streamlit run streamlit_app.py

pause

