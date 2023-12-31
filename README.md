# ETS2/ATS Telemetry Overlay
Show truck telemetry as game overlay!

![Alt text](image.png)

✅ Speed with **RPM indicator**!


✅ Speed limit indicator


✅ Cruise control indicator


✅ Fuel level and **liter/km inficator**!


✅ Next stop countdown timer (fatigue)


✅ Job delivery remaining time and **will highlight if running  late**!


✅ Auto hides!


## Requirements

✏️ Download and run [Ets2 Telemetry Server](https://github.com/Funbit/ets2-telemetry-server) first! It check for the process Ets2Telemetry.exe and exits automatically if not found.


✏️ You MUST run ETS2 / ATS in **Windowed Mode**


✏️ Optional: Download and run [Borderless Gaming](https://github.com/Codeusa/Borderless-Gaming) to resize to bordeless full screeen



## Install from Source Code
To install you must have Python 3.9+ and run the following command:

``python -m pip install git+https://github.com/rpfilomeno/ETS2-ATS-Telemetry-Overlay.git``

## Run from Source code
On the command line run:

``python -m truckmon``

## Build Executable
Checkout the source code from git, have Python 3.9+ installed.

### Install the package in the git repository:

``python -m pip install .``

### Install Pyinstaller:

``python -m pip install pyinstaller``

### Build the installer (will create an exe at dist\run_truckmon.exe):

``pyinstaller installer\run_truckmon.py --clean --add-data "truckmon/data/*;truckmon/data" --noconsole --onefile --icon installer\truckmon.ico``

