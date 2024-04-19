@echo off
cd /d "%~dp0"
cd viperboxinterface
call conda activate viperbox
uvicorn main:app --reload < nul
