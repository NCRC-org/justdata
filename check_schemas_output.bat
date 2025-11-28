@echo off
echo Checking BigQuery table schemas...
echo Output will be saved to schema_check_results.txt
python apps\dataexplorer\check_schemas_simple.py > schema_check_results.txt 2>&1
type schema_check_results.txt
echo.
echo Results also saved to schema_check_results.txt
pause

