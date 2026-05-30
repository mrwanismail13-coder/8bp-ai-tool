import os
import pygame
import pygame.gfxdraw
import win32gui
import win32con
import win32api
import dxcam
import cv2
import numpy as np
import math
import sys
import time
import keyboard
import torch

from ultralytics import YOLO
from filterpy.kalman import KalmanFilter

# =========================================================
# 🚀 PERFORMANCE
# =========================================================

cv2.setUseOptimized(True)
cv2.setNumThreads(4)

# =========================================================
# 🎯 SETTINGS
# =========================================================

FPS = 144
BALL_RADIUS = 16
LINE_THICKNESS = 2
CUSHION_PADDING = 26

SCREEN_WIDTH = win32api.GetSystemMetrics(0)
SCREEN_HEIGHT = win32api.GetSystemMetrics(1)

TRANSPARENT = (0, 0, 0)

WHITE = (255,255,255)
BLACK = (0,0,0)
RED = (255,0,0)
GREEN = (0,255,0)
BLUE = (0,162,232)
CYAN = (0,255,255)
YELLOW = (255,255,0)
ORANGE = (255,165,0)
PINK = (255,0,128)

# =========================================================
# 🧠 DEVICE
# =========================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print("DEVICE:", DEVICE)

# =========================================================
# 🧠 LOAD YOLO
# =========================================================


import os

MODEL_PATH = "models/yolov8n.pt"

print("Current Directory:", os.getcwd())
print("Model Exists:", os.path.exists(MODEL_PATH))

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

model = YOLO(MODEL_PATH)

# =========================================================
# 🎮 PYGAME
# =========================================================

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT),
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
    | win32con.WS_EX_NOACTIVATE
)

win32gui.SetLayeredWindowAttributes(
    hwnd,
    win32api.RGB(*TRANSPARENT),
    0,
    win32con.LWA_COLORKEY
)

# =========================================================
# 📷 DXCAM
# =========================================================

camera = dxcam.create(output_color="BGR")

camera.start(
    target_fps=FPS,
    video_mode=True
)

clock = pygame.time.Clock()

# =========================================================
# 🧠 MEMORY
# =========================================================

class WhiteBallMemory:
    def __init__(self):
        self.pos = None

    def update(self, p):
        if p is not None:
            self.pos = p
        return self.pos

white_memory = WhiteBallMemory()

# =========================================================
# 🎯 TARGET KALMAN
# =========================================================

class TargetManager:

    def __init__(self):
        self.locked = None
        self.kf = None

    def init_kf(self, x, y):

        self.kf = KalmanFilter(dim_x=4, dim_z=2)

        self.kf.x = np.array([x, y, 0., 0.])

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

        self.kf.P *= 10
        self.kf.R *= 0.1
        self.kf.Q *= 0.01

    def lock(self, x, y):
        self.locked = (x, y)
        self.init_kf(x, y)

    def update(self):

        if self.kf is None:
            return self.locked

        self.kf.predict()
        self.kf.update(np.array(self.locked))

        return (
            int(self.kf.x[0]),
            int(self.kf.x[1])
        )

    def clear(self):
        self.locked = None
        self.kf = None

target_manager = TargetManager()

# =========================================================
# 🎯 TABLE DETECT
# =========================================================

def detect_table(frame):

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower = np.array([30,40,40])
    upper = np.array([100,255,255])

    mask = cv2.inRange(hsv, lower, upper)

    contours,_ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if contours:

        largest = max(contours, key=cv2.contourArea)

        if cv2.contourArea(largest) > 40000:

            x,y,w,h = cv2.boundingRect(largest)

            return (x,y,w,h)

    return None

# =========================================================
# 🎯 DISTANCE
# =========================================================

