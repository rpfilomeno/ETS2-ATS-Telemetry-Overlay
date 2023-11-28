echo off
setlocal

.\venv\Scripts\python.exe -m pip install .

echo:
:PROMPT
SET /P AREYOUSURE=Create distributsble (Y/[N])?
IF /I "%AREYOUSURE%" NEQ "Y" GOTO END

.\venv\Scripts\pyinstaller.exe installer\run_truckmon.py --clean --add-data "truckmon/data/*;truckmon/data" --noconsole --onefile --icon installer/truckmon.ico

:END
endlocal


