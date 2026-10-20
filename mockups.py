"""Procedural mockups drawn with Pillow (no template files). Clean and stylised: great for quick client previews, not photo-real."""
import colorsys
from collections import Counter
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 2400, 1600
KINDS = ["business-card", "poster-frame", "phone", "browser", "signboard", "logo-board"]
SETS = {"logo": ["logo-board", "business-card", "signboard", "phone"],
        "poster": ["poster-frame", "phone"], "website": ["browser", "phone", "poster-frame"]}
ALL = {"logo": ["logo-board", "business-card", "signboard", "phone", "poster-frame", "browser"], "art": ["poster-frame", "phone", "browser", "business-card"]}
BG = {"business-card": (232, 226, 218), "poster-frame": (214, 208, 200), "phone": (240, 236, 230),
      "browser": (222, 226, 232), "signboard": (96, 98, 104), "logo-board": (232, 228, 222)}

def rgb(c, default):
    try: return ImageColor.getrgb(c)[:3] if c else default
    except ValueError: return default

def lum(c): return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255
def darker(c, f): return tuple(int(v * f) for v in c)

def flat(im):
    im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.getchannel("A")); return bg

def pixels(im, n=48):
    s = im.convert("RGBA"); s.thumbnail((n, n)); d = s.tobytes()
    return [(d[i], d[i + 1], d[i + 2]) for i in range(0, len(d), 4) if d[i + 3] > 128]

def mean_lum(im):
    p = pixels(im); return sum(lum(c) for c in p) / len(p) if p else .5

def trim(logo):
    """Crop transparent margins. An opaque logo on a white background gets its white knocked out."""
    im = logo.convert("RGBA"); a = im.getchannel("A")
    if a.getextrema()[0] > 250:
        corners = [im.getpixel(p)[:3] for p in ((0, 0), (im.width - 1, 0), (0, im.height - 1), (im.width - 1, im.height - 1))]
        if all(min(c) >= 235 for c in corners):
            m = ImageChops.darker(ImageChops.darker(im.getchannel("R"), im.getchannel("G")), im.getchannel("B"))
            im.putalpha(m.point(lambda p: min(255, int((255 - p) * 2.2))))
    bb = im.getchannel("A").point(lambda p: 255 if p > 8 else 0).getbbox()
    return im.crop(bb) if bb else im

def dominant(im, knock=True):
    src = trim(im) if knock else im
    best, score = None, 0
    for c, n in Counter((r // 16 * 16, g // 16 * 16, b // 16 * 16) for r, g, b in pixels(src, 64)).most_common(14):
        h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in c])
        if s > .25 and .2 < v < .98 and n > score: best, score = c, n
    return best or (31, 41, 55)

def mono(im, c):
    o = Image.new("RGBA", im.size, tuple(c) + (255,)); o.putalpha(im.getchannel("A")); return o

def fit_logo(lg, fc):
    """Keep the logo's own colours if they read on this background, otherwise use a one-colour version."""
    if abs(lum(fc) - mean_lum(lg)) > .45: return lg
    return mono(lg, (255, 255, 255) if lum(fc) < .6 else (26, 26, 26))

def face(d, size, mode, color=None, top=False):
    if mode != "logo":
        return ImageOps.fit(flat(d), size, Image.LANCZOS, centering=(.5, 0 if top else .5)).convert("RGBA")
    fc = color or (255, 255, 255); f = Image.new("RGBA", size, fc + (255,)); lg = trim(d)
    s = min(size[0] * .58 / lg.width, size[1] * .5 / lg.height)
    lg = fit_logo(lg.resize((max(1, int(lg.width * s)), max(1, int(lg.height * s))), Image.LANCZOS), fc)
    f.alpha_composite(lg, ((size[0] - lg.width) // 2, (size[1] - lg.height) // 2)); return f

def scene(bg, size=(W, H)):
    base, edge = Image.new("RGB", size, bg), Image.new("RGB", size, darker(bg, .8))
    m = Image.radial_gradient("L").resize(size, Image.BICUBIC).point(lambda p: int(p * .9))
    return Image.composite(edge, base, m).convert("RGBA")

def smask(size, r):
    s = 3; m = Image.new("L", (size[0] * s, size[1] * s), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] * s - 1, size[1] * s - 1), r * s, fill=255); return m.resize(size, Image.LANCZOS)

def rnd(im, r):
    im = im.convert("RGBA"); im.putalpha(ImageChops.multiply(im.getchannel("A"), smask(im.size, r))); return im

