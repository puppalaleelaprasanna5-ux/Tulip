
import math
import random
import pygame

pygame.init()

# ==================================================
# THE WHOLE LIFE OF A LILY - A GLOWING PARTICLE BLOOM
# ==================================================

WIDTH, HEIGHT = 900, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Whole Life of a Lily")
clock = pygame.time.Clock()

GROUND = 705
STEM_BASE = GROUND - 22
STEM_X = 470
FLOWER_TOP = 330
SPIN_START = 10.6    # the lily starts turning once fully open
SPIN_SPEED = 0.45    # radians per second

# The camera looks very slightly down onto the plant
TILT = math.radians(24)
COS_T, SIN_T = math.cos(TILT), math.sin(TILT)

DEEP_PINK = (235, 40, 150)
VIOLET = (220, 110, 235)
PALE = (248, 220, 255)
LILAC = (205, 175, 255)
MINT = (165, 255, 160)
DARK_GREEN = (30, 125, 70)
ANTHER = (255, 150, 40)
GOLD = (255, 210, 90)   # warm golden-yellow for the petal and leaf tips

rng = random.Random(7)
start_time = pygame.time.get_ticks()

# Everything that glows is drawn here, then added onto the sky
scene = pygame.Surface((WIDTH, HEIGHT))


def clamp(v):
    return max(0.0, min(1.0, v))


def ease(v):
    v = clamp(v)
    return v * v * (3 - 2 * v)


def mix(c1, c2, t):
    t = clamp(t)
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def shade(c, k):
    return (
        max(0, min(255, int(c[0] * k))),
        max(0, min(255, int(c[1] * k))),
        max(0, min(255, int(c[2] * k))),
    )


def scale(c, k):
    # Fast brightness scale for colors already known to be in range
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k))


def dot(x, y, color, size):
    scene.fill(color, (int(x), int(y), size, size))


def project(x0, y0, X, Y, Z):
    # 3D offset (X right, Y up, Z toward viewer) to screen position
    return x0 + X, y0 - Y * COS_T + Z * SIN_T


def make_glow(radius, color, strength):
    sprite = pygame.Surface((radius * 2, radius * 2))

    for r in range(radius, 0, -2):
        k = (1 - r / radius) ** 2 * strength
        pygame.draw.circle(sprite, shade(color, k), (radius, radius), r)

    return sprite


def add_glow(sprite, x, y, k):
    if k <= 0.02:
        return

    tinted = sprite.copy()
    tinted.fill(shade((255, 255, 255), k), special_flags=pygame.BLEND_MULT)
    half = sprite.get_width() // 2
    scene.blit(tinted, (int(x - half), int(y - half)),
               special_flags=pygame.BLEND_ADD)


def make_background():
    bg = pygame.Surface((WIDTH, HEIGHT))

    # Deep night gradient, a little bluer near the ground
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = (int(5 + 12 * t), int(7 + 12 * t), int(18 + 42 * t))
        pygame.draw.line(bg, color, (0, y), (WIDTH, y))

    halo = make_glow(380, (30, 40, 120), 0.55)
    bg.blit(halo, (STEM_X - 380, 470 - 380), special_flags=pygame.BLEND_ADD)
    return bg


background = make_background()
flower_glow = make_glow(130, (255, 70, 180), 0.6)
pistil_glow = make_glow(30, (140, 255, 190), 1.0)
anther_glow = make_glow(16, ANTHER, 1.0)

# --------------------------------------------------
# Stable particle seeds keep every shape recognizable
# --------------------------------------------------

stars = [
    (rng.randrange(WIDTH), rng.randrange(HEIGHT),
     rng.uniform(0, 6.28), rng.choice([1, 1, 1, 2]))
    for _ in range(140)
]

stem_seeds = [
    (rng.random(), rng.gauss(0, 0.45), rng.choice([1, 1, 2]),
     rng.uniform(0, 6.28))
    for _ in range(480)
]

# (attach fraction, azimuth, rise, arch, twist, length, width, appears at)
# Each leaf leaves the stem rising, arches over so its tip dips,
# and is twisted so the blade is seen at a slant
LEAVES = [
    (0.10, 195, 52, 55, 28, 200, 21, 2.0),
    (0.17, -10, 48, 50, -25, 210, 21, 2.6),
    (0.33, 165, 50, 48, 22, 160, 17, 3.4),
    (0.42, 15, 55, 52, -20, 155, 17, 4.1),
]

