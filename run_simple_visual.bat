@echo off
echo Starting Simple Visual Human Body Avatar...
echo.
echo This will open the visual human body avatar in your browser.
echo.
echo If you see any errors, make sure you have Python and Streamlit installed.
echo.
pause
python -m streamlit run simple_visual_body.py --server.port 8511
pause
