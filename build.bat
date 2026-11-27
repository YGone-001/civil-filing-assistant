@echo off
setlocal
pushd "%~dp0" || exit /b 1
echo Building the application...
python -m PyInstaller --noconfirm --onedir --windowed --name "民事立案文书助手" --icon "assets\app_icon.ico" --add-data "assets\app_icon.png;assets" --clean %* "main.py"
set "CFA_BUILD_EXIT=%ERRORLEVEL%"
popd
if not "%CFA_BUILD_EXIT%"=="0" (
    echo Build failed with exit code %CFA_BUILD_EXIT%.
    exit /b %CFA_BUILD_EXIT%
)
echo Build complete.
