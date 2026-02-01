@echo off
setlocal

set TOOL_NAME=AHKDumper
set ENTRY_SCRIPT=dumper.py
set INSTALL_DIR=%~dp0
set INSTALL_DIR=%INSTALL_DIR:~0,-1%

echo.
echo ============================================
echo            %TOOL_NAME% Installer
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Install Python 3 and try again.
    pause
    exit /b 1
)

echo Installing required Python libraries...
python -m pip install --upgrade pip >nul
python -m pip install -r assets\requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
set /p ADDPATH=Do you want to add %TOOL_NAME% to SYSTEM PATH? (Y/N): 

if /I "%ADDPATH%"=="Y" (
    if not exist "%INSTALL_DIR%\add2path.ps1" (
        echo [ERROR] add2path.ps1 not found.
        pause
        exit /b 1
    )

    echo.
    echo Requesting administrator privileges...
    powershell -Command ^
      "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%INSTALL_DIR%\add2path.ps1\"' -Verb RunAs"
)

cls
echo.
echo ============================================
echo What this tool does:
echo --------------------------------------------
echo - Extracts strings from compiled AutoHotkey EXEs
echo - Dumps raw strings for manual reconstruction
echo - Supports offsets, grouping, GUI-only mode
echo.
echo NOTE:
echo This does NOT fully decompile scripts.
echo The first thousands of lines may be junk —
echo this is expected AHK runtime data.
echo.
echo Developed by %AUTHOR%
echo ============================================
echo.
echo If you added to PATH, open a NEW terminal to use:
echo   dumper --help
echo.
pause
cls

python "%INSTALL_DIR%\%ENTRY_SCRIPT%" --help
pause