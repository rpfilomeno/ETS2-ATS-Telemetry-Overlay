"""
Main script
"""
from urllib import request
import os
import sys
import time
import json
import ctypes
import backoff
import pygame
from dateutil import parser
from pygame import freetype
from win32 import win32api, winxpgui, win32gui
from win32gui import FindWindow, GetWindowRect
from win32.lib import win32con
from infi.systray import SysTrayIcon
from win10toast import ToastNotifier
from loguru import logger
import psutil

GAME_VISIBILITY = True
API_URL = "http://localhost:25555/api/ets2/telemetry"
GAME_NAMES = ["Euro Truck Simulator 2",
              "American Truck Simulator"]


pygame.init()
display_info = pygame.display.Info()
OVERLAY_XPOS = round(display_info.current_w / 2) - 180
OVERLAY_YPOS = display_info.current_h - 50
OVERLAY_SIZE = 21


def build_overlay() -> pygame.Surface:
    """
    Setup overlay
    """
    x = y = 0
    display_info = pygame.display.Info()
    w = display_info.current_w
    h = display_info.current_h
    for name in GAME_NAMES:
        hwnd = FindWindow(None, name)
        if hwnd:
            x, y, w, h = GetWindowRect(hwnd)
    os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (x,y)
    screen = pygame.display.set_mode((w,h), pygame.NOFRAME)

    pygame.display.set_caption('Truckmon Overlay')


    # Create layered window
    hwnd = pygame.display.get_wm_info()["window"]
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


def game_loop():
    """
    main render loop
    """
    
    global GAME_VISIBILITY
    telemetry_data = None
    last_cruise = 0
    dx = dy = dw = dh = 0
    gauge_h_spacing = 25  # todo: user config

    clock = pygame.time.Clock()
    timer_event = pygame.USEREVENT + 1
    pygame.time.set_timer(timer_event, 500)

    last_time = time.time()
    game_done = False

    screen=build_overlay()
    while not game_done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_done = True
                pygame.display.quit()
            
            if event.type == timer_event:
                telemetry_data = get_telemetry()

                if(time.time() - last_time > 10):
                    resize_window()


            

        screen.fill((0, 0, 0))

        focused_window = winxpgui.GetWindowText (winxpgui.GetForegroundWindow())
        if focused_window not in GAME_NAMES:
            pygame.display.update()
            continue

        if not GAME_VISIBILITY:
            pygame.display.update()
            continue

        if not telemetry_data:
            continue

        if telemetry_data["game"]["paused"]:
            pygame.display.update()
            continue

       
        mx, my = pygame.mouse.get_pos()
        if dw and dh:
            if OVERLAY_XPOS < mx < (dx + dw) and OVERLAY_YPOS < my < (dy + dh):
                pygame.display.update()
                continue
        dx = OVERLAY_XPOS
        dy = OVERLAY_YPOS


        # draw speed
        rpm_percentage = telemetry_data["truck"]["engineRpm"]/telemetry_data["truck"]["engineRpmMax"]
        rpm_color = (0, 130, 0)
        if rpm_percentage > 0.50 :
            rpm_color = (20, 148, 222)
            
        if rpm_percentage > 0.70 :
            rpm_color = (191, 4, 4)

        w, h = draw_gauge(
            screen,
            (255, 255, 255),
            dx,
            dy,
            value=str(round(telemetry_data["truck"]["speed"])),
            name="speed",
            unit="km/h",
            size=OVERLAY_SIZE,
            fill_mode=True,
            fill_percentage= rpm_percentage,
            fill_color= rpm_color
        )

        # draw speed limits
        dx = dx + w + gauge_h_spacing
        w, h = draw_gauge(
            screen,
            (242, 111, 229),
            dx,
            dy,
            value=str(round(telemetry_data["navigation"]["speedLimit"])),
            name="limit",
            unit="km/h",
            size=OVERLAY_SIZE,
            fill_mode=True
            if (
                telemetry_data["truck"]["speed"]
                >= telemetry_data["navigation"]["speedLimit"] and telemetry_data["navigation"]["speedLimit"]
            )
            else False,
        )

        # draw cruise control
        last_cruise = (
            telemetry_data["truck"]["cruiseControlSpeed"]
            if (telemetry_data["truck"]["cruiseControlSpeed"] > 0)
            else last_cruise
        )
        dx = dx + w + gauge_h_spacing
        w, h = draw_gauge(
            screen,
            (227, 227, 5),
            dx,
            dy,
            value=str(round(last_cruise)),
            name="cruise",
            unit="km/h",
            size=OVERLAY_SIZE,
            fill_mode=telemetry_data["truck"]["cruiseControlOn"],
        )

        # draw fuel
        dx = dx + w + gauge_h_spacing
        w, h = draw_gauge(
            screen,
            (2, 223, 235),
            dx,
            dy,
            value=str(round(telemetry_data["truck"]["fuel"])),
            name="fuel",
            unit= "%.2f l/km" % telemetry_data["truck"]["fuelAverageConsumption"],
            size= OVERLAY_SIZE,
            fill_mode=telemetry_data["truck"]["fuelWarningOn"],
        )

        rest_time = parser.isoparse(telemetry_data["game"]["nextRestStopTime"])
        rest_hour = str(rest_time.hour)
        rest_minute = str(rest_time.minute)

        # draw rest
        dx = dx + w + gauge_h_spacing
        w, h = draw_gauge(
            screen,
            (176, 96, 56),
            dx,
            dy,
            value="{:02}:{:02}".format(int(rest_time.hour), int(rest_time.minute)),
            name="next stop",
            unit="remaining",
            size=OVERLAY_SIZE,
            fill_mode=True if int(rest_hour) < 1 else False,
        )

        # calculate job time
        game_now = parser.isoparse(telemetry_data["game"]["time"])
        job_due = parser.isoparse(telemetry_data["job"]["deadlineTime"])
        nav_estimate = parser.isoparse(telemetry_data["navigation"]["estimatedTime"])
        if telemetry_data["job"]["income"] == 0:
            job_time = "No Job"
            late_flag = False
        else:
            diff = job_due - game_now
            diff_hours, diff_remainder = divmod(diff.seconds, 3600)
            diff_hours += diff.days * 24
            diff_minutes, diff_seconds = divmod(diff_remainder, 60)
            job_time = "{:02}:{:02}".format(int(diff_hours), int(diff_minutes))
            late_flag = True if diff_hours < 1 else False 

        # draw job timer
        dx = dx + w + gauge_h_spacing
        w, h = draw_gauge(
            screen,
            (157, 95, 227),
            dx,
            dy,
            value=job_time,
            name="remaining",
            unit="time",
            size=OVERLAY_SIZE,
            fill_mode= late_flag
        )

        dw = w
        dh = h

        pygame.display.flip()
        clock.tick(30)

    logger.debug("Exiting game loop")


