"""
Main script
"""
from collections import deque
from urllib import request
import os
import sys
import time
import json
import ctypes
import backoff
import pygame
from dateutil import parser
from win32 import win32api, winxpgui, win32gui
from win32gui import FindWindow, GetWindowRect
from win32.lib import win32con
from infi.systray import SysTrayIcon
from loguru import logger



from config import GAME_NAMES, API_URL, OVERLAY_SIZE
from common import build_overlay, resize_window, check_process, message_box, notify
from gauges import draw_gauge, draw_laps


pygame.init()
display_info = pygame.display.Info()
overlay_xpos = round(display_info.current_w / 2) - 180
overlay_ypos = display_info.current_h - 50
game_done=False



def game_loop():
    """
    main render loop
    """
    global game_done
    global game_visibility
    telemetry_data = None
    last_cruise = 0
    laps = deque([("*","00:00",0)])
    dx = dy = dw = dh = 0
    gauge_h_spacing = 25  # todo: user config

    clock = pygame.time.Clock()
    timer_event = pygame.USEREVENT + 1
    pygame.time.set_timer(timer_event, 500)

    last_time = time.time()
 
    screen=build_overlay()
    while not game_done:
        #logger.debug(game_done)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_done = True
             
            if event.type == timer_event:
                if game_done:
                    continue
                telemetry_data = get_telemetry()

                if(time.time() - last_time > 10):
                    resize_window()


        screen.fill((0, 0, 0))

        focused_window = winxpgui.GetWindowText (winxpgui.GetForegroundWindow())
        if focused_window not in GAME_NAMES:
            pygame.display.update()
            continue

        if not game_visibility:
            pygame.display.update()
            continue

        if not telemetry_data:
            continue

        if telemetry_data["game"]["paused"]:
            pygame.display.update()
            continue

       
        mx, my = pygame.mouse.get_pos()
        if dw and dh:
            if overlay_xpos < mx < (dx + dw) and overlay_ypos < my < (dy + dh):
                pygame.display.update()
                continue
        dx = overlay_xpos
        dy = overlay_ypos


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

        if telemetry_data["job"]["income"] == 0:
            job_time = "No Job"
            late_flag = False
        else:
            distance = telemetry_data["navigation"]["estimatedDistance"]
            

            game_now = parser.isoparse(telemetry_data["game"]["time"])
            job_due = parser.isoparse(telemetry_data["job"]["deadlineTime"])
            diff = job_due - game_now
            diff_hours, diff_remainder = divmod(diff.seconds, 3600)
            diff_hours += diff.days * 24
            diff_minutes, _ = divmod(diff_remainder, 60)
            job_time = "{:02}:{:02}".format(int(diff_hours), int(diff_minutes))
            late_flag = True if diff_hours < 1 else False 

            nav_estimate = parser.isoparse(telemetry_data["navigation"]["estimatedTime"])
            
            estimate = nav_estimate - game_now
            est_hours, est_remainder = divmod(estimate.seconds, 3600)
            est_hours += estimate.days * 24
            est_minutes, _ = divmod(est_remainder, 60)
            est_time = "{:02}:{:02}".format(int(est_hours), int(est_minutes))

            advantage = job_due - nav_estimate
            adv_hours, adv_remainder = divmod(advantage.seconds, 3600)
            adv_hours += advantage.days * 24
            adv_minutes, _ = divmod(adv_remainder, 60)
            adv_time = "{:02}:{:02}".format(int(adv_hours), int(est_minutes))

            dst_km, dst_remainder = divmod(distance, 1000)
            
            # recoed lap per km
            if dst_remainder == 0:
                ( last_indicator, last_lap_str, last_lap_sec) =  laps[-1]

                if last_indicator == "*":
                    change_indicator = "↗"
                elif advantage.seconds > last_lap_sec:
                    change_indicator = "↗"
                elif advantage.seconds < last_lap_sec:
                    change_indicator = "↘"
                else:
                    change_indicator = "↔"
                laps.append((change_indicator, adv_time, advantage.seconds))
                #keeps last 3
                if len(laps) > 3 or last_indicator == "*":
                    laps.popleft()
            

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


def game_visibility(systray):
    """Toggle overlay visibility"""
    logger.debug("user toggles visibility")
    global game_visibility
    game_visibility = not game_visibility
    if not game_visibility:
        notify( "Truckmon is hidden!","You have toggled to hide the overlay.")

def game_stop(systray):
    """exit truckmon"""
    logger.debug("user exits from sys tray")
    global game_done
    game_done = True


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
    systray.shutdown()
    pygame.quit()


