@echo off
echo Creating virtual environment...
python -m venv venv

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete!
echo To activate the virtual environment, run: venv\Scripts\activate.bat
echo To run the backend, use: run_backend.bat
pause
