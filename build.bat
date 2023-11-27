echo off
setlocal

.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip freeze > requirements.txt
.\venv\Scripts\python.exe -m pip uninstall -r requirements.txt -y
.\venv\Scripts\python.exe -m pip install .
.\venv\Scripts\python.exe -m pip freeze > requirements.txt

echo:
:PROMPT
SET /P AREYOUSURE=Create distributsble (Y/[N])?
IF /I "%AREYOUSURE%" NEQ "Y" GOTO END

.\venv\Scripts\pyinstaller.exe installer\run_truckmon.py --clean --add-data "truckmon/data/*;truckmon/data" --noconsole --onefile --icon installer/truckmon.ico

:END
endlocal