leaf_seeds = []
for _ in LEAVES:
    points = []
    for _ in range(300):
        u = rng.uniform(-1, 1)
        t = rng.random()

        # Bright edges and midrib, darker body
        edge = abs(u)
        light = 0.45 + 0.55 * max(edge ** 3, 1 - edge * 6)
        cr, cg, cb = shade(mix(DARK_GREEN, MINT, light), 0.55 + 0.45 * light)

        # Per-point constants computed once here, not on every frame
        profile = math.sin(math.pi * t ** 0.75) ** 0.8 * (1 + 0.07 * math.sin(t * 22))
        c05, s05 = math.cos(0.5 * t), math.sin(0.5 * t)
        gold_grad = clamp(t) ** 1.8

        # Softer gold on the leaves (0.7), as a precomputed colour delta
        dr = (GOLD[0] - cr) * 0.7
        dg = (GOLD[1] - cg) * 0.7
        db = (GOLD[2] - cb) * 0.7

        points.append((t, u, rng.choice([1, 1, 2]), rng.uniform(0, 6.28),
                       profile, c05, s05, gold_grad, cr, cg, cb, dr, dg, db))
    leaf_seeds.append(points)

# Six identical petals, evenly spaced around the centre for full symmetry
N_PETALS = 6
PETAL_AZ = [math.radians(30 + i * 60) for i in range(N_PETALS)]
PETAL_LEN = 192
PETAL_WID = 54
PETAL_BRIGHT = 1.0
# Each petal dips down a little, one after another
PETAL_DROOP = math.radians(13)

# Blooming timing — each petal unfolds a little after the one before
OPEN_START, OPEN_DUR, PETAL_STAGGER = 6.4, 4.2, 0.28


def petal_color(t, u):
    color = mix(DEEP_PINK, VIOLET, t * 2.2)
    color = mix(color, PALE, (t - 0.5) * 2.0)

    # Lighter rims and a pale streak down the middle catch the light
    if abs(u) > 0.85 or abs(u) < 0.06:
        color = mix(color, PALE, 0.45)

    return shade(color, 1)


# One shared particle set, drawn for every petal, so all six are identical.
# Stratified placement (grid + jitter) spreads particles evenly for smooth,
# tulip-like edges, and every per-point constant is computed once, not per frame.
petal_pts = []
petal_phases = []
N_T, N_U = 24, 12
for it in range(N_T):
    for iu in range(N_U):
        t = (it + rng.uniform(0.15, 0.85)) / N_T
        u = (iu + rng.uniform(0.15, 0.85)) / N_U * 2.0 - 1.0

        # Smooth, elongated tulip blade: narrow base, rounded body, soft tip
        profile = math.sin(math.pi * t) ** 0.6 * (1.0 - 0.18 * t)
        gold_grad = clamp(t) ** 1.8
        size = 2 if rng.random() < 0.22 else 1
        phase = rng.uniform(0, 6.28)

        cr, cg, cb = petal_color(t, u)
        # Gold delta precomputed: final colour = base + delta * (gild * gold_grad)
        dr, dg, db = GOLD[0] - cr, GOLD[1] - cg, GOLD[2] - cb

        petal_pts.append((t, u, size, phase, profile, gold_grad,
                          cr, cg, cb, dr, dg, db))
        petal_phases.append(phase)

ground_seeds = []
for _ in range(2200):
    x = rng.uniform(0, WIDTH)
    mound = 18 + 34 * math.exp(-((x - STEM_X) / 250) ** 2)
    depth = abs(rng.gauss(0, 1)) * 45
    top_light = 1 - clamp(depth / 50)
    color = shade(mix((90, 60, 170), (215, 160, 255), top_light),
                  0.35 + 0.55 * top_light)
    ground_seeds.append((x, GROUND + 22 - mound + depth, color,
                         rng.choice([1, 1, 2]), rng.uniform(0, 6.28)))

# Most of the ground is still, so it is drawn once; a few motes twinkle
ground_layer = pygame.Surface((WIDTH, HEIGHT))
for x, y, color, size, phase in ground_seeds:
    ground_layer.fill(scale(color, 0.8), (int(x), int(y), size, size))
