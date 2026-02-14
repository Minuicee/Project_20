@echo off
setlocal

:: -------------------------------
:: Activate virtual environment
:: -------------------------------
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate
) ELSE (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b
)

:: -------------------------------
:: Download requirements if missing
:: -------------------------------
if not exist "requirements\requirements.txt" (
    echo requirements.txt not found. Downloading...
    if not exist "requirements" mkdir requirements
    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/requirements/requirements.txt -OutFile requirements\requirements.txt"

    echo Installing required packages...
    pip install --upgrade pip
    pip install -r requirements\requirements.txt
)

:: -------------------------------
:: Ensure main.py exists
:: -------------------------------
set REPO_URL=https://raw.githubusercontent.com/Minuicee/Project_20/main/main.py
set LOCAL_FILE=main.py

if not exist "%LOCAL_FILE%" (
    echo main.py not found. Downloading from GitHub...
    powershell -Command "Invoke-WebRequest -Uri %REPO_URL% -OutFile %LOCAL_FILE%"
)

:: -------------------------------
:: Run the main script without terminal
:: -------------------------------
start "" pythonw "%LOCAL_FILE%"

