@echo off
REM Delete previous build and dist folders, and .spec file if they exist
rmdir /s /q build
rmdir /s /q dist
del /q *.spec

REM Run PyInstaller to create the executable
pyinstaller --onefile --console so2_autoroll.py

REM Copy config.txt and Traits_Power_Scores.csv to the dist folder
copy config.txt dist\config.txt
copy README.md dist\README.md
copy Traits_Power_Scores.csv dist\Traits_Power_Scores.csv

REM Pause to keep the console open after completion
pause
