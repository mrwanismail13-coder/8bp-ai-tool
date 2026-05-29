# =========================================================
# 🎱 8 BALL POOL AI PRO
# YOLOv8 + ONNX + CUDA + DirectX Overlay
# Ultra Stable / No Shake / Multi Bank System
# =========================================================

import os
import cv2
import dxcam
import torch
import time
import math
import queue
import keyboard
import numpy as np
import pygame
import pygame.gfxdraw
import win32gui
import win32con
import win32api

from ultralytics import YOLO
from filterpy.kalman import KalmanFilter

# =========================================================
# ⚡ OpenCV Optimizations
# =========================================================

cv2.setUseOptimized(True)
cv2.setNumThreads(8)

# =========================================================
# ⚡ SETTINGS
# =========================================================

FPS = 144

BALL_RADIUS = 16

SCREEN_W = win32api.GetSystemMetrics(0)
SCREEN_H = win32api.GetSystemMetrics(1)

TRANSPARENT = (0, 0, 0)

# =========================================================
# 🎨 COLORS
# =========================================================

WHITE = (255,255,255)
BLACK = (0,0,0)

GREEN = (0,255,0)
RED = (255,0,0)
BLUE = (0,162,232)
CYAN = (0,255,255)
YELLOW = (255,255,0)
ORANGE = (255,140,0)

GUI_BG = (18,18,25)

# =========================================================
# ⚡ CUDA CHECK
# =========================================================

DEVICE = 0 if torch.cuda.is_available() else "cpu"

print("DEVICE:", DEVICE)

# =========================================================
# 🤖 LOAD YOLO MODEL
# =========================================================

model = YOLO("best.pt")

# =========================================================
# 🎥 DXCAM
# =========================================================

camera = dxcam.create(output_color="BGR")

camera.start(
    target_fps=FPS,
    video_mode=True
)

# =========================================================
# 🎮 PYGAME OVERLAY
# =========================================================

pygame.init()

screen = pygame.display.set_mode(
    (SCREEN_W, SCREEN_H),
    pygame.NOFRAME
)

hwnd = pygame.display.get_wm_info()["window"]

styles = win32gui.GetWindowLong(
    hwnd,
    win32con.GWL_EXSTYLE
)

win32gui.SetWindowLong(
    hwnd,
    win32con.GWL_EXSTYLE,
    styles
    | win32con.WS_EX_LAYERED
    | win32con.WS_EX_TRANSPARENT
    | win32con.WS_EX_TOPMOST
    | win32con.WS_EX_NOACTIVATE
)

win32gui.SetLayeredWindowAttributes(
    hwnd,
    win32api.RGB(*TRANSPARENT),
    0,
    win32con.LWA_COLORKEY
)

clock = pygame.time.Clock()

# =========================================================
# 🧠 KALMAN FILTER
# =========================================================

class SmoothTracker:

    def __init__(self):

        self.kf = KalmanFilter(dim_x=4, dim_z=2)

        self.kf.F = np.array([
            [1,0,1,0],
            [0,1,0,1],
            [0,0,1,0],
            [0,0,0,1]
        ])

        self.kf.H = np.array([
            [1,0,0,0],
            [0,1,0,0]
        ])

        self.kf.P *= 100

        self.kf.R *= 0.3

        self.kf.Q *= 0.01

        self.initialized = False

    def update(self, x, y):

        if not self.initialized:

            self.kf.x = np.array([x,y,0,0])

            self.initialized = True

        self.kf.predict()

        self.kf.update(np.array([x,y]))

        return (
            int(self.kf.x[0]),
            int(self.kf.x[1])
        )

# =========================================================
# 🧠 TRACKERS
# =========================================================

white_tracker = SmoothTracker()

target_tracker = SmoothTracker()

# =========================================================
# 🎯 TARGETS
# =========================================================

locked_target = None

selected_pocket = 0

show_overlay = True

line_thickness = 2

# =========================================================
# 📐 FUNCTIONS
# =========================================================

def distance(a,b):

    return math.hypot(
        a[0]-b[0],
        a[1]-b[1]
    )

