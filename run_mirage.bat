@echo off
title MIRAGE Launcher
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_EXE="
set "PYTHONW_EXE="

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
    set "PYTHONW_EXE=%SCRIPT_DIR%.venv\Scripts\pythonw.exe"
) else if exist "%SCRIPT_DIR%venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
    set "PYTHONW_EXE=%SCRIPT_DIR%venv\Scripts\pythonw.exe"
) else (
    for %%P in (python.exe) do set "PYTHON_EXE=%%~$PATH:P"
    for %%P in (pythonw.exe) do set "PYTHONW_EXE=%%~$PATH:P"
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] No se encontro Python.
    echo Instala Python o crea un entorno virtual en ".venv" o "venv".
    pause
    exit /b 1
)

:START
cls
echo ===============================
echo      MIRAGE Launcher
echo ===============================
echo.
echo Python: "%PYTHON_EXE%"
echo.

if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" "%SCRIPT_DIR%src\gui.py"
) else (
    echo [INFO] pythonw.exe no encontrado. Se lanzara con python.exe.
    start "" "%PYTHON_EXE%" "%SCRIPT_DIR%src\gui.py"
)

echo.
echo MIRAGE fue lanzado.
echo ===============================
echo.
choice /c YN /m "Deseas lanzar otra instancia?"

if errorlevel 1 if not errorlevel 2 goto START

:END
echo.
echo Cerrando launcher...
timeout /t 2 >nul
endlocal
exit /b 0