twinkling = ground_seeds[::8]

# (center x, center y, radius, spin speed)
CIRCLES = [
    (STEM_X, 400, 265, 0.05),
    (330, 300, 120, -0.09),
    (280, 560, 175, 0.07),
    (660, 560, 165, -0.06),
    (735, 360, 120, 0.08),
]

# Each ring's dashes precomputed as unit (cos, sin) pairs, so the spinning
# animation needs no trig per dot — just a cheap rotation each frame.
CIRCLE_DOTS = []
for _cx, _cy, _radius, _speed in CIRCLES:
    _count = int(2 * math.pi * _radius / 7)
    _dots = []
    for _k in range(_count):
        if _k % 9 >= 5:        # short dashes: 5 dots on, 4 off
            continue
        _a = 2 * math.pi * _k / _count
        _dots.append((math.cos(_a), math.sin(_a)))
    CIRCLE_DOTS.append(_dots)

dust = []


# --------------------------------------------------
# Life cycle: sprout, leaves, bud, bloom, then the flower turns forever
# --------------------------------------------------

def life_stage(age):
    spin_time = max(0.0, age - SPIN_START)
    return {
        "growth": ease((age - 0.5) / 4.6),
        "bud": ease((age - 4.4) / 2.0),
        "opening": ease((age - 6.4) / 4.2),
        "stamens": ease((age - 8.8) / 1.8),
        # Once the lily has opened and begun to turn, a warm gold slowly gilds it
        "gild": ease((age - 12.5) / 3.2),
        # Eases into a steady turn instead of starting with a jolt
        "spin": SPIN_SPEED * (spin_time - 1.5 + 1.5 * math.exp(-spin_time / 1.5)),
    }


def stem_point(s, growth, elapsed):
    height = (STEM_BASE - FLOWER_TOP) * growth
    y = STEM_BASE - height * s
    x = (STEM_X + 6 * math.sin(s * 2.4)
         + math.sin(elapsed * 0.9) * 6 * s * s * growth)
    return x, y


def arc_point(length, e0, curl, t):
    # Distance out and height of a curve whose angle bends steadily
    angle = e0 - curl * t
    out = length * (math.sin(e0) - math.sin(angle)) / curl
    up = length * (math.cos(angle) - math.cos(e0)) / curl
    return out, up


# --------------------------------------------------
# Drawing
# --------------------------------------------------

def draw_stars(elapsed):
    fill = scene.fill
    msin = math.sin
    for sx, sy, phase, size in stars:
        k = 0.25 + 0.35 * (0.5 + 0.5 * msin(elapsed * 1.4 + phase))
        fill((int(170 * k), int(180 * k), int(255 * k)), (sx, sy, size, size))


def draw_circles(elapsed, alpha):
    if alpha <= 0:
        return

    fill = scene.fill
    mcos, msin = math.cos, math.sin
    l0, l1, l2 = LILAC

    for (cx, cy, radius, speed), dots in zip(CIRCLES, CIRCLE_DOTS):
        spin = elapsed * speed
        cs, sn = mcos(spin), msin(spin)
        off = spin - elapsed * 0.6 - cx
        co, so = mcos(off), msin(off)

        for cb, sb in dots:
            # Rotate the unit dot by the current spin (no trig in the loop)
            x = cx + radius * (cb * cs - sb * sn)
            y = cy + radius * (sb * cs + cb * sn)

            # A brighter streak travels slowly around each ring
            head = cb * co - sb * so
            if head < 0.0:
                head = 0.0
            # Fine 1px dots throughout, a touch softer, for a delicate ring
            kl = (0.45 + 0.4 * head ** 6) * alpha
            fill((int(l0 * kl), int(l1 * kl), int(l2 * kl)),
                 (int(x), int(y), 1, 1))


def draw_ground(elapsed):
    scene.blit(ground_layer, (0, 0), special_flags=pygame.BLEND_ADD)

    fill = scene.fill
    msin = math.sin
    for x, y, color, size, phase in twinkling:
        shimmer = 0.5 + 0.5 * msin(elapsed * 2 + phase)
        fill((int(color[0] * shimmer), int(color[1] * shimmer), int(color[2] * shimmer)),
             (int(x), int(y), size, size))