def draw_gauge(
    screen: pygame.Surface,
    color,
    x: int,
    y: int,
    value: float,
    name: str,
    unit: str,
    size=34.0,
    fill_mode=False,
    fill_percentage=1.0,
    fill_color=None,
):
    """
    Draw a gauge
    """

    min_width = 50  # todo: user config

    lcd_font = freetype.Font(
        os.path.join(os.path.realpath(os.path.dirname(__file__)), "data", "square.ttf")
    )

    if fill_mode:
        lcd_color = color if fill_color else (1, 1, 1)
        box_color = fill_color if fill_color else color

        
        lcd_surface, rect = lcd_font.render(text=value, fgcolor=lcd_color, size=size)
        dx = rect.width + 6

        if dx < min_width:
            dx = min_width

        fill = round(fill_percentage * (rect.height + 6))
        fill_diff = rect.height + 6 - fill

   
        pygame.draw.rect(screen, box_color, pygame.Rect(x - 3, y - 3 + fill_diff, dx, fill))

    else:
        lcd_surface, rect = lcd_font.render(text=value, fgcolor=color, size=size)

        dx = rect.width + 6

        if dx < min_width:
            dx = min_width

    screen.blit(lcd_surface, (x, y))

    # nane
    sqr_surface, rect2 = lcd_font.render(text=name, fgcolor=color, size=size * 0.5)
    screen.blit(sqr_surface, (x - 3, y - 6 - rect2.height))

    # units
    sqr_surface, rect3 = lcd_font.render(text=unit, fgcolor=color, size=size * 0.5)
    screen.blit(sqr_surface, (x + dx - rect3.width, y + rect.height + rect3.height))

    return (dx, rect.height + rect2.height + rect3.height)


def get_telemetry_fail(details):
    """Exits after giving up fetching telemetry"""
    message_box('Truckmon Exiting!', 'Error: Unable to fetch telemetry. Make sure the server is running first.', 0)
    pygame.quit()

@backoff.on_exception(
    backoff.expo,
    (Exception),
    on_backoff=lambda details: logger.error(
        "api fail: backing off {wait:0.1f} seconds after {tries}".format(**details)
    ),
    on_giveup=get_telemetry_fail,
    max_tries=10,
)


def get_telemetry():
    """fetch data from telemetry api"""
    with request.urlopen(API_URL) as url:
        data = json.load(url)
        #logger.debug(json2txttree(data))
        return data


def resize_window():
    """resize/move overlay"""

    display_info = pygame.display.Info()
    w = display_info.current_w
    h = display_info.current_h
    for name in GAME_NAMES:
        hwnd = FindWindow(None, name)
        if hwnd:
            x, y, w, h = GetWindowRect(hwnd)

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
    

def game_visibility(systray):
    """Toggle overlay visibility"""
    logger.debug("user toggles visibility")
    global GAME_VISIBILITY
    GAME_VISIBILITY = not GAME_VISIBILITY
    if not GAME_VISIBILITY:
        notify( "Truckmon is hidden!","You have toggled to hide the overlay.")

def game_stop(systray):
    """exit truckmon"""
    logger.debug("user exits from sys tray")
    pygame.quit()


@logger.catch
def main():
    """main eentry point"""
    if not check_process():
        logger.error("failed to detect Ets2Telemetry.exe")
        message_box('Truckmon Exiting!', 'Telemetry Server process not detected', 0)
        sys.exit(1)

    icon = os.path.join ( os.path.realpath(os.path.dirname(__file__)),'data','truckmon.ico')
    menu_options = (("Hide/Sow", None, game_visibility),)
    systray = SysTrayIcon(
        icon,
        "Truckmon", 
        menu_options,
        on_quit=game_stop
        )
    systray.start()
    notify("Truckmon is running","Check the system tray for option.")
    game_loop()

if __name__ == "__main__":
    main()
    sys.exit()
