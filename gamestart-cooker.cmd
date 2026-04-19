@echo off
setlocal
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
python -m gamestart_legacy_cooker %*

