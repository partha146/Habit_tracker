@echo off
echo Starting Habit Tracker...
python "%~dp0habit_tracker.py"
if errorlevel 1 (
    echo.
    echo Error! Installing dependencies first...
    pip install matplotlib pillow
    python "%~dp0habit_tracker.py"
)
pause
