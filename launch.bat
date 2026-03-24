@echo off
setlocal enabledelayedexpansion
REM Ensure we are in the script directory
cd /d "%~dp0"

echo [ani-cli-fr] Windows Launcher starting...

REM --- Detect Python ---
set "PYTHON_CMD="
set "FALLBACK_PYTHON="

REM Search in PATH using a loop without blocks
for /f "delims=" %%i in ('where.exe python python3 2^>nul') do call :check_python "%%i"

REM Search in common AppData paths if still not found
if defined PYTHON_CMD goto :python_check_done
if not exist "%LOCALAPPDATA%\Python\" goto :python_check_done
for /f "delims=" %%i in ('where.exe /r "%LOCALAPPDATA%\Python" python.exe 2^>nul') do call :check_python "%%i"
:python_check_done

REM Use fallback if no bs4-ready python was found
if defined PYTHON_CMD goto :python_set
if not defined FALLBACK_PYTHON goto :python_set
set "PYTHON_CMD=%FALLBACK_PYTHON%"
:python_set

if defined PYTHON_CMD goto :python_ok
echo [ERROR] Python not found. Please install Python 3 and add it to your PATH.
echo Tip: Disable "App execution aliases" for Python in Windows Settings if you see Store errors.
pause
exit /b 1
:python_ok

REM --- Check for BeautifulSoup4 ---
"!PYTHON_CMD!" -c "import bs4" >nul 2>&1
if not errorlevel 1 goto :bs4_ok
echo [INFO] Installing missing dependency: beautifulsoup4...
"!PYTHON_CMD!" -m pip install beautifulsoup4
if not errorlevel 1 goto :bs4_ok
echo [ERROR] Failed to install beautifulsoup4. Please install it manually: pip install beautifulsoup4
pause
exit /b 1
:bs4_ok

REM --- Detect Git Bash ---
set "GIB_BASH="
if exist "C:\Program Files\Git\bin\bash.exe" set "GIB_BASH=C:\Program Files\Git\bin\bash.exe"
if defined GIB_BASH goto :bash_found
if exist "C:\Program Files (x86)\Git\bin\bash.exe" set "GIB_BASH=C:\Program Files (x86)\Git\bin\bash.exe"
if defined GIB_BASH goto :bash_found
if exist "%USERPROFILE%\AppData\Local\Programs\Git\bin\bash.exe" set "GIB_BASH=%USERPROFILE%\AppData\Local\Programs\Git\bin\bash.exe"
:bash_found

if not defined GIB_BASH for /f "delims=" %%i in ('where.exe bash 2^>nul') do set "GIB_BASH=%%i"

if defined GIB_BASH goto :bash_ok
echo [ERROR] Git Bash (bash.exe) not found.
echo Please install Git for Windows or ensure it is in your PATH.
pause
exit /b 1
:bash_ok

REM --- Launch ani-cli ---
echo [INFO] Using Python: !PYTHON_CMD!
echo [INFO] Launching ani-cli...
"!GIB_BASH!" ./ani-cli %*
set "EXIT_CODE=!errorlevel!"
if !EXIT_CODE! neq 0 echo [INFO] Script exited with code !EXIT_CODE!.
pause
exit /b

REM --- Subroutines ---

:check_python
REM Test if it's a working python
"%~1" -c "import sys; sys.exit(0)" >nul 2>&1
if errorlevel 1 exit /b

REM Set as fallback if it's the first working one
if not defined FALLBACK_PYTHON set "FALLBACK_PYTHON=%~1"

REM Check if it already has bs4
"%~1" -c "import bs4" >nul 2>&1
if errorlevel 1 exit /b
if not defined PYTHON_CMD set "PYTHON_CMD=%~1"
exit /b
