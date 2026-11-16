@echo off
rem ---------------------------------------------------------------------------
rem  The Models Resource / VG Resource downloader - Windows
rem
rem  Il sito e' protetto da Cloudflare (challenge JavaScript): curl riceve 403,
rem  quindi i download passano da un vero Chrome pilotato da Playwright.
rem
rem  Uso:
rem    download.bat                 interfaccia grafica
rem    download.bat --tui           interfaccia a terminale
rem    download.bat --gui <url>     grafica con l'URL gia' compilato
rem    download.bat <url> [...]     riga di comando
rem ---------------------------------------------------------------------------
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "VENV=.venv"
set "PYEXE=%VENV%\Scripts\python.exe"

if not exist "%PYEXE%" (
    echo Preparo l'ambiente Python ^(solo la prima volta^)...

    set "PYCMD="
    where py >nul 2>nul && set "PYCMD=py -3"
    if not defined PYCMD (
        where python >nul 2>nul && set "PYCMD=python"
    )
    if not defined PYCMD (
        echo.
        echo ERRORE: Python 3 non trovato.
        echo Scaricalo da https://www.python.org/downloads/windows/
        echo durante l'installazione spunta "Add python.exe to PATH".
        echo.
        pause
        exit /b 1
    )

    %PYCMD% -m venv "%VENV%"
    if errorlevel 1 (
        echo.
        echo ERRORE: creazione dell'ambiente virtuale fallita.
        pause
        exit /b 1
    )
)

"%PYEXE%" -c "import playwright" >nul 2>nul
if errorlevel 1 (
    echo Installo playwright...
    "%PYEXE%" -m pip install --quiet --upgrade pip >nul 2>nul
    "%PYEXE%" -m pip install --quiet playwright
    if errorlevel 1 (
        echo.
        echo ERRORE: installazione di playwright fallita.
        pause
        exit /b 1
    )
)

rem --- modalita' a terminale forzata
if /i "%~1"=="--tui" (
    shift
    "%PYEXE%" vg_tui.py %*
    goto :fine
)

rem --- grafica con URL precompilato
if /i "%~1"=="--gui" (
    shift
    "%PYEXE%" -c "import tkinter" >nul 2>nul
    if errorlevel 1 (
        echo Interfaccia grafica non disponibile: uso la modalita' a terminale.
        "%PYEXE%" vg_tui.py %*
    ) else (
        "%PYEXE%" vg_gui.py %*
    )
    goto :fine
)

rem --- con argomenti: riga di comando
if not "%~1"=="" (
    "%PYEXE%" vg_download.py %*
    goto :fine
)

rem --- nessun argomento: grafica se possibile
"%PYEXE%" -c "import tkinter" >nul 2>nul
if errorlevel 1 (
    echo tkinter non disponibile: uso la modalita' a terminale.
    echo Per la grafica reinstallando Python spunta "tcl/tk and IDLE".
    "%PYEXE%" vg_tui.py
) else (
    "%PYEXE%" vg_gui.py
)

:fine

set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo Uscita con codice %RC%.
    pause
)
exit /b %RC%
