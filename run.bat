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
)

:: -------------------------------
:: Install / upgrade requirements
:: -------------------------------
echo Installing required packages...
pip install --upgrade pip
pip install -r requirements\requirements.txt

:: -------------------------------
:: Check for new main.py from GitHub
:: -------------------------------
set REPO_URL=https://raw.githubusercontent.com/Minuicee/Project_20/main/main.py
set LOCAL_FILE=main.py

powershell -Command "Invoke-WebRequest -Uri %REPO_URL% -OutFile temp_main.py"

:: Compare temp with local
fc temp_main.py %LOCAL_FILE% >nul
IF %ERRORLEVEL% NEQ 0 (
    echo New version detected. Updating main.py...
    move /Y temp_main.py %LOCAL_FILE%
) ELSE (
    del temp_main.py
)

:: -------------------------------
:: Run the main script
:: -------------------------------
python %LOCAL_FILE%

pause