def draw_stem(st, elapsed):
    growth = st["growth"]
    if growth <= 0:
        return

    fill = scene.fill
    msin = math.sin
    g0, g1, g2 = DARK_GREEN
    dg0, dg1, dg2 = MINT[0] - g0, MINT[1] - g1, MINT[2] - g2

    for t, u, size, phase in stem_seeds:
        x, y = stem_point(t, growth, elapsed)
        width = 3.4 - 1.4 * t
        light = 0.5 + 0.5 * msin(phase + elapsed * 2)
        fill((int(g0 + dg0 * light), int(g1 + dg1 * light), int(g2 + dg2 * light)),
             (int(x + u * width), int(y), size, size))


_leaf_cache = [None] * len(LEAVES)


def build_leaf_cache(leaf, seeds):
    # A fully-grown, fully-gilded leaf has a fixed local shape and colour, so
    # its point offsets (relative to the moving attach point) are cached once.
    fraction, azimuth, rise, arch, twist, length, width, appears = leaf
    az = math.radians(azimuth)
    ca, sa = math.cos(az), math.sin(az)
    e0 = math.radians(rise)
    curl = math.radians(arch)
    if abs(curl) < 0.01:
        curl = 0.01
    sin_e0, cos_e0 = math.sin(e0), math.cos(e0)
    inv_curl = 1.0 / curl
    ctw, stw = math.cos(math.radians(twist)), math.sin(math.radians(twist))
    facing = 0.8 + 0.2 * sa

    out = []
    for t, u, size, phase, profile, c05, s05, gold_grad, cr, cg, cb, dr, dg, db in seeds:
        angle = e0 - curl * t
        sin_a, cos_a = math.sin(angle), math.cos(angle)
        o = length * (sin_e0 - sin_a) * inv_curl
        up = length * (cos_a - cos_e0) * inv_curl
        across = u * width * profile
        cos_tw = ctw * c05 - stw * s05
        sin_tw = stw * c05 + ctw * s05
        flat = across * cos_tw
        sideways = across * sin_tw
        r = o - flat * sin_a
        X = r * ca - sideways * sa
        Z = r * sa + sideways * ca
        Y = up + flat * cos_a
        YZ = -Y * COS_T + Z * SIN_T          # vertical screen offset, precomputed
        g = gold_grad                        # gild == 1 at the steady state
        out.append((X, YZ, size, phase, facing,
                    cr + dr * g, cg + dg * g, cb + db * g))
    return out


def draw_leaf(idx, leaf, seeds, st, age, elapsed):
    fraction, azimuth, rise, arch, twist, length, width, appears = leaf
    progress = ease((age - appears) / 2.2)

    if progress <= 0:
        return

    ax, ay = stem_point(fraction, st["growth"], elapsed)

    # Steady state: reuse the cached shape and colour, no trig per particle
    if progress >= 0.999 and st["gild"] >= 0.999:
        cache = _leaf_cache[idx]
        if cache is None:
            cache = _leaf_cache[idx] = build_leaf_cache(leaf, seeds)
        fill = scene.fill
        msin = math.sin
        e25 = elapsed * 2.5
        for X, YZ, size, phase, facing, fr, fg, fb in cache:
            k = (0.85 + 0.15 * msin(e25 + phase)) * facing
            fill((int(fr * k), int(fg * k), int(fb * k)),
                 (int(ax + X), int(ay + YZ), size, size))
        return

    az = math.radians(azimuth)
    ca, sa = math.cos(az), math.sin(az)

    # A young leaf hugs the stem, then leans out and arches as it grows
    sway = math.sin(elapsed * 1.1 + fraction * 9) * 0.06
    e0 = math.radians(90 - (90 - rise) * progress)
    curl = math.radians(arch) * progress + sway
    if abs(curl) < 0.01:
        curl = 0.01

    sin_e0, cos_e0 = math.sin(e0), math.cos(e0)
    inv_curl = 1.0 / curl
    leaf_len = length * progress
    half_w = width * progress
    ctw, stw = math.cos(math.radians(twist)), math.sin(math.radians(twist))
    facing = 0.8 + 0.2 * sa
    gild = st["gild"]
    g_on = gild > 0
    fill = scene.fill
    msin, mcos = math.sin, math.cos

    for t, u, size, phase, profile, c05, s05, gold_grad, cr, cg, cb, dr, dg, db in seeds:
        angle = e0 - curl * t
        sin_a, cos_a = msin(angle), mcos(angle)
        out = leaf_len * (sin_e0 - sin_a) * inv_curl
        up = leaf_len * (cos_a - cos_e0) * inv_curl
        across = u * half_w * profile

        # The blade turns a little more toward its tip (angle-addition identity)
        cos_tw = ctw * c05 - stw * s05
        sin_tw = stw * c05 + ctw * s05
        flat = across * cos_tw
        sideways = across * sin_tw

        r = out - flat * sin_a
        X = r * ca - sideways * sa
        Z = r * sa + sideways * ca
        Y = up + flat * cos_a

        x = ax + X
        y = ay - Y * COS_T + Z * SIN_T
        k = (0.85 + 0.15 * msin(elapsed * 2.5 + phase)) * facing

        # Warm gold blends in softly toward the leaf tip, fading to green inward
        if g_on:
            g = gild * gold_grad
            fill((int((cr + dr * g) * k), int((cg + dg * g) * k), int((cb + db * g) * k)),
                 (int(x), int(y), size, size))
        else:
            fill((int(cr * k), int(cg * k), int(cb * k)), (int(x), int(y), size, size))


