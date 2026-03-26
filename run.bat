@echo off
setlocal

set BASE=https://raw.githubusercontent.com/Minuicee/Project_20/main

:: -------------------------------
:: Activate virtual environment
:: -------------------------------
if not exist "venv\Scripts\activate.bat" (
    echo Virtual environment not found. Please run install.bat first.
    pause
    exit /b
)
call venv\Scripts\activate

:: -------------------------------
:: Install requirements if missing
:: -------------------------------
if not exist "requirements\requirements.txt" (
    echo requirements.txt not found. Downloading...
    if not exist "requirements" mkdir requirements
    powershell -Command "Invoke-WebRequest -Uri %BASE%/requirements/requirements.txt -OutFile requirements\requirements.txt"
    echo Installing required packages...
    pip install --upgrade pip
    pip install -r requirements\requirements.txt
)

:: -------------------------------
:: Download main.py if missing
:: -------------------------------
if not exist "main.py" (
    echo main.py not found. Downloading...
    powershell -Command "Invoke-WebRequest -Uri %BASE%/main.py -OutFile main.py"
)

:: -------------------------------
:: Run without terminal window
:: -------------------------------
if exist "venv\Scripts\pythonw.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py
) else (
    echo pythonw.exe not found in venv.
    pause
)