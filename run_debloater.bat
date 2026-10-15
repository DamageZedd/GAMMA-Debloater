@echo off
title S.T.A.L.K.E.R. G.A.M.M.A. Debloater & Storage Optimizer
cd /d "%~dp0"
python gamma_debloater.py
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start GUI. Please ensure Python 3.10+ is installed and on your PATH.
    pause
)
