@echo off
setlocal EnableDelayedExpansion

:main_menu
cls
echo.
echo ====================================
echo      BookForge Studio - Windows     
echo       (Please use Python 3.10)
echo ====================================
echo.
echo [Setup/Installation Commands]
echo 1) Install dependencies (pip)
echo.
echo [Production/Server Commands]
echo 2) Start main server
echo 3) Start VM server (Runpod/similar)
echo 4) Start Chatterbox service
echo 5) Start DIA service  
echo 6) Start Higgs service
echo 7) Start VibeVoice service
echo 8) Start VibeVoice 7B (large) service
echo.
echo [Developer Commands]
echo 9) Developer menu
echo.
echo 10) Exit
echo.
set /p choice="Enter your choice (1-10): "

if "%choice%"=="1" goto install_deps
if "%choice%"=="2" goto main_server
if "%choice%"=="3" goto vm_server
if "%choice%"=="4" goto chatterbox_service
if "%choice%"=="5" goto dia_service
if "%choice%"=="6" goto higgs_service
if "%choice%"=="7" goto vibevoice_service
if "%choice%"=="8" goto vibevoice_large_service
if "%choice%"=="9" goto dev_menu
if "%choice%"=="10" goto exit
goto invalid_choice

:install_deps
echo.
echo Installing Python requirements...
pip install -r requirements.txt
echo.
echo Installing FFmpeg...
echo Checking if FFmpeg is already installed...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo FFmpeg not found. Please install FFmpeg manually:
    echo 1. Download from https://ffmpeg.org/download.html#build-windows
    echo 2. Extract to a folder like C:\ffmpeg
    echo 3. Add C:\ffmpeg\bin to your PATH environment variable
    echo 4. Restart this script after installation
    echo.
    pause
) else (
    echo FFmpeg is already installed and available.
)
echo.
echo Installation complete!
pause
goto main_menu

:main_server
echo.
echo Starting main server...
python app.py
pause
goto main_menu

:vm_server
echo.
echo Starting VM server...
python app.py --host 0.0.0.0 --port 8000
pause
goto main_menu

:chatterbox_service
echo.
echo Starting Chatterbox service...
python run_model.py chatterbox
pause
goto main_menu

:dia_service
echo.
echo Starting DIA service...
python run_model.py dia
pause
goto main_menu

:higgs_service
echo.
echo Starting Higgs service...
python run_model.py higgs
pause
goto main_menu

:vibevoice_service
echo.
echo Starting VibeVoice service...
python run_model.py vibevoice
pause
goto main_menu

:vibevoice_large_service
echo.
echo Starting VibeVoice 7B (large) service...
python run_model.py vibevoice --large
pause
goto main_menu

:dev_menu
cls
echo.
echo =====================================
echo      Developer Commands
echo =====================================
echo.
echo 1) Local development server (hot reload)
echo 2) Local testing UI (no GPU)
echo 3) Mock service
echo 4) Back to main menu
echo.
set /p dev_choice="Enter your choice (1-4): "

if "%dev_choice%"=="1" goto local_dev
if "%dev_choice%"=="2" goto local_test_ui
if "%dev_choice%"=="3" goto mock_service
if "%dev_choice%"=="4" goto main_menu
goto invalid_dev_choice

:local_dev
echo.
echo Starting local development server...
python app.py --dev
pause
goto dev_menu

:local_test_ui
echo.
echo Starting local testing UI...
set TESTING_UI=true
python app.py --dev
pause
goto dev_menu

:mock_service
echo.
echo Starting mock service...
python run_model.py mock
pause
goto dev_menu

:invalid_choice
echo.
echo Invalid choice. Please enter a number between 1-10.
pause
goto main_menu

:invalid_dev_choice
echo.
echo Invalid choice. Please enter a number between 1-4.
pause
goto dev_menu

:exit
echo.
echo Goodbye!
exit /b 0