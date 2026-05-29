import math

def ghost_ball(target, pocket, radius):

    dx = target[0] - pocket[0]
    dy = target[1] - pocket[1]

    dist = math.hypot(dx, dy)

    if dist == 0:
        return target

    ratio = (dist + radius * 2) / dist

    return (
        pocket[0] + dx * ratio,
        pocket[1] + dy * ratio
    )

def calculate_bank(target, pocket, bounds, side):

    left, top, right, bottom = bounds

    if side == "top":
        mirror = (pocket[0], top - (pocket[1] - top))

    elif side == "bottom":
        mirror = (pocket[0], bottom + (bottom - pocket[1]))

    elif side == "left":
        mirror = (left - (pocket[0] - left), pocket[1])

    else:
        mirror = (right + (right - pocket[0]), pocket[1])

    tx, ty = target
    mx, my = mirror

    if side in ["top", "bottom"]:

        yb = top if side == "top" else bottom

        bx = tx + (mx - tx) * ((yb - ty) / (my - ty))

        return bx, yb

    xb = left if side == "left" else right

    by = ty + (my - ty) * ((xb - tx) / (mx - tx))

    return xb, by