def draw_petal(i, bx, by, spin, size_scale, age, elapsed, nod, gild):
    # Each petal unfolds smoothly from its base, a little after the one before
    po = ease((age - OPEN_START - i * PETAL_STAGGER) / OPEN_DUR)
    if po <= 0:
        return

    # A gentle, even sway once open — smooth, no jitter or sudden transitions
    sway = math.radians(5) * math.sin(elapsed * 1.1 - i * 1.05) * po
    az = PETAL_AZ[i] + spin + sway
    ca, sa = math.cos(az), math.sin(az)

    # This petal's own downward dip, staggered after the previous one
    pn = nod + PETAL_DROOP * (0.5 + 0.5 * math.sin(elapsed * 0.7 - i * 1.05)) * po
    nod_c, nod_s = math.cos(pn), math.sin(pn)

    p_len = PETAL_LEN * size_scale * (0.6 + 0.4 * po)
    p_wid = PETAL_WID * size_scale * (0.55 + 0.45 * po)
    base = 4 + 5 * po

    # Closed bud curls its tips in; the open petal rotates smoothly outward
    e0 = math.radians(82 - 27 * po)
    curl = math.radians(-16 + 91 * po)
    if abs(curl) < 0.01:
        curl = 0.01
    sin_e0, cos_e0 = math.sin(e0), math.cos(e0)
    inv_curl = 1.0 / curl

    facing = PETAL_BRIGHT * (0.82 + 0.18 * (0.5 + 0.5 * sa))
    flicker = elapsed * 3 + i
    g_on = gild > 0
    fill = scene.fill
    msin, mcos = math.sin, math.cos

    for t, u, p_size, phase, profile, gold_grad, cr, cg, cb, dr, dg, db in petal_pts:
        angle = e0 - curl * t
        out = base + p_len * (sin_e0 - msin(angle)) * inv_curl
        up = p_len * (mcos(angle) - cos_e0) * inv_curl
        across = u * p_wid * profile

        X = out * ca - across * sa
        Z = out * sa + across * ca
        # The whole bloom nods toward the viewer as it turns
        up_t = up * nod_c - Z * nod_s
        Z_t = up * nod_s + Z * nod_c
        x = bx + X
        y = by - up_t * COS_T + Z_t * SIN_T

        k = facing * (0.8 + 0.2 * msin(flicker + phase))

        # Warm gold grows toward the tip, blending into the pink/violet inward
        if g_on:
            g = gild * gold_grad
            fill((int((cr + dr * g) * k), int((cg + dg * g) * k), int((cb + db * g) * k)),
                 (int(x), int(y), p_size, p_size))
        else:
            fill((int(cr * k), int(cg * k), int(cb * k)),
                 (int(x), int(y), p_size, p_size))


# At the fully-open steady state every petal shares one identical local shape,
# so it is built once and cached; only the cheap rotation and the per-frame
# flicker change after that — no trigonometry runs per particle.
_petal_shape = None


