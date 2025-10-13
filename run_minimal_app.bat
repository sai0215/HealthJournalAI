@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
streamlit run streamlit_app_minimal.py --server.port 8508
pause
