@echo off
setlocal
rem Keep stdin intact; Codex sends the event JSON through it.
if defined COAUTHOR_HOOK_PYTHON goto explicit
if defined CLAUDE_PLUGIN_PYTHON goto legacy
py -3 -c "import sys" >nul 2>&1
if errorlevel 1 goto unavailable
py -3 -B "%~dp0codex_gate.py"
if errorlevel 1 goto failed
exit /b 0
:explicit
"%COAUTHOR_HOOK_PYTHON%" -B "%~dp0codex_gate.py"
if errorlevel 1 goto failed
exit /b 0
:legacy
"%CLAUDE_PLUGIN_PYTHON%" -B "%~dp0codex_gate.py"
if errorlevel 1 goto failed
exit /b 0
:failed
echo HOOK-INTERPRETER: harness hook failed to execute >&2
exit /b 2
:unavailable
echo HOOK-INTERPRETER: set COAUTHOR_HOOK_PYTHON to a Python 3 interpreter with harness dependencies >&2
exit /b 2
