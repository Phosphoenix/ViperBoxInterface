@echo off
SET SCRIPT_URL=https://raw.githubusercontent.com/sbalk/viperboxinterface/main/setup/download_script.ps1
powershell -Command "& { iwr -useb %SCRIPT_URL% | iex; }"