def distance(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# =========================================================
# 🎯 GHOST BALL
# =========================================================

def ghost_ball(target, pocket):

    dx = target[0] - pocket[0]
    dy = target[1] - pocket[1]

    dist = math.hypot(dx,dy)

    if dist == 0:
        return target

    ratio = (dist + BALL_RADIUS*2)/dist

    gx = pocket[0] + dx * ratio
    gy = pocket[1] + dy * ratio

    return (gx,gy)

# =========================================================
# 🎯 DRAW 3 LINES
# =========================================================

def draw_3lines(surface, start, end, color, white_mode=False):

    dx = end[0]-start[0]
    dy = end[1]-start[1]

    dist = math.hypot(dx,dy)

    if dist == 0:
        return

    ux = dx/dist
    uy = dy/dist

    nx = -uy * BALL_RADIUS
    ny = ux * BALL_RADIUS

    if white_mode:

        pygame.draw.line(
            surface,
            WHITE,
            (start[0]+nx, start[1]+ny),
            (end[0]+nx, end[1]+ny),
            LINE_THICKNESS
        )

        pygame.draw.line(
            surface,
            BLACK,
            start,
            end,
            LINE_THICKNESS
        )

        pygame.draw.line(
            surface,
            WHITE,
            (start[0]-nx, start[1]-ny),
            (end[0]-nx, end[1]-ny),
            LINE_THICKNESS
        )

    else:

        pygame.draw.line(
            surface,
            color,
            (start[0]+nx, start[1]+ny),
            (end[0]+nx, end[1]+ny),
            LINE_THICKNESS
        )

        pygame.draw.line(
            surface,
            color,
            start,
            end,
            LINE_THICKNESS
        )

        pygame.draw.line(
            surface,
            color,
            (start[0]-nx, start[1]-ny),
            (end[0]-nx, end[1]-ny),
            LINE_THICKNESS
        )

# =========================================================
# 🎯 FIND WHITE
# =========================================================

def detect_white_ball(table):

    gray = cv2.cvtColor(table, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray,(5,5),0)

    circles = cv2.HoughCircles(
        blur,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=30,
        param1=100,
        param2=20,
        minRadius=12,
        maxRadius=20
    )

    if circles is None:
        return None

    circles = np.round(circles[0,:]).astype(int)

    best = None
    best_score = 0

    for (cx,cy,r) in circles:

        roi = table[
            max(0,cy-r):cy+r,
            max(0,cx-r):cx+r
        ]

        if roi.size == 0:
            continue

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(
            hsv,
            np.array([0,0,180]),
            np.array([180,40,255])
        )

        score = np.sum(mask == 255)

        if score > best_score:
            best_score = score
            best = (cx,cy)

    return best

# =========================================================
# 🎯 MAIN
# =========================================================

table_bounds = None

running = True

while running:

    clock.tick(FPS)

    if keyboard.is_pressed("ctrl+q"):
        running = False

    screen.fill(TRANSPARENT)

    frame = camera.get_latest_frame()

    if frame is None:
        continue

    if table_bounds is None:

        table_bounds = detect_table(frame)

        pygame.display.update()
        continue

    tx,ty,tw,th = table_bounds

    table = frame[ty:ty+th, tx:tx+tw]

    if table.size == 0:
        continue

    pockets = [

        (tx+25, ty+25),
        (tx+tw//2, ty+15),
        (tx+tw-25, ty+25),

        (tx+25, ty+th-25),
        (tx+tw//2, ty+th-15),
        (tx+tw-25, ty+th-25)
    ]

    # =====================================================
    # 🎯 WHITE DETECT
    # =====================================================

    white_local = detect_white_ball(table)

    stable_white = None

    if white_local:

        stable_white = white_memory.update(
            (white_local[0]+tx, white_local[1]+ty)
        )

    else:
        stable_white = white_memory.update(None)

    # =====================================================
    # 🎯 LOCK TARGET
    # =====================================================

    mx,my = win32api.GetCursorPos()

    if keyboard.is_pressed("z"):

        target_manager.lock(mx,my)

        time.sleep(0.2)

    if keyboard.is_pressed("x"):

        target_manager.clear()

        time.sleep(0.2)

    stable_target = target_manager.update()

    # =====================================================
    # 🎯 DRAW TABLE
    # =====================================================

    pygame.draw.rect(
        screen,
        CYAN,
        (
            tx+CUSHION_PADDING,
            ty+CUSHION_PADDING,
            tw-(CUSHION_PADDING*2),
            th-(CUSHION_PADDING*2)
        ),
        2
    )

    # =====================================================
    # 🎯 DRAW POCKETS
    # =====================================================

    for i,p in enumerate(pockets):

        pygame.gfxdraw.filled_circle(
            screen,
            p[0],
            p[1],
            6,
            RED
        )

    # =====================================================
    # 🎯 DRAW WHITE
    # =====================================================

    if stable_white:

        pygame.gfxdraw.aacircle(
            screen,
            int(stable_white[0]),
            int(stable_white[1]),
            BALL_RADIUS,
            WHITE
        )

    # =====================================================
    # 🎯 DRAW TARGET
    # =====================================================

    if stable_target:

        pygame.gfxdraw.aacircle(
            screen,
            int(stable_target[0]),
            int(stable_target[1]),
            BALL_RADIUS,
            ORANGE
        )

    # =====================================================
    # 🎯 AIM SYSTEM
    # =====================================================

    if stable_white and stable_target:

        selected_pocket = pockets[0]

        for p in pockets:

            if distance(stable_target,p) < distance(stable_target,selected_pocket):
                selected_pocket = p

        ghost = ghost_ball(
            stable_target,
            selected_pocket
        )

        draw_3lines(
            screen,
            stable_white,
            ghost,
            WHITE,
            white_mode=True
        )

        draw_3lines(
            screen,
            stable_target,
            selected_pocket,
            CYAN
        )

        pygame.gfxdraw.aacircle(
            screen,
            int(ghost[0]),
            int(ghost[1]),
            BALL_RADIUS,
            WHITE
        )

    # =====================================================
    # 🎯 YOLO DEBUG
    # =====================================================

    if model is not None:

        try:

            results = model.predict(
                table,
                verbose=False,
                conf=0.4,
                device=DEVICE
            )

        except:
            pass

    # =====================================================
    # 🎯 UI
    # =====================================================

    font = pygame.font.SysFont("Arial",16,True)

    txt = font.render(
        "8BP AI TOOL - CTRL+Q EXIT | Z LOCK | X CLEAR",
        True,
        CYAN
    )

    screen.blit(txt,(20,20))

    pygame.display.update()

# =========================================================
# 🛑 EXIT
# =========================================================

camera.stop()

pygame.quit()

sys.exit()
