"""Single source of truth for the spider design pack and the reference build.

All lengths are metres; the drawing pack prints them in millimetres.
"""

import math

BODY_CENTRE_Y = 0.040
ATTACH_R = 0.032
COXA_H = 0.030
FEMUR_H = 0.074
TIBIA_H = 0.074

ATTACH_Z = 0.115
COXA_TAIL_Z = 0.112
FEMUR_TAIL_Z = 0.066
FOOT_Z = 0.0015

BODY_LENGTH = 0.180
LEG_SPAN = 0.420
STANCE_HEIGHT = 0.120

# right-hand legs; left-hand legs are mirrored about x = 0
RIGHT_ANGLES = {1: 45.0, 3: 20.0, 5: 0.0, 7: -35.0}
PHASES = {1: 0, 2: 12, 3: 6, 4: 18, 5: 12, 6: 0, 7: 18, 8: 6}
# group A (odd legs) phases 0/6/12/18; group B = A + 12

STANCE_FRAMES = 18
SWING_FRAMES = 6
CYCLE = 24

KEY_POSES = [(1, "touchdown"), (10, "mid-stance"), (18, "lift-off"), (21, "mid-swing")]

SWING_LIFT_DEG = 8.0     # coxa lift about the horizontal lateral axis
SWING_KNEE_DEG = 6.0     # extra femur lift
SWING_REACH_DEG = 9.0    # coxa yaw about world Z


def leg_direction(leg):
    """Unit vector in the XY plane for a leg's outward direction."""
    if leg % 2 == 1:
        deg = RIGHT_ANGLES[leg]
    else:
        deg = 180.0 - RIGHT_ANGLES[leg - 1]
    rad = math.radians(deg)
    return (math.cos(rad), math.sin(rad), 0.0), deg


def leg_points(leg):
    u, deg = leg_direction(leg)
    bx, by = 0.0, BODY_CENTRE_Y

    def p(radius, z):
        return (bx + radius * u[0], by + radius * u[1], z)

    attach = p(ATTACH_R, ATTACH_Z)
    coxa_tail = p(ATTACH_R + COXA_H, COXA_TAIL_Z)
    femur_tail = p(ATTACH_R + COXA_H + FEMUR_H, FEMUR_TAIL_Z)
    foot = p(ATTACH_R + COXA_H + FEMUR_H + TIBIA_H, FOOT_Z)
    return deg, attach, coxa_tail, femur_tail, foot


def bone_table():
    """Rows: name, parent, head xyz, tail xyz, head radius (mm), angle."""
    rows = [("body", "", (0.0, 0.0, STANCE_HEIGHT), (0.0, -0.050, STANCE_HEIGHT), 0.0, 0.0)]
    for leg in range(1, 9):
        deg, attach, coxa_tail, femur_tail, foot = leg_points(leg)
        rows.append((f"leg_{leg:02d}_coxa", "body", attach, coxa_tail, ATTACH_R, deg))
        rows.append((f"leg_{leg:02d}_femur", f"leg_{leg:02d}_coxa", coxa_tail, femur_tail, 0.0, deg))
        rows.append((f"leg_{leg:02d}_tibia", f"leg_{leg:02d}_femur", femur_tail, foot, 0.0, deg))
    return rows


def stance_window(leg):
    """Cycle frames [start, end] (0-based, inclusive) in which the foot is down."""
    p = PHASES[leg]
    return p, (p + STANCE_FRAMES - 1) % CYCLE


def is_stance(leg, t):
    p = PHASES[leg]
    return ((t - p) % CYCLE) < STANCE_FRAMES


def foot_at_rest(leg):
    return leg_points(leg)[4]


def span_feet():
    xs = [foot_at_rest(leg)[0] for leg in range(1, 9)]
    return max(xs) - min(xs)
