@echo off
cd /d "%~dp0"
cd viperboxinterface
call conda activate viperbox
uvicorn server:app < nul
exit
