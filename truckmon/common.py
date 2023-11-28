import os
import ctypes
from pygame import display, Surface, NOFRAME
from win32 import winxpgui
import psutil
from win10toast import ToastNotifier
from win32 import win32api, winxpgui, win32gui
from win32.lib import win32con
from win32gui import FindWindow, GetWindowRect
from loguru import logger

from config import GAME_NAMES

def resize_window():
    """resize/move overlay"""

    display_info = display.Info()
    w = display_info.current_w
    h = display_info.current_h
    for name in GAME_NAMES:
        hwnd = FindWindow(None, name)
        if hwnd:
            x, y, w, h = GetWindowRect(hwnd)

    if not hwnd:
        return

    hwnd = winxpgui.FindWindow(None, 'Truckmon Overlay')
    winxpgui.MoveWindow(hwnd, x, y, w, h, True)



def check_process() -> bool:
    """Check if Ets2Telemetry is running """
    for process in psutil.process_iter():
        if process.name() == "Ets2Telemetry.exe":
            return True
    return False

def message_box(title, text, style):
    """
    Display message box
    Styles:
    0 : OK
    1 : OK | Cancel
    2 : Abort | Retry | Ignore
    3 : Yes | No | Cancel
    4 : Yes | No
    5 : Retry | Cancel 
    6 : Cancel | Try Again | Continue
    """
    logger.debug( "%s: %s" % (title, text))
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)


def notify(title, message):
    """Display toast notication"""
    logger.debug( "%s: %s" % (title, message))
    icon = os.path.join ( os.path.realpath(os.path.dirname(__file__)),'data','truckmon.ico')
    toast = ToastNotifier()
    toast.show_toast(
        title,
        message,
        duration = 20,
        icon_path = icon,
        threaded = True,
    )

def build_overlay() -> Surface:
    """
    Setup overlay
    """
    x = y = 0
    display_info = display.Info()
    w = display_info.current_w
    h = display_info.current_h
    for name in GAME_NAMES:
        hwnd = FindWindow(None, name)
        if hwnd:
            x, y, w, h = GetWindowRect(hwnd)
 
    os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x,y)
    screen = display.set_mode((w,h), NOFRAME)
    display.set_caption('Truckmon Overlay')

    # Create layered window
    hwnd = display.get_wm_info()["window"]
    winxpgui.SetWindowLong(
        hwnd,
        win32con.GWL_EXSTYLE,
        win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED,
    )

    winxpgui.SetWindowLong(
        hwnd,
        win32con.GWL_EXSTYLE,
        (
            win32con.WS_EX_COMPOSITED
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_NOACTIVATE
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TRANSPARENT
        ),
    )

    winxpgui.SetLayeredWindowAttributes(
        hwnd, win32api.RGB(0, 0, 0), 0, win32con.LWA_COLORKEY
    )

    winxpgui.SetWindowPos(
        hwnd,
        win32con.HWND_TOPMOST,
        0,
        0,
        0,
        0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
    )

    return screen
    