def disc(r, color):
    s = 4 if r < 100 else 2; m = Image.new("L", (2 * r * s, 2 * r * s), 0); ImageDraw.Draw(m).ellipse((0, 0, 2 * r * s - 1, 2 * r * s - 1), fill=255)
    im = Image.new("RGBA", (2 * r, 2 * r), tuple(color) + (255,)); im.putalpha(m.resize((2 * r, 2 * r), Image.LANCZOS)); return im

def put(base, layer, center, angle=0, blur=45, off=(0, 35), op=.4):
    if angle: layer = layer.rotate(angle, Image.BICUBIC, expand=True)
    x, y = int(center[0] - layer.width / 2), int(center[1] - layer.height / 2); pad = blur * 3
    sh = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    sh.paste((0, 0, 0, 255), (pad, pad), layer.getchannel("A").point(lambda p: int(p * op)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.paste(sh, (x - pad + off[0], y - pad + off[1]), sh); base.paste(layer, (x, y), layer)

def font(n):
    try: return ImageFont.load_default(size=n)
    except Exception: return ImageFont.load_default()

def spot(size, strength):
    """Soft light that fades to exactly zero before the edge of its box (no visible rectangle)."""
    return Image.radial_gradient("L").resize(size, Image.BICUBIC).point(lambda p: int(max(0, 255 - p * 1.42) * strength))

def vgrad(size, c1, c2):
    m = Image.linear_gradient("L").resize(size, Image.BICUBIC)
    return Image.composite(Image.new("RGB", size, c2), Image.new("RGB", size, c1), m).convert("RGBA")

# ---- kinds: each takes (design, back, bg, brand, mode) and returns an RGBA scene ----
def business_card(d, b, bg, brand, mode):
    base, cw, ch = scene(bg), 1100, 660
    if mode == "logo": f, bk = face(d, (cw, ch), "logo", brand), face(d, (cw, ch), "logo", (255, 255, 255))
    else: f, bk = face(d, (cw, ch), "art"), (face(b, (cw, ch), "art") if b is not None else None)
    if bk is not None:
        put(base, rnd(bk, 22), (W * .40, H * .42), -9); put(base, rnd(f, 22), (W * .60, H * .58), 6)
    else:
        for i in (3, 2, 1): put(base, rnd(Image.new("RGBA", (cw, ch), (245, 245, 245, 255)), 22), (W / 2 + i * 8, H / 2 + i * 8), -5, 12, (0, 6), .2)
        put(base, rnd(f, 22), (W / 2, H / 2), -5)
    return base

def poster_frame(d, b, bg, brand, mode):
    base = scene(bg)
    if mode == "logo": aw, ah = 780, 1040
    else:
        ar = max(.55, min(d.width / d.height, 1.7)); aw, ah = (1300, int(1300 / ar)) if ar >= 1 else (int(1000 * ar), 1000)
    art = face(d, (aw, ah), mode, brand); mat, fr = 70, 28; tw, th = aw + 2 * (mat + fr), ah + 2 * (mat + fr)
    glow = spot((1800, 1800), .22)
    base.paste((255, 255, 255, 255), (W // 2 - 900, -700), glow)
    f = Image.new("RGBA", (tw, th), (28, 28, 30, 255)); f.paste((250, 249, 247, 255), (fr, fr, tw - fr, th - fr)); f.paste(art, (fr + mat, fr + mat))
    put(base, f, (W / 2, H / 2 + 20), 0, 55, (25, 45), .45); return base

def phone(d, b, bg, brand, mode):
    base, pw, ph = scene(bg), 640, 1320
    base.alpha_composite(disc(640, brand), (W // 2 - 640, H // 2 - 640))
    rim = rnd(Image.new("RGBA", (pw, ph), (88, 89, 94, 255)), 108)
    blk = rnd(Image.new("RGBA", (pw - 12, ph - 12), (10, 10, 12, 255)), 100); rim.paste(blk, (6, 6), blk)
    sw, sh = pw - 44, ph - 44; scr = face(d, (sw, sh), mode, (255, 255, 255) if mode == "logo" else None)
    gl = Image.new("RGBA", (sw, sh), (0, 0, 0, 0)); ImageDraw.Draw(gl).polygon([(0, 0), (int(sw * .6), 0), (0, int(sh * .42))], fill=(255, 255, 255, 26)); scr.alpha_composite(gl)
    scr = rnd(scr, 84); rim.paste(scr, (22, 22), scr)
    isl = rnd(Image.new("RGBA", (176, 50), (0, 0, 0, 255)), 25); rim.paste(isl, ((pw - 176) // 2, 44), isl)
    put(base, rim, (W / 2, H / 2 + 10), 7, 60, (40, 60), .45); return base

def browser(d, b, bg, brand, mode):
    base, ww, wh, bar = scene(bg), 1900, 1180, 84
    win = Image.new("RGBA", (ww, wh), (255, 255, 255, 255)); dr = ImageDraw.Draw(win); dr.rectangle((0, 0, ww, bar), fill=(236, 236, 238, 255))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): win.alpha_composite(disc(14, c), (34 + i * 44, 28))
    win.paste(rnd(Image.new("RGBA", (ww - 520, bar - 40), (255, 255, 255, 255)), 20), (260, 20))
    win.paste(face(d, (ww, wh - bar), mode, brand, top=True), (0, bar))
    put(base, rnd(win, 30), (W / 2, H / 2 + 20), 0, 70, (0, 60), .45); return base

def signboard(d, b, bg, brand, mode):
    base = scene(bg); base = Image.blend(base, Image.effect_noise((W, H), 22).convert("RGBA"), .05)
    bw, bh, cx, cy = 1700, 560, W // 2, H // 2 + 90
    for x in (-520, 520):
        lamp = rnd(Image.new("RGBA", (200, 34), (40, 40, 44, 255)), 12); stem = Image.new("RGBA", (10, 60), (40, 40, 44, 255))
        base.paste(lamp, (cx + x - 100, cy - bh // 2 - 78), lamp); base.paste(stem, (cx + x - 5, cy - bh // 2 - 50), stem)
    frame = rnd(Image.new("RGBA", (bw, bh), (74, 76, 82, 255)), 16); inner = rnd(face(d, (bw - 60, bh - 60), "logo", brand), 8); frame.paste(inner, (30, 30), inner)
    put(base, frame, (cx, cy), 0, 50, (0, 50), .5)
    for x in (-520, 520):
        glow = spot((900, 620), .32)
        base.paste((255, 236, 200, 255), (cx + x - 450, cy - bh // 2 - 90), glow)
    return base

def logo_board(d, b, bg, brand, mode):
    tw, th, g = 760, 640, 40; size = (3 * tw + 4 * g, 2 * th + 3 * g); base = Image.new("RGBA", size, bg + (255,)); lg = trim(d); f = font(30)
    dark_c = darker(brand, .55)
    tiles = [("On white", (255, 255, 255), None), ("On black", (17, 17, 17), None), ("On brand colour", brand, None),
             ("On warm grey", (228, 222, 212), None), ("On dark gradient", (17, 17, 17), dark_c), ("Small sizes", (255, 255, 255), None)]
    for i, (label, c1, c2) in enumerate(tiles):
        t = vgrad((tw, th), c1, c2) if c2 else Image.new("RGBA", (tw, th), c1 + (255,)); dr = ImageDraw.Draw(t)
        if label == "Small sizes":
            hs = [170, 100, 56, 30]; ws = [int(lg.width * h / lg.height) for h in hs]; k = min(1, (tw - 120 - 90) / sum(ws)); x = 60
            for h, w in zip(hs, ws):
                h, w = max(8, int(h * k)), max(8, int(w * k)); l2 = fit_logo(lg.resize((w, h), Image.LANCZOS), c1); t.alpha_composite(l2, (x, th // 2 - 60 - h // 2)); x += w + 30
        else:
            s = min(tw * .6 / lg.width, th * .5 / lg.height); l2 = fit_logo(lg.resize((max(1, int(lg.width * s)), max(1, int(lg.height * s))), Image.LANCZOS), c1)
            t.alpha_composite(l2, ((tw - l2.width) // 2, (th - l2.height) // 2 - 20))
        dr.text((36, th - 70), label, font=f, fill=(255, 255, 255, 190) if lum(c1) < .55 else (30, 30, 30, 170))
        t = rnd(t, 28); base.paste(t, (g + (i % 3) * (tw + g), g + (i // 3) * (th + g)), t)
    return base

FUNCS = {"business-card": business_card, "poster-frame": poster_frame, "phone": phone, "browser": browser, "signboard": signboard, "logo-board": logo_board}

def render(kind, design, back=None, bg="", brand="", mode="art"):
    mode = "logo" if kind in ("signboard", "logo-board") else mode
    d = design.convert("RGBA"); b = back.convert("RGBA") if back else None
    br = rgb(brand, None) or dominant(d, knock=(mode == "logo"))
    return FUNCS[kind](d, b, rgb(bg, BG[kind]), br, mode).convert("RGB")
