@echo off
REM Delete previous build and dist folders, and .spec file if they exist
rmdir /s /q build
rmdir /s /q dist
del /q *.spec

REM Run PyInstaller to create the executable
pyinstaller --onefile --icon=app_icon.ico --add-data "tesseract;./tesseract" --add-data "app_icon.ico;."  --version-file=version.txt --noconsole so2_autoroll.py

REM Copy README.txt to dist folder
copy README.txt dist\README.txt

REM Change to the dist directory
cd dist

REM Check if the first parameter is "zip"
if "%1"=="zip" (
    REM Compress all files in the dist directory into SoD2_AutoReroll_Mod.zip
    powershell Compress-Archive -Path * -DestinationPath SoD2_AutoReroll_Mod.zip

    REM Delete all files in the dist directory except mod.zip
    for %%f in (*) do (
        if not "%%f" == "SoD2_AutoReroll_Mod.zip" del "%%f"
    )
) else (
    REM Move the executable to the desktop
    move /y so2_autoroll.exe "%USERPROFILE%\Desktop\so2_autoroll.exe"
)

REM Change back to the original directory
cd ..
