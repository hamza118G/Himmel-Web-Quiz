@echo off
REM Check if Python is installed
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Installing Python...

    REM Download Python installer
    echo Downloading Python installer...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe' -OutFile 'python-installer.exe'"

    REM Install Python silently
    echo Installing Python...
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1

    REM Clean up the installer
    del python-installer.exe

    REM Verify Python installation
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo Python installation failed. Please install Python manually from https://www.python.org/
        pause
        exit /b
    )
    echo Python installed successfully.
)

REM Ensure pip is installed
python -m ensurepip >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to ensure pip installation.
    pause
    exit /b
)

REM Upgrade pip to avoid package installation issues
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to upgrade pip.
    pause
    exit /b
)

REM Install required Python packages
echo Installing required Python packages...
python -m pip install flask pandas flask-cors openpyxl >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to install required packages.
    pause
    exit /b
)

REM Run the Python scripts
cd Himmel
start cmd /k "python himmel.py"
start cmd /k "python exam_mode.py"
cd ..

cd "Practice Mode"
start cmd /k "python practice_mode.py"
cd ..

cd "Question Bank"
start cmd /k "python question_bank.py"
cd ..

timeout /t 7 >nul
start homepage.html
exit
