@echo off
echo Building the application...
pyinstaller --noconfirm --onedir --windowed --name "民事立案文书助手" --clean "main.py"
echo Build complete. Check the 'dist' folder.
pause