def build_petal_shape(po, size_scale):
    p_len = PETAL_LEN * size_scale * (0.6 + 0.4 * po)
    p_wid = PETAL_WID * size_scale * (0.55 + 0.45 * po)
    base = 4 + 5 * po
    e0 = math.radians(82 - 27 * po)
    curl = math.radians(-16 + 91 * po)
    if abs(curl) < 0.01:
        curl = 0.01
    sin_e0, cos_e0 = math.sin(e0), math.cos(e0)
    inv_curl = 1.0 / curl

    shape = []
    for t, u, size, phase, profile, gold_grad, cr, cg, cb, dr, dg, db in petal_pts:
        angle = e0 - curl * t
        out = base + p_len * (sin_e0 - math.sin(angle)) * inv_curl
        up = p_len * (math.cos(angle) - cos_e0) * inv_curl
        across = u * p_wid * profile
        shape.append((out, up, across, size, gold_grad, cr, cg, cb, dr, dg, db))
    return shape


def draw_petal_fast(i, bx, by, spin, elapsed, nod, gild, shape, bright):
    sway = math.radians(5) * math.sin(elapsed * 1.1 - i * 1.05)
    az = PETAL_AZ[i] + spin + sway
    ca, sa = math.cos(az), math.sin(az)
    # This petal's own downward dip, staggered after the previous one
    pn = nod + PETAL_DROOP * (0.5 + 0.5 * math.sin(elapsed * 0.7 - i * 1.05))
    nod_c, nod_s = math.cos(pn), math.sin(pn)
    facing = PETAL_BRIGHT * (0.82 + 0.18 * (0.5 + 0.5 * sa))
    fill = scene.fill

    idx = 0
    for out, up, across, size, gold_grad, cr, cg, cb, dr, dg, db in shape:
        X = out * ca - across * sa
        Z = out * sa + across * ca
        up_t = up * nod_c - Z * nod_s
        Z_t = up * nod_s + Z * nod_c
        x = bx + X
        y = by - up_t * COS_T + Z_t * SIN_T

        k = facing * bright[idx]
        idx += 1
        g = gild * gold_grad
        fill((int((cr + dr * g) * k), int((cg + dg * g) * k), int((cb + db * g) * k)),
             (int(x), int(y), size, size))


def draw_stamens(bx, by, spin, grow, elapsed, nod_c, nod_s):
    if grow <= 0:
        return

    def place(X, up, Z):
        # Same forward nod the petals use, so the whole bloom tilts together
        up_t = up * nod_c - Z * nod_s
        Z_t = up * nod_s + Z * nod_c
        return bx + X, by - up_t * COS_T + Z_t * SIN_T

    # Six filaments tipped with glowing orange pollen
    for i in range(6):
        az = math.radians(45 + i * 60) + spin
        ca, sa = math.cos(az), math.sin(az)
        length = 128 * grow
        e0, curl = math.radians(72), math.radians(40)

        for j in range(1, 26):
            out, up = arc_point(length, e0, curl, j / 25)
            x, y = place(out * ca, up, out * sa)
            dot(x, y, (170, 145, 162), 1)

        out, up = arc_point(length, e0, curl, 1)
        x, y = place(out * ca, up, out * sa)
        pulse = 0.8 + 0.2 * math.sin(elapsed * 4 + i)
        # Stamens kept a touch softer, so the petals read as the brighter layer
        add_glow(anther_glow, x, y, grow * pulse * 0.68)

        # Fatter pollen grains at each filament tip (same size, a bit softer)
        for k in range(12):
            a = k * 2.4 + i
            dot(x + 6 * math.cos(a), y + 4 * math.sin(a),
                scale(ANTHER, grow * pulse * 0.78), 4 if k % 3 == 0 else 2)

    # Central pistil
    for j in range(1, 30):
        out, up = arc_point(140 * grow, math.radians(86), math.radians(10), j / 29)
        x, y = place(out * math.cos(spin), up, out * math.sin(spin))
        dot(x, y, (150, 185, 160), 1)

    add_glow(pistil_glow, x, y, 0.28 * grow)


