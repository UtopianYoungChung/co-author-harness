@echo off
set PYTHONUTF8=1
set PY=C:\Users\young\AppData\Local\Python\pythoncore-3.14-64\python.exe
set HARNESS=B:\Agents\co-author-harness

echo ====================================================
echo === skill-check =====================================
echo ====================================================
"%PY%" "%HARNESS%\scripts\skill-check.py"
echo.
echo ====================================================
echo === version-check ===================================
echo ====================================================
"%PY%" "%HARNESS%\scripts\version-check.py"
echo.
echo ====================================================
echo === catalog-check ===================================
echo ====================================================
"%PY%" "%HARNESS%\scripts\catalog-check.py"
echo.
echo ====================================================
echo === path-hygiene-check ==============================
echo ====================================================
"%PY%" "%HARNESS%\scripts\path-hygiene-check.py"
echo.
echo === done ============================================
