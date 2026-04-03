@echo off
title Thermal Sentinel — Setup
echo.
echo  ============================================
echo   Thermal Sentinel — One-Time Setup
echo  ============================================
echo.
echo  Step 1: Upgrading pip...
python -m pip install --upgrade pip setuptools wheel --quiet
echo  Done.
echo.
echo  Step 2: Installing API dependencies...
python -m pip install --prefer-binary -r requirements.txt --quiet
echo  Done.
echo.
echo  Step 3: Installing detector dependencies...
echo  (This downloads PyTorch + YOLO — takes 5-10 mins)
python -m pip install --prefer-binary -r requirements-local.txt --quiet
echo  Done.
echo.
echo  ============================================
echo   Setup complete! Now run: start_all.bat
echo  ============================================
echo.
pause
