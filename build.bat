@echo off
REM ==========================================================
REM  Operatie Bureaucratie - bouwt dist\OperatieBureaucratie.exe
REM  Vereist: Python 3.10+ (64-bit) op Windows 10/11
REM ==========================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Virtuele omgeving aanmaken...
    py -3 -m venv .venv || python -m venv .venv || goto :error
)
set PY=.venv\Scripts\python.exe

echo [2/4] Afhankelijkheden installeren...
%PY% -m pip install --quiet --upgrade pip
%PY% -m pip install --quiet -r requirements.txt || goto :error

echo [3/4] Tests uitvoeren...
%PY% -m unittest discover -s tests || goto :error

echo [4/4] EXE bouwen met PyInstaller...
%PY% -m PyInstaller --noconfirm --clean OperatieBureaucratie.spec || goto :error

echo.
echo Klaar! Het spel staat in: dist\OperatieBureaucratie.exe
exit /b 0

:error
echo.
echo Er is iets misgegaan. Uw aanvraag is afgewezen.
exit /b 1
