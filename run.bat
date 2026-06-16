@echo off
REM PJ-AG2 复现实验脚本 (Windows)
REM 用法: 双击 run.bat 或在终端中运行 run.bat

echo ==========================================
echo   PJ-AG2: 选择性长期记忆对话 Agent
echo   复现实验
echo ==========================================
echo.

echo [1/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Generating test cases...
python data/generate_tests.py
if errorlevel 1 (
    echo [ERROR] Failed to generate test cases.
    pause
    exit /b 1
)

echo [3/3] Running evaluation (5 modes x 38 tests)...
python main.py
if errorlevel 1 (
    echo [ERROR] Evaluation failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   Done!
echo   Results: results\comparison_table.md
echo   Results: results\eval_summary.json
echo ==========================================
pause
