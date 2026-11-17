@echo off
echo ============================================
echo  WoundWatch - ML Model Setup
echo ============================================
echo.

REM Navigate to ML folder
cd /d "%~dp0"

echo [1/4] Installing ML dependencies...
pip install tensorflow pillow numpy datasets huggingface_hub --quiet
echo Done!
echo.

echo [2/4] Downloading wound dataset...
python download_dataset.py
echo.

echo [3/4] Training ML model (this takes 5-10 minutes)...
python train_model.py
echo.

echo [4/4] Copying model to backend...
set BACKEND=..\backend
if exist "%BACKEND%" (
    copy /Y wound_model.h5 "%BACKEND%\wound_model.h5"
    copy /Y wound_labels.json "%BACKEND%\wound_labels.json"
    copy /Y wound_analyzer_ml.py "%BACKEND%\wound_analyzer.py"
    echo Model files copied to backend!
) else (
    echo WARNING: backend folder not found at %BACKEND%
    echo Manually copy these files to your backend folder:
    echo   - wound_model.h5
    echo   - wound_labels.json
    echo   - wound_analyzer_ml.py (rename to wound_analyzer.py)
)

echo.
echo ============================================
echo  SETUP COMPLETE!
echo ============================================
echo.
echo Restart your backend server to use the ML model.
echo The backend will automatically use ML if model exists,
echo or fall back to OpenCV if not.
echo.
pause