def draw_flower(st, elapsed, age):
    bud = st["bud"]
    if bud <= 0:
        return

    opening = st["opening"]
    spin = st["spin"]
    gild = st["gild"]
    bx, by = stem_point(1, st["growth"], elapsed)

    add_glow(flower_glow, bx, by - 50, (0.35 + 0.65 * opening) * bud)

    # Bigger bloom, closer to the reference
    size_scale = 0.3 + 1.12 * bud

    # The open lily leans toward the viewer and gently nods as it turns
    nod = (math.radians(20) + math.radians(4) * math.sin(elapsed * 0.8)) * opening
    nod_c, nod_s = math.cos(nod), math.sin(nod)

    # Painter's order: draw the petals from the far side to the near side
    order = sorted(range(N_PETALS), key=lambda i: math.sin(PETAL_AZ[i] + spin))

    # Once every petal is fully open, all six share one cached shape (fast path)
    last_po = ease((age - OPEN_START - (N_PETALS - 1) * PETAL_STAGGER) / OPEN_DUR)
    if last_po >= 0.999 and bud >= 0.999:
        global _petal_shape
        if _petal_shape is None:
            _petal_shape = build_petal_shape(1.0, size_scale)
        e3 = elapsed * 3.0
        bright = [0.8 + 0.2 * math.sin(e3 + ph) for ph in petal_phases]
        for i in order:
            draw_petal_fast(i, bx, by, spin, elapsed, nod, gild,
                            _petal_shape, bright)
    else:
        for i in order:
            draw_petal(i, bx, by, spin, size_scale, age, elapsed, nod, gild)

    # Stamens drawn last, so they stay visible as the petals bend past them
    draw_stamens(bx, by, spin, st["stamens"], elapsed, nod_c, nod_s)


def update_dust(dt, st, elapsed):
    # Pollen motes drift up from the open lily
    if st["stamens"] > 0 and rng.random() < 0.5 * st["stamens"]:
        bx, by = stem_point(1, st["growth"], elapsed)
        dust.append([bx + rng.uniform(-90, 90), by - rng.uniform(30, 130),
                     rng.uniform(1.2, 2.6), rng.uniform(12, 32)])

    for p in dust[:]:
        p[1] -= p[3] * dt
        p[0] += math.sin(p[1] * 0.05) * 0.3
        p[2] -= dt * 0.5

        if p[2] <= 0:
            dust.remove(p)
        else:
            dot(p[0], p[1], scale((255, 190, 140), p[2] / 2.6),
                2 if p[2] > 1.8 else 1)


def add_bloom():
    # Cheap bloom: shrink the glowing layer, blow it back up, add it twice
    small = pygame.transform.smoothscale(scene, (WIDTH // 6, HEIGHT // 6))
    soft = pygame.transform.smoothscale(small, (WIDTH, HEIGHT))
    screen.blit(soft, (0, 0), special_flags=pygame.BLEND_ADD)
    screen.blit(soft, (0, 0), special_flags=pygame.BLEND_ADD)


running = True
paused = False
paused_at = 0

while running:
    dt = clock.tick(30) / 1000

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            if event.key == pygame.K_r:
                start_time = pygame.time.get_ticks()
                dust.clear()

            if event.key == pygame.K_SPACE:
                paused = not paused
                if paused:
                    paused_at = pygame.time.get_ticks()
                else:
                    start_time += pygame.time.get_ticks() - paused_at

    now = paused_at if paused else pygame.time.get_ticks()
    age = (now - start_time) / 1000
    elapsed = age
    st = life_stage(age)

    scene.fill((0, 0, 0))

    draw_stars(elapsed)
    draw_circles(elapsed, ease((age - 1.5) / 3.0))
    draw_ground(elapsed)

    # Leaves pointing away from us go behind the stem
    for idx, (leaf, seeds) in enumerate(zip(LEAVES, leaf_seeds)):
        if math.sin(math.radians(leaf[1])) < 0:
            draw_leaf(idx, leaf, seeds, st, age, elapsed)

    draw_stem(st, elapsed)

    for idx, (leaf, seeds) in enumerate(zip(LEAVES, leaf_seeds)):
        if math.sin(math.radians(leaf[1])) >= 0:
            draw_leaf(idx, leaf, seeds, st, age, elapsed)

    draw_flower(st, elapsed, age)
    update_dust(0 if paused else dt, st, elapsed)

    screen.blit(background, (0, 0))
    screen.blit(scene, (0, 0), special_flags=pygame.BLEND_ADD)
    add_bloom()

    pygame.display.flip()

pygame.quit()
