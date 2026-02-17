@echo off
REM Quick install - run this first if pip is slow
cd /d c:\Users\hp\Desktop\AdpativHealth
call .venv\Scripts\activate.bat

echo Installing core packages...
pip install --upgrade pip wheel setuptools

echo Installing web framework...
pip install fastapi uvicorn[standard] python-multipart

echo Installing database...
pip install sqlalchemy

echo Installing validation...
pip install pydantic pydantic-settings email-validator

echo Installing auth...
pip install python-jose[cryptography] passlib[bcrypt] bcrypt cryptography python-dotenv

echo Installing ML (this takes longest)...
pip install numpy scikit-learn joblib

echo.
echo ========================================
echo   Installation complete! Starting server...
echo ========================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
pause