# =========================================================

def ghost_ball(target, pocket):

    dx = target[0] - pocket[0]
    dy = target[1] - pocket[1]

    dist = math.hypot(dx,dy)

    if dist == 0:
        return target

    ratio = (dist + BALL_RADIUS*2) / dist

    return (
        pocket[0] + dx*ratio,
        pocket[1] + dy*ratio
    )

# =========================================================

def draw_3line(start,end,color):

    dx = end[0]-start[0]
    dy = end[1]-start[1]

    dist = math.hypot(dx,dy)

    if dist == 0:
        return

    ux = dx/dist
    uy = dy/dist

    nx = -uy * BALL_RADIUS
    ny = ux * BALL_RADIUS

    pygame.draw.line(
        screen,
        color,
        (
            int(start[0]+nx),
            int(start[1]+ny)
        ),
        (
            int(end[0]+nx),
            int(end[1]+ny)
        ),
        line_thickness
    )

    pygame.draw.line(
        screen,
        color,
        (
            int(start[0]),
            int(start[1])
        ),
        (
            int(end[0]),
            int(end[1])
        ),
        line_thickness
    )

    pygame.draw.line(
        screen,
        color,
        (
            int(start[0]-nx),
            int(start[1]-ny)
        ),
        (
            int(end[0]-nx),
            int(end[1]-ny)
        ),
        line_thickness
    )

# =========================================================

def calculate_bank(target,pocket,bounds,side):

    left,top,right,bottom = bounds

    left += BALL_RADIUS
    right -= BALL_RADIUS
    top += BALL_RADIUS
    bottom -= BALL_RADIUS

    tx,ty = target
    px,py = pocket

    if side == "top":

        mirror_y = top - (py-top)

        bx = tx + (px-tx)*(top-ty)/(mirror_y-ty)

        return (bx,top)

    if side == "bottom":

        mirror_y = bottom + (bottom-py)

        bx = tx + (px-tx)*(bottom-ty)/(mirror_y-ty)

        return (bx,bottom)

    if side == "left":

        mirror_x = left - (px-left)

        by = ty + (py-ty)*(left-tx)/(mirror_x-tx)

        return (left,by)

    if side == "right":

        mirror_x = right + (right-px)

        by = ty + (py-ty)*(right-tx)/(mirror_x-tx)

        return (right,by)

    return None

# =========================================================
# 🎱 MAIN LOOP
# =========================================================

running = True

