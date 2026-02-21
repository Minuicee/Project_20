@echo off
setlocal

echo =============================
echo SRS AI Installer
echo =============================
echo.

:: ---------------------------------
:: Always download global data files
:: ---------------------------------
if not exist "data" mkdir data

echo Downloading core data files...

powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/data/feature_data.csv -OutFile data/feature_data.csv"
powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/data/reward_data.csv -OutFile data/reward_data.csv"

:: ---------------------------------
:: Ask user for set name
:: ---------------------------------
echo.
echo Enter set name (e.g. template)
echo Leave empty to use template.
echo.

set /p SET_NAME=Set name: 

if "%SET_NAME%"=="" set SET_NAME=template

:: ---------------------------------
:: Prepare local directory
:: ---------------------------------
if not exist "sets" mkdir sets
if not exist "sets\%SET_NAME%" mkdir sets\%SET_NAME%

echo Installing set: %SET_NAME%

:: ---------------------------------
:: Try downloading selected set
:: ---------------------------------
powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/%SET_NAME%/language1.csv -OutFile sets/%SET_NAME%/language1.csv -ErrorAction SilentlyContinue"
powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/%SET_NAME%/language2.csv -OutFile sets/%SET_NAME%/language2.csv -ErrorAction SilentlyContinue"
powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/%SET_NAME%/data/l1_data.csv -OutFile sets/%SET_NAME%/data/l1_data.csv -ErrorAction SilentlyContinue"
powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/%SET_NAME%/data/l2_data.csv -OutFile sets/%SET_NAME%/data/l2_data.csv -ErrorAction SilentlyContinue"

if exist "sets\main\language1.csv" (
    echo Set installed successfully.
) else (
    echo Invalid set name. Installing template instead...

    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/template/language1.csv -OutFile sets/template/language1.csv"
    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/template/language2.csv -OutFile sets/template/language2.csv"
    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/template/data/l1_data.csv -OutFile sets/template/data/l1_data.csv"
    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/sets/template/data/l2_data.csv -OutFile sets/template/data/l2_data.csv"

)



echo set installed.

:: -------------------------------
:: Check if Python is installed
:: -------------------------------
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed.
    pause
    exit /b
)

:: -------------------------------
:: Create / activate virtual environment
:: -------------------------------
if not exist "venv" (
    python -m venv venv
)

call venv\Scripts\activate

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

:: Download new file to temp
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
:: Download run_main.bat if missing
:: -------------------------------
if not exist "run.bat" (
    echo run.bat not found. Downloading...
    powershell -Command "Invoke-WebRequest -Uri https://raw.githubusercontent.com/Minuicee/Project_20/main/run.bat -OutFile run.bat"
) ELSE (
    echo run.bat already exists.
)


pause
