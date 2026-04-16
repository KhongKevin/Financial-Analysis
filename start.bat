@echo off
echo =========================================
echo Starting Finance Dashboard Environment
echo =========================================

:: Start backend in a new command window
echo [API] Starting Flask backend...
start "Backend (Flask)" cmd /k "if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) & python app.py"

:: Start frontend in a new command window
echo [UI] Starting React frontend...
start "Frontend (React)" cmd /k "cd frontend & npm run dev"

echo.
echo =========================================
echo Both services have been launched!
echo Backend API : http://localhost:5000
echo Frontend UI : http://localhost:3000
echo =========================================
echo.
pause
