@echo off
REM AEON developmental self-model: one-click hackathon demo (Windows).
REM Needs Python 3.10+ on PATH. No packages, no API keys, no internet.
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
echo Running tests...
%PY% -m unittest tests.test_aeon_develop || (echo Tests failed & pause & exit /b 1)
echo Opening dashboard at http://127.0.0.1:8770  (click "Guided demo")
start "" http://127.0.0.1:8770
%PY% -m aeon_develop serve --port 8770 --tps 20
