@echo off
echo Checking BigQuery table schemas...
python apps\dataexplorer\check_schemas_simple.py
pause

