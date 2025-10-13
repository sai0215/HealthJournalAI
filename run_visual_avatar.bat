@echo off
echo Starting Visual Human Body Avatar...
echo.
echo This will open the visual human body avatar in your browser.
echo.
echo If you see any errors, make sure you have Python and Streamlit installed.
echo.
pause
python -m streamlit run visual_body_avatar.py --server.port 8510
pause
