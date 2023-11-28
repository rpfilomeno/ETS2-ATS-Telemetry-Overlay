import os
from collections import deque
from pygame import draw, freetype, Surface, Rect

def draw_laps(screen: Surface, x: int, y:int, distance: int, estimate: str ,laps: deque ):
    """Draw estimate and laps"""
    pass

def draw_gauge(
    screen: Surface,
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

   
        draw.rect(screen, box_color, Rect(x - 3, y - 3 + fill_diff, dx, fill))

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
