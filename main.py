import pygame
import dxcam
import cv2
import win32api
import win32gui
import win32con
import keyboard

from detector import detect_balls
from tracker import BallTracker
from physics import ghost_ball
from renderer import *

pygame.init()

WIDTH = win32api.GetSystemMetrics(0)
HEIGHT = win32api.GetSystemMetrics(1)

screen = pygame.display.set_mode(
    (WIDTH, HEIGHT),
    pygame.NOFRAME
)

hwnd = pygame.display.get_wm_info()["window"]

styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

win32gui.SetWindowLong(
    hwnd,
    win32con.GWL_EXSTYLE,
    styles
    | win32con.WS_EX_LAYERED
    | win32con.WS_EX_TRANSPARENT
    | win32con.WS_EX_TOPMOST
)

win32gui.SetLayeredWindowAttributes(
    hwnd,
    0,
    0,
    win32con.LWA_COLORKEY
)

camera = dxcam.create(output_color="BGR")

camera.start(target_fps=240)

clock = pygame.time.Clock()

tracker = BallTracker()

running = True

while running:

    clock.tick(240)

    if keyboard.is_pressed("ctrl+q"):
        running = False

    frame = camera.get_latest_frame()

    if frame is None:
        continue

    screen.fill((0,0,0))

    balls = detect_balls(frame)

    for ball in balls:

        x = ball["x"]
        y = ball["y"]
        r = ball["r"]

        tx, ty = tracker.update(x, y)

        draw_ball(
            screen,
            tx,
            ty,
            r,
            (0,255,255)
        )

    pygame.display.update()

pygame.quit()
