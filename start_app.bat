@echo off
cd /d "%~dp0"
call conda activate viperbox
uvicorn main:app --reload < nul

@REM call python main.py
