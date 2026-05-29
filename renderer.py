import pygame
import pygame.gfxdraw

WHITE = (255,255,255)
CYAN = (0,255,255)
GREEN = (0,255,0)

def draw_aaline(screen, start, end, color, thickness=1):

    pygame.draw.aaline(screen, color, start, end)

def draw_ball(screen, x, y, r, color):

    pygame.gfxdraw.aacircle(screen, int(x), int(y), r, color)
    pygame.gfxdraw.filled_circle(screen, int(x), int(y), r-1, color)

def draw_bank_point(screen, x, y):

    pygame.gfxdraw.aacircle(screen, int(x), int(y), 8, CYAN)
