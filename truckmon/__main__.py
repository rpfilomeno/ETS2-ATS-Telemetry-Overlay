"""
Main script
"""
from urllib import request
import os
import json
import backoff
import pygame
from dateutil import parser
from pygame import freetype
from win32 import win32api, winxpgui, win32gui
from win32.lib import win32con
from json2txttree import json2txttree
from loguru import logger
import psutil


API_URL = "http://localhost:25555/api/ets2/telemetry"

pygame.init()
# initial render position
display_info = pygame.display.Info()
OVERLAY_XPOS = round(display_info.current_w / 2) - 180
OVERLAY_YPOS = display_info.current_h - 50
OVERLAY_SIZE = 21


@logger.catch
def main():
    """
    main entry
    """

    screen = build_overlay()
    game_loop(screen)


def build_overlay() -> pygame.Surface:
    """
    Setup overlay
    """
    display_info = pygame.display.Info()
    screen = pygame.display.set_mode(
        (display_info.current_w, display_info.current_h), pygame.NOFRAME
    )

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


def game_loop(screen: pygame.Surface):
    """
    main render loop
    """
    gauge_h_spacing = 25  # todo: user config

    game_done = False
    telemetry_data = None
    last_cruise = 0
    dx = dy = dw = dh = 0

    clock = pygame.time.Clock()

    time_delay = 500
    timer_event = pygame.USEREVENT + 1
    pygame.time.set_timer(timer_event, time_delay)

    check_delay = 10000
    check_event = pygame.USEREVENT + 2
    pygame.time.set_timer(check_event, check_delay)

    while not game_done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_done = True
            if event.type == check_event:
                if not check_process():
                    game_done = True

            if event.type == timer_event:
                telemetry_data = get_telemetry()

        screen.fill((0, 0, 0))

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

        # draw speed
        dx = OVERLAY_XPOS
        dy = OVERLAY_YPOS

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
                >= telemetry_data["navigation"]["speedLimit"]
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
        if game_now > job_due:
            remain = "No Job"
            late_flag = False
        else:
            diff = job_due - game_now
            diff_hours, diff_remainder = divmod(diff.seconds, 3600)
            diff_hours += diff.days * 24
            diff_minutes, diff_seconds = divmod(diff_remainder, 60)
            job_time = "{:02}:{:02}".format(int(diff_hours), int(diff_minutes))
            late_flag = True if diff.seconds - nav_estimate.second < 30 * 60 else False 

        # draw job timer
        dx = dx + w + gauge_h_spacing
        w, h = draw_gauge(
            screen,
            (157, 95, 227),
            dx,
            dy,
            value=job_time,
            name="delivery",
            unit="remaining",
            size=OVERLAY_SIZE,
            fill_mode= late_flag
        )

        dw = w
        dh = h

        pygame.display.flip()
        clock.tick(30)


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

        # pygame.draw.rect(
        #     screen, color, pygame.Rect(x - 3, y - 3, dx, rect.height + 6 ),1
        # )

    screen.blit(lcd_surface, (x, y))

    # nane
    sqr_surface, rect2 = lcd_font.render(text=name, fgcolor=color, size=size * 0.5)
    screen.blit(sqr_surface, (x - 3, y - 3 - rect2.height))

    # units
    sqr_surface, rect3 = lcd_font.render(text=unit, fgcolor=color, size=size * 0.5)
    screen.blit(sqr_surface, (x + dx - rect3.width, y + rect.height + rect3.height))

    return (dx, rect.height + rect2.height + rect3.height)


@backoff.on_exception(
    backoff.expo,
    (Exception),
    on_backoff=lambda details: logger.error(
        "API ERROR: Backing off {wait:0.1f} seconds after {tries}".format(**details)
    ),
    max_tries=5,
)
def get_telemetry():
    with request.urlopen(API_URL) as url:
        data = json.load(url)
        #logger.info(json2txttree(data))
        return data


def check_process() -> bool:
    for process in psutil.process_iter():
        if process.name() == "Ets2Telemetry.exe":
            return True
    return False


if __name__ == "__main__":
    main()
