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

OVERLAY_XPOS = 530
OVERLAY_YPOS = 100
OVERLAY_SIZE = 18


@logger.catch
def main():
    """
    main entry
    """
    pygame.init()

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

    game_done = False
    telemetry_data = None
    clock = pygame.time.Clock()

    time_delay = 1000
    timer_event = pygame.USEREVENT + 1
    pygame.time.set_timer(timer_event, time_delay)

    while not game_done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_done = True
            elif event.type == timer_event:
                if check_process():
                    telemetry_data = get_telemetry()
                else:
                    game_done = True

        screen.fill((0, 0, 0))

        if not telemetry_data:
            continue

        # if telemetry_data["game"]["paused"]:
        #     continue

        dx = OVERLAY_XPOS
        w, h = draw_gauge(
            screen,
            (0, 130, 0),
            dx,
            OVERLAY_YPOS,
            value=str(round(telemetry_data["truck"]["speed"])),
            name="speed",
            unit="km/h",
            size=OVERLAY_SIZE,
        )

        dx = dx + w + 20
        w, h = draw_gauge(
            screen,
            (242, 111, 229),
            dx,
            OVERLAY_YPOS,
            value=str(round(telemetry_data["navigation"]["speedLimit"])),
            name="limit",
            unit="km/h",
            size=OVERLAY_SIZE,
        )

        dx = dx + w + 20
        w, h = draw_gauge(
            screen,
            (227, 227, 5),
            dx,
            OVERLAY_YPOS,
            value=str(round(telemetry_data["truck"]["cruiseControlSpeed"])),
            name="cruise",
            unit="km/h",
            size=OVERLAY_SIZE,
            fill_mode=telemetry_data["truck"]["cruiseControlOn"],
        )

        dx = dx + w + 20
        w, h = draw_gauge(
            screen,
            (2, 223, 235),
            dx,
            OVERLAY_YPOS,
            value=str(round(telemetry_data["truck"]["fuel"])),
            name="fuel",
            unit="liters",
            size=OVERLAY_SIZE,
            fill_mode=False,
        )

        if "remainingTime" in telemetry_data["job"]:
            game_now = parser.isoparse(telemetry_data["game"]["time"])
            job_due = parser.isoparse(telemetry_data["job"]["deadlineTime"])
            remain = (job_due - game_now)
             

            dx = dx + w + 20
            w, h = draw_gauge(
                screen,
                (255, 255, 255),
                dx,
                OVERLAY_YPOS,
                value=str(remain),
                name="Job",
                unit="remaining",
                size=OVERLAY_SIZE,
            )

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
):
    """
    Draw a gauge
    """

    lcd_font = freetype.Font(
        os.path.join(os.path.realpath(os.path.dirname(__file__)), "data","square.ttf")
    )

    if fill_mode:
        lcd_surface, rect = lcd_font.render(
            text=value, fgcolor=(1, 1, 1), bgcolor=color, size=size
        )
    else:
        lcd_surface, rect = lcd_font.render(text=value, fgcolor=color, size=size)

    screen.blit(lcd_surface, (x, y))

    pygame.draw.rect(
        screen, color, pygame.Rect(x - 3, y - 3, rect.width + 6, rect.height + 6), 1
    )

    sqr_surface, rect2 = lcd_font.render(text=name, fgcolor=color, size=size * 0.35)
    screen.blit(sqr_surface, (x - 3, y - 3 - rect2.height))

    sqr_surface, rect3 = lcd_font.render(text=unit, fgcolor=color, size=size * 0.35)
    screen.blit(
        sqr_surface, (x + rect.width - rect3.width, y + rect.height + rect3.height)
    )

    return (rect.width, rect.height + rect2.height + rect3.height)


@backoff.on_exception(
    backoff.expo,
    (Exception),
    on_backoff=lambda details: logger.error(
        "API ERROR: Backing off {wait:0.1f} seconds after {tries}".format(**details)
    ),max_tries=5
)
def get_telemetry():
    with request.urlopen(API_URL) as url:
        data = json.load(url)
        logger.info(json2txttree(data))
        return data
    
def check_process() -> bool:
    for process in psutil.process_iter():
        if process.name() == 'Ets2Telemetry.exe':
            return True
    return False


if __name__ == "__main__":
    main()