while running:

    clock.tick(FPS)

    if keyboard.is_pressed("ctrl+q"):
        running = False

    if keyboard.is_pressed("ctrl+h"):
        show_overlay = not show_overlay
        time.sleep(0.2)

    screen.fill(TRANSPARENT)

    frame = camera.get_latest_frame()

    if frame is None:
        continue

    # =====================================================
    # 🤖 YOLO DETECTION
    # =====================================================

    results = model.predict(

        source=frame,

        conf=0.45,

        verbose=False,

        device=DEVICE,

        imgsz=960
    )

    white_ball = None

    all_balls = []

    table_box = None

    pockets = []

    for r in results:

        boxes = r.boxes

        for box in boxes:

            cls = int(box.cls[0])

            conf = float(box.conf[0])

            x1,y1,x2,y2 = map(int,box.xyxy[0])

            cx = int((x1+x2)/2)
            cy = int((y1+y2)/2)

            label = model.names[cls]

            # =============================================
            # TABLE
            # =============================================

            if label == "table":

                table_box = (
                    x1,
                    y1,
                    x2,
                    y2
                )

            # =============================================
            # POCKETS
            # =============================================

            elif label == "pocket":

                pockets.append((cx,cy))

            # =============================================
            # WHITE BALL
            # =============================================

            elif label == "white":

                white_ball = (
                    cx,
                    cy
                )

            # =============================================
            # TARGET BALLS
            # =============================================

            elif label == "ball":

                all_balls.append((cx,cy))

    # =====================================================
    # 🧠 SMOOTHING
    # =====================================================

    if white_ball:

        white_ball = white_tracker.update(
            white_ball[0],
            white_ball[1]
        )

    # =====================================================
    # 🎯 TARGET LOCK
    # =====================================================

    mx,my = win32api.GetCursorPos()

    if keyboard.is_pressed("z"):

        nearest = None

        best_dist = 999999

        for b in all_balls:

            d = distance((mx,my),b)

            if d < best_dist:

                best_dist = d

                nearest = b

        if nearest:

            locked_target = nearest

        time.sleep(0.2)

    # =====================================================
    # ❌ CLEAR
    # =====================================================

    if keyboard.is_pressed("x"):

        locked_target = None

        time.sleep(0.2)

    # =====================================================
    # 🧠 TARGET SMOOTH
    # =====================================================

    if locked_target:

        locked_target = target_tracker.update(
            locked_target[0],
            locked_target[1]
        )

    # =====================================================
    # 🎱 DRAW
    # =====================================================

    if show_overlay:

        # ================================================
        # TABLE
        # ================================================

        if table_box:

            tx1,ty1,tx2,ty2 = table_box

            pygame.draw.rect(
                screen,
                CYAN,
                (
                    tx1,
                    ty1,
                    tx2-tx1,
                    ty2-ty1
                ),
                2
            )

            table_bounds = (
                tx1,
                ty1,
                tx2,
                ty2
            )

        # ================================================
        # POCKETS
        # ================================================

        for i,p in enumerate(pockets):

            col = GREEN if i == selected_pocket else RED

            pygame.gfxdraw.filled_circle(
                screen,
                p[0],
                p[1],
                8,
                col
            )

        # ================================================
        # WHITE BALL
        # ================================================

        if white_ball:

            pygame.gfxdraw.aacircle(
                screen,
                white_ball[0],
                white_ball[1],
                BALL_RADIUS,
                WHITE
            )

        # ================================================
        # TARGET BALL
        # ================================================

        if locked_target:

            pygame.gfxdraw.aacircle(
                screen,
                locked_target[0],
                locked_target[1],
                BALL_RADIUS,
                ORANGE
            )

        # ================================================
        # AIM SYSTEM
        # ================================================

        if white_ball and locked_target and len(pockets) > 0:

            current_pocket = pockets[selected_pocket]

            # ============================================
            # GHOST BALL
            # ============================================

            g = ghost_ball(
                locked_target,
                current_pocket
            )

            pygame.gfxdraw.aacircle(
                screen,
                int(g[0]),
                int(g[1]),
                BALL_RADIUS,
                WHITE
            )

            # ============================================
            # MAIN LINES
            # ============================================

            draw_3line(
                white_ball,
                g,
                WHITE
            )

            draw_3line(
                locked_target,
                current_pocket,
                CYAN
            )

            # ============================================
            # BANK SYSTEM
            # ============================================

            if table_box:

                side = None

                if keyboard.is_pressed("i"):
                    side = "top"

                elif keyboard.is_pressed("m"):
                    side = "bottom"

                elif keyboard.is_pressed("j"):
                    side = "left"

                elif keyboard.is_pressed("k"):
                    side = "right"

                if side:

                    bp = calculate_bank(
                        locked_target,
                        current_pocket,
                        table_bounds,
                        side
                    )

                    if bp:

                        pygame.draw.line(
                            screen,
                            GREEN,
                            (
                                int(locked_target[0]),
                                int(locked_target[1])
                            ),
                            (
                                int(bp[0]),
                                int(bp[1])
                            ),
                            2
                        )

                        pygame.draw.line(
                            screen,
                            GREEN,
                            (
                                int(bp[0]),
                                int(bp[1])
                            ),
                            current_pocket,
                            2
                        )

                        pygame.gfxdraw.filled_circle(
                            screen,
                            int(bp[0]),
                            int(bp[1]),
                            5,
                            YELLOW
                        )

    # =====================================================
    # 🎮 HOTKEYS
    # =====================================================

    for i in range(1,7):

        if keyboard.is_pressed(str(i)):

            selected_pocket = i-1

    pygame.display.update()

# =========================================================
# EXIT
# =========================================================

camera.stop()

pygame.quit()
