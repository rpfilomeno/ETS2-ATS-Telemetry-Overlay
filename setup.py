import sys
from distutils.core import setup

if sys.version_info < (3, 9):
    sys.exit('Python 3.9 or higher is required')

setup(
    name='ETS2/ATS Telemetry Overlay',
    version='0.1.0',
    description='Provides an overlay of iomportant truck telemetry',
    author='@notatallshaw',
    url='https://github.com/rpfilomeno/ETS2-ATS-Telemetry-Overlay.git',
    packages=['truckmon'],
    include_package_data=True,
    install_requires=[
        'pywin32',
        'pywin32-ctypes',
        'pygame',
        'backoff',
        'loguru',
        'python-dateutil',
        'psutil',
        'infi.systray',
        'win10toast',
        'pyinstaller',
    ],
)